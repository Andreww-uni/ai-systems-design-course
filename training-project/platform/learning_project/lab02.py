"""Laboratory 02 governed structured-output workflow.

The approved contract (LAB02_DESIGN_DECISIONS.md questions 1-10) fixes the
source and fragment identifiers, the artifact schemas, the writer
responsibilities, and the digest-binding chain. This module implements exactly
that contract and refuses every path that deviates from it.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .workflow import WorkflowError

# Approved source and fragment identifiers (question 2).
SOURCE_HEADING = "### 1.3 Structured output controls syntax, not meaning"
FURTHER_READING_BOUNDARY = "> **Further reading:**"
SOURCE_ID = "module-02-foundation-models-and-ai-application-architecture"
FRAGMENT_ID = "module-02-1-3-structured-output-controls-v1"
COURSE_PATH = (
    "modules/02_Foundation_Models_and_AI_Application_Architecture/"
    "02_Foundation_Models_and_AI_Application_Architecture_Theory.md"
)
SOURCE_RELATIVE_PATH = Path("sources") / f"{SOURCE_ID}.md"
CONCEPT_RELATIVE_PATH = Path("concepts/structured-output.md")
CONCEPT_ID = "structured-output"
PROPOSAL_ID_PREFIX = "lab02-structured-output-"
REQUEST_ID = "lab02-structured-output-v1"

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PROPOSAL_ID_RE = re.compile(r"^lab02-structured-output-[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# The three approved source-support claim categories (question 3 item 4).
CLAIM_KINDS = ("definition", "syntax-vs-semantics", "authority-boundary")
PROPOSAL_FIELDS = {
    "schema_version",
    "concept_id",
    "title",
    "definition",
    "key_points",
    "source_support",
    "tags",
}
SOURCE_SUPPORT_ENTRY_FIELDS = {"claim_kind", "claim", "quote"}

# Fields that must never appear in canonical vault records.
FORBIDDEN_CANONICAL_KEY_FRAGMENTS = ("provider", "model", "adapter", "harness")


class Lab02InputError(Exception):
    """Required inputs cannot be read; mapped to exit status 2 by the CLI."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise WorkflowError(message)


def _extract_source_fragment(theory_text: str) -> str:
    lines = theory_text.splitlines(keepends=True)
    try:
        start = next(
            index for index, line in enumerate(lines) if line.rstrip("\r\n") == SOURCE_HEADING
        )
        end = next(
            index
            for index in range(start + 1, len(lines))
            if lines[index].startswith(FURTHER_READING_BOUNDARY)
        )
    except StopIteration as exc:
        raise WorkflowError(
            "Theory must contain the exact Laboratory 02 section and its Further reading boundary."
        ) from exc
    fragment = "".join(lines[start:end])
    if not fragment.endswith("\n"):
        fragment += "\n"
    return fragment


def _read_markdown_record(path: Path) -> tuple[dict, str]:
    try:
        text = path.read_text(encoding="utf-8")
        marker, frontmatter, body = text.split("---\n", 2)
        metadata = yaml.safe_load(frontmatter)
    except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
        raise WorkflowError(f"Markdown record cannot be read: {path}: {exc}") from exc
    if marker or not isinstance(metadata, dict):
        raise WorkflowError(f"Markdown record has invalid frontmatter: {path}")
    return metadata, body


def _render_markdown_record(metadata: dict, body: str) -> str:
    return "---\n" + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True) + "---\n" + body


def _without_attribution(metadata: dict) -> dict:
    return {
        key: value
        for key, value in metadata.items()
        if key not in ("registered_at", "registered_by")
    }


def _proposal_payload(body: str) -> dict:
    match = re.fullmatch(
        r"# Candidate proposal: .*?\n\n"
        r"The JSON object below is the normalized candidate payload\. It has no authority until "
        r"it passes deterministic validation and receives an explicit human decision\.\n\n"
        r"```json\n(.*)\n```\n",
        body,
        flags=re.DOTALL,
    )
    if match is None:
        raise WorkflowError("Proposal body does not contain the canonical JSON payload block.")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"Proposal payload is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise WorkflowError("Proposal payload must be a JSON object.")
    return payload


def _confine_proposal_id(proposal_id: str) -> None:
    if not isinstance(proposal_id, str) or not PROPOSAL_ID_RE.fullmatch(proposal_id):
        raise WorkflowError(
            "proposal_id must match lab02-structured-output-<run-or-revision-id>."
        )
    if ".." in proposal_id or "/" in proposal_id or "\\" in proposal_id:
        raise WorkflowError("proposal_id must not contain path separators.")


def _resolve_vault(vault: Path, course_root: Path | None) -> Path:
    resolved_vault = vault.resolve()
    if course_root is not None:
        resolved_course = course_root.resolve()
        if resolved_vault == resolved_course or resolved_course in resolved_vault.parents:
            raise WorkflowError("The Markdown vault must remain outside the course repository.")
    return resolved_vault


def _read_json_object(path: Path, label: str) -> tuple[dict, bytes]:
    try:
        data = path.read_bytes()
        value = json.loads(data)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"{label} cannot be read: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError(f"{label} must contain a JSON object.")
    return value, data


