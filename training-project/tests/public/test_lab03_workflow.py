import json
import tempfile
import unittest
from pathlib import Path

import yaml

from learning_project.lab03 import (
    ExposureLedger,
    build_blinded_index,
    build_positions,
    check_near_duplicates,
    classify_failure,
    close_unstarted_positions,
    freeze_protocol,
    ingest_curator_candidate,
    load_family,
    record_assessment,
    record_completion_status,
    record_recommendation,
    record_regression,
    record_selected_comparison,
    record_transfer_case,
    record_variant_b,
    run_position,
    select_family,
    start_calibration,
    structural_check,
    submit_calibration,
    verify_lab03,
)
from learning_project.workflow import WorkflowError

TRAINING_PROJECT = Path(__file__).resolve().parent.parent.parent
CASES = TRAINING_PROJECT / "cases" / "lab03"
RESERVES = CASES / "reserves"
INSTRUCTIONS = TRAINING_PROJECT / "instructions" / "lab03"
CALIBRATION = CASES / "calibration"
AUTHORED_FAILURE = CASES / "authored-failure" / "authored-failure.json"

STUDENT = "student-01"


def fixture_runner(request: dict) -> str:
    return json.dumps(
        {"case_id": request["case_id"], "proposed_text": "Fixture answer grounded in the source."},
        ensure_ascii=False,
    )


class Lab03FamilyContractTests(unittest.TestCase):
    def test_all_course_reserve_families_load(self) -> None:
        families = [load_family(p) for p in sorted(RESERVES.glob("*/family.json"))]
        self.assertEqual(len(families), 3)
        check_near_duplicates(families)

    def test_development_inputs_load_with_two_cases(self) -> None:
        family = load_family(CASES / "development" / "dev-common-inputs.json", expected_cases=2)
        self.assertEqual(len(family["cases"]), 2)

    def test_family_with_a_missing_evidence_situation_is_rejected(self) -> None:
        family = load_family(RESERVES / "reserve-criteria-chain" / "family.json")
        family["cases"] = family["cases"][:3]
        family["expected_behaviors"] = family["expected_behaviors"][:3]
        path = Path(tempfile.mkdtemp()) / "broken-family.json"
        path.write_text(json.dumps(family), encoding="utf-8")
        with self.assertRaises(WorkflowError):
            load_family(path)

    def test_near_duplicate_case_text_across_families_is_rejected(self) -> None:
        first = load_family(RESERVES / "reserve-criteria-chain" / "family.json")
        second = load_family(RESERVES / "reserve-experiment-discipline" / "family.json")
        second["cases"][0]["task"] = first["cases"][0]["task"]
        second["cases"][0]["supplied_source"] = first["cases"][0]["supplied_source"]
        with self.assertRaises(WorkflowError):
            check_near_duplicates([first, second])


class Lab03FailureClassificationTests(unittest.TestCase):
    def test_authentication_quota_and_rate_limit_are_route_wide(self) -> None:
        for message in (
            "openrouter authentication failed: key is not set",
            "HTTP 429: rate limit exceeded",
            "account quota exhausted",
        ):
            self.assertEqual(classify_failure(message), "route-wide")

    def test_malformed_output_is_position_specific(self) -> None:
        self.assertEqual(classify_failure("response is not valid JSON"), "position-specific")


class Lab03CalibrationTests(unittest.TestCase):
    def test_calibration_flow_compares_student_and_reviewed_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report_dir = Path(temp)
            path = start_calibration(
                report_dir=report_dir, packet_id="calibration-a", packets_dir=CALIBRATION, student=STUDENT
            )
            labels = yaml.safe_load(path.read_text(encoding="utf-8"))
            answers = {"cal-a-1": "S", "cal-a-2": "I", "cal-a-3": "U", "cal-a-4": "Q"}
            for item in labels["labels"]:
                item["category"] = answers[item["output_id"]]
                item["rationale"] = "test rationale"
            path.write_text(yaml.safe_dump(labels), encoding="utf-8")
            result = submit_calibration(
                report_dir=report_dir, packet_id="calibration-a", packets_dir=CALIBRATION, student=STUDENT
            )
            self.assertEqual(result["agreement"], 4)
            with self.assertRaises(WorkflowError):
                start_calibration(
                    report_dir=report_dir, packet_id="calibration-a", packets_dir=CALIBRATION, student=STUDENT
                )


