import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from learning_project.lab02 import import_response, prepare_request, register_source
from learning_project.workflow import WorkflowError


SOURCE_ID = "module-02-foundation-models-and-ai-application-architecture"
FRAGMENT_ID = "module-02-1-3-structured-output-controls-v1"

THEORY_TEXT = """# Module 02

Intro.

### 1.3 Structured output controls syntax, not meaning

Structured output is machine-readable.

Valid JSON syntax does not prove semantic support.

Only an authorized human decision permits accepted state.

> **Further reading:** excluded material.

## 2. Next section
"""

EXPECTED_FRAGMENT = """### 1.3 Structured output controls syntax, not meaning

Structured output is machine-readable.

Valid JSON syntax does not prove semantic support.

Only an authorized human decision permits accepted state.

"""

VALID_RESPONSE = {
    "schema_version": "1.0",
    "concept_id": "structured-output",
    "title": "Structured Output",
    "definition": "Model output intended to follow an explicit machine-readable organization.",
    "key_points": [
        "A syntactic gate checks parsing.",
        "A deterministic gate checks invariants.",
        "A semantic gate requires human judgment.",
    ],
    "source_support": [
        {
            "claim_kind": "definition",
            "claim": "The output follows an explicit machine-readable organization.",
            "quote": "Structured output is machine-readable.",
        },
        {
            "claim_kind": "syntax-vs-semantics",
            "claim": "Syntactic validity does not establish semantic support.",
            "quote": "Valid JSON syntax does not prove semantic support.",
        },
        {
            "claim_kind": "authority-boundary",
            "claim": "Accepted state requires a human decision.",
            "quote": "Only an authorized human decision permits accepted state.",
        },
    ],
    "tags": ["domain/ai-engineering"],
}


