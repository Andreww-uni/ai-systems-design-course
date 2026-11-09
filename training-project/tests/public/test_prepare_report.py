import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from learning_project.cli import main


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def write_png(path: Path, width: int, height: int, color: tuple[int, int, int] = (32, 64, 128)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (width, height), color).save(path, format="PNG")


class PrepareReportCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.report_dir = self.root / "reports" / "lab01"
        self.screenshots = self.report_dir / "screenshots"
        self.report_path = self.report_dir / "REPORT.md"
        self.small_image = self.screenshots / "01-git-remotes.png"
        write_png(self.small_image, 40, 20)
        self.report_path.write_text(
            "# Report\n\n![git remotes](screenshots/01-git-remotes.png)\n",
            encoding="utf-8",
        )

    def test_prepare_report_writes_submission_copy_without_changing_the_source(self) -> None:
        source_before = self.report_path.read_text(encoding="utf-8")
        image_before = self.small_image.read_bytes()

        code, out, err = run_cli(["prepare-report", str(self.report_path)])

        submission = self.report_dir / "submission" / "REPORT.md"
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertTrue(submission.is_file())
        self.assertIn(str(submission), out)
        self.assertIn("Embedded images: 1", out)
        self.assertEqual(self.report_path.read_text(encoding="utf-8"), source_before)
        self.assertEqual(self.small_image.read_bytes(), image_before)
        embedded = submission.read_text(encoding="utf-8")
        self.assertIn("data:image/png;base64,", embedded)
        self.assertNotIn("screenshots/01-git-remotes.png", embedded)

    def test_lab02_generated_submission_report_is_ignored_by_git(self) -> None:
        project_root = Path(__file__).resolve().parents[2]

        result = subprocess.run(
            ["git", "-C", str(project_root), "check-ignore", "reports/lab02/submission/REPORT.md"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_lab01_generated_submission_report_is_ignored_by_git(self) -> None:
        project_root = Path(__file__).resolve().parents[2]

        result = subprocess.run(
            ["git", "-C", str(project_root), "check-ignore", "reports/lab01/submission/REPORT.md"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_generated_submission_reports_are_ignored_for_current_and_future_labs(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        shutil.copyfile(project_root / ".gitignore", self.root / ".gitignore")
        for lab in ("lab04", "lab05", "lab06", "lab99"):
            with self.subTest(lab=lab):
                result = subprocess.run(
                    ["git", "-C", str(self.root), "check-ignore", f"reports/{lab}/submission/REPORT.md"],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_source_reports_and_evidence_are_not_ignored_by_submission_rule(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        shutil.copyfile(project_root / ".gitignore", self.root / ".gitignore")
        for path in ("reports/lab05/REPORT.md", "reports/lab05/screenshots/01-query-rewriting.png", "reports/lab05/evaluation/judgment.json"):
            with self.subTest(path=path):
                result = subprocess.run(
                    ["git", "-C", str(self.root), "check-ignore", path],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 1, result.stderr)

    def test_prepare_report_leaves_data_uris_and_http_links_unchanged(self) -> None:
        self.report_path.write_text(
            "![already](data:image/png;base64,AAAA)\n"
            "![remote](https://example.invalid/shot.png)\n",
            encoding="utf-8",
        )

        code, _, err = run_cli(["prepare-report", str(self.report_path)])

        submission = self.report_dir / "submission" / "REPORT.md"
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        text = submission.read_text(encoding="utf-8")
        self.assertIn("data:image/png;base64,AAAA", text)
        self.assertIn("https://example.invalid/shot.png", text)
        self.assertIn("Embedded images: 0", run_cli(["prepare-report", str(self.report_path)])[1])

    def test_prepare_report_refuses_a_missing_image(self) -> None:
        self.report_path.write_text("![missing](screenshots/missing.png)\n", encoding="utf-8")

        code, _, err = run_cli(["prepare-report", str(self.report_path)])

        self.assertEqual(code, 1)
        self.assertIn("not found", err)
        self.assertFalse((self.report_dir / "submission" / "REPORT.md").exists())

    def test_prepare_report_refuses_to_overwrite_the_source_report(self) -> None:
        code, _, err = run_cli(
            ["prepare-report", str(self.report_path), "--output", str(self.report_path)]
        )

        self.assertEqual(code, 1)
        self.assertIn("must not overwrite the source report", err)

    def test_prepare_report_resizes_an_oversized_screenshot(self) -> None:
        large_image = self.screenshots / "02-workstation-capabilities.png"
        write_png(large_image, 1600, 1200, color=(200, 10, 10))
        self.report_path.write_text(
            "![capabilities](screenshots/02-workstation-capabilities.png)\n",
            encoding="utf-8",
        )

        code, _, err = run_cli(["prepare-report", str(self.report_path)])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        embedded = (self.report_dir / "submission" / "REPORT.md").read_text(encoding="utf-8")
        prefix = "data:image/png;base64,"
        start = embedded.index(prefix) + len(prefix)
        end = embedded.index(")", start)
        from base64 import b64decode

        payload = b64decode(embedded[start:end])
        with Image.open(io.BytesIO(payload)) as image:
            self.assertLessEqual(image.width, 800)
            self.assertLessEqual(image.height, 600)
        with Image.open(large_image) as original:
            self.assertEqual(original.size, (1600, 1200))

    def test_prepare_report_embeds_the_real_lab01_template_for_both_proposer_paths(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "fixtures" / "lab01" / "REPORT.md"
        shutil.copyfile(fixture, self.report_path)
        screenshot_names = (
            "01-git-remotes.png",
            "02-workstation-capabilities.png",
            "03-public-tests.png",
            "04-proposer-session.png",
            "05-external-vault.png",
            "06-premature-apply-refused.png",
            "07-accepted-contract.png",
        )
        for name in screenshot_names:
            write_png(self.screenshots / name, 40, 20)

        code, out, err = run_cli(["prepare-report", str(self.report_path)])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("Embedded images: 7", out)

        source = self.report_path.read_text(encoding="utf-8")
        source = source.replace("04-proposer-session.png", "04-manual-fallback.png")
        self.report_path.write_text(source, encoding="utf-8")
        write_png(self.screenshots / "04-manual-fallback.png", 40, 20)

        code, out, err = run_cli(["prepare-report", str(self.report_path)])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("Embedded images: 7", out)

        shutil.copyfile(fixture, self.report_path)
        source = self.report_path.read_text(encoding="utf-8")
        source = source.replace(
            "![сеанс пропонувача або запасний шлях](screenshots/04-proposer-session.png)\n",
            "",
        )
        self.report_path.write_text(source, encoding="utf-8")

        code, out, err = run_cli(["prepare-report", str(self.report_path)])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("Embedded images: 6", out)

    def test_prepare_report_embeds_all_images_from_the_real_lab02_template(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "fixtures" / "lab02" / "REPORT.md"
        shutil.copyfile(fixture, self.report_path)
        screenshot_names = (
            "01-offline-gates.png",
            "02-refusal-unchanged.png",
            "03-live-comparison.png",
            "04-review-decision.png",
            "05-controlled-apply.png",
            "06-final-result.png",
        )
        for name in screenshot_names:
            write_png(self.screenshots / name, 40, 20)
        source_before = self.report_path.read_text(encoding="utf-8")

        code, out, err = run_cli(["prepare-report", str(self.report_path)])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("Embedded images: 6", out)
        self.assertEqual(self.report_path.read_text(encoding="utf-8"), source_before)
        self.assertEqual(source_before.count("screenshots/"), 6)
        self.assertNotIn("data:image/", source_before)
        submission = (self.report_dir / "submission" / "REPORT.md").read_text(encoding="utf-8")
        self.assertEqual(submission.count("data:image/png;base64,"), 6)
        for name in screenshot_names:
            self.assertNotIn(f"screenshots/{name}", submission)

    def test_prepare_report_embeds_all_images_from_the_real_lab03_template(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "fixtures" / "lab03" / "REPORT.md"
        shutil.copyfile(fixture, self.report_path)
        screenshot_names = (
            "01-calibration.png",
            "02-development.png",
            "03-freeze.png",
            "04-held-out-execution.png",
            "05-scoring-recommendation.png",
            "06-regression.png",
            "07-final-verification.png",
        )
        for name in screenshot_names:
            write_png(self.screenshots / name, 40, 20)
        source_before = self.report_path.read_text(encoding="utf-8")

        code, out, err = run_cli(["prepare-report", str(self.report_path)])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("Embedded images: 7", out)
        self.assertEqual(self.report_path.read_text(encoding="utf-8"), source_before)
        self.assertEqual(source_before.count("screenshots/"), 7)
        self.assertNotIn("data:image/", source_before)
        submission = (self.report_dir / "submission" / "REPORT.md").read_text(encoding="utf-8")
        self.assertEqual(submission.count("data:image/png;base64,"), 7)
        for name in screenshot_names:
            self.assertNotIn(f"screenshots/{name}", submission)

    def test_prepare_report_embeds_only_applicable_images_from_a_partial_lab03_report(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "fixtures" / "lab03" / "REPORT.md"
        source = fixture.read_text(encoding="utf-8")
        source = "\n".join(
            line
            for line in source.splitlines()
            if "screenshots/" not in line or "07-final-verification.png" in line
        ) + "\n"
        self.report_path.write_text(source, encoding="utf-8")
        write_png(self.screenshots / "07-final-verification.png", 40, 20)

        code, out, err = run_cli(["prepare-report", str(self.report_path)])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("Embedded images: 1", out)
        submission = (self.report_dir / "submission" / "REPORT.md").read_text(encoding="utf-8")
        self.assertEqual(submission.count("data:image/png;base64,"), 1)
        self.assertNotIn("screenshots/07-final-verification.png", submission)

    def test_prepare_report_embeds_all_images_from_the_real_lab04_template(self) -> None:
        fixture = Path(__file__).resolve().parents[2] / "fixtures" / "lab04" / "REPORT.md"
        shutil.copyfile(fixture, self.report_path)
        screenshot_names = (
            "01-boundary-selection.png",
            "02-embedding-index.png",
            "03-retrieval-comparison.png",
            "04-relevance-metrics.png",
            "05-operational-decision.png",
            "06-final-verification.png",
        )
        for name in screenshot_names:
            write_png(self.screenshots / name, 40, 20)
        source_before = self.report_path.read_text(encoding="utf-8")

        code, out, err = run_cli(["prepare-report", str(self.report_path)])

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("Embedded images: 6", out)
        self.assertEqual(self.report_path.read_text(encoding="utf-8"), source_before)
        self.assertEqual(source_before.count("screenshots/"), 6)
        self.assertNotIn("data:image/", source_before)
        submission = (self.report_dir / "submission" / "REPORT.md").read_text(encoding="utf-8")
        self.assertEqual(submission.count("data:image/png;base64,"), 6)
        for name in screenshot_names:
            self.assertNotIn(f"screenshots/{name}", submission)


if __name__ == "__main__":
    unittest.main()
