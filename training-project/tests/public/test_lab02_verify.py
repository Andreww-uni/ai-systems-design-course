import hashlib
import json
import os
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
    revise_candidate,
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


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=check,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )


def init_git(root: Path) -> None:
    git(root, "init")
    git(root, "config", "user.email", "test@example.test")
    git(root, "config", "user.name", "Test")
    git(root, "config", "commit.gpgsign", "false")


def write_review(
    path: Path,
    *,
    proposal_id: str,
    validation: dict,
    validation_path: Path,
    verdict: str = "acceptable",
    review_id: str = "lab02-structured-output-review",
    rationale: str = "The candidate is supported by all three exact quotations.",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "review_id": review_id,
                "proposal_id": proposal_id,
                "proposal_sha256": validation["proposal_sha256"],
                "validation_id": validation["validation_id"],
                "validation_sha256": hashlib.sha256(validation_path.read_bytes()).hexdigest(),
                "findings": {
                    "definition": "The definition matches the source.",
                    "control_gates": "The three gates are explained correctly.",
                    "authority_boundary": "The authority boundary is preserved.",
                },
                "verdict": verdict,
                "rationale": rationale,
                "reviewed_by": "student-01",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


class Lab02FinalVerificationTests(unittest.TestCase):
    def test_course_tree_drift_excludes_student_paths_but_reports_upstream_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_git(root)
            upstream = root / "training-project/platform/learning_project/lab02.py"
            upstream.parent.mkdir(parents=True)
            upstream.write_text("original\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-m", "baseline")

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

    def test_course_tree_drift_reports_committed_staged_unstaged_and_untracked_upstream_changes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_git(root)
            tracked = root / "modules/upstream.md"
            tracked.parent.mkdir(parents=True)
            tracked.write_text("original\n", encoding="utf-8")
            platform = root / "training-project/platform/owned.py"
            platform.parent.mkdir(parents=True)
            platform.write_text("owned\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-m", "baseline")
            baseline = git(root, "rev-parse", "HEAD").stdout.strip()

            tracked.write_text("committed drift\n", encoding="utf-8")
            git(root, "add", str(tracked))
            git(root, "commit", "-m", "upstream commit")
            platform.write_text("unstaged\n", encoding="utf-8")
            staged = root / "modules/staged.md"
            staged.write_text("staged\n", encoding="utf-8")
            git(root, "add", str(staged))
            untracked = root / "modules/untracked.md"
            untracked.write_text("untracked\n", encoding="utf-8")
            (root / "training-project/reports/lab02/REPORT.md").parent.mkdir(parents=True)
            (root / "training-project/reports/lab02/REPORT.md").write_text("ok\n", encoding="utf-8")

            self.assertEqual(
                course_tree_drift(root, baseline=baseline),
                [
                    "modules/staged.md",
                    "modules/untracked.md",
                    "modules/upstream.md",
                    "training-project/platform/owned.py",
                ],
            )

    def test_committed_drift_cannot_be_hidden_by_staging_baseline_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_git(root)
            upstream = root / "upstream.md"
            upstream.write_text("baseline\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-m", "baseline")
            baseline = git(root, "rev-parse", "HEAD").stdout.strip()
            upstream.write_text("committed drift\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-m", "drift")
            upstream.write_text("baseline\n", encoding="utf-8")
            git(root, "add", ".")
            self.assertEqual(course_tree_drift(root, baseline), ["upstream.md"])

    def _add_live_run(self, vault: Path, report_dir: Path, fixture_dir: Path, run_id: str) -> None:
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

    def _write_report(self, report_dir: Path) -> None:
        screenshot_dir = report_dir / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        for name in SCREENSHOTS:
            (screenshot_dir / name).write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        report_dir.joinpath("REPORT.md").write_text(
            "# Laboratory 02 report\n\nSynthetic fixture evidence, not live inference.\n"
            + "\n".join(f"![checkpoint](screenshots/{name})" for name in SCREENSHOTS)
            + "\n",
            encoding="utf-8",
        )

    def _select_and_apply(
        self,
        vault: Path,
        report_dir: Path,
        proposal_id: str,
        validation_path: Path,
        review_path: Path | None = None,
    ) -> Path:
        validation = validate_candidate(
            vault=vault,
            report_dir=report_dir,
            proposal_id=proposal_id,
            output_path=validation_path,
        )
        review_path = write_review(
            review_path or (report_dir / "semantic-review.yaml"),
            proposal_id=proposal_id,
            validation=validation,
            validation_path=validation_path,
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
        return review_path

    def _build_submission(
        self,
        root: Path,
        *,
        selected_run_id: str = "live-primary-01",
        course_layout: str = "nested",
        course_commit: str | None = None,
    ) -> tuple[Path, Path, Path, Path]:
        if course_layout == "published":
            project_root = root / "course"
            report_dir = project_root / "training-project/reports/lab02"
            fixture_dir = project_root / "training-project/fixtures/lab02"
        else:
            project_root = root / "course"
            report_dir = project_root / "reports/lab02"
            fixture_dir = project_root / "fixtures/lab02"
        vault = root / "vault"
        theory_path = project_root / COURSE_PATH
        theory_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REAL_THEORY, theory_path)
        fixture_dir.mkdir(parents=True, exist_ok=True)
        for fixture in FIXTURES.iterdir():
            shutil.copy2(fixture, fixture_dir / fixture.name)
        register_source(
            course_root=project_root,
            theory_path=theory_path,
            vault=vault,
            course_repository="https://example.test/course.git",
            course_commit=course_commit or "a" * 40,
            registered_by="student-01",
        )

        for run_id in ("live-primary-01", "live-primary-02"):
            self._add_live_run(vault, report_dir, fixture_dir, run_id)
        compare_live_runs(
            vault=vault,
            report_dir=report_dir,
            run_ids=("live-primary-01", "live-primary-02"),
            output_path=report_dir / "live-comparison.json",
        )
        proposal_id = f"lab02-structured-output-{selected_run_id}"
        validation_path = report_dir / f"runs/{selected_run_id}/validation-result.json"
        self._select_and_apply(vault, report_dir, proposal_id, validation_path)
        self._write_report(report_dir)
        return vault, report_dir, fixture_dir, project_root

    def test_verify_passes_a_complete_submission_without_changing_the_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, fixture_dir, project_root = self._build_submission(root)
            before = vault_snapshot(vault)

            result = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
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

    def test_verify_requires_relative_markdown_links_for_every_screenshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, fixture_dir, project_root = self._build_submission(root)
            report_dir.joinpath("REPORT.md").write_text(
                "# Laboratory 02 report\n\n" + "\n".join(SCREENSHOTS) + "\n",
                encoding="utf-8",
            )

            result = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
                fixture_dir=fixture_dir,
            )

            submission_check = next(
                check for check in result["checks"] if check["check_id"] == "submission-files"
            )
            self.assertEqual(submission_check["status"], "failed")
            self.assertIn("relative Markdown image link", submission_check["message"])

    def test_verify_refuses_embedded_images_in_the_source_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, fixture_dir, project_root = self._build_submission(root)
            report_path = report_dir / "REPORT.md"
            report_path.write_text(
                report_path.read_text(encoding="utf-8")
                + "\n![embedded](data:image/png;base64,AAAA)\n",
                encoding="utf-8",
            )

            result = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
                fixture_dir=fixture_dir,
            )

            submission_check = next(
                check for check in result["checks"] if check["check_id"] == "submission-files"
            )
            self.assertEqual(submission_check["status"], "failed")
            self.assertIn("Source REPORT.md must keep relative image links", submission_check["message"])

    def test_verify_fails_when_a_canonical_record_gains_a_provider_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, fixture_dir, project_root = self._build_submission(root)
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
                course_root=project_root,
                fixture_dir=fixture_dir,
            )

            self.assertEqual(result["status"], "failed")
            provider_check = next(
                check for check in result["checks"] if check["check_id"] == "provider-isolation"
            )
            self.assertEqual(provider_check["status"], "failed")

    def _build_git_submission(self, root: Path) -> tuple[Path, Path, Path, Path, str]:
        project_root = root / "course"
        theory_path = project_root / COURSE_PATH
        theory_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REAL_THEORY, theory_path)
        fixture_dir = project_root / "training-project/fixtures/lab02"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        for fixture in FIXTURES.iterdir():
            shutil.copy2(fixture, fixture_dir / fixture.name)
        platform = project_root / "training-project/platform/learning_project/lab02.py"
        platform.parent.mkdir(parents=True)
        platform.write_text("upstream-owned\n", encoding="utf-8")
        init_git(project_root)
        git(project_root, "add", "modules", "training-project/fixtures", "training-project/platform")
        git(project_root, "commit", "-m", "source baseline")
        baseline = git(project_root, "rev-parse", "HEAD").stdout.strip()
        vault, report_dir, fixture_dir, project_root = self._build_submission(
            root,
            course_layout="published",
            course_commit=baseline,
        )
        return vault, report_dir, fixture_dir, project_root, baseline

    def test_verify_passes_before_and_after_a_student_only_commit_in_a_real_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, fixture_dir, project_root, baseline = self._build_git_submission(root)
            source_bytes = (vault / "sources/module-02-foundation-models-and-ai-application-architecture.md").read_bytes()
            concept_bytes = (vault / "concepts/structured-output.md").read_bytes()
            before = vault_snapshot(vault)

            before_commit = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
                fixture_dir=fixture_dir,
            )
            self.assertEqual(before_commit["status"], "passed", before_commit["checks"])
            course_check = next(
                check for check in before_commit["checks"] if check["check_id"] == "course-commit"
            )
            self.assertEqual(course_check["status"], "passed")
            self.assertNotIn("matches git HEAD and upstream-owned paths are unchanged", course_check["message"])

            git(project_root, "add", "training-project/reports")
            git(project_root, "commit", "-m", "feat(lab02): student evidence")
            head = git(project_root, "rev-parse", "HEAD").stdout.strip()
            self.assertNotEqual(head, baseline)

            after_commit = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
                fixture_dir=fixture_dir,
            )
            self.assertEqual(after_commit["status"], "passed", after_commit["checks"])
            self.assertEqual(after_commit["course_commit"], baseline)
            self.assertEqual(
                (vault / "sources/module-02-foundation-models-and-ai-application-architecture.md").read_bytes(),
                source_bytes,
            )
            self.assertEqual((vault / "concepts/structured-output.md").read_bytes(), concept_bytes)
            self.assertEqual(vault_snapshot(vault), before)

            checkout = root / "submitted-checkout"
            git(root, "clone", str(project_root), str(checkout))
            copied_report = root / "disposable-report"
            shutil.copytree(checkout / "training-project/reports/lab02", copied_report)
            original_report = (report_dir / "verification-report.json").read_bytes()
            checkout_result = verify_lab02(
                vault=vault,
                report_dir=copied_report,
                course_root=checkout,
                fixture_dir=checkout / "training-project/fixtures/lab02",
            )
            self.assertEqual(checkout_result["status"], "passed", checkout_result["checks"])
            self.assertEqual(git(checkout, "status", "--porcelain").stdout, "")
            self.assertEqual((report_dir / "verification-report.json").read_bytes(), original_report)
            screenshot_digest = hashlib.sha256(
                (report_dir / "screenshots/06-final-result.png").read_bytes()
            ).hexdigest()
            self.assertEqual(
                after_commit["artifacts"]["report/screenshots/06-final-result.png"],
                screenshot_digest,
            )

    def test_verify_fails_for_committed_and_working_tree_upstream_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, fixture_dir, project_root, _baseline = self._build_git_submission(root)
            git(project_root, "add", "training-project/reports")
            git(project_root, "commit", "-m", "feat(lab02): student evidence")

            platform = project_root / "training-project/platform/learning_project/lab02.py"
            platform.write_text("drifted\n", encoding="utf-8")
            unstaged = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
                fixture_dir=fixture_dir,
            )
            self.assertEqual(unstaged["status"], "failed", unstaged["checks"])
            self.assertEqual(
                next(check for check in unstaged["checks"] if check["check_id"] == "course-commit")["status"],
                "failed",
            )

            git(project_root, "add", "training-project/platform/learning_project/lab02.py")
            staged = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
                fixture_dir=fixture_dir,
            )
            self.assertEqual(staged["status"], "failed")

            git(project_root, "commit", "-m", "upstream drift")
            committed = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
                fixture_dir=fixture_dir,
            )
            self.assertEqual(committed["status"], "failed")
            self.assertIn(
                "training-project/platform/learning_project/lab02.py",
                next(check for check in committed["checks"] if check["check_id"] == "course-commit")["message"],
            )

            git(project_root, "checkout", "HEAD", "--", "training-project/platform/learning_project/lab02.py")
            leaked = project_root / "modules/leaked-upstream.md"
            leaked.write_text("untracked upstream\n", encoding="utf-8")
            untracked = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
                fixture_dir=fixture_dir,
            )
            self.assertEqual(untracked["status"], "failed")

    def test_verify_fails_when_the_registered_baseline_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, fixture_dir, project_root = self._build_submission(
                root,
                course_layout="published",
                course_commit="deadbeef" * 5,
            )
            init_git(project_root)
            git(project_root, "add", ".")
            git(project_root, "commit", "-m", "student clone")

            result = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
                fixture_dir=fixture_dir,
            )
            self.assertEqual(result["status"], "failed")
            message = next(
                check for check in result["checks"] if check["check_id"] == "course-commit"
            )["message"]
            self.assertRegex(message, "missing|unresolvable")

    def test_verify_accepts_the_second_live_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, fixture_dir, project_root = self._build_submission(
                root, selected_run_id="live-primary-02"
            )
            result = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
                fixture_dir=fixture_dir,
            )
            self.assertEqual(result["status"], "passed", result["checks"])
            self.assertEqual(
                result["selected_candidate"]["proposal_id"],
                "lab02-structured-output-live-primary-02",
            )

    def test_verify_accepts_rejection_then_a_new_generation_without_replacing_the_bound_review(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, fixture_dir, project_root = self._prepare_two_live_runs(root)
            rejected_id = "lab02-structured-output-live-primary-01"
            rejected_validation = report_dir / "runs/live-primary-01/validation-result.json"
            validation = validate_candidate(
                vault=vault,
                report_dir=report_dir,
                proposal_id=rejected_id,
                output_path=rejected_validation,
            )
            rejected_review = write_review(
                report_dir / "reviews/lab02-structured-output-live-primary-01.yaml",
                proposal_id=rejected_id,
                validation=validation,
                validation_path=rejected_validation,
                verdict="unsupported",
                review_id="lab02-structured-output-live-primary-01-review",
                rationale="The first live candidate is unsupported.",
            )
            rejected_bytes = rejected_review.read_bytes()
            record_decision(
                vault=vault,
                proposal_id=rejected_id,
                validation_path=rejected_validation,
                review_path=rejected_review,
                status="rejected",
                recorded_by="student-01",
                reason="Unsupported definition.",
            )
            self._add_live_run(vault, report_dir, fixture_dir, "live-retry-03")
            retry_id = "lab02-structured-output-live-retry-03"
            retry_validation = report_dir / "runs/live-retry-03/validation-result.json"
            self._select_and_apply(vault, report_dir, retry_id, retry_validation)
            self._write_report(report_dir)

            result = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
                fixture_dir=fixture_dir,
            )
            self.assertEqual(result["status"], "passed", result["checks"])
            self.assertEqual(result["selected_candidate"]["proposal_id"], retry_id)
            self.assertEqual(rejected_review.read_bytes(), rejected_bytes)
            self.assertEqual(len(list((vault / "operations").glob("*-apply.md"))), 1)

    def _prepare_two_live_runs(self, root: Path) -> tuple[Path, Path, Path, Path]:
        project_root = root / "course"
        report_dir = project_root / "reports/lab02"
        fixture_dir = project_root / "fixtures/lab02"
        vault = root / "vault"
        theory_path = project_root / COURSE_PATH
        theory_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REAL_THEORY, theory_path)
        fixture_dir.mkdir(parents=True, exist_ok=True)
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
            self._add_live_run(vault, report_dir, fixture_dir, run_id)
        compare_live_runs(
            vault=vault,
            report_dir=report_dir,
            run_ids=("live-primary-01", "live-primary-02"),
            output_path=report_dir / "live-comparison.json",
        )
        return vault, report_dir, fixture_dir, project_root

    def test_verify_accepts_rejection_then_a_human_revision_without_replacing_the_bound_review(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault, report_dir, fixture_dir, project_root = self._prepare_two_live_runs(root)
            parent_id = "lab02-structured-output-live-primary-01"
            parent_validation = report_dir / "runs/live-primary-01/validation-result.json"
            validation = validate_candidate(
                vault=vault,
                report_dir=report_dir,
                proposal_id=parent_id,
                output_path=parent_validation,
            )
            rejected_review = write_review(
                report_dir / "reviews/lab02-structured-output-live-primary-01.yaml",
                proposal_id=parent_id,
                validation=validation,
                validation_path=parent_validation,
                verdict="unsupported",
                review_id="lab02-structured-output-live-primary-01-review",
                rationale="The first live candidate is unsupported.",
            )
            rejected_bytes = rejected_review.read_bytes()
            record_decision(
                vault=vault,
                proposal_id=parent_id,
                validation_path=parent_validation,
                review_path=rejected_review,
                status="rejected",
                recorded_by="student-01",
                reason="Unsupported definition.",
            )
            parent_path = vault / "proposals" / f"{parent_id}.md"
            parent_bytes = parent_path.read_bytes()
            parent_sha256 = hashlib.sha256(parent_bytes).hexdigest()
            revision_path = report_dir / "revisions/human-01.yaml"
            revision_path.parent.mkdir(parents=True)
            revision_path.write_text(
                "schema_version: \"1.0\"\n"
                "revision_id: human-01\n"
                "derived_from:\n"
                f"  proposal_id: {parent_id}\n"
                f"  proposal_sha256: {parent_sha256}\n"
                "changes:\n"
                "  definition: Structured output is machine-readable model output bound by human review.\n"
                "rationale: Recover from an unsupported live candidate without editing it in place.\n"
                "revised_by: student-01\n",
                encoding="utf-8",
            )
            revise_candidate(vault=vault, revision_path=revision_path)
            revised_id = "lab02-structured-output-human-01"
            revised_validation = report_dir / "revisions/human-01/validation-result.json"
            self._select_and_apply(vault, report_dir, revised_id, revised_validation)
            self._write_report(report_dir)

            result = verify_lab02(
                vault=vault,
                report_dir=report_dir,
                course_root=project_root,
                fixture_dir=fixture_dir,
            )
            self.assertEqual(result["status"], "passed", result["checks"])
            self.assertEqual(result["selected_candidate"]["proposal_id"], revised_id)
            self.assertEqual(result["selected_candidate"]["origin"], "human-revision")
            self.assertEqual(rejected_review.read_bytes(), rejected_bytes)
            self.assertEqual(parent_path.read_bytes(), parent_bytes)
            self.assertEqual(len(list((vault / "operations").glob("*-apply.md"))), 1)


if __name__ == "__main__":
    unittest.main()
