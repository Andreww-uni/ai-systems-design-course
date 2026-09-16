import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from learning_project.lab02 import (
    apply_candidate,
    compare_live_runs,
    import_response,
    prepare_request,
    record_decision,
    record_run_metadata,
    register_source,
    revise_candidate,
    validate_candidate,
)
from learning_project.workflow import WorkflowError


THEORY_TEXT = """# Module 02

### 1.3 Structured output controls syntax, not meaning

Structured output is machine-readable.

Valid JSON syntax does not prove semantic support.

Only an authorized human decision permits accepted state.

> **Further reading:** excluded material.
"""

VALID_CANDIDATE = {
    "schema_version": "1.0",
    "concept_id": "structured-output",
    "title": "Structured Output",
    "definition": "Structured output is machine-readable model output.",
    "key_points": [
        "A syntactic gate checks parsing.",
        "A deterministic gate checks invariants.",
        "A semantic gate requires human judgment.",
    ],
    "source_support": [
        {
            "claim_kind": "definition",
            "claim": "The output is machine-readable.",
            "quote": "Structured output is machine-readable.",
        },
        {
            "claim_kind": "syntax-vs-semantics",
            "claim": "Syntax does not prove semantic support.",
            "quote": "Valid JSON syntax does not prove semantic support.",
        },
        {
            "claim_kind": "authority-boundary",
            "claim": "A human decision controls accepted state.",
            "quote": "Only an authorized human decision permits accepted state.",
        },
    ],
    "tags": ["domain/ai-engineering"],
}


def create_candidate(
    root: Path,
    run_id: str = "live-primary-01",
    candidate: dict | None = None,
    evidence_kind: str = "live",
) -> tuple[Path, Path, Path]:
    course_root = root / "course"
    vault = root / "vault"
    report_dir = course_root / "reports/lab02"
    theory_path = course_root / "module-02-theory.md"
    theory_path.parent.mkdir()
    theory_path.write_text(THEORY_TEXT, encoding="utf-8")
    register_source(
        course_root=course_root,
        theory_path=theory_path,
        vault=vault,
        course_repository="https://example.test/course.git",
        course_commit="a" * 40,
        registered_by="student-01",
    )
    prepare_request(vault=vault, report_dir=report_dir, run_id=run_id)
    raw_path = report_dir / "runs" / run_id / "raw-response.txt"
    raw_path.write_text(json.dumps(candidate or VALID_CANDIDATE) + "\n", encoding="utf-8")
    proposal_path = import_response(
        vault=vault,
        report_dir=report_dir,
        run_id=run_id,
        evidence_kind=evidence_kind,
    )
    return vault, report_dir, proposal_path


class Lab02ValidationTests(unittest.TestCase):
    def test_validation_accepts_a_bound_candidate_with_three_exact_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault, report_dir, proposal_path = create_candidate(Path(temp_dir))
            output_path = report_dir / "runs/live-primary-01/validation-result.json"

            result = validate_candidate(
                vault=vault,
                report_dir=report_dir,
                proposal_id="lab02-structured-output-live-primary-01",
                output_path=output_path,
            )

            self.assertTrue(result["valid"], result["errors"])
            self.assertEqual(
                result["proposal_sha256"],
                hashlib.sha256(proposal_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(result["validation_id"], "lab02-structured-output-live-primary-01-validation")
            self.assertEqual(result["syntactic_gate"]["status"], "passed")
            self.assertEqual(result["invariant_gate"]["status"], "passed")
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), result)

    def test_validation_accepts_a_descriptive_tag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = json.loads(json.dumps(VALID_CANDIDATE))
            candidate["tags"] = ["structured-output"]
            vault, report_dir, _ = create_candidate(Path(temp_dir), candidate=candidate)

            result = validate_candidate(
                vault=vault,
                report_dir=report_dir,
                proposal_id="lab02-structured-output-live-primary-01",
                output_path=report_dir / "runs/live-primary-01/validation-result.json",
            )

            self.assertTrue(result["valid"], result["errors"])

    def test_validation_rejects_reusing_one_exact_quote_for_multiple_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = json.loads(json.dumps(VALID_CANDIDATE))
            candidate["source_support"][1]["quote"] = candidate["source_support"][0]["quote"]
            vault, report_dir, _ = create_candidate(Path(temp_dir), candidate=candidate)

            result = validate_candidate(
                vault=vault,
                report_dir=report_dir,
                proposal_id="lab02-structured-output-live-primary-01",
                output_path=report_dir / "runs/live-primary-01/validation-result.json",
            )

            self.assertFalse(result["valid"])
            self.assertIn("The three source quotes must be distinct.", result["errors"])

    def test_validation_rejects_wrong_claim_category_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = json.loads(json.dumps(VALID_CANDIDATE))
            candidate["source_support"][0]["claim_kind"] = "syntax-vs-semantics"
            vault, report_dir, _ = create_candidate(Path(temp_dir), candidate=candidate)

            result = validate_candidate(
                vault=vault,
                report_dir=report_dir,
                proposal_id="lab02-structured-output-live-primary-01",
                output_path=report_dir / "runs/live-primary-01/validation-result.json",
            )

            self.assertFalse(result["valid"])
            self.assertIn("three claim categories in declared order", result["errors"][0])


