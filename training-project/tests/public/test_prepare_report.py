import contextlib
import io
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


if __name__ == "__main__":
    unittest.main()
