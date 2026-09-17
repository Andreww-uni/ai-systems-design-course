import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from learning_project.cli import main
from learning_project.lab02 import register_source


REAL_THEORY = (
    Path(__file__).resolve().parents[3]
    / "modules/02_Foundation_Models_and_AI_Application_Architecture/"
    "02_Foundation_Models_and_AI_Application_Architecture_Theory.md"
)


class Lab02CommandLineTests(unittest.TestCase):
    def test_check_fixtures_reports_three_offline_gates_without_changing_the_vault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            course_root = root / "course"
            vault = root / "vault"
            theory_path = course_root / (
                "modules/02_Foundation_Models_and_AI_Application_Architecture/"
                "02_Foundation_Models_and_AI_Application_Architecture_Theory.md"
            )
            theory_path.parent.mkdir(parents=True)
            theory_path.write_bytes(REAL_THEORY.read_bytes())
            register_source(
                course_root=course_root,
                theory_path=theory_path,
                vault=vault,
                course_repository="https://example.test/course.git",
                course_commit="a" * 40,
                registered_by="student-01",
            )
            before = {
                path.relative_to(vault).as_posix(): path.read_bytes()
                for path in vault.rglob("*")
                if path.is_file()
            }
            stdout, stderr = io.StringIO(), io.StringIO()

            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["lab02", "check-fixtures", "--vault", str(vault)])

            self.assertEqual(code, 0)
            self.assertEqual(stderr.getvalue(), "")
            output = stdout.getvalue()
            self.assertIn("valid-response.json: passed deterministic gates", output)
            self.assertIn("malformed-response.txt: refused at syntactic gate", output)
            self.assertIn(
                "semantic-unsupported-response.json: passed deterministic gates; semantic review required",
                output,
            )
            self.assertIn("accepted state: unchanged", output)
            after = {
                path.relative_to(vault).as_posix(): path.read_bytes()
                for path in vault.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

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
