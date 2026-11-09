"""Public acceptance tests for reviewed source-to-graph preparation."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from learning_project.cli import main


class GraphPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.review = self.root / "preparation" / "review.json"
        self.collection = self.root / "collection"
        self.graph = self.root / "preparation" / "graph.json"

    def cli(self, *args):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            try:
                code = main(["lab06", *map(str, args)])
            except SystemExit as exc:
                code = exc.code
        return code, stream.getvalue()

    def read(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def complete_review(self):
        code, output = self.cli("prepare-graph-review", "--output", self.review)
        self.assertEqual(code, 0, output)
        review = self.read(self.review)
        review["reviewer"] = "synthetic-test-reviewer"
        review["authorize"] = True
        for mention in review["reviewed_input"]["mentions"]:
            match = mention["proposed_concept_id"]
            review["mention_reviews"][mention["id"]] = {
                "outcome": "match" if match else "unresolved", "concept_id": match,
                "rationale": "Context identifies the accepted concept." if match else "Wording does not identify a unique concept.",
            }
        decisions = {"P-1": "accept", "P-2": "accept", "P-3": "reject", "P-4": "blocked"}
        reasons = {"P-1": "F-1 states this direction in the teaching route.",
                   "P-2": "F-2 states this direction in the teaching route.",
                   "P-3": "F-1 does not state the reverse direction.",
                   "P-4": "M-6 remains unresolved; no accepted endpoint."}
        for pid, decision in decisions.items():
            review["relation_reviews"][pid] = {"decision": decision, "rationale": reasons[pid]}
        self.save_review(review)
        return review

    def save_review(self, review):
        self.review.write_text(json.dumps(review), encoding="utf-8")

    def test_apply_records_only_exact_human_accepted_changes(self):
        review = self.complete_review()
        code, output = self.cli("apply-graph-review", "--review", self.review, "--collection", self.collection)
        self.assertEqual(code, 0, output)
        accepted = self.read(self.collection / "accepted.json")
        self.assertEqual(accepted["review"], review)
        self.assertEqual([r["id"] for r in accepted["relations"]], ["R-1", "R-2"])
        self.assertEqual(len(accepted["concepts"]), 3)
        self.assertEqual(len(accepted["mention_associations"]), 5)
        self.assertEqual([a["concept_id"] for a in accepted["mention_associations"]].count("C-QUERY"), 3)
        self.assertFalse(any(a["mention_id"] == "M-6" for a in accepted["mention_associations"]))
        self.assertEqual(accepted["relations"][0]["from"], "C-RET")
        self.assertEqual(accepted["relations"][0]["to"], "C-QUERY")
        self.assertEqual(accepted["relations"][0]["qualification"], "In this teaching route")

    def test_writer_requires_completed_explicit_authorization(self):
        review = self.complete_review()
        for field, value in [("authorize", False), ("authorize", "true"), ("reviewer", "")]:
            with self.subTest(field=field, value=value):
                changed = json.loads(json.dumps(review))
                changed[field] = value
                self.save_review(changed)
                code, output = self.cli("apply-graph-review", "--review", self.review, "--collection", self.collection)
                self.assertEqual(code, 1, output)
                self.assertFalse((self.collection / "accepted.json").exists())

    def test_incomplete_or_malformed_item_review_stops_before_storage(self):
        review = self.complete_review()
        changes = [
            lambda r: r["mention_reviews"]["M-1"].update(outcome="pending"),
            lambda r: r["mention_reviews"]["M-1"].update(concept_id="F-1"),
            lambda r: r["mention_reviews"]["M-6"].update(concept_id="C-QUERY"),
            lambda r: r["mention_reviews"].pop("M-5"),
            lambda r: r["mention_reviews"]["M-1"].update(rationale=""),
            lambda r: r["relation_reviews"]["P-1"].update(decision="pending"),
            lambda r: r["relation_reviews"]["P-4"].update(decision="accept"),
            lambda r: r["relation_reviews"]["P-1"].update(decision="blocked"),
            lambda r: r["relation_reviews"]["P-1"].update(rationale=""),
            lambda r: r.update(mention_reviews=[]),
            lambda r: r["relation_reviews"].update(extra={}),
        ]
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                changed = json.loads(json.dumps(review))
                change(changed)
                self.save_review(changed)
                code, output = self.cli("apply-graph-review", "--review", self.review, "--collection", self.collection)
                self.assertEqual(code, 1, output)
                self.assertFalse((self.collection / "accepted.json").exists())

    def test_compilation_is_deterministic_and_does_not_accept_or_infer_edges(self):
        self.complete_review()
        code, output = self.cli("apply-graph-review", "--review", self.review, "--collection", self.collection)
        self.assertEqual(code, 0, output)
        before = (self.collection / "accepted.json").read_bytes()
        for target in [self.graph, self.graph.with_name("rebuilt.json")]:
            code, output = self.cli("compile-graph", "--collection", self.collection, "--output", target)
            self.assertEqual(code, 0, output)
        self.assertEqual(self.graph.read_bytes(), self.graph.with_name("rebuilt.json").read_bytes())
        self.assertEqual((self.collection / "accepted.json").read_bytes(), before)
        graph = self.read(self.graph)
        self.assertEqual(len(graph["nodes"]), 3)
        self.assertEqual([(e["from"], e["to"]) for e in graph["edges"]], [("C-RET", "C-QUERY"), ("C-QUERY", "C-MODEL")])
        self.assertEqual([e["relation_record_id"] for e in graph["edges"]], ["R-1", "R-2"])
        self.assertEqual(graph["edges"][0]["support_fragment_ids"], ["F-1"])
        self.assertEqual(graph["fragments"][0]["provenance"]["source_id"], "S-TEACH")

    def test_verifier_detects_changed_graph_or_accepted_records(self):
        self.complete_review()
        self.assertEqual(self.cli("apply-graph-review", "--review", self.review, "--collection", self.collection)[0], 0)
        self.assertEqual(self.cli("compile-graph", "--collection", self.collection, "--output", self.graph)[0], 0)
        args = ("verify-graph", "--collection", self.collection, "--graph", self.graph)
        code, output = self.cli(*args)
        self.assertEqual(code, 0, output)
        self.assertIn("3 nodes and 2 edges", output)
        graph = self.read(self.graph)
        graph["edges"][0]["to"] = "C-MODEL"
        self.graph.write_text(json.dumps(graph), encoding="utf-8")
        self.assertEqual(self.cli(*args)[0], 1)
        accepted_path = self.collection / "accepted.json"
        accepted = self.read(accepted_path)
        accepted["relations"][0]["to"] = "C-MODEL"
        accepted_path.write_text(json.dumps(accepted), encoding="utf-8")
        self.assertEqual(self.cli("compile-graph", "--collection", self.collection, "--output", self.graph.with_name("bad.json"))[0], 1)
        self.assertFalse(self.graph.with_name("bad.json").exists())

    def test_changed_reviewed_input_is_not_authorization_for_original_proposals(self):
        review = self.complete_review()
        review["reviewed_input"]["proposals"][0]["to_mention"] = "M-4"
        self.save_review(review)
        self.assertEqual(self.cli("apply-graph-review", "--review", self.review, "--collection", self.collection)[0], 1)
        self.assertFalse((self.collection / "accepted.json").exists())

    def test_all_outputs_refuse_regular_files_and_links_without_changing_targets(self):
        self.complete_review()
        self.assertEqual(self.cli("apply-graph-review", "--review", self.review, "--collection", self.collection)[0], 0)
        outside = self.root / "outside.txt"
        outside.write_text("unchanged", encoding="utf-8")
        operations = [
            (self.root / "other" / "review.json", ("prepare-graph-review", "--output")),
            (self.root / "other-collection" / "accepted.json", None),
            (self.graph, ("compile-graph", "--collection", self.collection, "--output")),
        ]
        for target, prefix in operations:
            target.parent.mkdir(parents=True, exist_ok=True)
            for kind in ("regular", "dangling", "external"):
                with self.subTest(target=target.name, kind=kind):
                    if kind == "regular":
                        target.write_text("existing", encoding="utf-8")
                    else:
                        try:
                            target.symlink_to(outside if kind == "external" else self.root / "absent")
                        except OSError:
                            if __import__("os").name == "nt":
                                continue  # Native writer tests own Windows reparse-point coverage.
                            raise
                    args = (*prefix, target) if prefix else ("apply-graph-review", "--review", self.review, "--collection", target.parent)
                    code, output = self.cli(*args)
                    self.assertEqual(code, 1, output)
                    self.assertEqual(outside.read_text(encoding="utf-8"), "unchanged")
                    if kind == "regular":
                        self.assertEqual(target.read_text(encoding="utf-8"), "existing")
                    else:
                        self.assertTrue(target.is_symlink())
                    target.unlink()

    def test_observed_extraction_and_occurrence_locations_match_replay(self):
        from learning_project.lab06 import DEFAULT_INPUT
        source = self.read(DEFAULT_INPUT)
        observation = self.read(DEFAULT_INPUT.with_name("extraction-observation.json"))
        self.assertEqual(json.loads(observation["raw_response"]), observation["outcome"])
        self.assertEqual(observation["request"]["fragments"], source["fragments"])
        mentions = {m["id"]: m for m in source["mentions"]}
        fragments = {f["id"]: f for f in source["fragments"]}
        for mention in mentions.values():
            self.assertEqual(fragments[mention["fragment_id"]]["text"][mention["start"]:mention["end"]], mention["text"])
        for p, result in zip(source["proposals"][:2], observation["outcome"]["relations"], strict=True):
            self.assertEqual(mentions[p["from_mention"]]["proposed_concept_id"], result["dependent_concept_id"])
            self.assertEqual(mentions[p["to_mention"]]["proposed_concept_id"], result["prerequisite_concept_id"])
            self.assertEqual(p["support_fragment_ids"], [result["support_fragment_id"]])
            self.assertEqual(p["qualification"], result["qualification"])

    def test_prepare_has_no_preaccepted_judgments(self):
        code, output = self.cli("prepare-graph-review", "--output", self.review)
        self.assertEqual(code, 0, output)
        review = self.read(self.review)
        self.assertEqual(review["reviewer"], "")
        self.assertIs(review["authorize"], False)
        self.assertTrue(all(x["outcome"] == "pending" for x in review["mention_reviews"].values()))
        self.assertTrue(all(x["decision"] == "pending" for x in review["relation_reviews"].values()))
        self.assertEqual(len(review["reviewed_input"]["concepts"]), 3)
        self.assertEqual(review["proposal_structure"], {"P-1": "conforms", "P-2": "conforms", "P-3": "conforms", "P-4": "unresolved endpoint"})
        self.assertFalse(self.collection.exists())


if __name__ == "__main__":
    unittest.main()