class Lab02RevisionTests(unittest.TestCase):
    def test_revision_creates_a_new_candidate_and_preserves_the_model_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, parent_path = create_candidate(root)
            parent_bytes = parent_path.read_bytes()
            parent_sha256 = hashlib.sha256(parent_bytes).hexdigest()
            revision_path = report_dir / "revisions/human-01.yaml"
            revision_path.parent.mkdir(parents=True)
            revision_path.write_text(
                "schema_version: \"1.0\"\n"
                "revision_id: human-01\n"
                "derived_from:\n"
                "  proposal_id: lab02-structured-output-live-primary-01\n"
                f"  proposal_sha256: {parent_sha256}\n"
                "changes:\n"
                "  definition: Structured output is a machine-readable candidate, not accepted meaning.\n"
                "rationale: Clarify the authority boundary stated in the source.\n"
                "revised_by: student-01\n",
                encoding="utf-8",
            )

            revised_path = revise_candidate(vault=vault, revision_path=revision_path)

            self.assertEqual(parent_path.read_bytes(), parent_bytes)
            self.assertEqual(
                revised_path,
                vault / "proposals/lab02-structured-output-human-01.md",
            )
            _, frontmatter_text, body = revised_path.read_text(encoding="utf-8").split(
                "---\n", 2
            )
            frontmatter = yaml.safe_load(frontmatter_text)
            self.assertEqual(frontmatter["origin"], "human-revision")
            self.assertEqual(
                frontmatter["derived_from"],
                {
                    "proposal_id": "lab02-structured-output-live-primary-01",
                    "proposal_sha256": parent_sha256,
                },
            )
            self.assertIn("revision_input_sha256", frontmatter)
            self.assertEqual(frontmatter["revision"]["changed_fields"], ["definition"])
            self.assertIn("machine-readable candidate, not accepted meaning", body)

            result = validate_candidate(
                vault=vault,
                report_dir=report_dir,
                proposal_id="lab02-structured-output-human-01",
                output_path=report_dir / "revisions/human-01-validation-result.json",
            )
            self.assertTrue(result["valid"], result["errors"])


