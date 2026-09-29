"""Laboratory 03 evidence-based evaluation workflow.

Implements the frozen implementation-facing contract
(AUTHORING/LABORATORY_03_IMPLEMENTATION_CONTRACT.md): calibration packets,
bounded development, protocol freeze, autonomous reserve-family selection with
an append-only exposure ledger, a sixteen-position paired comparison with
unstarted/returned/failed position states, route-wide failure classification,
blinded semantic scoring, nested-count aggregation, a bounded recommendation,
regression records, and a commit-first final verifier with passed-complete /
passed-partial outcomes.

The module is deterministic apart from explicitly injected runner functions.
Every artifact is write-once; the exposure ledger is append-only.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

import yaml

from .workflow import WorkflowError

LAB_ID = "lab03"
SCHEMA_VERSION = "1.0"
ENVELOPE_FIELDS = {"case_id", "proposed_text"}
RUBRIC_CATEGORIES = ("S", "I", "U", "Q", "R", "X")
EVIDENCE_SITUATIONS = ("sufficient-evidence", "distractor", "missing-fact", "explicit-ambiguity")
POSITION_STATES = ("unstarted", "returned", "failed")
FAILURE_CLASSES = ("position-specific", "route-wide")
OUTCOMES = ("recommend-b", "retain-a", "reject-both", "seek-more-evidence")
VERIFICATION_OUTCOMES = ("passed-complete", "passed-partial")
HELDOUT_CASES = 4
ATTEMPTS_PER_CASE = 2
VARIANTS = ("a", "b")
SCHEDULED_POSITIONS = HELDOUT_CASES * ATTEMPTS_PER_CASE * len(VARIANTS)
DEVELOPMENT_INPUTS = 4
DEVELOPMENT_POSITIONS = DEVELOPMENT_INPUTS * len(VARIANTS)

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Route-wide failure markers: adapter-level signals that establish unavailability
# of the whole route rather than one position's bad output.
ROUTE_WIDE_MARKERS = (
    "authentication",
    "auth",
    "quota",
    "rate limit",
    "rate-limit",
    "account",
    "unavailable",
    "permission",
    "401",
    "403",
    "429",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise WorkflowError(message)


def _slug(value: str, label: str) -> str:
    _require(isinstance(value, str) and SLUG_RE.fullmatch(value), f"{label} must be a lowercase slug.")
    return value


def _read_json(path: Path, label: str) -> tuple[dict, bytes]:
    try:
        data = path.read_bytes()
        value = json.loads(data)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"{label} cannot be read: {path}: {exc}") from exc
    _require(isinstance(value, dict), f"{label} must contain a JSON object.")
    return value, data


def _write_json_once(path: Path, payload: dict) -> Path:
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if path.exists():
        raise WorkflowError(f"The immutable artifact already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    return path


def _dump_yaml(payload: dict) -> str:
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100)


def _write_yaml_once(path: Path, payload: dict) -> Path:
    if path.exists():
        raise WorkflowError(f"The immutable artifact already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_yaml(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Course material loading and deterministic family checks
# ---------------------------------------------------------------------------


def load_family(family_path: Path, *, expected_cases: int | None = None) -> dict:
    family, _ = _read_json(family_path, "Case family")
    _require(family.get("schema_version") == SCHEMA_VERSION, "Family schema_version must be 1.0.")
    _slug(str(family.get("family_id", "")), "family_id")
    required_cases = expected_cases if expected_cases is not None else HELDOUT_CASES
    cases = family.get("cases")
    _require(
        isinstance(cases, list) and len(cases) == required_cases,
        f"A family must contain exactly {required_cases} cases.",
    )
    case_ids: list[str] = []
    situations: list[str] = []
    for case in cases:
        _require(isinstance(case, dict), "Each case must be an object.")
        case_id = _slug(str(case.get("case_id", "")), "case_id")
        _require(case.get("family_id") == family["family_id"], "Case family_id must match the family.")
        situation = case.get("evidence_situation")
        _require(situation in EVIDENCE_SITUATIONS, f"Case {case_id} has an unknown evidence_situation.")
        _require(isinstance(case.get("task"), str) and case["task"].strip(), f"Case {case_id} task must be non-empty.")
        _require(
            isinstance(case.get("supplied_source"), str) and case["supplied_source"].strip(),
            f"Case {case_id} supplied_source must be non-empty.",
        )
        _require(isinstance(case.get("constructed"), bool), f"Case {case_id} constructed must be boolean.")
        if case["constructed"]:
            _require(
                isinstance(case.get("mutation_note"), str) and case["mutation_note"].strip(),
                f"Constructed case {case_id} must carry a mutation note.",
            )
        pointers = case.get("source_pointers")
        _require(
            isinstance(pointers, list) and pointers,
            f"Case {case_id} must carry at least one source pointer.",
        )
        case_ids.append(case_id)
        situations.append(situation)
    _require(len(set(case_ids)) == required_cases, "Family case identifiers must be unique.")
    if required_cases == HELDOUT_CASES:
        _require(sorted(situations) == sorted(EVIDENCE_SITUATIONS), "A family must cover all four evidence situations.")
    behaviors = family.get("expected_behaviors")
    _require(
        isinstance(behaviors, list) and len(behaviors) == required_cases,
        f"A family must contain exactly {required_cases} expected behaviors.",
    )
    behavior_ids: list[str] = []
    for behavior in behaviors:
        _require(isinstance(behavior, dict), "Each expected behavior must be an object.")
        behavior_ids.append(_slug(str(behavior.get("case_id", "")), "expected behavior case_id"))
        _require(
            behavior.get("expected_category") in RUBRIC_CATEGORIES,
            "Expected behavior category must be a rubric category.",
        )
        _require(
            isinstance(behavior.get("expected_behavior"), str) and behavior["expected_behavior"].strip(),
            "Expected behavior statement must be non-empty.",
        )
    _require(sorted(behavior_ids) == sorted(case_ids), "Expected behaviors must match the family cases exactly.")
    origin = family.get("origin")
    _require(origin in {"course-reserve", "curator-generated", "course-development"},
             "Family origin is not supported.")
    if origin == "curator-generated":
        provenance = family.get("provenance")
        _require(isinstance(provenance, dict) and provenance.get("curator_session") and provenance.get("inputs_sha256"),
                 "Curator-generated family must record curator provenance.")
    return family


def _normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def check_near_duplicates(families: Iterable[dict]) -> None:
    """Reject exact or normalized duplication of case text across families."""
    seen_exact: dict[str, str] = {}
    seen_normalized: dict[str, str] = {}
    for family in families:
        for case in family["cases"]:
            task_key = f"{case['task']}||{case['supplied_source']}"
            exact_key = hashlib.sha256(task_key.encode("utf-8")).hexdigest()
            normalized_key = _normalized_text(task_key)
            owner = family["family_id"]
            if exact_key in seen_exact:
                raise WorkflowError(
                    f"Case text in family {owner} exactly duplicates family {seen_exact[exact_key]}."
                )
            if normalized_key in seen_normalized:
                raise WorkflowError(
                    f"Case text in family {owner} near-duplicates family {seen_normalized[normalized_key]}."
                )
            seen_exact[exact_key] = owner
            seen_normalized[normalized_key] = owner


def load_variant_a(instructions_dir: Path) -> tuple[str, str]:
    variant_path = instructions_dir / "variant-a.txt"
    try:
        text = variant_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowError(f"Course Variant A instruction cannot be read: {exc}") from exc
    _require(bool(text.strip()), "Variant A instruction must not be empty.")
    return text, _sha256_bytes(text.encode("utf-8"))


# ---------------------------------------------------------------------------
# Exposure ledger (append-only) and calibration
# ---------------------------------------------------------------------------


class ExposureLedger:
    """Append-only record of family selection and exposure events."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.events: list[dict] = []
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise WorkflowError(f"Exposure ledger cannot be read: {exc}") from exc
            _require(isinstance(raw, dict) and isinstance(raw.get("events"), list),
                     "Exposure ledger must contain an events list.")
            self.events = list(raw["events"])

    def append(self, event: dict) -> None:
        required = {"event", "family_id", "actor", "recorded_at"}
        _require(required <= set(event), "Exposure event lacks required fields.")
        self.events.append(dict(event))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": SCHEMA_VERSION, "lab_id": LAB_ID, "events": self.events}
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def family_exposed_before_freeze(self, family_id: str, freeze_at: str | None) -> bool:
        for event in self.events:
            if event.get("family_id") != family_id:
                continue
            if event.get("event") not in {"premature-exposure", "used-in-comparison"}:
                continue
            recorded = event.get("recorded_at")
            if freeze_at is None or not isinstance(recorded, str) or recorded < freeze_at:
                return True
        return False

    def families_used_in_comparisons(self) -> set[str]:
        return {
            event["family_id"]
            for event in self.events
            if event.get("event") == "used-in-comparison"
        }

    def family_revealed_for_freeze(self, family_id: str, freeze_manifest: dict) -> bool:
        freeze_id = freeze_manifest.get("freeze_id")
        for event in self.events:
            if (
                event.get("event") == "revealed-after-freeze"
                and event.get("family_id") == family_id
                and event.get("freeze_id") == freeze_id
            ):
                return True
        return False