def _read_yaml_object(path: Path, label: str) -> tuple[dict, bytes]:
    try:
        data = path.read_bytes()
        value = yaml.safe_load(data)
    except (OSError, yaml.YAMLError) as exc:
        raise WorkflowError(f"{label} cannot be read: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError(f"{label} must contain a YAML mapping.")
    return value, data


def register_source(
    *,
    course_root: Path,
    theory_path: Path,
    vault: Path,
    course_repository: str,
    course_commit: str,
    registered_by: str,
) -> Path:
    """Register the exact Module 02 subsection as an immutable source record."""
    resolved_vault = _resolve_vault(vault, course_root)
    resolved_course_root = course_root.resolve()
    try:
        theory_bytes = theory_path.read_bytes()
        theory_text = theory_bytes.decode("utf-8")
        course_path = theory_path.resolve().relative_to(resolved_course_root).as_posix()
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise WorkflowError(f"Theory source cannot be read from the course repository: {exc}") from exc

    fragment = _extract_source_fragment(theory_text)
    fragment_sha256 = _sha256_bytes(fragment.encode("utf-8"))
    metadata = {
        "schema_version": "1.0",
        "record_type": "source",
        "source_id": SOURCE_ID,
        "title": "Module 02 source — Structured output controls syntax, not meaning",
        "tags": ["record/source", "domain/ai-engineering"],
        "course_repository": course_repository,
        "course_commit": course_commit,
        "course_path": course_path,
        "source_file_sha256": _sha256_bytes(theory_bytes),
        "fragments": [
            {
                "fragment_id": FRAGMENT_ID,
                "heading": SOURCE_HEADING,
                "boundary_start": SOURCE_HEADING,
                "boundary_end": FURTHER_READING_BOUNDARY,
                "fragment_sha256": fragment_sha256,
            }
        ],
        "registered_at": _now(),
        "registered_by": registered_by,
    }
    rendered = _render_markdown_record(metadata, fragment)
    source_path = resolved_vault / SOURCE_RELATIVE_PATH
    if source_path.exists():
        try:
            existing_metadata, existing_fragment = _read_markdown_record(source_path)
        except WorkflowError as exc:
            raise WorkflowError(f"Existing source record is unreadable: {exc}") from exc
        if (
            _without_attribution(existing_metadata) == _without_attribution(metadata)
            and existing_fragment == fragment
        ):
            return source_path
        raise WorkflowError(
            "The immutable Laboratory 02 source record already exists with different content."
        )
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(rendered, encoding="utf-8")
    return source_path


def _read_source_record(vault: Path) -> tuple[dict, str]:
    source_path = vault / SOURCE_RELATIVE_PATH
    metadata, fragment = _read_markdown_record(source_path)
    if metadata.get("source_id") != SOURCE_ID:
        raise WorkflowError("Registered source_id is not canonical.")
    fragments = metadata.get("fragments")
    _require(isinstance(fragments, list) and len(fragments) == 1, "Source must have one fragment.")
    fragment_entry = fragments[0]
    _require(
        isinstance(fragment_entry, dict)
        and fragment_entry.get("fragment_id") == FRAGMENT_ID
        and fragment_entry.get("fragment_sha256") == _sha256_bytes(fragment.encode("utf-8")),
        "Source fragment identifiers or digest do not match the registered bytes.",
    )
    return metadata, fragment


def prepare_request(
    *, vault: Path, report_dir: Path, run_id: str, course_root: Path | None = None
) -> Path:
    """Write a deterministic, provider-neutral model request for one run."""
    if not SLUG_RE.fullmatch(run_id):
        raise WorkflowError("run_id must be a lowercase slug without spaces.")
    _resolve_vault(vault, course_root)
    source_metadata, fragment = _read_source_record(vault)
    fragment_sha256 = source_metadata["fragments"][0]["fragment_sha256"]

    request = {
        "schema_version": "1.0",
        "request_id": REQUEST_ID,
        "operation": "create",
        "target_concept_id": CONCEPT_ID,
        "source": {
            "source_id": SOURCE_ID,
            "fragment_id": FRAGMENT_ID,
            "fragment_sha256": fragment_sha256,
            "text": fragment,
        },
        "constraints": {
            "source_only": True,
            "exact_quotes": True,
            "external_knowledge_allowed": False,
        },
        "output_schema_version": "1.0",
    }
    request_path = report_dir / "runs" / run_id / "model-request.json"
    rendered = json.dumps(request, indent=2, ensure_ascii=False) + "\n"
    if request_path.exists():
        if request_path.read_text(encoding="utf-8") == rendered:
            return request_path
        raise WorkflowError("The immutable model request already exists with different content.")
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(rendered, encoding="utf-8")
    return request_path


def _proposed_concept(candidate: dict) -> dict:
    return {key: candidate[key] for key in ("concept_id", "title", "definition", "key_points", "source_support", "tags")}


def import_response(
    *,
    vault: Path,
    report_dir: Path,
    run_id: str,
    evidence_kind: str,
    course_root: Path | None = None,
) -> Path:
    """Parse one raw JSON response and write an immutable model-normalized proposal."""
    if not SLUG_RE.fullmatch(run_id):
        raise WorkflowError("run_id must be a lowercase slug without spaces.")
    if evidence_kind not in {"live", "fixture"}:
        raise WorkflowError("evidence_kind must be live or fixture.")
    _resolve_vault(vault, course_root)

    run_dir = report_dir / "runs" / run_id
    request_path = run_dir / "model-request.json"
    raw_path = run_dir / "raw-response.txt"
    try:
        request_bytes = request_path.read_bytes()
        request = json.loads(request_bytes)
        raw_bytes = raw_path.read_bytes()
        candidate = json.loads(raw_bytes)
    except OSError as exc:
        raise WorkflowError(f"Run evidence cannot be read: {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"Raw response is not one valid JSON value: {exc}") from exc
    if not isinstance(request, dict) or request.get("request_id") != REQUEST_ID:
        raise WorkflowError("Model request does not match the Laboratory 02 request contract.")
    if not isinstance(candidate, dict):
        raise WorkflowError("Raw response must contain one JSON object.")
    normalized_candidate = {key: candidate[key] for key in PROPOSAL_FIELDS if key in candidate}

    source_path = vault / SOURCE_RELATIVE_PATH
    source_metadata, _ = _read_source_record(vault)
    fragment_sha256 = source_metadata["fragments"][0]["fragment_sha256"]
    proposal_id = f"{PROPOSAL_ID_PREFIX}{run_id}"
    proposal_path = vault / "proposals" / f"{proposal_id}.md"
    if proposal_path.exists():
        raise WorkflowError("The immutable proposal record already exists.")

    metadata = {
        "schema_version": "1.0",
        "record_type": "proposal",
        "proposal_id": proposal_id,
        "status": "proposed",
        "origin": "model-normalized",
        "target": CONCEPT_RELATIVE_PATH.as_posix(),
        "evidence": {
            "run_id": run_id,
            "evidence_kind": evidence_kind,
            "request_id": request.get("request_id"),
            "request_sha256": _sha256_bytes(request_bytes),
            "raw_response_sha256": _sha256_bytes(raw_bytes),
            "source_id": SOURCE_ID,
            "source_sha256": _sha256_bytes(source_path.read_bytes()),
            "fragment_id": FRAGMENT_ID,
            "fragment_sha256": fragment_sha256,
        },
        "proposed_concept": _proposed_concept(normalized_candidate),
        "created_at": _now(),
        "created_by": "learning-project lab02 import",
    }
    body = (
        f"# Candidate proposal: {normalized_candidate.get('title', 'Unvalidated')}\n\n"
        "The JSON object below is the normalized candidate payload. It has no authority until "
        "it passes deterministic validation and receives an explicit human decision.\n\n"
        "```json\n"
        + json.dumps(normalized_candidate, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n```\n"
    )
    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text(_render_markdown_record(metadata, body), encoding="utf-8")
    return proposal_path


def revise_candidate(
    *, vault: Path, revision_path: Path, course_root: Path | None = None
) -> Path:
    """Create an immutable human-revised successor to an existing candidate."""
    _resolve_vault(vault, course_root)
    revision, revision_bytes = _read_yaml_object(revision_path, "Revision input")
    if revision.get("schema_version") != "1.0":
        raise WorkflowError("Revision schema_version must be 1.0.")
    revision_id = revision.get("revision_id")
    if not isinstance(revision_id, str) or not SLUG_RE.fullmatch(revision_id):
        raise WorkflowError("revision_id must be a lowercase slug without spaces.")
    derived_from = revision.get("derived_from")
    if not isinstance(derived_from, dict):
        raise WorkflowError("Revision must identify its derived_from proposal.")
    parent_id = derived_from.get("proposal_id")
    parent_digest = derived_from.get("proposal_sha256")
    if not isinstance(parent_id, str) or not isinstance(parent_digest, str):
        raise WorkflowError("Revision parent identifier and digest are required.")
    _confine_proposal_id(parent_id)
    changes = revision.get("changes")
    allowed_changes = {"definition", "key_points", "source_support", "tags"}
    if not isinstance(changes, dict) or not changes or not set(changes) <= allowed_changes:
        raise WorkflowError(
            "Revision changes must replace at least one allowed candidate content field."
        )
    rationale = revision.get("rationale")
    revised_by = revision.get("revised_by")
    if not isinstance(rationale, str) or not rationale.strip():
        raise WorkflowError("Revision rationale must be a non-empty string.")
    if not isinstance(revised_by, str) or not revised_by.strip():
        raise WorkflowError("Revision must name the human who authored it.")

    parent_path = vault / "proposals" / f"{parent_id}.md"
    try:
        parent_bytes = parent_path.read_bytes()
        parent_metadata, parent_body = _read_markdown_record(parent_path)
        candidate = _proposal_payload(parent_body)
    except OSError as exc:
        raise WorkflowError(f"Parent proposal cannot be read: {exc}") from exc
    if parent_digest != _sha256_bytes(parent_bytes):
        raise WorkflowError("Revision parent digest does not match the immutable proposal.")

    revised_candidate = dict(candidate)
    revised_candidate.update(changes)
    proposal_id = f"{PROPOSAL_ID_PREFIX}{revision_id}"
    proposal_path = vault / "proposals" / f"{proposal_id}.md"
    if proposal_path.exists():
        raise WorkflowError("The immutable revised proposal already exists.")

    metadata = {
        "schema_version": "1.0",
        "record_type": "proposal",
        "proposal_id": proposal_id,
        "status": "proposed",
        "origin": "human-revision",
        "target": CONCEPT_RELATIVE_PATH.as_posix(),
        "evidence": parent_metadata.get("evidence"),
        "derived_from": {
            "proposal_id": parent_id,
            "proposal_sha256": _sha256_bytes(parent_bytes),
        },
        "revision_input_sha256": _sha256_bytes(revision_bytes),
        "revision": {
            "revision_id": revision_id,
            "changed_fields": list(changes),
            "rationale": rationale.strip(),
            "revised_by": revised_by.strip(),
        },
        "proposed_concept": _proposed_concept(revised_candidate),
        "created_at": _now(),
        "created_by": "learning-project lab02 revise",
    }
    body = (
        f"# Candidate proposal: {revised_candidate.get('title', 'Unvalidated')}\n\n"
        "The JSON object below is the normalized candidate payload. It has no authority until "
        "it passes deterministic validation and receives an explicit human decision.\n\n"
        "```json\n"
        + json.dumps(revised_candidate, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n```\n"
    )
    proposal_path.write_text(_render_markdown_record(metadata, body), encoding="utf-8")
    return proposal_path


def _validate_candidate_invariants(
    candidate: dict, fragment: str, source_metadata: dict, source_sha256: str
) -> list[str]:
    errors: list[str] = []
    if set(candidate) != PROPOSAL_FIELDS:
        errors.append("Candidate must contain exactly the required output fields.")
    if candidate.get("schema_version") != "1.0":
        errors.append("Candidate schema_version must be 1.0.")
    if candidate.get("concept_id") != CONCEPT_ID:
        errors.append("Candidate concept_id must be structured-output.")
    if candidate.get("title") != "Structured Output":
        errors.append("Candidate title must be Structured Output.")
    if not isinstance(candidate.get("definition"), str) or not candidate.get("definition", "").strip():
        errors.append("Candidate definition must be a non-empty string.")
    key_points = candidate.get("key_points")
    if (
        not isinstance(key_points, list)
        or len(key_points) != 3
        or any(not isinstance(item, str) or not item.strip() for item in key_points)
    ):
        errors.append("Candidate key_points must contain exactly three non-empty strings.")
    tags = candidate.get("tags")
    if not isinstance(tags, list) or not tags or any(not isinstance(t, str) or not t.strip() for t in tags):
        errors.append("Candidate tags must be a non-empty list of non-empty strings.")

    support = candidate.get("source_support")
    if not isinstance(support, list) or len(support) != 3:
        errors.append("Candidate source_support must contain exactly three entries.")
    else:
        kinds = tuple(
            item.get("claim_kind") if isinstance(item, dict) else None for item in support
        )
        if kinds != CLAIM_KINDS:
            errors.append(
                "Candidate source_support must contain the three claim categories in declared order."
            )
        for index, item in enumerate(support, start=1):
            if not isinstance(item, dict) or set(item) != SOURCE_SUPPORT_ENTRY_FIELDS:
                errors.append(f"source_support entry {index} has invalid fields.")
                continue
            if not isinstance(item.get("claim"), str) or not item["claim"].strip():
                errors.append(f"source_support entry {index} claim must be non-empty.")
            quote = item.get("quote")
            if not isinstance(quote, str) or not quote.strip() or quote not in fragment:
                errors.append(f"source_support entry {index} quote is not exact source text.")
        quotes = [item.get("quote") for item in support if isinstance(item, dict)]
        if len(quotes) == 3 and len(set(quotes)) != 3:
            errors.append("The three source quotes must be distinct.")
    return errors


def validate_candidate(
    *,
    vault: Path,
    report_dir: Path,
    proposal_id: str,
    output_path: Path,
    course_root: Path | None = None,
) -> dict:
    """Validate deterministic invariants and write a digest-bound result."""
    _resolve_vault(vault, course_root)
    _confine_proposal_id(proposal_id)
    syntactic_errors: list[str] = []
    invariant_errors: list[str] = []

    proposal_path = vault / "proposals" / f"{proposal_id}.md"
    try:
        proposal_bytes = proposal_path.read_bytes()
        metadata, body = _read_markdown_record(proposal_path)
        candidate = _proposal_payload(body)
    except (OSError, WorkflowError) as exc:
        proposal_bytes = b""
        metadata = {}
        candidate = {}
        syntactic_errors.append(str(exc))

    if not syntactic_errors:
        if set(candidate) != PROPOSAL_FIELDS:
            syntactic_errors.append("Candidate payload does not parse as the required JSON object.")
        source_path = vault / SOURCE_RELATIVE_PATH
        try:
            source_metadata, fragment = _read_source_record(vault)
            source_sha256 = _sha256_bytes(source_path.read_bytes())
        except WorkflowError as exc:
            source_metadata, fragment, source_sha256 = {}, "", ""
            invariant_errors.append(str(exc))
        invariant_errors.extend(
            _validate_candidate_invariants(candidate, fragment, source_metadata, source_sha256)
        )

        if metadata.get("proposal_id") != proposal_id:
            invariant_errors.append("Proposal proposal_id does not match the selected proposal.")
        if metadata.get("origin") not in {"model-normalized", "human-revision"}:
            invariant_errors.append("Proposal origin is not model-normalized or human-revision.")
        if metadata.get("target") != CONCEPT_RELATIVE_PATH.as_posix():
            invariant_errors.append("Proposal target is not the approved concept path.")
        proposed = metadata.get("proposed_concept")
        if not isinstance(proposed, dict) or _proposed_concept(candidate) != proposed:
            invariant_errors.append("Proposal proposed_concept does not match the payload.")
        evidence = metadata.get("evidence")
        if not isinstance(evidence, dict):
            invariant_errors.append("Proposal evidence must be an object.")
        else:
            if evidence.get("source_id") != SOURCE_ID:
                invariant_errors.append("Proposal evidence source_id is not canonical.")
            if evidence.get("fragment_id") != FRAGMENT_ID:
                invariant_errors.append("Proposal evidence fragment_id is not canonical.")
            if evidence.get("source_sha256") != source_sha256:
                invariant_errors.append("Proposal source digest does not match the registered source.")
            if evidence.get("fragment_sha256") != source_metadata.get("fragments", [{}])[0].get(
                "fragment_sha256"
            ):
                invariant_errors.append("Proposal fragment digest does not match the registered source.")
            run_id = evidence.get("run_id")
            run_dir = report_dir / "runs" / str(run_id)
            for name, evidence_field in (
                ("model-request.json", "request_sha256"),
                ("raw-response.txt", "raw_response_sha256"),
            ):
                try:
                    actual = _sha256_bytes((run_dir / name).read_bytes())
                except OSError as exc:
                    invariant_errors.append(f"Run evidence {name} cannot be read: {exc}")
                else:
                    if evidence.get(evidence_field) != actual:
                        invariant_errors.append(
                            f"Proposal {evidence_field} does not match run evidence."
                        )

    result = {
        "schema_version": "1.0",
        "validation_id": f"{proposal_id}-validation",
        "proposal_id": proposal_id,
        "proposal_sha256": _sha256_bytes(proposal_bytes),
        "validator_version": "1.0",
        "syntactic_gate": {
            "status": "passed" if not syntactic_errors else "failed",
            "errors": syntactic_errors,
        },
        "invariant_gate": {
            "status": "passed" if not invariant_errors else "failed",
            "errors": invariant_errors,
        },
        "errors": syntactic_errors + invariant_errors,
        "valid": not (syntactic_errors or invariant_errors),
        "checked_at": _now(),
    }
    if output_path.exists():
        raise WorkflowError("The immutable validation result already exists.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result


def _validate_review_bindings(
    *,
    proposal_id: str,
    proposal_sha256: str,
    validation: dict,
    validation_bytes: bytes,
    review: dict,
) -> None:
    if not validation.get("valid"):
        raise WorkflowError("The candidate did not pass deterministic validation.")
    if validation.get("proposal_id") != proposal_id:
        raise WorkflowError("Validation references a different proposal_id.")
    if validation.get("proposal_sha256") != proposal_sha256:
        raise WorkflowError("Validation does not bind the current proposal bytes.")
    if review.get("schema_version") != "1.0":
        raise WorkflowError("Semantic review schema_version must be 1.0.")
    if review.get("proposal_id") != proposal_id:
        raise WorkflowError("Semantic review references a different proposal_id.")
    if review.get("proposal_sha256") != proposal_sha256:
        raise WorkflowError("Semantic review does not bind the current proposal bytes.")
    if review.get("validation_id") != validation.get("validation_id"):
        raise WorkflowError("Semantic review references a different validation_id.")
    if review.get("validation_sha256") != _sha256_bytes(validation_bytes):
        raise WorkflowError("Semantic review does not bind the current validation result.")
    if review.get("verdict") not in {"acceptable", "unsupported"}:
        raise WorkflowError("Semantic review verdict must be acceptable or unsupported.")
    findings = review.get("findings")
    if not isinstance(findings, dict):
        raise WorkflowError("Semantic review must contain separate findings.")
    for finding in ("definition", "control_gates", "authority_boundary"):
        if not isinstance(findings.get(finding), str) or not findings[finding].strip():
            raise WorkflowError(f"Semantic review finding {finding} must be non-empty.")
    for field in ("review_id", "rationale", "reviewed_by"):
        if not isinstance(review.get(field), str) or not review[field].strip():
            raise WorkflowError(f"Semantic review {field} must be a non-empty string.")


def record_decision(
    *,
    vault: Path,
    proposal_id: str,
    validation_path: Path,
    review_path: Path,
    status: str,
    recorded_by: str,
    reason: str | None = None,
    course_root: Path | None = None,
) -> Path:
    """Record one immutable decision bound to proposal, validation, and review bytes."""
    _resolve_vault(vault, course_root)
    _confine_proposal_id(proposal_id)
    if status not in {"approved", "rejected"}:
        raise WorkflowError("Decision status must be approved or rejected.")
    if not isinstance(recorded_by, str) or not recorded_by.strip():
        raise WorkflowError("Decision must name the human who recorded it.")
    proposal_path = vault / "proposals" / f"{proposal_id}.md"
    try:
        proposal_bytes = proposal_path.read_bytes()
    except OSError as exc:
        raise WorkflowError(f"Proposal cannot be read: {exc}") from exc
    proposal_sha256 = _sha256_bytes(proposal_bytes)
    validation, validation_bytes = _read_json_object(validation_path, "Validation result")
    review, review_bytes = _read_yaml_object(review_path, "Semantic review")
    _validate_review_bindings(
        proposal_id=proposal_id,
        proposal_sha256=proposal_sha256,
        validation=validation,
        validation_bytes=validation_bytes,
        review=review,
    )
    if status == "approved" and review["verdict"] != "acceptable":
        raise WorkflowError("Only a semantically acceptable candidate may be approved.")
    if status == "rejected" and (not isinstance(reason, str) or not reason.strip()):
        raise WorkflowError("A rejected decision must include a non-empty reason.")

    decision_id = f"{proposal_id}-decision"
    decision_path = vault / "decisions" / f"{decision_id}.md"
    if decision_path.exists():
        raise WorkflowError("The immutable decision record already exists.")
    metadata = {
        "schema_version": "1.0",
        "record_type": "decision",
        "decision_id": decision_id,
        "status": status,
        "proposal_id": proposal_id,
        "proposal_sha256": proposal_sha256,
        "validation_id": validation["validation_id"],
        "validation_sha256": _sha256_bytes(validation_bytes),
        "review_id": review["review_id"],
        "semantic_review_sha256": _sha256_bytes(review_bytes),
        "rationale": reason.strip() if isinstance(reason, str) else review["rationale"].strip(),
        "recorded_by": recorded_by.strip(),
        "recorded_at": _now(),
    }
    body = (
        f"# Decision for {proposal_id}\n\n"
        f"Status: **{status}**\n\n"
        f"Rationale: {metadata['rationale']}\n"
    )
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    decision_path.write_text(_render_markdown_record(metadata, body), encoding="utf-8")
    return decision_path


def _live_ancestor(vault: Path, proposal_metadata: dict) -> bool:
    """Return True when the proposal descends from a live model-normalized run."""
    current = proposal_metadata
    seen: set[str] = set()
    while True:
        origin = current.get("origin")
        evidence = current.get("evidence")
        if not isinstance(evidence, dict):
            raise WorkflowError("Proposal lacks evidence bindings.")
        if origin == "model-normalized":
            return evidence.get("evidence_kind") == "live"
        derived_from = current.get("derived_from")
        if not isinstance(derived_from, dict):
            raise WorkflowError("Human-revised proposal lacks derived_from ancestry.")
        parent_id = derived_from.get("proposal_id")
        parent_sha = derived_from.get("proposal_sha256")
        if not isinstance(parent_id, str) or not isinstance(parent_sha, str):
            raise WorkflowError("Human-revised proposal has incomplete ancestry.")
        if parent_id in seen:
            raise WorkflowError("Proposal ancestry contains a cycle.")
        seen.add(parent_id)
        parent_path = vault / "proposals" / f"{parent_id}.md"
        parent_bytes = parent_path.read_bytes()
        if _sha256_bytes(parent_bytes) != parent_sha:
            raise WorkflowError("Proposal parent digest does not match the immutable parent.")
        current, _ = _read_markdown_record(parent_path)


def apply_candidate(
    *,
    vault: Path,
    proposal_id: str,
    validation_path: Path,
    review_path: Path,
    course_root: Path | None = None,
) -> tuple[Path, Path]:
    """Apply one exactly approved, live-descended candidate without overwriting."""
    _resolve_vault(vault, course_root)
    _confine_proposal_id(proposal_id)
    proposal_path = vault / "proposals" / f"{proposal_id}.md"
    decision_path = vault / "decisions" / f"{proposal_id}-decision.md"
    concept_path = vault / CONCEPT_RELATIVE_PATH
    operation_id = f"{proposal_id}-apply"
    operation_path = vault / "operations" / f"{operation_id}.md"
    if concept_path.exists():
        raise WorkflowError("Accepted concept already exists and will not be overwritten.")
    if operation_path.exists():
        raise WorkflowError("Application operation already exists and will not be overwritten.")

    try:
        proposal_bytes = proposal_path.read_bytes()
        proposal_metadata, proposal_body = _read_markdown_record(proposal_path)
        candidate = _proposal_payload(proposal_body)
        decision_bytes = decision_path.read_bytes()
        decision, _ = _read_markdown_record(decision_path)
    except OSError as exc:
        raise WorkflowError(f"Application input cannot be read: {exc}") from exc

    if not _live_ancestor(vault, proposal_metadata):
        raise WorkflowError("Application requires a candidate that descends from a live response.")

    source_path = vault / SOURCE_RELATIVE_PATH
    try:
        source_bytes = source_path.read_bytes()
        source_metadata, _ = _read_source_record(vault)
    except (OSError, WorkflowError) as exc:
        raise WorkflowError(f"Registered source cannot be read: {exc}") from exc
    evidence = proposal_metadata.get("evidence")
    if not isinstance(evidence, dict):
        raise WorkflowError("Proposal lacks evidence bindings.")
    if evidence.get("source_sha256") != _sha256_bytes(source_bytes):
        raise WorkflowError("Registered source bytes changed after proposal creation.")
    if evidence.get("fragment_sha256") != source_metadata["fragments"][0]["fragment_sha256"]:
        raise WorkflowError("Registered source fragment changed after proposal creation.")

    proposal_sha256 = _sha256_bytes(proposal_bytes)
    validation, validation_bytes = _read_json_object(validation_path, "Validation result")
    review, review_bytes = _read_yaml_object(review_path, "Semantic review")
    _validate_review_bindings(
        proposal_id=proposal_id,
        proposal_sha256=proposal_sha256,
        validation=validation,
        validation_bytes=validation_bytes,
        review=review,
    )
    if review["verdict"] != "acceptable":
        raise WorkflowError("Application requires an acceptable semantic review.")
    expected_decision = {
        "proposal_id": proposal_id,
        "proposal_sha256": proposal_sha256,
        "validation_id": validation["validation_id"],
        "validation_sha256": _sha256_bytes(validation_bytes),
        "review_id": review["review_id"],
        "semantic_review_sha256": _sha256_bytes(review_bytes),
        "status": "approved",
    }
    for field, expected in expected_decision.items():
        if decision.get(field) != expected:
            raise WorkflowError(f"Decision {field} does not bind the current application inputs.")

    accepted_at = _now()
    concept_metadata = {
        "schema_version": "1.0",
        "record_type": "concept",
        "concept_id": CONCEPT_ID,
        "title": "Structured Output",
        "tags": ["record/concept", *candidate["tags"]],
        "definition": candidate["definition"],
        "key_points": candidate["key_points"],
        "source_support": candidate["source_support"],
        "accepted_from": {
            "proposal_id": proposal_id,
            "proposal_sha256": proposal_sha256,
            "decision_id": decision["decision_id"],
            "decision_sha256": _sha256_bytes(decision_bytes),
        },
        "accepted_at": accepted_at,
    }
    support_sections = []
    for item in candidate["source_support"]:
        support_sections.append(
            f"### {item['claim_kind']}\n\n{item['claim']}\n\n> {item['quote']}\n"
        )
    concept_body = (
        "# Structured Output\n\n"
        + candidate["definition"]
        + "\n\n## Key points\n\n"
        + "".join(f"- {point}\n" for point in candidate["key_points"])
        + "\n## Source support\n\n"
        + "\n".join(support_sections)
    )
    concept_bytes = _render_markdown_record(concept_metadata, concept_body).encode("utf-8")
    operation_metadata = {
        "schema_version": "1.0",
        "record_type": "operation",
        "operation_id": operation_id,
        "status": "applied",
        "action": "create",
        "target_path": CONCEPT_RELATIVE_PATH.as_posix(),
        "proposal_id": proposal_id,
        "proposal_sha256": proposal_sha256,
        "decision_id": decision["decision_id"],
        "decision_sha256": _sha256_bytes(decision_bytes),
        "concept_sha256": _sha256_bytes(concept_bytes),
        "applied_at": accepted_at,
    }
    operation_bytes = _render_markdown_record(
        operation_metadata,
        f"# Application operation {operation_id}\n\n"
        "Created `concepts/structured-output.md` from the exactly approved candidate.\n",
    ).encode("utf-8")
    concept_path.parent.mkdir(parents=True, exist_ok=True)
    operation_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        concept_path.write_bytes(concept_bytes)
        operation_path.write_bytes(operation_bytes)
    except OSError as exc:
        concept_path.unlink(missing_ok=True)
        operation_path.unlink(missing_ok=True)
        raise WorkflowError(f"Accepted records could not be written: {exc}") from exc
    return concept_path, operation_path


def record_run_metadata(
    *,
    report_dir: Path,
    run_id: str,
    evidence_kind: str,
    adapter: str,
    model_id: str,
    recorded_by: str,
) -> Path:
    """Bind declared run attribution to exact request and response bytes."""
    if not SLUG_RE.fullmatch(run_id):
        raise WorkflowError("run_id must be a lowercase slug without spaces.")
    if evidence_kind not in {"live", "fixture"}:
        raise WorkflowError("evidence_kind must be live or fixture.")
    if adapter not in {"agy", "openai-compatible", "offline-fixture"}:
        raise WorkflowError("adapter is not supported by the Laboratory 02 evidence contract.")
    if evidence_kind == "live" and adapter == "offline-fixture":
        raise WorkflowError("Offline fixture evidence cannot be declared live.")
    for field_name, value in (("model_id", model_id), ("recorded_by", recorded_by)):
        if not isinstance(value, str) or not value.strip():
            raise WorkflowError(f"{field_name} must be a non-empty string.")
    run_dir = report_dir / "runs" / run_id
    request_path = run_dir / "model-request.json"
    raw_path = run_dir / "raw-response.txt"
    try:
        request_bytes = request_path.read_bytes()
        request = json.loads(request_bytes)
        raw_bytes = raw_path.read_bytes()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"Run evidence cannot be recorded: {exc}") from exc
    if not isinstance(request, dict):
        raise WorkflowError("Model request must contain one JSON object.")
    metadata_path = run_dir / "run-metadata.json"
    if metadata_path.exists():
        raise WorkflowError("The immutable run metadata already exists.")
    metadata = {
        "schema_version": "1.0",
        "run_id": run_id,
        "evidence_kind": evidence_kind,
        "adapter": adapter,
        "model_id": model_id.strip(),
        "request_id": request.get("request_id"),
        "request_sha256": _sha256_bytes(request_bytes),
        "raw_response_sha256": _sha256_bytes(raw_bytes),
        "recorded_at": _now(),
        "recorded_by": recorded_by.strip(),
        "attribution_limit": "Declared run metadata is not cryptographic proof of external inference.",
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return metadata_path


def _structural_differences(raw_a: bytes, raw_b: bytes) -> dict:
    try:
        obj_a = json.loads(raw_a)
        obj_b = json.loads(raw_b)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "raw_bytes_differ": raw_a != raw_b,
            "top_level_keys_differ": None,
            "definition_differs": None,
            "key_points_differs": None,
            "source_support_quotes_differ": None,
        }
    a_dict = obj_a if isinstance(obj_a, dict) else {}
    b_dict = obj_b if isinstance(obj_b, dict) else {}
    return {
        "raw_bytes_differ": raw_a != raw_b,
        "top_level_keys_differ": set(a_dict) != set(b_dict),
        "definition_differs": a_dict.get("definition") != b_dict.get("definition"),
        "key_points_differs": a_dict.get("key_points") != b_dict.get("key_points"),
        "source_support_quotes_differ": [
            s.get("quote") if isinstance(s, dict) else None
            for s in a_dict.get("source_support", [])
        ]
        != [s.get("quote") if isinstance(s, dict) else None for s in b_dict.get("source_support", [])],
    }


def compare_live_runs(
    *,
    vault: Path,
    report_dir: Path,
    run_ids: tuple[str, str],
    output_path: Path,
    course_root: Path | None = None,
) -> dict:
    """Compare two separately recorded live runs of the same exact request."""
    _resolve_vault(vault, course_root)
    if len(set(run_ids)) != 2:
        raise WorkflowError("Live comparison requires two distinct run IDs.")
    runs: list[dict] = []
    raw_pairs: list[bytes] = []
    for run_id in run_ids:
        run_dir = report_dir / "runs" / run_id
        metadata, _ = _read_json_object(run_dir / "run-metadata.json", "Run metadata")
        if metadata.get("run_id") != run_id or metadata.get("evidence_kind") != "live":
            raise WorkflowError("Live comparison requires metadata for the selected live run.")
        request_bytes = (run_dir / "model-request.json").read_bytes()
        raw_bytes = (run_dir / "raw-response.txt").read_bytes()
        if metadata.get("request_sha256") != _sha256_bytes(request_bytes):
            raise WorkflowError("Run metadata request digest does not match current bytes.")
        if metadata.get("raw_response_sha256") != _sha256_bytes(raw_bytes):
            raise WorkflowError("Run metadata raw-response digest does not match current bytes.")
        proposal_id = f"{PROPOSAL_ID_PREFIX}{run_id}"
        proposal_path = vault / "proposals" / f"{proposal_id}.md"
        try:
            proposal_sha256 = _sha256_bytes(proposal_path.read_bytes())
        except OSError as exc:
            raise WorkflowError(f"Live proposal cannot be read: {exc}") from exc
        runs.append(
            {
                "run_id": run_id,
                "adapter": metadata["adapter"],
                "model_id": metadata["model_id"],
                "request_sha256": metadata["request_sha256"],
                "raw_response_sha256": metadata["raw_response_sha256"],
                "proposal_id": proposal_id,
                "proposal_sha256": proposal_sha256,
            }
        )
        raw_pairs.append(raw_bytes)
    if runs[0]["request_sha256"] != runs[1]["request_sha256"]:
        raise WorkflowError("Live runs must use identical model-request bytes.")
    same_model = (
        runs[0]["adapter"] == runs[1]["adapter"]
        and runs[0]["model_id"] == runs[1]["model_id"]
    )
    comparison = {
        "schema_version": "1.0",
        "comparison_id": "lab02-live-comparison",
        "comparison_kind": "same-model-variability" if same_model else "fallback-portability",
        "run_ids": list(run_ids),
        "request_sha256": runs[0]["request_sha256"],
        "runs": runs,
        "structural_differences": _structural_differences(raw_pairs[0], raw_pairs[1]),
        "generated_at": _now(),
    }
    if output_path.exists():
        raise WorkflowError("The immutable live comparison already exists.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return comparison


def _vault_snapshot(vault: Path) -> dict[str, str]:
    return {
        path.relative_to(vault).as_posix(): _sha256_bytes(path.read_bytes())
        for path in sorted(vault.rglob("*"))
        if path.is_file()
    }


def _verify_approved_fixtures(vault: Path, report_dir: Path, fixture_dir: Path) -> None:
    expected = {
        "valid-response.json",
        "malformed-response.txt",
        "semantic-unsupported-response.json",
    }
    _require(
        expected == {path.name for path in fixture_dir.iterdir() if path.is_file()},
        "Approved Laboratory 02 fixture set is incomplete or contains unexpected files.",
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        temp_vault = temp_root / "vault"
        temp_report = temp_root / "reports/lab02"
        source_target = temp_vault / SOURCE_RELATIVE_PATH
        source_target.parent.mkdir(parents=True)
        shutil.copy2(vault / SOURCE_RELATIVE_PATH, source_target)

        for run_id, filename in (
            ("fixture-valid", "valid-response.json"),
            ("fixture-unsupported", "semantic-unsupported-response.json"),
        ):
            prepare_request(vault=temp_vault, report_dir=temp_report, run_id=run_id)
            raw_path = temp_report / "runs" / run_id / "raw-response.txt"
            shutil.copy2(fixture_dir / filename, raw_path)
            proposal_path = import_response(
                vault=temp_vault,
                report_dir=temp_report,
                run_id=run_id,
                evidence_kind="fixture",
            )
            result = validate_candidate(
                vault=temp_vault,
                report_dir=temp_report,
                proposal_id=proposal_path.stem,
                output_path=temp_report / "runs" / run_id / "validation-result.json",
            )
            _require(result["valid"], f"Approved fixture {filename} is structurally invalid.")

        malformed_run = "fixture-malformed"
        prepare_request(vault=temp_vault, report_dir=temp_report, run_id=malformed_run)
        malformed_raw = temp_report / "runs" / malformed_run / "raw-response.txt"
        shutil.copy2(fixture_dir / "malformed-response.txt", malformed_raw)
        try:
            import_response(
                vault=temp_vault,
                report_dir=temp_report,
                run_id=malformed_run,
                evidence_kind="fixture",
            )
        except WorkflowError:
            pass
        else:
            raise WorkflowError("Malformed fixture was not rejected at the syntactic gate.")
        _require(
            not (temp_vault / "proposals" / f"{PROPOSAL_ID_PREFIX}fixture-malformed.md").exists(),
            "Malformed fixture created a proposal record.",
        )
        _require(
            not (temp_vault / CONCEPT_RELATIVE_PATH).exists(),
            "Fixture verification changed accepted knowledge.",
        )


def check_approved_fixtures(
    *,
    vault: Path,
    course_root: Path | None = None,
    fixture_dir: Path | None = None,
) -> dict[str, str]:
    """Exercise all approved offline fixtures without changing accepted state."""
    if fixture_dir is None:
        fixture_dir = Path(__file__).resolve().parent.parent.parent / "fixtures" / "lab02"
    resolved_vault = _resolve_vault(vault, course_root)
    before = _vault_snapshot(resolved_vault)
    _verify_approved_fixtures(resolved_vault, Path(), fixture_dir)
    _require(_vault_snapshot(resolved_vault) == before, "Fixture checks changed vault bytes.")
    return {
        "valid-response.json": "passed deterministic gates",
        "malformed-response.txt": "refused at syntactic gate",
        "semantic-unsupported-response.json": (
            "passed deterministic gates; semantic review required"
        ),
        "accepted state": "unchanged",
    }


def _discover_git_root(start: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def course_tree_drift(git_root: Path) -> list[str]:
    """Return changed paths outside the two student-owned project areas."""
    try:
        tracked = subprocess.run(
            ["git", "-C", str(git_root), "diff", "--name-only", "HEAD", "--"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        untracked = subprocess.run(
            ["git", "-C", str(git_root), "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise WorkflowError(f"Course repository state cannot be inspected: {exc}") from exc

    def student_owned(path: str) -> bool:
        normalized = "/" + path.strip("/") + "/"
        return "/training-project/reports/" in normalized or "/training-project/student/" in normalized

    return sorted({path for path in [*tracked, *untracked] if path and not student_owned(path)})


def _forbidden_canonical_fields(metadata: dict) -> list[str]:
    offenders = []
    for key in metadata:
        lowered = key.lower()
        if any(fragment in lowered for fragment in FORBIDDEN_CANONICAL_KEY_FRAGMENTS):
            offenders.append(key)
    return offenders


def verify_lab02(
    *,
    vault: Path,
    report_dir: Path,
    course_root: Path | None = None,
    fixture_dir: Path | None = None,
) -> dict:
    """Verify the complete Laboratory 02 evidence chain without mutating the vault."""
    if fixture_dir is None:
        fixture_dir = Path(__file__).resolve().parent.parent.parent / "fixtures" / "lab02"
    resolved_vault = _resolve_vault(vault, course_root)
    try:
        before = _vault_snapshot(resolved_vault)
    except OSError as exc:
        raise Lab02InputError(f"Vault cannot be read: {exc}") from exc
    if not (report_dir / "runs").exists() and not (report_dir / "REPORT.md").exists():
        raise Lab02InputError("Report directory does not contain Laboratory 02 evidence.")

    checks: list[dict] = []
    context: dict[str, object] = {}
    artifacts: dict[str, str] = {}

    def check(check_id: str, action) -> None:
        try:
            detail = action()
        except Exception as exc:  # Each check must be reported instead of hiding later failures.
            checks.append({"check_id": check_id, "status": "failed", "message": str(exc)})
        else:
            checks.append({"check_id": check_id, "status": "passed", "message": detail or "verified"})

    def verify_source() -> str:
        source_path = resolved_vault / SOURCE_RELATIVE_PATH
        source_metadata, fragment = _read_source_record(resolved_vault)
        _require(source_metadata.get("course_commit"), "Source lacks course_commit.")
        _require(source_metadata.get("course_path") == COURSE_PATH, "Source course_path is not canonical.")
        artifacts[f"vault/{SOURCE_RELATIVE_PATH.as_posix()}"] = _sha256_bytes(source_path.read_bytes())
        context["source_metadata"] = source_metadata
        return "registered source and exact fragment digest match"

    check("source", verify_source)

    def verify_course_commit() -> str:
        source_metadata = context["source_metadata"]
        course_commit = source_metadata.get("course_commit")
        base = course_root if course_root is not None else Path.cwd()
        git_root = _discover_git_root(base)
        if git_root is None:
            return "course commit not compared: no git repository discovered"
        head = subprocess.run(
            ["git", "-C", str(git_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        _require(head == course_commit, "Registered course commit does not match git HEAD.")
        drift = course_tree_drift(git_root)
        _require(
            not drift,
            "Upstream-owned course paths differ from the registered commit: " + ", ".join(drift),
        )
        return "registered course commit matches git HEAD and upstream-owned paths are unchanged"

    check("course-commit", verify_course_commit)

    check(
        "approved-fixtures",
        lambda: (
            _verify_approved_fixtures(resolved_vault, report_dir, fixture_dir)
            or "three approved fixtures verified"
        ),
    )

    def verify_live_comparison() -> str:
        comparison, _ = _read_json_object(report_dir / "live-comparison.json", "Live comparison")
        run_ids = comparison.get("run_ids")
        _require(
            isinstance(run_ids, list) and len(run_ids) == 2 and len(set(run_ids)) == 2,
            "Live comparison must identify two distinct run IDs.",
        )
        runs = comparison.get("runs")
        _require(isinstance(runs, list) and len(runs) == 2, "Live comparison needs two runs.")
        proposal_ids: list[str] = []
        request_digests: list[str] = []
        raw_digests: list[str] = []
        adapters_and_models: list[tuple[str, str]] = []
        for run_id, run in zip(run_ids, runs, strict=True):
            _require(isinstance(run, dict) and run.get("run_id") == run_id, "Run order differs.")
            run_dir = report_dir / "runs" / run_id
            metadata, _ = _read_json_object(run_dir / "run-metadata.json", "Run metadata")
            _require(metadata.get("evidence_kind") == "live", "Comparison includes a fixture run.")
            request_digest = _sha256_bytes((run_dir / "model-request.json").read_bytes())
            raw_digest = _sha256_bytes((run_dir / "raw-response.txt").read_bytes())
            _require(metadata.get("request_sha256") == request_digest, "Request digest changed.")
            _require(metadata.get("raw_response_sha256") == raw_digest, "Raw digest changed.")
            proposal_id = f"{PROPOSAL_ID_PREFIX}{run_id}"
            proposal_digest = _sha256_bytes(
                (resolved_vault / "proposals" / f"{proposal_id}.md").read_bytes()
            )
            _require(run.get("proposal_sha256") == proposal_digest, "Proposal digest changed.")
            _require(run.get("request_sha256") == request_digest, "Comparison request changed.")
            _require(run.get("raw_response_sha256") == raw_digest, "Comparison raw changed.")
            proposal_ids.append(proposal_id)
            request_digests.append(request_digest)
            raw_digests.append(raw_digest)
            adapters_and_models.append((str(metadata.get("adapter")), str(metadata.get("model_id"))))
        _require(len(set(request_digests)) == 1, "Live requests are not byte-identical.")
        expected_kind = (
            "same-model-variability"
            if len(set(adapters_and_models)) == 1
            else "fallback-portability"
        )
        _require(
            comparison.get("comparison_kind") == expected_kind,
            "Live comparison kind does not match adapter and model metadata.",
        )
        _require(
            isinstance(comparison.get("structural_differences"), dict),
            "Live comparison lacks deterministic structural differences.",
        )
        context["live_proposal_ids"] = proposal_ids
        context["comparison"] = comparison
        context["comparison_kind"] = expected_kind
        context["live_run_ids"] = run_ids
        return f"two live runs verified as {expected_kind}"

    check("live-comparison", verify_live_comparison)

    def verify_selected_candidate() -> str:
        review, review_bytes = _read_yaml_object(report_dir / "semantic-review.yaml", "Semantic review")
        proposal_id = review.get("proposal_id")
        _require(isinstance(proposal_id, str), "Semantic review lacks proposal_id.")
        _confine_proposal_id(proposal_id)
        proposal_path = resolved_vault / "proposals" / f"{proposal_id}.md"
        proposal_bytes = proposal_path.read_bytes()
        proposal_sha256 = _sha256_bytes(proposal_bytes)
        validation_path = None
        for candidate_path in report_dir.rglob("validation-result.json"):
            if _sha256_bytes(candidate_path.read_bytes()) == review.get("validation_sha256"):
                validation_path = candidate_path
                break
        _require(validation_path is not None, "Review-bound validation result was not found.")
        validation, validation_bytes = _read_json_object(validation_path, "Selected validation result")
        _validate_review_bindings(
            proposal_id=proposal_id,
            proposal_sha256=proposal_sha256,
            validation=validation,
            validation_bytes=validation_bytes,
            review=review,
        )
        _require(review.get("verdict") == "acceptable", "Selected review is not acceptable.")
        proposal_metadata, _ = _read_markdown_record(proposal_path)
        _require(
            _live_ancestor(resolved_vault, proposal_metadata),
            "Selected candidate does not descend from a live run.",
        )
        context.update(
            {
                "proposal_id": proposal_id,
                "proposal_sha256": proposal_sha256,
                "validation_id": validation.get("validation_id"),
                "validation_bytes": validation_bytes,
                "review": review,
                "review_bytes": review_bytes,
                "proposal_metadata": proposal_metadata,
            }
        )
        return "selected candidate is valid, acceptable, and descends from a live run"

    check("selected-candidate", verify_selected_candidate)

    def verify_decision_and_state() -> str:
        proposal_id = str(context["proposal_id"])
        proposal_sha256 = str(context["proposal_sha256"])
        validation_bytes = context["validation_bytes"]
        review_bytes = context["review_bytes"]
        _require(isinstance(validation_bytes, bytes), "Validation bytes are unavailable.")
        _require(isinstance(review_bytes, bytes), "Review bytes are unavailable.")
        decision_path = resolved_vault / "decisions" / f"{proposal_id}-decision.md"
        decision_bytes = decision_path.read_bytes()
        decision, _ = _read_markdown_record(decision_path)
        _require(decision.get("status") == "approved", "Decision is not approved.")
        _require(decision.get("proposal_sha256") == proposal_sha256, "Decision proposal changed.")
        _require(
            decision.get("validation_sha256") == _sha256_bytes(validation_bytes),
            "Decision validation changed.",
        )
        _require(
            decision.get("semantic_review_sha256") == _sha256_bytes(review_bytes),
            "Decision review changed.",
        )
        concept_path = resolved_vault / CONCEPT_RELATIVE_PATH
        concept_bytes = concept_path.read_bytes()
        concept, _ = _read_markdown_record(concept_path)
        operation_id = f"{proposal_id}-apply"
        operation_path = resolved_vault / "operations" / f"{operation_id}.md"
        operation, _ = _read_markdown_record(operation_path)
        accepted_from = concept.get("accepted_from")
        _require(isinstance(accepted_from, dict), "Concept lacks accepted_from bindings.")
        _require(
            accepted_from.get("proposal_sha256") == proposal_sha256, "Concept proposal changed."
        )
        _require(
            accepted_from.get("decision_sha256") == _sha256_bytes(decision_bytes),
            "Concept decision changed.",
        )
        _require(concept.get("concept_id") == CONCEPT_ID, "Concept concept_id is not canonical.")
        _require(
            operation.get("concept_sha256") == _sha256_bytes(concept_bytes),
            "Operation concept digest differs from accepted concept bytes.",
        )
        _require(operation.get("status") == "applied", "Operation status is not applied.")
        _require(operation.get("action") == "create", "Operation action is not create.")
        _require(operation.get("decision_sha256") == _sha256_bytes(decision_bytes), "Operation decision changed.")
        apply_operations = list((resolved_vault / "operations").glob("*-apply.md"))
        _require(len(apply_operations) == 1, "More than one successful apply operation exists.")
        return "approval, concept, and operation digest chain matches"

    check("accepted-state", verify_decision_and_state)

    def verify_provider_isolation() -> str:
        canonical_paths = [
            resolved_vault / SOURCE_RELATIVE_PATH,
            *(resolved_vault / "proposals").glob("*.md"),
            *(resolved_vault / "decisions").glob("*.md"),
            *(resolved_vault / "operations").glob("*.md"),
            resolved_vault / CONCEPT_RELATIVE_PATH,
        ]
        offenders: list[str] = []
        for path in canonical_paths:
            metadata, _ = _read_markdown_record(path)
            for key in _forbidden_canonical_fields(metadata):
                offenders.append(f"{path.relative_to(resolved_vault)}:{key}")
        _require(not offenders, "Canonical records contain provider/model/harness fields: " + ", ".join(offenders))
        return "canonical records are free of provider, model, and harness fields"

    check("provider-isolation", verify_provider_isolation)

    def verify_submission_files() -> str:
        names = (
            "01-offline-gates.png",
            "02-refusal-unchanged.png",
            "03-live-comparison.png",
            "04-review-decision.png",
            "05-controlled-apply.png",
            "06-final-result.png",
        )
        report_text = (report_dir / "REPORT.md").read_text(encoding="utf-8")
        for name in names:
            screenshot = report_dir / "screenshots" / name
            _require(screenshot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), f"{name} is not PNG.")
            _require(name in report_text, f"REPORT.md does not reference {name}.")
        return "REPORT.md references all six required PNG screenshots"

    check("submission-files", verify_submission_files)

    def build_artifact_map() -> str:
        for path in sorted(report_dir.rglob("*")):
            if path.is_file() and path.name != "verification-report.json":
                artifacts[f"report/{path.relative_to(report_dir).as_posix()}"] = _sha256_bytes(
                    path.read_bytes()
                )
        for record_type in ("sources", "proposals", "decisions", "operations", "concepts"):
            record_dir = resolved_vault / record_type
            for path in sorted(record_dir.rglob("*.md")):
                artifacts[f"vault/{path.relative_to(resolved_vault).as_posix()}"] = _sha256_bytes(
                    path.read_bytes()
                )
        return f"{len(artifacts)} artifacts mapped by path and digest"

    check("artifact-map", build_artifact_map)
    check(
        "vault-read-only",
        lambda: (
            "vault bytes remained unchanged"
            if _vault_snapshot(resolved_vault) == before
            else (_ for _ in ()).throw(WorkflowError("Final verifier changed vault bytes."))
        ),
    )

    status = "passed" if all(item["status"] == "passed" for item in checks) else "failed"
    source_metadata = context.get("source_metadata")
    report = {
        "schema_version": "1.0",
        "lab_id": "lab02",
        "status": status,
        "generated_at": _now(),
        "course_commit": (
            source_metadata.get("course_commit") if isinstance(source_metadata, dict) else None
        ),
        "live_runs": context.get("live_run_ids"),
        "comparison_kind": context.get("comparison_kind"),
        "selected_candidate": {
            "proposal_id": context.get("proposal_id"),
            "proposal_sha256": context.get("proposal_sha256"),
            "validation_id": context.get("validation_id"),
            "origin": (
                context.get("proposal_metadata", {}).get("origin")
                if isinstance(context.get("proposal_metadata"), dict)
                else None
            ),
        },
        "artifacts": artifacts,
        "checks": checks,
        "summary": {
            "passed": sum(item["status"] == "passed" for item in checks),
            "failed": sum(item["status"] == "failed" for item in checks),
        },
    }
    output_path = report_dir / "verification-report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report