class Lab03WorkflowTests(unittest.TestCase):
    def _prepare_development(self, report_dir: Path) -> None:
        record_transfer_case(
            report_dir=report_dir,
            transfer_case={
                "case_id": "transfer-approval",
                "task": "State who approves requests.",
                "supplied_source": "A supervisor approves requests.",
                "provenance": "public test scenario",
            },
            perturbation={
                "case_id": "transfer-approval-perturbed",
                "task": "State who approves requests.",
                "supplied_source": "A supervisor records requests.",
                "provenance": "public test scenario",
                "perturbation_note": "verb changed",
                "expectation": "authority claim must disappear",
            },
        )
        record_variant_b(
            report_dir=report_dir,
            variant_b_text="Variant B text for tests.",
            change_declaration={
                "changed_property": "length bound",
                "mechanism": "bounded paragraph",
                "declared_factors": ["length bound"],
            },
        )

    def _protocol(self) -> dict:
        return {
            "engineering_decision": "adopt B only if at least as supported as A",
            "hypothesis": "B reduces unsupported additions",
            "semantic_acceptance": "B has no more critical unsupported than A",
            "blocking_failures": "route-wide failure before eight positions",
            "attempt_budget": 16,
            "order_rule": "schedule order",
            "timing_boundary": "one session",
            "resume_window": "48h",
            "route": "offline fixture",
        }

    def test_full_heldout_lifecycle_reaches_passed_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report_dir = Path(temp)
            self._prepare_development(report_dir)
            ledger = ExposureLedger(report_dir / "exposure-ledger.json")
            manifest = freeze_protocol(
                report_dir=report_dir,
                protocol=self._protocol(),
                reserves_dir=RESERVES,
                ledger=ledger,
                student=STUDENT,
            )
            family = select_family(
                reserves_dir=RESERVES, ledger=ledger, freeze_manifest=manifest, student=STUDENT
            )
            comparison_dir = Path(manifest["comparison_dir"])
            positions = build_positions(comparison_dir=comparison_dir, family=family, kind="held-out")
            self.assertEqual(len(positions), 16)
            cases_by_id = {c["case_id"]: c for c in family["cases"]}
            instructions = {
                "a": (INSTRUCTIONS / "variant-a.txt").read_text(encoding="utf-8"),
                "b": (report_dir / "development" / "variant-b.txt").read_text(encoding="utf-8"),
            }
            for position in positions:
                result = run_position(
                    comparison_dir=comparison_dir,
                    schedule=json.loads((comparison_dir / "schedule.json").read_text(encoding="utf-8")),
                    position_id=position["position_id"],
                    cases_by_id=cases_by_id,
                    instructions=instructions,
                    runner=fixture_runner,
                    adapter="offline-fixture",
                    model_id="offline-fixture",
                    recorded_by=STUDENT,
                )
                self.assertEqual(result["outcome"], "returned")
            index = build_blinded_index(comparison_dir=comparison_dir, family=family)
            self.assertEqual(len(index["entries"]), 16)
            for entry in index["entries"]:
                record_assessment(
                    comparison_dir=comparison_dir,
                    blind_id=entry["blind_id"],
                    assessment={
                        "category": entry["expected_category"],
                        "source_pointer": "supplied source",
                        "rationale": "test rationale",
                    },
                )
            record_selected_comparison(
                report_dir=report_dir, comparison_id=manifest["freeze_id"], student=STUDENT
            )
            from learning_project.lab03 import aggregate as aggregate_lab03

            aggregate_lab03(comparison_dir=comparison_dir)
            record_recommendation(
                comparison_dir=comparison_dir,
                outcome="seek-more-evidence",
                rationale="fixture evidence carries no live signal",
                limitations=["offline fixture"],
                student=STUDENT,
            )
            record_regression(
                report_dir=report_dir,
                regression={
                    "regression_id": "test-regression",
                    "source_kind": "authored-fixture",
                    "fixture_id": "authored-failure-supported-plus-invented",
                    "model_authorship_claim": "none",
                    "diagnosis": "unsupported added claim",
                    "expected_behavior_review": "supported answers add nothing",
                    "reviewed_by": STUDENT,
                },
            )
            (report_dir / "REPORT.md").write_text("# Report\n", encoding="utf-8")
            record_completion_status(
                report_dir=report_dir,
                status="complete",
                detail={"executed_positions": 16},
            )
            verification = verify_lab03(report_dir=report_dir, final_commit="a" * 40)
            self.assertEqual(verification["outcome"], "passed-complete")

    def test_route_wide_failure_and_honest_partial_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report_dir = Path(temp)
            self._prepare_development(report_dir)
            ledger = ExposureLedger(report_dir / "exposure-ledger.json")
            manifest = freeze_protocol(
                report_dir=report_dir,
                protocol=self._protocol(),
                reserves_dir=RESERVES,
                ledger=ledger,
                student=STUDENT,
            )
            family = select_family(
                reserves_dir=RESERVES, ledger=ledger, freeze_manifest=manifest, student=STUDENT
            )
            comparison_dir = Path(manifest["comparison_dir"])
            build_positions(comparison_dir=comparison_dir, family=family, kind="held-out")

            def failing_runner(request: dict) -> str:
                raise RuntimeError("authentication failed for the route")

            result = run_position(
                comparison_dir=comparison_dir,
                schedule=json.loads((comparison_dir / "schedule.json").read_text(encoding="utf-8")),
                position_id=family["cases"][0]["case_id"] and f"pos-{family['cases'][0]['case_id']}-a-1",
                cases_by_id={c["case_id"]: c for c in family["cases"]},
                instructions={"a": "a", "b": "b"},
                runner=failing_runner,
                adapter="openrouter",
                model_id="test",
                recorded_by=STUDENT,
            )
            self.assertEqual(result, {
                "position_id": f"pos-{family['cases'][0]['case_id']}-a-1",
                "outcome": "failed",
                "failure_class": "route-wide",
            })
            closure = close_unstarted_positions(
                comparison_dir=comparison_dir, reason="route unavailable", student=STUDENT
            )
            self.assertEqual(len(closure["closed_positions"]), 15)
            (report_dir / "REPORT.md").write_text("Partial completion report.\n", encoding="utf-8")
            record_completion_status(
                report_dir=report_dir,
                status="honest-partial",
                detail={"executed_positions": 1, "closed_unstarted": 15},
            )
            verification = verify_lab03(report_dir=report_dir, final_commit="b" * 40)
            self.assertEqual(verification["outcome"], "passed-partial")

    def test_premature_exposure_removes_family_from_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report_dir = Path(temp)
            ledger = ExposureLedger(report_dir / "exposure-ledger.json")
            from learning_project.lab03 import eligible_families, record_premature_exposure

            before = eligible_families(RESERVES, ledger, freeze_at=None)
            record_premature_exposure(ledger=ledger, family_id=before[0], student=STUDENT)
            after = eligible_families(RESERVES, ledger, freeze_at=None)
            self.assertNotIn(before[0], after)
            self.assertEqual(len(after), len(before) - 1)

    def test_structural_check_rejects_envelope_with_extra_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            comparison_dir = Path(temp)
            (comparison_dir / "schedule.json").write_text(
                json.dumps({
                    "positions": [
                        {"position_id": "pos-x-a-1", "case_id": "case-x", "state": "returned"}
                    ]
                }),
                encoding="utf-8",
            )
            attempt_dir = comparison_dir / "attempts" / "pos-x-a-1"
            attempt_dir.mkdir(parents=True)
            (attempt_dir / "raw-response.txt").write_text(
                json.dumps({"case_id": "case-x", "proposed_text": "ok", "extra": 1}), encoding="utf-8"
            )
            result = structural_check(comparison_dir=comparison_dir, position_id="pos-x-a-1")
            self.assertFalse(result["valid"])

    def test_curator_candidate_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            comparison_dir = Path(temp)
            prior = load_family(RESERVES / "reserve-criteria-chain" / "family.json")
            curator_input = {
                "prior_families": [
                    {
                        "family_id": prior["family_id"],
                        "cases": prior["cases"],
                        "expected_behaviors": prior["expected_behaviors"],
                    }
                ]
            }
            candidate = load_family(RESERVES / "reserve-experiment-discipline" / "family.json")
            candidate = json.loads(json.dumps(candidate))  # deep copy
            candidate["family_id"] = "curator-new-family"
            for case in candidate["cases"]:
                case["family_id"] = "curator-new-family"
                case["task"] = case["task"] + " (curator)"
            for behavior in candidate["expected_behaviors"]:
                pass  # behavior case ids still match
            family = ingest_curator_candidate(
                comparison_dir=comparison_dir,
                candidate_family=candidate,
                curator_input=curator_input,
                curator_session="curator-session-01",
            )
            self.assertEqual(family["origin"], "curator-generated")
            self.assertIn("curator_session", family["provenance"])

    def test_written_development_records_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report_dir = Path(temp)
            self._prepare_development(report_dir)
            self.assertTrue((report_dir / "development" / "variant-b.txt").exists())
            with self.assertRaises(WorkflowError):
                record_variant_b(
                    report_dir=report_dir,
                    variant_b_text="Different text.",
                    change_declaration={
                        "changed_property": "a",
                        "mechanism": "m",
                        "declared_factors": ["a", "b"],
                    },
                )


if __name__ == "__main__":
    unittest.main()