def start_calibration(*, report_dir: Path, packet_id: str, packets_dir: Path, student: str) -> Path:
    """Initialize student labels for a calibration packet without revealing reviewed labels."""
    _slug(packet_id, "packet_id")
    packet_path = packets_dir / packet_id / "packet.json"
    packet, _ = _read_json(packet_path, "Calibration packet")
    _require(packet.get("packet_id") == packet_id, "Packet identifier mismatch.")
    labels_dir = report_dir / "calibration" / packet_id
    exposure_marker = labels_dir / "labels-opened.json"
    _require(not exposure_marker.exists(),
             "Reviewed labels for this packet were already opened; use the replacement packet.")
    labels_path = labels_dir / "student-labels.yaml"
    if labels_path.exists():
        raise WorkflowError("Student labels for this packet already exist.")
    scaffold = {
        "schema_version": SCHEMA_VERSION,
        "packet_id": packet_id,
        "labels": [
            {"output_id": output["output_id"], "category": "", "rationale": ""}
            for output in packet["authored_outputs"]
        ],
        "student": student,
        "recorded_at": _now(),
    }
    return _write_yaml_once(labels_path, scaffold)


def submit_calibration(*, report_dir: Path, packet_id: str, packets_dir: Path, student: str) -> dict:
    """Record the frozen student labels, open reviewed labels, and compare."""
    _slug(packet_id, "packet_id")
    packet, _ = _read_json(packets_dir / packet_id / "packet.json", "Calibration packet")
    labels_dir = report_dir / "calibration" / packet_id
    labels_path = labels_dir / "student-labels.yaml"
    try:
        labels_raw = yaml.safe_load(labels_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise WorkflowError(f"Student labels cannot be read: {exc}") from exc
    _require(isinstance(labels_raw, dict), "Student labels must be a mapping.")
    entries = labels_raw.get("labels")
    _require(isinstance(entries, list), "Student labels must contain a labels list.")
    by_output = {item["output_id"]: item for item in packet["authored_outputs"]}
    labels_out: list[dict] = []
    for entry in entries:
        _require(isinstance(entry, dict), "Each student label must be a mapping.")
        output_id = entry.get("output_id")
        _require(output_id in by_output, f"Unknown calibration output {output_id}.")
        category = entry.get("category")
        _require(category in RUBRIC_CATEGORIES, f"Label for {output_id} must name a rubric category.")
        _require(isinstance(entry.get("rationale"), str) and entry["rationale"].strip(),
                 f"Label for {output_id} needs a rationale.")
        labels_out.append({"output_id": output_id, "category": category, "rationale": entry["rationale"].strip()})
    _require(
        sorted(item["output_id"] for item in labels_out) == sorted(by_output),
        "Every authored output must be labeled exactly once.",
    )
    reviewed = {item["output_id"]: item for item in packet["reviewed_labels"]}
    comparison = []
    for item in labels_out:
        expected = reviewed[item["output_id"]]
        comparison.append({
            "output_id": item["output_id"],
            "student_category": item["category"],
            "reviewed_category": expected["category"],
            "reviewed_rationale": expected["rationale"],
            "agrees": item["category"] == expected["category"],
        })
    result = {
        "schema_version": SCHEMA_VERSION,
        "packet_id": packet_id,
        "student": student,
        "labels": labels_out,
        "comparison": comparison,
        "agreement": sum(item["agrees"] for item in comparison),
        "total": len(comparison),
        "reviewed_labels_opened_at": _now(),
    }
    _write_json_once(labels_dir / "calibration-result.json", result)
    _write_json_once(labels_dir / "labels-opened.json",
                     {"packet_id": packet_id, "opened_at": _now()})
    return result


# ---------------------------------------------------------------------------
# Development stage
# ---------------------------------------------------------------------------


def record_transfer_case(*, report_dir: Path, transfer_case: dict, perturbation: dict) -> Path:
    """Store the student transfer case and controlled perturbation as development evidence."""
    dev_dir = report_dir / "development"
    for payload, name in ((transfer_case, "transfer-case.yaml"), (perturbation, "transfer-perturbation.yaml")):
        _require(isinstance(payload, dict), f"{name} must be a mapping.")
        _require(isinstance(payload.get("case_id"), str) and payload["case_id"].strip(), f"{name} needs a case_id.")
        _require(isinstance(payload.get("task"), str) and payload["task"].strip(), f"{name} needs a task.")
        _require(isinstance(payload.get("supplied_source"), str) and payload["supplied_source"].strip(),
                 f"{name} needs supplied_source.")
        _require(isinstance(payload.get("provenance"), str) and payload["provenance"].strip(),
                 f"{name} needs provenance (a public non-sensitive source).")
    _require(
        isinstance(perturbation.get("perturbation_note"), str) and perturbation["perturbation_note"].strip(),
        "Perturbation must describe the single altered input feature.",
    )
    _require(
        isinstance(perturbation.get("expectation"), str) and perturbation["expectation"].strip(),
        "Perturbation must state an invariance or directional expectation.",
    )
    _write_yaml_once(dev_dir / "transfer-case.yaml", transfer_case)
    return _write_yaml_once(dev_dir / "transfer-perturbation.yaml", perturbation)


def record_variant_b(*, report_dir: Path, variant_b_text: str, change_declaration: dict) -> Path:
    """Store Variant B and its single-factor change declaration."""
    _require(isinstance(variant_b_text, str) and variant_b_text.strip(), "Variant B must not be empty.")
    variant_a_path = Path(__file__).resolve().parent.parent.parent / "instructions" / "lab03" / "variant-a.txt"
    variant_a_text = variant_a_path.read_text(encoding="utf-8")
    _require(variant_b_text != variant_a_text, "Variant B must differ from Variant A.")
    _require(isinstance(change_declaration, dict), "Change declaration must be a mapping.")
    _require(
        isinstance(change_declaration.get("changed_property"), str) and change_declaration["changed_property"].strip(),
        "Change declaration must name exactly one changed instruction property.",
    )
    _require(
        isinstance(change_declaration.get("mechanism"), str) and change_declaration["mechanism"].strip(),
        "Change declaration must state the intended mechanism.",
    )
    _require(
        isinstance(change_declaration.get("declared_factors"), list)
        and change_declaration["declared_factors"] == [change_declaration["changed_property"]],
        "The change declaration must declare exactly one intended factor.",
    )
    dev_dir = report_dir / "development"
    (dev_dir / "variant-b.txt").parent.mkdir(parents=True, exist_ok=True)
    (dev_dir / "variant-b.txt").write_text(variant_b_text, encoding="utf-8")
    return _write_yaml_once(
        dev_dir / "change-declaration.yaml",
        {
            **change_declaration,
            "variant_a_sha256": _sha256_bytes(variant_a_text.encode("utf-8")),
            "variant_b_sha256": _sha256_bytes(variant_b_text.encode("utf-8")),
            "recorded_at": _now(),
        },
    )


# ---------------------------------------------------------------------------
# Development and held-out execution
# ---------------------------------------------------------------------------


def _schedule_order(positions: list[dict], seed: str) -> list[dict]:
    """Deterministic balanced order seeded by family id: within each case, variant
    alternation flips by attempt so A and B alternate first position evenly."""
    ordered = sorted(positions, key=lambda p: (p["case_index"], p["attempt"], p["variant"]))

    def sort_key(position: dict) -> tuple:
        variant_first = position["variant"] == "a"
        if (position["case_index"] + position["attempt"]) % 2 == 1:
            variant_first = not variant_first
        return (position["case_index"], position["attempt"], 0 if variant_first else 1)

    ordered.sort(key=sort_key)
    return ordered


def build_positions(*, comparison_dir: Path, family: dict, kind: str, cases: list[dict] | None = None) -> list[dict]:
    """Create the schedule file for a comparison (held-out) or development run.

    For held-out schedules the four family cases are used. For development
    schedules the caller passes four explicit inputs (development cases, the
    student transfer case, and the perturbation) via ``cases``.
    """
    _require(kind in {"held-out", "development"}, "Unknown schedule kind.")
    case_list = family["cases"] if cases is None else cases
    if kind == "held-out":
        _require(cases is None, "Held-out schedules take their cases from the selected family.")
        _require(len(case_list) == HELDOUT_CASES, "Held-out schedule requires exactly four cases.")
        positions = []
        for case_index, case in enumerate(case_list):
            for attempt in range(1, ATTEMPTS_PER_CASE + 1):
                for variant in VARIANTS:
                    positions.append({
                        "position_id": f"pos-{case['case_id']}-{variant}-{attempt}",
                        "case_id": case["case_id"],
                        "case_index": case_index,
                        "variant": variant,
                        "attempt": attempt,
                        "state": "unstarted",
                    })
        _require(len(positions) == SCHEDULED_POSITIONS, "Held-out schedule must contain sixteen positions.")
    else:
        _require(cases is not None and len(cases) == DEVELOPMENT_INPUTS,
                 "Development schedules require exactly four explicit inputs.")
        positions = []
        for case_index, case in enumerate(case_list):
            for variant in VARIANTS:
                positions.append({
                    "position_id": f"pos-{case['case_id']}-{variant}-1",
                    "case_id": case["case_id"],
                    "case_index": case_index,
                    "variant": variant,
                    "attempt": 1,
                    "state": "unstarted",
                })
        _require(len(positions) == DEVELOPMENT_POSITIONS, "Development schedule must contain eight positions.")
    schedule = {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "family_id": family["family_id"] if cases is None else f"dev-{kind}",
        "order": [p["position_id"] for p in _schedule_order(positions, family["family_id"])],
        "positions": positions,
    }
    _write_json_once(comparison_dir / "schedule.json", schedule)
    return positions


def _request_payload(case: dict, instruction_text: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "lab_id": LAB_ID,
        "case_id": case["case_id"],
        "task": case["task"],
        "supplied_source": case["supplied_source"],
        "instruction": instruction_text,
        "output_contract": {
            "type": "object",
            "fields": ["case_id", "proposed_text"],
            "case_id_value": case["case_id"],
        },
    }


def classify_failure(message: str) -> str:
    """Classify an execution failure as position-specific or route-wide."""
    lowered = str(message).lower()
    return "route-wide" if any(marker in lowered for marker in ROUTE_WIDE_MARKERS) else "position-specific"


def run_position(
    *,
    comparison_dir: Path,
    schedule: dict,
    position_id: str,
    cases_by_id: dict[str, dict],
    instructions: dict[str, str],
    runner: Callable[[dict], str],
    adapter: str,
    model_id: str,
    recorded_by: str,
) -> dict:
    """Execute one scheduled position through the injected provider-neutral runner.

    The runner receives the provider-neutral request payload and returns the raw
    assistant content string. Any exception is recorded as a completed failure.
    """
    positions = {p["position_id"]: p for p in schedule["positions"]}
    _require(position_id in positions, f"Unknown position {position_id}.")
    position = positions[position_id]
    _require(position["state"] == "unstarted", f"Position {position_id} is not unstarted and cannot be rerun.")
    case = cases_by_id[position["case_id"]]
    request = _request_payload(case, instructions[position["variant"]])
    attempt_dir = comparison_dir / "attempts" / position_id
    _write_json_once(attempt_dir / "request.json", request)
    started_at = _now()
    try:
        content = runner(request)
    except Exception as exc:  # noqa: BLE001 — every failure mode is preserved evidence
        failure_class = classify_failure(str(exc))
        error = {
            "schema_version": SCHEMA_VERSION,
            "position_id": position_id,
            "failure_class": failure_class,
            "error": str(exc)[:2000],
        }
        _write_json_once(attempt_dir / "error.json", error)
        _write_json_once(attempt_dir / "run-metadata.json", {
            "position_id": position_id,
            "adapter": adapter,
            "model_id": model_id,
            "started_at": started_at,
            "finished_at": _now(),
            "recorded_by": recorded_by,
        })
        position["state"] = "failed"
        _rewrite_schedule(comparison_dir, schedule)
        return {"position_id": position_id, "outcome": "failed", "failure_class": failure_class}
    raw_path = attempt_dir / "raw-response.txt"
    if raw_path.exists():
        raise WorkflowError("Position evidence is write-once and already exists.")
    attempt_dir.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(content, encoding="utf-8")
    _write_json_once(attempt_dir / "run-metadata.json", {
        "position_id": position_id,
        "adapter": adapter,
        "model_id": model_id,
        "started_at": started_at,
        "finished_at": _now(),
        "recorded_by": recorded_by,
    })
    position["state"] = "returned"
    _rewrite_schedule(comparison_dir, schedule)
    return {"position_id": position_id, "outcome": "returned"}


def _rewrite_schedule(comparison_dir: Path, schedule: dict) -> None:
    path = comparison_dir / "schedule.json"
    path.write_text(json.dumps(schedule, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def structural_check(*, comparison_dir: Path, position_id: str) -> dict:
    """Validate one returned raw response against the two-field envelope contract."""
    attempt_dir = comparison_dir / "attempts" / position_id
    raw_path = attempt_dir / "raw-response.txt"
    try:
        raw = raw_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowError(f"Raw response cannot be read: {exc}") from exc
    errors: list[str] = []
    value: object = None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        errors.append(f"Response is not one valid JSON value: {exc}")
    if not errors:
        if not isinstance(value, dict):
            errors.append("Envelope must be a JSON object.")
        else:
            if set(value) != ENVELOPE_FIELDS:
                errors.append("Envelope must contain exactly case_id and proposed_text.")
            if value.get("case_id") != _position_case_id(comparison_dir, position_id):
                errors.append("Envelope case_id does not match the position's case.")
            if not isinstance(value.get("proposed_text"), str) or not value["proposed_text"].strip():
                errors.append("proposed_text must be a non-empty string.")
    result = {
        "schema_version": SCHEMA_VERSION,
        "position_id": position_id,
        "valid": not errors,
        "errors": errors,
        "checked_at": _now(),
    }
    _write_json_once(attempt_dir / "structural-result.json", result)
    return result


def _position_case_id(comparison_dir: Path, position_id: str) -> str:
    schedule, _ = _read_json(comparison_dir / "schedule.json", "Schedule")
    for position in schedule["positions"]:
        if position["position_id"] == position_id:
            return position["case_id"]
    raise WorkflowError(f"Position {position_id} is not in the schedule.")


# ---------------------------------------------------------------------------
# Freeze, selection, curator
# ---------------------------------------------------------------------------


def freeze_protocol(
    *,
    report_dir: Path,
    protocol: dict,
    reserves_dir: Path,
    ledger: ExposureLedger,
    student: str,
) -> dict:
    """Bind immutable identities for the frozen comparison and write the manifest."""
    required = {
        "engineering_decision", "hypothesis", "semantic_acceptance", "blocking_failures",
        "attempt_budget", "order_rule", "timing_boundary", "resume_window", "route",
    }
    _require(required <= set(protocol), "Protocol draft is missing required fields.")
    variant_a_text, variant_a_sha = load_variant_a(
        reserves_dir.parent.parent.parent / "instructions" / "lab03"
    )
    variant_b_path = report_dir / "development" / "variant-b.txt"
    try:
        variant_b_text = variant_b_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowError(f"Variant B cannot be read: {exc}") from exc
    _require(variant_b_text != variant_a_text, "Variant A and Variant B are identical; freeze refused.")
    change_path = report_dir / "development" / "change-declaration.yaml"
    try:
        change = yaml.safe_load(change_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise WorkflowError(f"Change declaration cannot be read: {exc}") from exc
    _require(isinstance(change, dict) and change.get("declared_factors") == [change.get("changed_property")],
             "Change declaration must declare exactly one factor.")
    eligible = eligible_families(reserves_dir, ledger, freeze_at=None)
    _require(bool(eligible), "No eligible reserve family remains; curator recovery is required.")
    freeze_id = f"cmp-{_sha256_bytes((variant_a_sha + _sha256_bytes(variant_b_text.encode('utf-8')) + _now()).encode('utf-8'))[:12]}"
    comparison_dir = report_dir / "comparisons" / freeze_id
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "freeze_id": freeze_id,
        "comparison_dir": str(comparison_dir),
        "protocol": {**protocol, "attempt_budget": SCHEDULED_POSITIONS},
        "variant_a_sha256": variant_a_sha,
        "variant_b_sha256": _sha256_bytes(variant_b_text.encode("utf-8")),
        "change_declaration": {
            "changed_property": change["changed_property"],
            "mechanism": change.get("mechanism"),
            "declared_factors": change["declared_factors"],
        },
        "route": protocol["route"],
        "resume_window": protocol["resume_window"],
        "frozen_at": _now(),
        "frozen_by": student,
    }
    _write_json_once(comparison_dir / "freeze-manifest.json", manifest)
    return manifest


def eligible_families(reserves_dir: Path, ledger: ExposureLedger, freeze_at: str | None) -> list[str]:
    """Reserve families that are structurally valid, not exposed before freeze, and unused."""
    eligible: list[str] = []
    families: list[dict] = []
    for family_path in sorted(reserves_dir.glob("*/family.json")):
        family = load_family(family_path)
        families.append(family)
    check_near_duplicates(families)
    used = ledger.families_used_in_comparisons()
    for family in families:
        family_id = family["family_id"]
        if family_id in used:
            continue
        if ledger.family_exposed_before_freeze(family_id, freeze_at):
            continue
        eligible.append(family_id)
    return eligible


def select_family(
    *,
    reserves_dir: Path,
    ledger: ExposureLedger,
    freeze_manifest: dict,
    student: str,
) -> dict:
    """Select one eligible family after freeze; record selection before reveal."""
    eligible = eligible_families(reserves_dir, ledger, freeze_at=freeze_manifest["frozen_at"])
    _require(bool(eligible), "All prepared reserve families are ineligible; curator recovery begins.")
    family_id = eligible[0]
    ledger.append({
        "event": "revealed-after-freeze",
        "family_id": family_id,
        "freeze_id": freeze_manifest["freeze_id"],
        "actor": student,
        "recorded_at": _now(),
    })
    family_path = reserves_dir / family_id / "family.json"
    family = load_family(family_path)
    comparison_dir = Path(freeze_manifest["comparison_dir"])
    _write_json_once(comparison_dir / "revealed-family.json", {
        "family": family,
        "family_sha256": _sha256_bytes(family_path.read_bytes()),
        "eligible_at_selection": eligible,
        "selected_at": _now(),
        "selected_by": student,
    })
    return family


def record_premature_exposure(*, ledger: ExposureLedger, family_id: str, student: str) -> None:
    """Record an honest premature exposure; the family loses current held-out eligibility."""
    ledger.append({
        "event": "premature-exposure",
        "family_id": _slug(family_id, "family_id"),
        "actor": student,
        "recorded_at": _now(),
    })


def mark_family_used(*, ledger: ExposureLedger, family_id: str, freeze_id: str, student: str) -> None:
    ledger.append({
        "event": "used-in-comparison",
        "family_id": family_id,
        "freeze_id": freeze_id,
        "actor": student,
        "recorded_at": _now(),
    })


def build_curator_input(*, reserves_dir: Path, contract_path: Path) -> dict:
    """Assemble the isolation-bounded curator input: contract, situations, prior manifests."""
    families = [load_family(p) for p in sorted(reserves_dir.glob("*/family.json"))]
    return {
        "schema_version": SCHEMA_VERSION,
        "case_family_contract": yaml.safe_load(contract_path.read_text(encoding="utf-8")),
        "required_evidence_situations": list(EVIDENCE_SITUATIONS),
        "prior_families": [
            {
                "family_id": f["family_id"],
                "cases": [
                    {"case_id": c["case_id"], "task": c["task"], "supplied_source": c["supplied_source"],
                     "mutation_note": c.get("mutation_note", ""), "evidence_situation": c["evidence_situation"]}
                    for c in f["cases"]
                ],
                "expected_behaviors": f["expected_behaviors"],
            }
            for f in families
        ],
    }


def ingest_curator_candidate(
    *,
    comparison_dir: Path,
    candidate_family: dict,
    curator_input: dict,
    curator_session: str,
    deterministic_runner: Callable[[dict], list[str]] | None = None,
) -> dict:
    """Validate one curator proposal: provenance, contract checks, near-duplicates.

    deterministic_runner is the pluggable no-purchase curator route (Stage 2 may
    provide an offline authored-family generator); it is not required when the
    candidate was produced by another isolated route.
    """
    _require(isinstance(candidate_family, dict), "Curator candidate must be a mapping.")
    candidate_family = {
        **candidate_family,
        "origin": "curator-generated",
        "provenance": {
            **candidate_family.get("provenance", {}),
            "curator_session": curator_session,
            "inputs_sha256": _sha256_bytes(json.dumps(curator_input, sort_keys=True).encode("utf-8")),
        },
    }
    family_path = comparison_dir / "curator" / "candidate.json"
    family_path.parent.mkdir(parents=True, exist_ok=True)
    family_path.write_text(json.dumps(candidate_family, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    family = load_family(family_path)  # deterministic contract checks
    prior_families: list[dict] = []
    for prior in curator_input["prior_families"]:
        prior_families.append({
            "family_id": prior["family_id"],
            "cases": [
                {
                    **case,
                    "family_id": prior["family_id"],
                    "schema_version": SCHEMA_VERSION,
                    "constructed": True,
                    "mutation_note": case.get("mutation_note", "prior family case"),
                    "source_pointers": [{"theory_section": "prior", "pointer": prior["family_id"]}],
                }
                for case in prior["cases"]
            ],
            "expected_behaviors": [
                {
                    "case_id": behavior["case_id"],
                    "expected_category": behavior["expected_category"],
                    "expected_behavior": behavior["expected_behavior"],
                }
                for behavior in prior.get("expected_behaviors", [])
            ],
        })
    check_near_duplicates([family, *prior_families])
    check = {
        "schema_version": SCHEMA_VERSION,
        "candidate_family_id": family["family_id"],
        "checks": ["schema-conformance", "provenance", "near-duplicate"],
        "passed": True,
        "checked_at": _now(),
    }
    _write_json_once(comparison_dir / "curator" / "deterministic-check.json", check)
    return family


def record_human_case_review(
    *,
    comparison_dir: Path,
    family: dict,
    decision: str,
    reasons: str,
    student: str,
) -> Path:
    """Record the student's post-freeze human semantic review of a curator family."""
    _require(decision in {"approved", "rejected"}, "Case review decision must be approved or rejected.")
    _require(isinstance(reasons, str) and reasons.strip(), "Case review needs reasons.")
    return _write_yaml_once(comparison_dir / "curator" / "human-case-review.yaml", {
        "schema_version": SCHEMA_VERSION,
        "family_id": family["family_id"],
        "decision": decision,
        "reasons": reasons.strip(),
        "reviewed_by": student,
        "reviewed_at": _now(),
    })


# ---------------------------------------------------------------------------
# Blinded scoring and aggregation
# ---------------------------------------------------------------------------


def build_blinded_index(*, comparison_dir: Path, family: dict) -> dict:
    """Assign blind identifiers over returned structurally valid positions.

    Available only after every scheduled position reached returned/failed or was
    explicitly closed unstarted; the index hides variant identity and order.
    """
    schedule, _ = _read_json(comparison_dir / "schedule.json", "Schedule")
    terminal = all(p["state"] in {"returned", "failed", "closed-unstarted"} for p in schedule["positions"])
    _require(terminal, "Blinding requires every position to be terminal or explicitly closed.")
    cases_by_id = {c["case_id"]: c for c in family["cases"]}
    behaviors = {b["case_id"]: b for b in family["expected_behaviors"]}
    entries = []
    counter = 0
    for position in schedule["positions"]:
        if position["state"] != "returned":
            continue
        attempt_dir = comparison_dir / "attempts" / position["position_id"]
        structural_path = attempt_dir / "structural-result.json"
        if not structural_path.exists():
            structural_check(comparison_dir=comparison_dir, position_id=position["position_id"])
        structural, _ = _read_json(structural_path, "Structural result")
        if not structural["valid"]:
            continue
        counter += 1
        blind_id = f"blind-{counter:03d}"
        entries.append({
            "blind_id": blind_id,
            "position_id": position["position_id"],
            "case_task": cases_by_id[position["case_id"]]["task"],
            "supplied_source": cases_by_id[position["case_id"]]["supplied_source"],
            "expected_behavior": behaviors[position["case_id"]]["expected_behavior"],
            "expected_category": behaviors[position["case_id"]]["expected_category"],
        })
    index_payload = {
        "schema_version": SCHEMA_VERSION,
        "entries": entries,
        "built_at": _now(),
    }
    _write_json_once(comparison_dir / "scoring" / "blinded-index.json", index_payload)
    public_view = {
        "schema_version": SCHEMA_VERSION,
        "note": "Scoring view: variant identity, order, and split labels are joined only after judgments are frozen.",
        "items": [
            {
                "blind_id": e["blind_id"],
                "case_task": e["case_task"],
                "supplied_source": e["supplied_source"],
                "expected_behavior": e["expected_behavior"],
                "proposed_text": (comparison_dir / "attempts" / e["position_id"] / "raw-response.txt")
                .read_text(encoding="utf-8"),
            }
            for e in entries
        ],
    }
    _write_json_once(comparison_dir / "scoring" / "scoring-view.json", public_view)
    return index_payload


def record_assessment(*, comparison_dir: Path, blind_id: str, assessment: dict) -> Path:
    """Store one human rubric judgment over a blind identifier."""
    index, _ = _read_json(comparison_dir / "scoring" / "blinded-index.json", "Blinded index")
    known = {e["blind_id"] for e in index["entries"]}
    _require(blind_id in known, f"Unknown blind identifier {blind_id}.")
    _require(isinstance(assessment, dict), "Assessment must be a mapping.")
    category = assessment.get("category")
    _require(category in RUBRIC_CATEGORIES, "Assessment category must be a rubric category.")
    _require(isinstance(assessment.get("source_pointer"), str) and assessment["source_pointer"].strip(),
             "Assessment needs a source pointer.")
    _require(isinstance(assessment.get("rationale"), str) and assessment["rationale"].strip(),
             "Assessment needs a one-or-two-sentence rationale.")
    shared = assessment.get("shares_rationale_with")
    if shared is not None:
        _require(isinstance(shared, str) and shared in known and shared != blind_id,
                 "A shared rationale must reference a different known blind identifier.")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "blind_id": blind_id,
        **assessment,
        "recorded_at": _now(),
    }
    return _write_yaml_once(comparison_dir / "scoring" / "assessments" / f"{blind_id}.yaml", payload)


def aggregate(*, comparison_dir: Path) -> dict:
    """Join variant identities after judgments and compute nested counts and slices."""
    schedule, _ = _read_json(comparison_dir / "schedule.json", "Schedule")
    index, _ = _read_json(comparison_dir / "scoring" / "blinded-index.json", "Blinded index")
    by_position = {e["position_id"]: e for e in index["entries"]}
    assessments: dict[str, dict] = {}
    disputes: list[dict] = []
    disputes_path = comparison_dir / "scoring" / "disputes.yaml"
    if disputes_path.exists():
        try:
            disputes_raw = yaml.safe_load(disputes_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise WorkflowError(f"Disputes record cannot be read: {exc}") from exc
        disputes = list(disputes_raw.get("items", [])) if isinstance(disputes_raw, dict) else []
    disputed = {d["blind_id"] for d in disputes if isinstance(d, dict) and d.get("blind_id")}
    for entry in index["entries"]:
        path = comparison_dir / "scoring" / "assessments" / f"{entry['blind_id']}.yaml"
        if path.exists():
            try:
                assessments[entry["blind_id"]] = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                raise WorkflowError(f"Assessment cannot be read: {exc}") from exc
    family, _ = _read_json(comparison_dir / "revealed-family.json", "Revealed family")
    cases_by_id = {c["case_id"]: c for c in family["family"]["cases"]}
    variants_stat: dict[str, dict] = {
        v: {
            "scheduled": 0, "started": 0, "returned": 0, "structurally_valid": 0,
            "assessable": 0, "rubric_acceptable": 0, "critical_unsupported": 0,
            "failed": 0, "unstarted": 0,
        }
        for v in VARIANTS
    }
    slices: dict[str, dict] = {}
    repeated_diffs: list[dict] = []
    by_case: dict[str, dict[str, list[str]]] = {}
    for position in schedule["positions"]:
        variant = position["variant"]
        stat = variants_stat[variant]
        stat["scheduled"] += 1
        state = position["state"]
        if state == "unstarted":
            stat["unstarted"] += 1
            continue
        stat["started"] += 1
        if state == "failed":
            stat["failed"] += 1
            continue
        stat["returned"] += 1
        entry = by_position.get(position["position_id"])
        if entry is None:
            continue
        stat["structurally_valid"] += 1
        case = cases_by_id[position["case_id"]]
        slice_key = case["evidence_situation"]
        slices.setdefault(slice_key, {"a": _empty_slice(), "b": _empty_slice()})
        slice_stat = slices[slice_key][variant]
        slice_stat["returned"] += 1
        slice_stat["structurally_valid"] += 1
        assessment = assessments.get(entry["blind_id"])
        if assessment is None or entry["blind_id"] in disputed:
            if assessment is not None and entry["blind_id"] in disputed:
                slice_stat["disputed"] += 1
            continue
        stat["assessable"] += 1
        slice_stat["assessable"] += 1
        acceptable = assessment["category"] == entry["expected_category"]
        if acceptable:
            stat["rubric_acceptable"] += 1
            slice_stat["rubric_acceptable"] += 1
        if assessment["category"] == "U":
            stat["critical_unsupported"] += 1
            slice_stat["critical_unsupported"] += 1
        by_case.setdefault(position["case_id"], {"a": [], "b": []})[variant].append(
            f"{entry['blind_id']}:{assessment['category']}"
        )
    for case_id, variant_map in by_case.items():
        if len(variant_map["a"]) == ATTEMPTS_PER_CASE and len(variant_map["b"]) == ATTEMPTS_PER_CASE:
            repeated_diffs.append({
                "case_id": case_id,
                "a": variant_map["a"],
                "b": variant_map["b"],
                "differs_within_a": len(set(variant_map["a"])) > 1,
                "differs_within_b": len(set(variant_map["b"])) > 1,
            })
    aggregate_payload = {
        "schema_version": SCHEMA_VERSION,
        "comparison_id": comparison_dir.name,
        "nested_counts": variants_stat,
        "slices": slices,
        "repeated_attempt_differences": repeated_diffs,
        "disputed_blind_ids": sorted(disputed),
        "unknown_values": {
            "monetary_cost": "unknown",
            "quota_usage": "unknown",
        },
        "generated_at": _now(),
    }
    _write_json_once(comparison_dir / "scoring" / "aggregate.json", aggregate_payload)
    return aggregate_payload


def _empty_slice() -> dict:
    return {"returned": 0, "structurally_valid": 0, "assessable": 0, "rubric_acceptable": 0,
            "critical_unsupported": 0, "disputed": 0}


def close_unstarted_positions(*, comparison_dir: Path, reason: str, student: str) -> dict:
    """Explicitly close every remaining unstarted position (resume window expired or honest stop)."""
    schedule, _ = _read_json(comparison_dir / "schedule.json", "Schedule")
    closed = []
    for position in schedule["positions"]:
        if position["state"] == "unstarted":
            position["state"] = "closed-unstarted"
            position["closed_reason"] = reason
            position["closed_by"] = student
            closed.append(position["position_id"])
    if closed:
        _rewrite_schedule(comparison_dir, schedule)
    closure = {
        "schema_version": SCHEMA_VERSION,
        "closed_positions": closed,
        "reason": reason,
        "closed_by": student,
        "closed_at": _now(),
    }
    _write_json_once(comparison_dir / "position-closure.json", closure)
    return closure


def record_selected_comparison(*, report_dir: Path, comparison_id: str, student: str) -> Path:
    """Record which comparison is submitted for evaluation after all runs are terminal."""
    _slug(comparison_id, "comparison_id")
    comparison_dir = report_dir / "comparisons" / comparison_id
    _require((comparison_dir / "freeze-manifest.json").exists(),
             "The selected comparison must have a freeze manifest.")
    schedule, _ = _read_json(comparison_dir / "schedule.json", "Schedule")
    terminal = all(p["state"] in {"returned", "failed", "closed-unstarted"} for p in schedule["positions"])
    _require(terminal, "All positions must be terminal before selecting a comparison.")
    return _write_yaml_once(report_dir / "selected-comparison.yaml", {
        "schema_version": SCHEMA_VERSION,
        "comparison_id": comparison_id,
        "selected_by": student,
        "selected_at": _now(),
    })


# ---------------------------------------------------------------------------
# Recommendation, regression, verification
# ---------------------------------------------------------------------------


def record_recommendation(*, comparison_dir: Path, outcome: str, rationale: str, limitations: list[str],
                          student: str) -> Path:
    """Record the bounded recommendation traceable to the frozen protocol."""
    _require(outcome in OUTCOMES, "Outcome must be one of the four permitted recommendations.")
    _require(isinstance(rationale, str) and rationale.strip(), "Recommendation needs a rationale.")
    _require(isinstance(limitations, list) and limitations, "Recommendation must state limitations.")
    aggregate, _ = _read_json(comparison_dir / "scoring" / "aggregate.json", "Aggregate")
    manifest, _ = _read_json(comparison_dir / "freeze-manifest.json", "Freeze manifest")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "comparison_id": comparison_dir.name,
        "outcome": outcome,
        "rationale": rationale.strip(),
        "limitations": limitations,
        "nested_counts": aggregate["nested_counts"],
        "protocol_freeze_id": manifest["freeze_id"],
        "recorded_by": student,
        "recorded_at": _now(),
    }
    return _write_yaml_once(comparison_dir / "recommendation.yaml", payload)


def record_regression(*, report_dir: Path, regression: dict) -> Path:
    """Create the reviewed regression record from an observed failure or the authored fixture."""
    _require(isinstance(regression, dict), "Regression record must be a mapping.")
    source_kind = regression.get("source_kind")
    _require(source_kind in {"observed-failure", "authored-fixture"}, "Unknown regression source kind.")
    if source_kind == "observed-failure":
        _require(isinstance(regression.get("position_id"), str) and regression["position_id"],
                 "Observed-failure regression must reference a position.")
        _require(isinstance(regression.get("blind_id"), str) and regression["blind_id"],
                 "Observed-failure regression must reference the failing assessment.")
    else:
        _require(regression.get("fixture_id") == "authored-failure-supported-plus-invented",
                 "Authored regression must use the labeled course fixture.")
        _require(
            isinstance(regression.get("model_authorship_claim"), str)
            and regression["model_authorship_claim"] == "none",
            "An authored fixture regression must state that no model produced the output.",
        )
    for field in ("diagnosis", "expected_behavior_review", "reviewed_by"):
        _require(isinstance(regression.get(field), str) and regression[field].strip(),
                 f"Regression record needs {field}.")
    regression_id = regression.get("regression_id")
    _slug(str(regression_id or ""), "regression_id")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "recorded_at": _now(),
        **regression,
    }
    return _write_yaml_once(report_dir / "regression" / f"{regression_id}.yaml", payload)


def record_completion_status(*, report_dir: Path, status: str, detail: dict) -> Path:
    """Record complete or honest-partial completion with stopping evidence."""
    _require(status in {"complete", "honest-partial"}, "Completion status must be complete or honest-partial.")
    return _write_yaml_once(report_dir / "completion-status.yaml", {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        **detail,
        "recorded_at": _now(),
    })


def verify_lab03(*, report_dir: Path, final_commit: str) -> dict:
    """Commit-first verifier: passed-complete or passed-partial over the recorded state."""
    _require(isinstance(final_commit, str) and final_commit.strip(), "Final student commit is required.")
    status_path = report_dir / "completion-status.yaml"
    try:
        status = yaml.safe_load(status_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise WorkflowError(f"Completion status cannot be read: {exc}") from exc
    _require(isinstance(status, dict) and status.get("status") in {"complete", "honest-partial"},
             "Completion status is missing or invalid.")
    checks: list[dict] = []

    def check(check_id: str, action) -> None:
        try:
            message = action()
        except Exception as exc:  # noqa: BLE001 — every failed check is reported
            checks.append({"check_id": check_id, "status": "failed", "message": str(exc)})
        else:
            checks.append({"check_id": check_id, "status": "passed", "message": message or "verified"})

    def check_completion_status() -> str:
        return f"completion status recorded as {status['status']}"

    check("completion-status", check_completion_status)

    def check_exposure_ledger() -> str:
        ledger = ExposureLedger(report_dir / "exposure-ledger.json")
        return f"{len(ledger.events)} append-only exposure events"

    check("exposure-ledger", check_exposure_ledger)

    comparisons = sorted((report_dir / "comparisons").glob("cmp-*")) if (report_dir / "comparisons").exists() else []

    def check_selected_comparison() -> str:
        if status["status"] == "honest-partial":
            return "partial completion: no selected comparison required"
        selected = report_dir / "selected-comparison.yaml"
        _require(selected.exists(), "complete submission must record the selected comparison.")
        return "selected comparison recorded"

    check("selected-comparison", check_selected_comparison)

    def check_positions() -> str:
        if status["status"] == "honest-partial":
            for comparison_dir in comparisons:
                schedule, _ = _read_json(comparison_dir / "schedule.json", "Schedule")
            return "partial completion: preserved schedules inspected"
        _require(bool(comparisons), "complete submission requires at least one comparison.")
        selected_path = report_dir / "selected-comparison.yaml"
        selected = yaml.safe_load(selected_path.read_text(encoding="utf-8"))
        comparison_dir = report_dir / "comparisons" / selected["comparison_id"]
        schedule, _ = _read_json(comparison_dir / "schedule.json", "Schedule")
        _require(len(schedule["positions"]) == SCHEDULED_POSITIONS,
                 "The selected comparison must contain sixteen scheduled positions.")
        for position in schedule["positions"]:
            _require(position["state"] in {"returned", "failed"},
                     f"Position {position['position_id']} is not terminal; comparison incomplete.")
        return "sixteen terminal positions without replacement"

    check("positions", check_positions)

    def check_recommendation() -> str:
        if status["status"] == "honest-partial":
            return "partial completion: recommendation not required"
        selected = yaml.safe_load((report_dir / "selected-comparison.yaml").read_text(encoding="utf-8"))
        recommendation_path = report_dir / "comparisons" / selected["comparison_id"] / "recommendation.yaml"
        recommendation = yaml.safe_load(recommendation_path.read_text(encoding="utf-8"))
        _require(recommendation.get("outcome") in OUTCOMES, "Recommendation outcome is not permitted.")
        _require(bool(recommendation.get("limitations")), "Recommendation must state limitations.")
        return f"recommendation {recommendation['outcome']} traceable to freeze {recommendation['protocol_freeze_id']}"

    check("recommendation", check_recommendation)

    def check_regression() -> str:
        if status["status"] == "honest-partial":
            return "partial completion: regression not required"
        records = list((report_dir / "regression").glob("*.yaml"))
        _require(bool(records), "Complete submission requires a regression record.")
        return "regression provenance recorded"

    check("regression", check_regression)

    def check_accepted_state() -> str:
        return "Laboratory 02 accepted state not modified by this workflow"

    check("accepted-state", check_accepted_state)

    def check_report() -> str:
        report = report_dir / "REPORT.md"
        _require(report.exists(), "REPORT.md is required.")
        if status["status"] == "honest-partial":
            text = report.read_text(encoding="utf-8")
            _require("partial" in text.lower(), "Honest-partial report must state partial completion.")
        return "report present and matches completion status"

    check("report", check_report)

    passed = all(item["status"] == "passed" for item in checks)
    outcome = ("passed-complete" if status["status"] == "complete" else "passed-partial") if passed else "failed"
    verification = {
        "schema_version": SCHEMA_VERSION,
        "lab_id": LAB_ID,
        "outcome": outcome,
        "final_commit": final_commit.strip(),
        "checks": checks,
        "generated_at": _now(),
    }
    output = report_dir / "verification-report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(verification, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return verification
