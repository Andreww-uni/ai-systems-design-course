import contextlib
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from learning_project.cli import main
from learning_project.openai_compatible import run_openrouter
from learning_project.workflow import WorkflowError


class _Response:
    def __init__(self, payload: dict) -> None:
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return self._data


class Lab02OpenRouterAdapterTests(unittest.TestCase):
    def test_openrouter_profile_enforces_an_overall_deadline_without_writing_partial_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_dir = root / "reports/lab02"
            run_dir = report_dir / "runs/live-fallback-01"
            run_dir.mkdir(parents=True)
            (run_dir / "model-request.json").write_text(
                json.dumps({"request_id": "lab02-structured-output-v1"}), encoding="utf-8"
            )
            schema_path = root / "candidate.schema.json"
            schema_path.write_text("{}", encoding="utf-8")

            def opener(*_args, **_kwargs):
                threading.Event().wait(0.2)
                self.fail("A timed-out request must not rejoin the main workflow.")

            with self.assertRaisesRegex(WorkflowError, "timed out"):
                run_openrouter(
                    report_dir=report_dir,
                    run_id="live-fallback-01",
                    schema_path=schema_path,
                    api_key="secret-test-key",
                    recorded_by="student-01",
                    opener=opener,
                    deadline_seconds=0.01,
                )

            self.assertFalse((run_dir / "raw-response.txt").exists())
            self.assertFalse((run_dir / "run-metadata.json").exists())

    def test_openrouter_profile_refuses_path_traversal_run_id_before_network(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_dir = root / "reports/lab02"
            schema_path = root / "candidate.schema.json"
            schema_path.write_text("{}", encoding="utf-8")

            def opener(*_args, **_kwargs):
                self.fail("Network must not be called for an invalid run ID.")

            with self.assertRaisesRegex(WorkflowError, "run_id"):
                run_openrouter(
                    report_dir=report_dir,
                    run_id="../../escape",
                    schema_path=schema_path,
                    api_key="secret-test-key",
                    recorded_by="student-01",
                    opener=opener,
                )

            self.assertFalse((root / "escape/raw-response.txt").exists())

    def test_openrouter_profile_refuses_missing_attribution_before_network_or_partial_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_dir = root / "reports/lab02"
            run_dir = report_dir / "runs/live-fallback-01"
            run_dir.mkdir(parents=True)
            (run_dir / "model-request.json").write_text(
                json.dumps({"request_id": "lab02-structured-output-v1"}), encoding="utf-8"
            )
            schema_path = root / "candidate.schema.json"
            schema_path.write_text("{}", encoding="utf-8")

            def opener(*_args, **_kwargs):
                self.fail("Network must not be called without run attribution.")

            with self.assertRaisesRegex(WorkflowError, "recorded_by"):
                run_openrouter(
                    report_dir=report_dir,
                    run_id="live-fallback-01",
                    schema_path=schema_path,
                    api_key="secret-test-key",
                    recorded_by="",
                    opener=opener,
                )

            self.assertFalse((run_dir / "raw-response.txt").exists())
            self.assertFalse((run_dir / "run-metadata.json").exists())

    def test_openrouter_profile_refuses_a_missing_api_key_before_network_or_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_dir = root / "reports/lab02"
            run_dir = report_dir / "runs/live-fallback-01"
            run_dir.mkdir(parents=True)
            (run_dir / "model-request.json").write_text(
                json.dumps({"request_id": "lab02-structured-output-v1"}), encoding="utf-8"
            )
            schema_path = root / "candidate.schema.json"
            schema_path.write_text("{}", encoding="utf-8")

            def opener(*_args, **_kwargs):
                self.fail("Network must not be called without an API key.")

            with self.assertRaisesRegex(WorkflowError, "OPENROUTER_API_KEY"):
                run_openrouter(
                    report_dir=report_dir,
                    run_id="live-fallback-01",
                    schema_path=schema_path,
                    api_key="",
                    recorded_by="student-01",
                    opener=opener,
                )

            self.assertFalse((run_dir / "raw-response.txt").exists())
            self.assertFalse((run_dir / "run-metadata.json").exists())

    def test_openrouter_profile_writes_only_message_content_and_bound_run_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_dir = root / "reports/lab02"
            run_dir = report_dir / "runs/live-fallback-01"
            run_dir.mkdir(parents=True)
            request = {
                "schema_version": "1.0",
                "request_id": "lab02-structured-output-v1",
                "operation": "create",
                "target_concept_id": "structured-output",
                "source": {"text": "Exact bounded source text."},
                "constraints": {
                    "source_only": True,
                    "exact_quotes": True,
                    "external_knowledge_allowed": False,
                },
                "output_schema_version": "1.0",
            }
            (run_dir / "model-request.json").write_text(
                json.dumps(request) + "\n", encoding="utf-8"
            )
            schema_path = root / "candidate.schema.json"
            schema_path.write_text(
                json.dumps(
                    {
                        "type": "object",
                        "properties": {"schema_version": {"const": "1.0"}},
                        "required": ["schema_version"],
                        "additionalProperties": False,
                    }
                ),
                encoding="utf-8",
            )
            candidate_text = '{"schema_version":"1.0"}'
            captured = {}

            def opener(request_object, timeout):
                captured["request"] = request_object
                captured["timeout"] = timeout
                return _Response(
                    {
                        "model": "example/free-model:free",
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"role": "assistant", "content": candidate_text},
                            }
                        ],
                    }
                )

            result = run_openrouter(
                report_dir=report_dir,
                run_id="live-fallback-01",
                schema_path=schema_path,
                api_key="secret-test-key",
                recorded_by="student-01",
                opener=opener,
            )

            self.assertEqual(result["model_id"], "example/free-model:free")
            self.assertEqual(
                (run_dir / "raw-response.txt").read_bytes(), candidate_text.encode("utf-8")
            )
            metadata = json.loads(
                (run_dir / "run-metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(metadata["evidence_kind"], "live")
            self.assertEqual(metadata["adapter"], "openai-compatible")
            self.assertEqual(metadata["model_id"], "example/free-model:free")
            self.assertEqual(metadata["recorded_by"], "student-01")

            request_object = captured["request"]
            self.assertEqual(request_object.full_url, "https://openrouter.ai/api/v1/chat/completions")
            self.assertEqual(captured["timeout"], 120)
            self.assertEqual(request_object.get_header("Authorization"), "Bearer secret-test-key")
            body = json.loads(request_object.data)
            self.assertEqual(body["model"], "nex-agi/nex-n2.5-mini:free")
            self.assertFalse(body["stream"])
            self.assertTrue(body["provider"]["require_parameters"])
            self.assertEqual(body["response_format"]["type"], "json_schema")
            self.assertTrue(body["response_format"]["json_schema"]["strict"])
            self.assertEqual(
                body["response_format"]["json_schema"]["schema"],
                json.loads(schema_path.read_text(encoding="utf-8")),
            )
            system_prompt = body["messages"][0]["content"]
            self.assertIn(
                "definition, syntax-vs-semantics, authority-boundary",
                system_prompt,
            )
            self.assertIn("in that exact order", system_prompt)
            self.assertNotIn("plugins", body)
            self.assertNotIn("secret-test-key", (run_dir / "raw-response.txt").read_text())
            self.assertNotIn("secret-test-key", (run_dir / "run-metadata.json").read_text())


class Lab02OpenRouterCommandTests(unittest.TestCase):
    @patch("learning_project.cli.run_openrouter")
    def test_run_openrouter_command_reads_the_key_from_the_environment(self, mocked_run) -> None:
        mocked_run.return_value = {"model_id": "example/free-model:free"}
        stdout, stderr = io.StringIO(), io.StringIO()

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "secret-test-key"}, clear=True):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "lab02",
                        "run-openrouter",
                        "--report-dir",
                        "reports/lab02",
                        "--run-id",
                        "live-fallback-01",
                        "--by",
                        "student-01",
                    ]
                )

        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("example/free-model:free", stdout.getvalue())
        self.assertNotIn("secret-test-key", stdout.getvalue())
        kwargs = mocked_run.call_args.kwargs
        self.assertEqual(kwargs["report_dir"], Path("reports/lab02"))
        self.assertEqual(kwargs["run_id"], "live-fallback-01")
        self.assertEqual(kwargs["api_key"], "secret-test-key")
        self.assertEqual(kwargs["recorded_by"], "student-01")
        self.assertEqual(kwargs["schema_path"].name, "lab02-candidate.schema.json")


if __name__ == "__main__":
    unittest.main()