class Lab02DecisionAndApplicationTests(unittest.TestCase):
    def _approve(self, report_dir, vault, proposal_id, validation_path):
        validation = validate_candidate(
            vault=vault,
            report_dir=report_dir,
            proposal_id=proposal_id,
            output_path=validation_path,
        )
        review_path = report_dir / "semantic-review.yaml"
        review_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": "1.0",
                    "review_id": "lab02-structured-output-review",
                    "proposal_id": proposal_id,
                    "proposal_sha256": validation["proposal_sha256"],
                    "validation_id": validation["validation_id"],
                    "validation_sha256": hashlib.sha256(
                        validation_path.read_bytes()
                    ).hexdigest(),
                    "findings": {
                        "definition": "The definition matches the source.",
                        "control_gates": "The three gates are explained correctly.",
                        "authority_boundary": "The authority boundary is preserved.",
                    },
                    "verdict": "acceptable",
                    "rationale": "The candidate is supported by the source.",
                    "reviewed_by": "student-01",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        decision_path = record_decision(
            vault=vault,
            proposal_id=proposal_id,
            validation_path=validation_path,
            review_path=review_path,
            status="approved",
            recorded_by="student-01",
        )
        return validation, review_path, decision_path

    def test_approved_review_creates_the_concept_and_operation_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, proposal_path = create_candidate(root)
            proposal_id = "lab02-structured-output-live-primary-01"
            validation_path = report_dir / "runs/live-primary-01/validation-result.json"
            validation, review_path, decision_path = self._approve(
                report_dir, vault, proposal_id, validation_path
            )
            concept_path, operation_path = apply_candidate(
                vault=vault,
                proposal_id=proposal_id,
                validation_path=validation_path,
                review_path=review_path,
            )

            decision = yaml.safe_load(decision_path.read_text(encoding="utf-8").split("---\n", 2)[1])
            self.assertEqual(decision["status"], "approved")
            self.assertEqual(decision["proposal_sha256"], hashlib.sha256(proposal_path.read_bytes()).hexdigest())
            self.assertEqual(decision["validation_id"], validation["validation_id"])
            self.assertIn("review_id", decision)
            self.assertEqual(concept_path, vault / "concepts/structured-output.md")
            self.assertEqual(operation_path, vault / f"operations/{proposal_id}-apply.md")
            concept = yaml.safe_load(concept_path.read_text(encoding="utf-8").split("---\n", 2)[1])
            self.assertEqual(concept["record_type"], "concept")
            self.assertEqual(concept["concept_id"], "structured-output")
            self.assertEqual(concept["definition"], VALID_CANDIDATE["definition"])
            self.assertIn("source_support", concept)
            self.assertEqual(concept["accepted_from"]["proposal_id"], proposal_id)
            self.assertIn("decision_id", concept["accepted_from"])
            operation = yaml.safe_load(operation_path.read_text(encoding="utf-8").split("---\n", 2)[1])
            self.assertEqual(operation["status"], "applied")
            self.assertEqual(operation["action"], "create")
            self.assertEqual(
                operation["concept_sha256"],
                hashlib.sha256(concept_path.read_bytes()).hexdigest(),
            )

    def test_apply_refuses_changed_source_without_creating_accepted_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, _ = create_candidate(root)
            proposal_id = "lab02-structured-output-live-primary-01"
            validation_path = report_dir / "runs/live-primary-01/validation-result.json"
            _, review_path, _ = self._approve(
                report_dir, vault, proposal_id, validation_path
            )
            source_path = (
                vault / "sources/module-02-foundation-models-and-ai-application-architecture.md"
            )
            source_path.write_text(
                source_path.read_text(encoding="utf-8") + "tampered\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(WorkflowError, "source"):
                apply_candidate(
                    vault=vault,
                    proposal_id=proposal_id,
                    validation_path=validation_path,
                    review_path=review_path,
                )

            self.assertFalse((vault / "concepts/structured-output.md").exists())
            self.assertFalse((vault / f"operations/{proposal_id}-apply.md").exists())

    def test_apply_refuses_a_fixture_candidate_without_live_ancestry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, _ = create_candidate(root, evidence_kind="fixture")
            proposal_id = "lab02-structured-output-live-primary-01"
            validation_path = report_dir / "runs/live-primary-01/validation-result.json"
            _, review_path, _ = self._approve(
                report_dir, vault, proposal_id, validation_path
            )

            with self.assertRaisesRegex(WorkflowError, "descends from a live response"):
                apply_candidate(
                    vault=vault,
                    proposal_id=proposal_id,
                    validation_path=validation_path,
                    review_path=review_path,
                )

            self.assertFalse((vault / "concepts/structured-output.md").exists())

    def test_apply_refuses_on_repeat_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, _ = create_candidate(root)
            proposal_id = "lab02-structured-output-live-primary-01"
            validation_path = report_dir / "runs/live-primary-01/validation-result.json"
            _, review_path, _ = self._approve(
                report_dir, vault, proposal_id, validation_path
            )
            apply_candidate(
                vault=vault,
                proposal_id=proposal_id,
                validation_path=validation_path,
                review_path=review_path,
            )
            concept_bytes = (vault / "concepts/structured-output.md").read_bytes()

            with self.assertRaisesRegex(WorkflowError, "will not be overwritten"):
                apply_candidate(
                    vault=vault,
                    proposal_id=proposal_id,
                    validation_path=validation_path,
                    review_path=review_path,
                )

            self.assertEqual(
                (vault / "concepts/structured-output.md").read_bytes(), concept_bytes
            )

    def test_confinement_rejects_path_traversal_in_proposal_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, _ = create_candidate(root)
            with self.assertRaisesRegex(WorkflowError, "proposal_id"):
                validate_candidate(
                    vault=vault,
                    report_dir=report_dir,
                    proposal_id="lab02-structured-output-../../etc",
                    output_path=report_dir / "runs/x-validation-result.json",
                )


class Lab02LiveComparisonTests(unittest.TestCase):
    def test_compare_live_runs_accepts_two_runs_with_identical_request_and_response_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, _ = create_candidate(root, run_id="live-primary-01")
            prepare_request(vault=vault, report_dir=report_dir, run_id="live-primary-02")
            second_raw = report_dir / "runs/live-primary-02/raw-response.txt"
            second_raw.write_text(json.dumps(VALID_CANDIDATE) + "\n", encoding="utf-8")
            import_response(
                vault=vault,
                report_dir=report_dir,
                run_id="live-primary-02",
                evidence_kind="live",
            )
            for run_id in ("live-primary-01", "live-primary-02"):
                record_run_metadata(
                    report_dir=report_dir,
                    run_id=run_id,
                    evidence_kind="live",
                    adapter="agy",
                    model_id="example-model",
                    recorded_by="student-01",
                )

            output_path = report_dir / "live-comparison.json"
            comparison = compare_live_runs(
                vault=vault,
                report_dir=report_dir,
                run_ids=("live-primary-01", "live-primary-02"),
                output_path=output_path,
            )

            self.assertEqual(comparison["comparison_kind"], "same-model-variability")
            self.assertEqual(comparison["run_ids"], ["live-primary-01", "live-primary-02"])
            self.assertEqual(
                comparison["runs"][0]["request_sha256"],
                comparison["runs"][1]["request_sha256"],
            )
            self.assertIn("structural_differences", comparison)
            self.assertFalse(comparison["structural_differences"]["raw_bytes_differ"])


if __name__ == "__main__":
    unittest.main()