class Lab02SourceRegistrationTests(unittest.TestCase):
    def test_register_source_preserves_the_exact_section_before_further_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            course_root = root / "course"
            vault = root / "vault"
            theory_path = course_root / "module-02-theory.md"
            theory_path.parent.mkdir()
            theory_path.write_text(THEORY_TEXT, encoding="utf-8")

            source_path = register_source(
                course_root=course_root,
                theory_path=theory_path,
                vault=vault,
                course_repository="https://example.test/course.git",
                course_commit="a" * 40,
                registered_by="student-01",
            )

            text = source_path.read_text(encoding="utf-8")
            _, frontmatter_text, fragment = text.split("---\n", 2)
            metadata = yaml.safe_load(frontmatter_text)
            self.assertEqual(
                source_path,
                vault / f"sources/{SOURCE_ID}.md",
            )
            self.assertEqual(fragment, EXPECTED_FRAGMENT)
            self.assertEqual(metadata["record_type"], "source")
            self.assertEqual(metadata["source_id"], SOURCE_ID)
            self.assertEqual(metadata["course_path"], "module-02-theory.md")
            fragments = metadata["fragments"]
            self.assertEqual(len(fragments), 1)
            self.assertEqual(fragments[0]["fragment_id"], FRAGMENT_ID)
            self.assertEqual(
                fragments[0]["fragment_sha256"],
                hashlib.sha256(EXPECTED_FRAGMENT.encode("utf-8")).hexdigest(),
            )
            self.assertEqual(fragments[0]["boundary_end"], "> **Further reading:**")

    def test_register_source_refuses_a_vault_inside_the_course_clone(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            course_root = Path(temp_dir) / "course"
            theory_path = course_root / "module-02-theory.md"
            theory_path.parent.mkdir()
            theory_path.write_text(THEORY_TEXT, encoding="utf-8")

            with self.assertRaisesRegex(WorkflowError, "outside the course repository"):
                register_source(
                    course_root=course_root,
                    theory_path=theory_path,
                    vault=course_root / "vault",
                    course_repository="https://example.test/course.git",
                    course_commit="a" * 40,
                    registered_by="student-01",
                )

    def test_register_source_is_a_no_op_for_the_same_source_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            course_root = root / "course"
            vault = root / "vault"
            theory_path = course_root / "module-02-theory.md"
            theory_path.parent.mkdir()
            theory_path.write_text(THEORY_TEXT, encoding="utf-8")
            arguments = {
                "course_root": course_root,
                "theory_path": theory_path,
                "vault": vault,
                "course_repository": "https://example.test/course.git",
                "course_commit": "a" * 40,
                "registered_by": "student-01",
            }

            source_path = register_source(**arguments)
            first_text = source_path.read_text(encoding="utf-8")
            register_source(**arguments)

            self.assertEqual(source_path.read_text(encoding="utf-8"), first_text)

    def test_register_source_refuses_different_content_for_the_same_source_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            course_root = root / "course"
            vault = root / "vault"
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

            with self.assertRaisesRegex(WorkflowError, "different content"):
                register_source(
                    course_root=course_root,
                    theory_path=theory_path,
                    vault=vault,
                    course_repository="https://example.test/course.git",
                    course_commit="b" * 40,
                    registered_by="student-01",
                )


class Lab02RequestPreparationTests(unittest.TestCase):
    def test_candidate_json_schema_matches_the_closed_request_contract(self) -> None:
        schema_path = (
            Path(__file__).resolve().parents[2] / "schemas/lab02-candidate.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(VALID_RESPONSE))
        support = schema["properties"]["source_support"]
        self.assertEqual(support["minItems"], 3)
        self.assertEqual(support["maxItems"], 3)
        self.assertIsInstance(support["items"], dict)
        self.assertEqual(
            set(support["items"]["required"]), {"claim_kind", "claim", "quote"}
        )
        self.assertEqual(
            set(support["items"]["properties"]["claim_kind"]["enum"]),
            {"definition", "syntax-vs-semantics", "authority-boundary"},
        )
        self.assertIsInstance(schema["properties"]["tags"]["items"], dict)

    def test_prepare_request_embeds_the_exact_registered_fragment_and_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
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

            request_path = prepare_request(
                vault=vault, report_dir=report_dir, run_id="live-primary-01"
            )

            request = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertEqual(
                request_path,
                report_dir / "runs/live-primary-01/model-request.json",
            )
            self.assertEqual(request["request_id"], "lab02-structured-output-v1")
            self.assertEqual(request["operation"], "create")
            self.assertEqual(request["target_concept_id"], "structured-output")
            self.assertEqual(request["source"]["source_id"], SOURCE_ID)
            self.assertEqual(request["source"]["fragment_id"], FRAGMENT_ID)
            self.assertEqual(request["source"]["text"], EXPECTED_FRAGMENT)
            self.assertEqual(
                request["source"]["fragment_sha256"],
                hashlib.sha256(EXPECTED_FRAGMENT.encode("utf-8")).hexdigest(),
            )
            self.assertTrue(request["constraints"]["source_only"])
            self.assertTrue(request["constraints"]["exact_quotes"])
            self.assertFalse(request["constraints"]["external_knowledge_allowed"])
            self.assertEqual(request["output_schema_version"], "1.0")

    def test_prepare_request_writes_identical_request_bytes_for_two_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
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

            first = prepare_request(
                vault=vault, report_dir=report_dir, run_id="live-primary-01"
            )
            second = prepare_request(
                vault=vault, report_dir=report_dir, run_id="live-primary-02"
            )

            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_prepare_request_refuses_to_overwrite_different_request_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
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
            request_path = prepare_request(
                vault=vault, report_dir=report_dir, run_id="live-primary-01"
            )
            request_path.write_text('{"tampered": true}\n', encoding="utf-8")

            with self.assertRaisesRegex(WorkflowError, "already exists"):
                prepare_request(
                    vault=vault, report_dir=report_dir, run_id="live-primary-01"
                )

    def test_import_response_creates_a_write_once_proposal_bound_to_raw_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
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
            prepare_request(vault=vault, report_dir=report_dir, run_id="live-primary-01")
            raw_path = report_dir / "runs/live-primary-01/raw-response.txt"
            transport_response = {
                **VALID_RESPONSE,
                "toolAction": "Submitting structured output candidate",
                "toolSummary": "Submit candidate payload",
            }
            raw_bytes = (json.dumps(transport_response, ensure_ascii=False) + "\n").encode("utf-8")
            raw_path.write_bytes(raw_bytes)

            proposal_path = import_response(
                vault=vault,
                report_dir=report_dir,
                run_id="live-primary-01",
                evidence_kind="live",
            )

            _, frontmatter_text, body = proposal_path.read_text(encoding="utf-8").split(
                "---\n", 2
            )
            frontmatter = yaml.safe_load(frontmatter_text)
            self.assertEqual(
                proposal_path,
                vault / "proposals/lab02-structured-output-live-primary-01.md",
            )
            self.assertEqual(
                frontmatter["proposal_id"], "lab02-structured-output-live-primary-01"
            )
            self.assertEqual(frontmatter["status"], "proposed")
            self.assertEqual(frontmatter["origin"], "model-normalized")
            self.assertEqual(frontmatter["target"], "concepts/structured-output.md")
            self.assertEqual(frontmatter["evidence"]["evidence_kind"], "live")
            self.assertEqual(
                frontmatter["evidence"]["raw_response_sha256"],
                hashlib.sha256(raw_bytes).hexdigest(),
            )
            self.assertEqual(frontmatter["evidence"]["source_id"], SOURCE_ID)
            self.assertEqual(frontmatter["evidence"]["fragment_id"], FRAGMENT_ID)
            self.assertEqual(
                frontmatter["proposed_concept"]["definition"],
                VALID_RESPONSE["definition"],
            )
            self.assertIn("```json", body)
            self.assertIn(VALID_RESPONSE["definition"], body)
            self.assertNotIn("toolAction", body)
            self.assertNotIn("toolSummary", body)
            self.assertEqual(raw_path.read_bytes(), raw_bytes)


if __name__ == "__main__":
    unittest.main()
