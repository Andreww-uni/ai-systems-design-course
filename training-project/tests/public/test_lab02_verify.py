import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from learning_project.lab02 import (
    apply_candidate,
    compare_live_runs,
    course_tree_drift,
    import_response,
    prepare_request,
    record_decision,
    record_run_metadata,
    register_source,
    validate_candidate,
    verify_lab02,
)

REAL_THEORY = (
    Path(__file__).resolve().parents[3]
    / "modules/02_Foundation_Models_and_AI_Application_Architecture/"
    "02_Foundation_Models_and_AI_Application_Architecture_Theory.md"
)
COURSE_PATH = (
    "modules/02_Foundation_Models_and_AI_Application_Architecture/"
    "02_Foundation_Models_and_AI_Application_Architecture_Theory.md"
)
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/lab02"
SCREENSHOTS = (
    "01-offline-gates.png",
    "02-refusal-unchanged.png",
    "03-live-comparison.png",
    "04-review-decision.png",
    "05-controlled-apply.png",
    "06-final-result.png",
)


def vault_snapshot(vault: Path) -> dict[str, bytes]:
    return {
        path.relative_to(vault).as_posix(): path.read_bytes()
        for path in sorted(vault.rglob("*"))
        if path.is_file()
    }


class Lab02FinalVerificationTests(unittest.TestCase):
    def test_course_tree_drift_excludes_student_paths_but_reports_upstream_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.test"], cwd=root, check=True
            )
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            upstream = root / "training-project/platform/learning_project/lab02.py"
            upstream.parent.mkdir(parents=True)
            upstream.write_text("original\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-m", "baseline"], cwd=root, check=True, capture_output=True
            )

            report = root / "training-project/reports/lab02/REPORT.md"
            report.parent.mkdir(parents=True)
            report.write_text("student evidence\n", encoding="utf-8")
            student = root / "training-project/student/note.txt"
            student.parent.mkdir(parents=True)
            student.write_text("student state\n", encoding="utf-8")
            upstream.write_text("changed\n", encoding="utf-8")

            self.assertEqual(
                course_tree_drift(root),
                ["training-project/platform/learning_project/lab02.py"],
            )

    def _build_submission(self, root: Path) -> tuple[Path, Path, Path]:
        project_root = root / "course"
        report_dir = project_root / "reports/lab02"
        vault = root / "vault"
        theory_path = project_root / COURSE_PATH
        theory_path.parent.mkdir(parents=True)
        shutil.copy2(REAL_THEORY, theory_path)
        fixture_dir = project_root / "fixtures/lab02"
        fixture_dir.mkdir(parents=True)
        for fixture in FIXTURES.iterdir():
            shutil.copy2(fixture, fixture_dir / fixture.name)
        register_source(
            course_root=project_root,
            theory_path=theory_path,
            vault=vault,
            course_repository="https://example.test/course.git",
            course_commit="a" * 40,
            registered_by="student-01",
        )

        for run_id in ("live-primary-01", "live-primary-02"):
            prepare_request(vault=vault, report_dir=report_dir, run_id=run_id)
            raw_path = report_dir / "runs" / run_id / "raw-response.txt"
            shutil.copy2(fixture_dir / "valid-response.json", raw_path)
            import_response(
                vault=vault,
                report_dir=report_dir,
                run_id=run_id,
                evidence_kind="live",
            )
            record_run_metadata(
                report_dir=report_dir,
                run_id=run_id,
                evidence_kind="live",
                adapter="agy",
                model_id="example-model",
                recorded_by="student-01",
            )
        compare_live_runs(
            vault=vault,
            report_dir=report_dir,
            run_ids=("live-primary-01", "live-primary-02"),
            output_path=report_dir / "live-comparison.json",
        )

        proposal_id = "lab02-structured-output-live-primary-01"
        validation_path = report_dir / "runs/live-primary-01/validation-result.json"
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
                    "validation_sha256": hashlib.sha256(validation_path.read_bytes()).hexdigest(),
                    "findings": {
                        "definition": "The definition matches the source.",
                        "control_gates": "The three gates are explained correctly.",
                        "authority_boundary": "The authority boundary is preserved.",
                    },
                    "verdict": "acceptable",
                    "rationale": "The candidate is supported by all three exact quotations.",
                    "reviewed_by": "student-01",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        record_decision(
            vault=vault,
            proposal_id=proposal_id,
            validation_path=validation_path,
            review_path=review_path,
            status="approved",
            recorded_by="student-01",
        )
        apply_candidate(
            vault=vault,
            proposal_id=proposal_id,
            validation_path=validation_path,
            review_path=review_path,
        )

        screenshot_dir = report_dir / "screenshots"
        screenshot_dir.mkdir(parents=True)
        for name in SCREENSHOTS:
            (screenshot_dir / name).write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        report_dir.joinpath("REPORT.md").write_text(
            "# Laboratory 02 report\n\n" + "\n".join(SCREENSHOTS) + "\n",
            encoding="utf-8",
        )
        return vault, report_dir, fixture_dir

    def test_verify_passes_a_complete_submission_without_changing_the_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, fixture_dir = self._build_submission(root)
            before = vault_snapshot(vault)

            result = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=root / "course",
                fixture_dir=fixture_dir,
            )

            self.assertEqual(result["status"], "passed", result["checks"])
            self.assertEqual(vault_snapshot(vault), before)
            output_path = report_dir / "verification-report.json"
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), result)
            self.assertTrue(all(check["status"] == "passed" for check in result["checks"]))
            self.assertIn("artifacts", result)
            self.assertIn("selected_candidate", result)
            self.assertEqual(result["comparison_kind"], "same-model-variability")

    def test_verify_fails_when_a_canonical_record_gains_a_provider_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, fixture_dir = self._build_submission(root)
            concept_path = vault / "concepts/structured-output.md"
            concept_path.write_text(
                concept_path.read_text(encoding="utf-8").replace(
                    "concept_id: structured-output",
                    "concept_id: structured-output\nmodel_id: leaked-model",
                    1,
                ),
                encoding="utf-8",
            )

            result = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=root / "course",
                fixture_dir=fixture_dir,
            )

            self.assertEqual(result["status"], "failed")
            provider_check = next(
                check for check in result["checks"] if check["check_id"] == "provider-isolation"
            )
            self.assertEqual(provider_check["status"], "failed")


if __name__ == "__main__":
    unittest.main()
