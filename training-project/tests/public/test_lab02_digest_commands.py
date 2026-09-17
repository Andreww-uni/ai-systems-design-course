import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DIGEST_SNIPPET = (
    "import hashlib,pathlib,sys; "
    "print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())"
)
LAB = (
    Path(__file__).resolve().parents[3]
    / "modules/02_Foundation_Models_and_AI_Application_Architecture/"
    "02_Foundation_Models_and_AI_Application_Architecture_Lab.md"
)
WINDOWS_PATHS = (
    r"C:\Users\Student\vault",
    r"C:\absolute\path\to\ai-systems-learning-vault",
)


class Lab02DigestCommandTests(unittest.TestCase):
    def test_documented_digest_commands_pass_paths_through_argv(self) -> None:
        text = LAB.read_text(encoding="utf-8")
        self.assertIn("sys.argv[1]", text)
        self.assertNotIn("Path('$vault", text)
        self.assertNotIn('Path("$vault', text)

    def test_argv_preserves_windows_paths_that_break_embedded_python_literals(self) -> None:
        for raw_path in WINDOWS_PATHS:
            printed = subprocess.run(
                [sys.executable, "-c", "import sys; print(sys.argv[1])", raw_path],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(printed.stdout.rstrip("\n"), raw_path)

            interpolated = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    f"from pathlib import Path; print(Path('{raw_path}'))",
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "vault": raw_path},
            )
            self.assertNotEqual(interpolated.stdout.rstrip("\n"), raw_path, interpolated.stderr)
            self.assertTrue(
                interpolated.returncode != 0
                or "unicodeescape" in interpolated.stderr.lower()
                or interpolated.stdout.rstrip("\n") != raw_path,
                interpolated.stderr or interpolated.stdout,
            )

    def test_argv_digest_matches_bytes_for_special_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cases = [
                root / "ordinary.txt",
                root / "path with spaces.txt",
                root / "student's vault.txt",
                root / "сховище.txt",
            ]
            for path in cases:
                payload = f"payload for {path.name}\n".encode("utf-8")
                path.write_bytes(payload)
                result = subprocess.run(
                    [sys.executable, "-c", DIGEST_SNIPPET, str(path)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), hashlib.sha256(payload).hexdigest())

    @unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "POSIX Bash check only")
    def test_posix_shell_quoting_preserves_argv_digest_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "student's сховище"
            target = vault / "proposals" / "lab02-structured-output-live-primary-01.md"
            target.parent.mkdir(parents=True)
            payload = b"canonical proposal bytes\n"
            target.write_bytes(payload)
            result = subprocess.run(
                [
                    "bash",
                    "-lc",
                    f'{shlex.quote(sys.executable)} -c "{DIGEST_SNIPPET}" "$vault/proposals/lab02-structured-output-live-primary-01.md"',
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "vault": str(vault)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), hashlib.sha256(payload).hexdigest())


if __name__ == "__main__":
    unittest.main()
