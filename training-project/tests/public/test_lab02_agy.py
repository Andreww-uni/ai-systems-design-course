import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from learning_project.cli import main
from learning_project.agy_adapter import run_agy
from learning_project.workflow import WorkflowError


class Lab02AgyAdapterTests(unittest.TestCase):
    def test_agy_profile_refuses_multiple_json_values_without_writing_partial_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_dir = root / "reports/lab02"
            run_dir = report_dir / "runs/live-primary-01"
            run_dir.mkdir(parents=True)
            (run_dir / "model-request.json").write_text(
                json.dumps({"request_id": "lab02-structured-output-v1"}), encoding="utf-8"
            )
            schema_path = root / "candidate.schema.json"
            schema_path.write_text("{}", encoding="utf-8")

            def runner(command, **_kwargs):
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps(
                        {"status": "SUCCESS", "response": '{"first":1}\n{"second":2}'}
                    ),
                    stderr="",
                )

            with self.assertRaisesRegex(WorkflowError, "exactly one JSON object"):
                run_agy(
                    report_dir=report_dir,
                    run_id="live-primary-01",
                    schema_path=schema_path,
                    model_id="gemini-3.8-flash-low",
                    recorded_by="student-01",
                    runner=runner,
                )

            self.assertFalse((run_dir / "raw-response.txt").exists())
            self.assertFalse((run_dir / "run-metadata.json").exists())

    def test_agy_profile_extracts_only_the_structured_response_and_records_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_dir = root / "reports/lab02"
            run_dir = report_dir / "runs/live-primary-01"
            run_dir.mkdir(parents=True)
            request = {"request_id": "lab02-structured-output-v1", "source": {"text": "source"}}
            (run_dir / "model-request.json").write_text(
                json.dumps(request) + "\n", encoding="utf-8"
            )
            schema_path = root / "candidate.schema.json"
            schema_path.write_text("{}", encoding="utf-8")
            candidate_text = '{"schema_version":"1.0"}'
            captured = {}

            def runner(command, **kwargs):
                captured["command"] = command
                captured["kwargs"] = kwargs
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps({"status": "SUCCESS", "response": candidate_text}),
                    stderr="",
                )

            result = run_agy(
                report_dir=report_dir,
                run_id="live-primary-01",
                schema_path=schema_path,
                model_id="gemini-3.8-flash-low",
                recorded_by="student-01",
                runner=runner,
            )

            self.assertEqual(result["model_id"], "gemini-3.8-flash-low")
            self.assertEqual(
                (run_dir / "raw-response.txt").read_bytes(), candidate_text.encode("utf-8")
            )
            metadata = json.loads(
                (run_dir / "run-metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(metadata["evidence_kind"], "live")
            self.assertEqual(metadata["adapter"], "agy")
            self.assertEqual(metadata["model_id"], "gemini-3.8-flash-low")
            self.assertEqual(metadata["recorded_by"], "student-01")

            command = captured["command"]
            self.assertEqual(command[0], "agy")
            self.assertEqual(command[1], "--print")
            self.assertIn("definition, syntax-vs-semantics, authority-boundary", command[2])
            self.assertIn("in that exact order", command[2])
            self.assertEqual(command[command.index("--model") + 1], "gemini-3.8-flash-low")
            self.assertEqual(command[command.index("--json-schema") + 1], str(schema_path))
            self.assertEqual(command[command.index("--output-format") + 1], "json")
            self.assertIn("--sandbox", command)
            self.assertEqual(captured["kwargs"]["timeout"], 330)
            self.assertTrue(captured["kwargs"]["capture_output"])
            self.assertTrue(captured["kwargs"]["text"])


class Lab02AgyCommandTests(unittest.TestCase):
    @patch("learning_project.cli.run_agy")
    def test_run_agy_command_uses_the_selected_model_and_run_attribution(self, mocked_run) -> None:
        mocked_run.return_value = {"model_id": "gemini-3.8-flash-low"}

        code = main(
            [
                "lab02",
                "run-agy",
                "--report-dir",
                "reports/lab02",
                "--run-id",
                "live-primary-01",
                "--model-id",
                "gemini-3.8-flash-low",
                "--by",
                "student-01",
            ]
        )

        self.assertEqual(code, 0)
        kwargs = mocked_run.call_args.kwargs
        self.assertEqual(kwargs["report_dir"], Path("reports/lab02"))
        self.assertEqual(kwargs["run_id"], "live-primary-01")
        self.assertEqual(kwargs["model_id"], "gemini-3.8-flash-low")
        self.assertEqual(kwargs["recorded_by"], "student-01")
        self.assertEqual(kwargs["schema_path"].name, "lab02-candidate.schema.json")


if __name__ == "__main__":
    unittest.main()
