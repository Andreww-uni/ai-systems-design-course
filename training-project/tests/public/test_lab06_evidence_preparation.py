"""Paired source-text preparation; no provider calls or semantic acceptance."""
from __future__ import annotations

import unittest

import test_lab06_graph_queries as queries


class EvidencePreparationTests(unittest.TestCase):
    def setUp(self):
        self.query = queries.GraphQueryTests()
        self.query.setUp()
        self.addCleanup(self.query.doCleanups)
        self.root = self.query.root
        self.read = self.query.read
        self.output = self.root / "evidence-preparation.json"

    def prepare(self, output=None, fixture=None):
        args = ["prepare-evidence", "--collection", self.query.collection,
                "--graph", self.query.graph, "--output", output or self.output]
        if fixture is not None:
            args += ["--fixture", fixture]
        return self.query.cli(*args)

    def test_paired_preparation_adds_source_text_not_graph_paths(self):
        before = self.query.graph.read_bytes(), (self.query.collection / "accepted.json").read_bytes()
        code, message = self.prepare()
        self.assertEqual(code, 0, message)
        result = self.read(self.output)
        pair = result["inputs"][0]["configurations"]
        baseline, expanded = pair["without graph expansion"], pair["with graph expansion"]
        self.assertEqual(baseline["candidate_fragment_ids"], ["F-1"])
        self.assertEqual(expanded["candidate_fragment_ids"], ["F-1", "F-2"])
        self.assertEqual(expanded["entry_node_lookup"], {"status": "resolved", "matched_node_ids": ["C-RET"]})
        self.assertEqual([p["relation_record_ids"] for p in expanded["paths"]], [["R-1"], ["R-1", "R-2"]])
        for config, ids in [(baseline, ["F-1"]), (expanded, ["F-1", "F-2"])]:
            request = config["bounded_model_request"]
            self.assertEqual(set(request), {"task instruction", "supplied source evidence", "output contract"})
            self.assertEqual([f["retrieval unit id"] for f in request["supplied source evidence"]], ids)
            self.assertNotIn("R-1", str(request))
            self.assertNotIn("C-QUERY", str(request))
        self.assertEqual(baseline["bounded_model_request"]["task instruction"], expanded["bounded_model_request"]["task instruction"])
        self.assertEqual(baseline["bounded_model_request"]["output contract"], expanded["bounded_model_request"]["output contract"])
        self.assertEqual(before, (self.query.graph.read_bytes(), (self.query.collection / "accepted.json").read_bytes()))

    def test_discovery_without_admission_preserves_original_order(self):
        self.assertEqual(self.prepare()[0], 0)
        inputs = self.read(self.output)["inputs"]
        self.assertEqual([item["input_id"] for item in inputs], ["support-addition", "budget-exclusion"])
        pair = inputs[1]["configurations"]
        baseline, expanded = pair["without graph expansion"], pair["with graph expansion"]
        self.assertEqual(expanded["candidate_fragment_ids"], ["F-1", "F-3", "F-2"])
        self.assertEqual(expanded["discovered_fragment_ids"], ["F-1", "F-2"])
        self.assertEqual(expanded["selection_record"]["exclusions"], [{
            "retrieval unit id": "F-2", "failed criterion": "context-budget fit",
            "evaluated criteria": ["provenance-link resolution", "context-budget fit"],
            "remaining context budget characters before unit": 96, "text character count": 133}])
        self.assertEqual(expanded["bounded_model_request"], baseline["bounded_model_request"])
        self.assertEqual(expanded["selection_record"]["remaining context budget characters"], 96)

    def verify(self):
        return self.query.cli("verify-evidence", "--collection", self.query.collection,
                              "--graph", self.query.graph, "--evidence", self.output)

    def test_verification_recomputes_every_trace_and_request(self):
        self.assertEqual(self.prepare()[0], 0)
        code, message = self.verify()
        self.assertEqual(code, 0, message)
        self.assertIn("2 teaching inputs and 4 requests", message)
        original = self.read(self.output)
        import copy
        for field in ["paths", "bounded_model_request", "candidate_fragment_ids", "selection_record"]:
            altered = copy.deepcopy(original)
            altered["inputs"][0]["configurations"]["with graph expansion"][field] = {}
            self.output.write_text(__import__("json").dumps(altered), encoding="utf-8")
            code, message = self.verify()
            self.assertEqual(code, 1, message)
            self.assertIn("differs", message)

    def test_invalid_preparation_inputs_fail_before_output(self):
        import copy
        from learning_project.lab06 import DEFAULT_INPUT
        fixture = self.read(DEFAULT_INPUT.with_name("evidence-preparation.json"))
        variants = []
        for field, value in [("schema_version", "unknown"), ("context_budget_characters", True),
                             ("inputs", None), ("inputs", []), ("input_kind", "")]:
            altered = copy.deepcopy(fixture)
            altered[field] = value
            variants.append(altered)
        for field, value in [("input_id", ""), ("target_label", None),
                             ("original_fragment_ids", ["NOT-REGISTERED"]),
                             ("original_fragment_ids", "F-1")]:
            altered = copy.deepcopy(fixture)
            altered["inputs"][0][field] = value
            variants.append(altered)
        altered = copy.deepcopy(fixture)
        altered["inputs"].append(copy.deepcopy(altered["inputs"][0]))
        variants.append(altered)
        import json
        for i, altered in enumerate(variants):
            with self.subTest(variant=i):
                path = self.root / f"invalid-{i}.json"
                path.write_text(json.dumps(altered), encoding="utf-8")
                out = self.root / f"invalid-output-{i}.json"
                code, message = self.prepare(out, path)
                self.assertEqual(code, 1, message)
                self.assertFalse(out.exists())

    def test_empty_original_result_prepares_empty_evidence_not_a_refusal(self):
        from learning_project.lab06 import _evidence_configuration
        from learning_project.workflow import WorkflowError
        try:
            prepared = _evidence_configuration(self.read(self.query.graph), "Embedding-based retrieval", [], 250, True)
        except WorkflowError as exc:
            self.fail(f"Empty retrieval must use the declared fallback: {exc}")
        self.assertEqual(prepared["entry_node_lookup"], {"status": "unresolved", "matched_node_ids": []})
        self.assertEqual(prepared["bounded_model_request"]["supplied source evidence"], [])
        self.assertNotIn("outcome_type", prepared)
        self.assertEqual(prepared["selection_record"]["remaining context budget characters"], 250)

    def test_selection_records_have_distinct_contextual_identifiers(self):
        self.assertEqual(self.prepare()[0], 0)
        identities = [c["selection_record"]["selection record id"] for i in self.read(self.output)["inputs"]
                      for c in i["configurations"].values()]
        self.assertEqual(len(identities), 4)
        self.assertEqual(len(set(identities)), 4)

    def test_lookup_uses_exact_primary_label_and_only_original_associations(self):
        from learning_project.lab06 import _evidence_configuration
        import copy
        graph = self.read(self.query.graph)
        for target, originals in [("Embedding-based retrieval", ["F-2"]),
                                  ("embedding-based retrieval", ["F-1"]),
                                  ("retrieval", ["F-1"])]:
            result = _evidence_configuration(graph, target, originals, 250, True)
            self.assertEqual(result["entry_node_lookup"], {"status": "unresolved", "matched_node_ids": []})
            self.assertEqual(result["paths"], [])
            self.assertEqual(result["candidate_fragment_ids"], originals)
            self.assertEqual(len(result["bounded_model_request"]["supplied source evidence"]), 1)
        multiple = copy.deepcopy(graph)
        multiple["nodes"][1]["primary_label"] = "Embedding-based retrieval"
        result = _evidence_configuration(multiple, "Embedding-based retrieval", ["F-1"], 250, True)
        self.assertEqual(result["entry_node_lookup"], {"status": "unresolved", "matched_node_ids": ["C-QUERY", "C-RET"]})
        self.assertEqual(result["paths"], [])
        graph["mention_associations"].append(copy.deepcopy(graph["mention_associations"][0]))
        result = _evidence_configuration(graph, "Embedding-based retrieval", ["F-1", "F-1"], 250, True)
        self.assertEqual(result["entry_node_lookup"]["matched_node_ids"], ["C-RET"])
        self.assertEqual(result["candidate_fragment_ids"], ["F-1", "F-2"])

    def test_duplicate_only_discovery_does_not_change_the_request(self):
        from learning_project.lab06 import _evidence_configuration
        graph = self.read(self.query.graph)
        baseline = _evidence_configuration(graph, "Embedding-based retrieval", ["F-1", "F-2"], 250, False)
        expanded = _evidence_configuration(graph, "Embedding-based retrieval", ["F-1", "F-2"], 250, True)
        self.assertEqual(expanded["added_fragment_ids"], [])
        self.assertEqual(len(expanded["paths"]), 2)
        self.assertEqual(expanded["bounded_model_request"], baseline["bounded_model_request"])

    def test_fragment_identity_not_similar_text_controls_deduplication(self):
        from learning_project.lab06 import _evidence_configuration
        graph = self.read(self.query.graph)
        graph["fragments"].append({**graph["fragments"][0], "id": "synthetic-same-text"})
        result = _evidence_configuration(graph, "Embedding-based retrieval", ["F-1", "synthetic-same-text"], 500, False)
        self.assertEqual(result["candidate_fragment_ids"], ["F-1", "synthetic-same-text"])
        self.assertEqual(len(result["bounded_model_request"]["supplied source evidence"]), 2)

    def test_provenance_failure_precedes_budget_and_does_not_stop_later_admission(self):
        from learning_project.lab06 import _evidence_configuration
        graph = self.read(self.query.graph)
        graph["fragments"][0]["provenance"]["source_id"] = "synthetic-missing-source"
        result = _evidence_configuration(graph, "Embedding-based retrieval", ["F-1", "F-3"], 55, False)
        self.assertEqual(result["selection_record"]["exclusions"][0]["failed criterion"], "provenance-link resolution")
        self.assertEqual(result["selection_record"]["exclusions"][0]["evaluated criteria"], ["provenance-link resolution"])
        self.assertEqual([u["retrieval unit id"] for u in result["bounded_model_request"]["supplied source evidence"]], ["F-3"])
        self.assertEqual(result["selection_record"]["remaining context budget characters"], 6)

    def test_evaluator_fields_and_unselected_text_do_not_enter_requests(self):
        from learning_project.lab06 import DEFAULT_INPUT
        import json
        fixture = self.read(DEFAULT_INPUT.with_name("evidence-preparation.json"))
        fixture["hidden answers"] = "DO-NOT-LEAK-ROOT"
        fixture["inputs"][0]["evaluator-only rubrics or judging instructions"] = "DO-NOT-LEAK-CASE"
        path = self.root / "private-fields.json"
        path.write_text(json.dumps(fixture), encoding="utf-8")
        self.assertEqual(self.prepare(fixture=path)[0], 0)
        result = self.read(self.output)
        for item in result["inputs"]:
            for config in item["configurations"].values():
                request = config["bounded_model_request"]
                self.assertNotIn("DO-NOT-LEAK", json.dumps(request))
                self.assertEqual(set(request), {"task instruction", "supplied source evidence", "output contract"})
        blocked = result["inputs"][1]["configurations"]["with graph expansion"]["bounded_model_request"]
        self.assertNotIn(self.read(self.query.graph)["fragments"][1]["text"], json.dumps(blocked))

    def test_missing_or_changed_prerequisites_stop_preparation_and_verification(self):
        self.assertEqual(self.prepare()[0], 0)
        accepted = self.query.collection / "accepted.json"
        paths = [self.query.graph, accepted]
        originals = [p.read_bytes() for p in paths]
        for path in paths:
            for missing in [False, True]:
                if missing:
                    path.unlink()
                else:
                    path.write_text("{}", encoding="utf-8")
                out = self.root / "must-not-exist.json"
                self.assertEqual(self.prepare(out)[0], 1)
                self.assertFalse(out.exists())
                self.assertEqual(self.verify()[0], 1)
                for p, data in zip(paths, originals):
                    p.write_bytes(data)

    def test_create_only_output_safety_and_determinism(self):
        self.assertEqual(self.prepare()[0], 0)
        second = self.root / "second.json"
        self.assertEqual(self.prepare(second)[0], 0)
        self.assertEqual(self.output.read_bytes(), second.read_bytes())
        target = self.root / "outside.txt"
        target.write_text("keep", encoding="utf-8")
        for kind in ["regular", "external", "dangling"]:
            out = self.root / "collision.json"
            if kind == "regular":
                out.write_text("preserve", encoding="utf-8")
            else:
                try:
                    out.symlink_to(target if kind == "external" else self.root / "absent")
                except OSError:
                    if __import__("os").name == "nt":
                        continue  # Native protected-writer tests own Windows reparse behavior.
                    raise
            self.assertEqual(self.prepare(out)[0], 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep")
            self.assertEqual(out.read_text(encoding="utf-8"), "preserve") if kind == "regular" else self.assertTrue(out.is_symlink())
            out.unlink()

    def test_supplied_policy_probes_expose_duplicate_only_and_unresolved_fallback(self):
        from learning_project.lab06 import DEFAULT_INPUT
        fixture = DEFAULT_INPUT.with_name("evidence-policy-probes.json")
        self.assertTrue(fixture.is_file(), "The required non-generation policy probes must be supplied.")
        self.assertEqual(self.prepare(fixture=fixture)[0], 0)
        inputs = self.read(self.output)["inputs"]
        self.assertEqual([i["input_id"] for i in inputs], ["duplicate-only", "unresolved-target"])
        duplicate, unresolved = [i["configurations"] for i in inputs]
        for pair in [duplicate, unresolved]:
            self.assertEqual(pair["without graph expansion"]["bounded_model_request"], pair["with graph expansion"]["bounded_model_request"])
        self.assertEqual(duplicate["with graph expansion"]["added_fragment_ids"], [])
        self.assertEqual(unresolved["with graph expansion"]["entry_node_lookup"]["status"], "unresolved")
        self.assertEqual(unresolved["with graph expansion"]["candidate_fragment_ids"], ["F-2"])


if __name__ == "__main__":
    unittest.main()
