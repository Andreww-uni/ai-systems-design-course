import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from learning_project.cli import main


class Lab02CommandLineTests(unittest.TestCase):
    def test_verify_returns_two_when_inputs_cannot_be_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault = root / "vault"
            report_dir = root / "course/reports/lab02"
            vault.mkdir()
            report_dir.mkdir(parents=True)
            stdout, stderr = io.StringIO(), io.StringIO()

            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "lab02",
                        "verify",
                        "--vault",
                        str(vault),
                        "--report-dir",
                        str(report_dir),
                    ]
                )

            self.assertEqual(code, 2)
            self.assertFalse((report_dir / "verification-report.json").exists())

    def test_verify_returns_one_and_writes_a_report_when_checks_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault = root / "vault"
            report_dir = root / "course/reports/lab02"
            vault.mkdir()
            report_dir.mkdir(parents=True)
            (report_dir / "REPORT.md").write_text("# Report\n", encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()

            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "lab02",
                        "verify",
                        "--vault",
                        str(vault),
                        "--report-dir",
                        str(report_dir),
                    ]
                )

            self.assertEqual(code, 1)
            report = json.loads(
                (report_dir / "verification-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["status"], "failed")
            self.assertIn("failed", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
