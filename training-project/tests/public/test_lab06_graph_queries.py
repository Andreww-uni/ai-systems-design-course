"""Bounded read-only queries over the graph accepted in Laboratory 06."""
from __future__ import annotations

import unittest

import test_lab06_graph_preparation as preparation


class GraphQueryTests(unittest.TestCase):
    def setUp(self):
        self.prep = preparation.GraphPreparationTests()
        self.prep.setUp()
        self.addCleanup(self.prep.doCleanups)
        self.prep.complete_review()  # Synthetic test authorization, not a student approval.
        self.cli = self.prep.cli
        self.read = self.prep.read
        self.graph = self.prep.graph
        self.collection = self.prep.collection
        self.root = self.prep.root
        self.assertEqual(self.cli("apply-graph-review", "--review", self.prep.review,
                                  "--collection", self.collection)[0], 0)
        self.assertEqual(self.cli("compile-graph", "--collection", self.collection,
                                  "--output", self.graph)[0], 0)

    def query(self, output, start="C-RET", depth=1):
        return self.cli("query-paths", "--collection", self.collection, "--graph", self.graph,
                        "--start", start, "--max-edges", depth, "--output", output)

    def test_one_edge_query_preserves_support_and_does_not_inspect_continuation(self):
        before = self.graph.read_bytes(), (self.collection / "accepted.json").read_bytes()
        out = self.root / "one-edge.json"
        code, message = self.query(out)
        self.assertEqual(code, 0, message)
        result = self.read(out)
        self.assertEqual(result["collection_version"], self.read(self.graph)["collection_version"])
        self.assertEqual(result["request"], {"start": "C-RET", "relation_type": "requires",
                         "direction": "outgoing", "max_edges": 1,
                         "cycle_policy": "no repeated node within a path"})
        self.assertEqual(result["start_status"], "present")
        self.assertEqual(result["paths"], [{"concept_ids": ["C-RET", "C-QUERY"],
                         "relation_record_ids": ["R-1"], "support_fragment_ids": [["F-1"]],
                         "qualifications": ["In this teaching route"],
                         "extension_status": "depth limit: continuation not inspected"}])
        self.assertEqual(before, (self.graph.read_bytes(), (self.collection / "accepted.json").read_bytes()))

    def test_two_edge_query_returns_prefix_and_full_path_without_inference(self):
        out = self.root / "two-edge.json"
        code, message = self.query(out, depth=2)
        self.assertEqual(code, 0, message)
        paths = self.read(out)["paths"]
        self.assertEqual([p["concept_ids"] for p in paths],
                         [["C-RET", "C-QUERY"], ["C-RET", "C-QUERY", "C-MODEL"]])
        self.assertEqual([p["relation_record_ids"] for p in paths], [["R-1"], ["R-1", "R-2"]])
        self.assertEqual(paths[1]["support_fragment_ids"], [["F-1"], ["F-2"]])
        self.assertEqual(paths[1]["qualifications"], ["In this teaching route"] * 2)
        self.assertEqual(paths[0]["extension_status"], "extended")
        self.assertEqual(paths[1]["extension_status"], "depth limit: continuation not inspected")
        self.assertEqual(len(self.read(self.graph)["edges"]), 2)
        self.assertFalse(any(e["from"] == "C-RET" and e["to"] == "C-MODEL"
                             for e in self.read(self.graph)["edges"]))

    def test_cycles_are_path_local_and_distinct_routes_are_retained(self):
        from learning_project.lab06 import _bounded_paths
        graph = self.read(self.graph)
        template = graph["edges"][0]
        graph["edges"] += [{**template, "relation_record_id": rid, "from": src, "to": dst, "type": kind}
                           for rid, src, dst, kind in [
                               ("synthetic-direct", "C-RET", "C-MODEL", "requires"),
                               ("synthetic-cycle", "C-MODEL", "C-RET", "requires"),
                               ("synthetic-self", "C-RET", "C-RET", "requires"),
                               ("synthetic-other", "C-RET", "C-MODEL", "related")]]
        # Pure policy regression; not an accepted teaching graph or new source claim.
        paths = _bounded_paths(graph, "C-RET", 2)
        self.assertEqual([p["concept_ids"] for p in paths], [
            ["C-RET", "C-MODEL"], ["C-RET", "C-QUERY"], ["C-RET", "C-QUERY", "C-MODEL"]])
        self.assertEqual(paths[0]["extension_status"], "no eligible outgoing requires edge")
        self.assertTrue(all(len(p["concept_ids"]) == len(set(p["concept_ids"])) for p in paths))
        graph["edges"].reverse()
        self.assertEqual(_bounded_paths(graph, "C-RET", 2), paths)

    def direct(self, output, start="C-RET", target="C-MODEL"):
        return self.cli("inspect-direct-edge", "--collection", self.collection, "--graph", self.graph,
                        "--start", start, "--target", target, "--output", output)

    def test_separate_direct_inspection_reports_complete_outgoing_set(self):
        for start, target, expected in [("C-RET", "C-MODEL", False),
                                         ("C-RET", "C-QUERY", True), ("C-MODEL", "C-RET", False)]:
            with self.subTest(start=start, target=target):
                out = self.root / f"direct-{start}-{target}.json"
                code, message = self.direct(out, start, target)
                self.assertEqual(code, 0, message)
                result = self.read(out)
                self.assertEqual(result["start_status"], "present")
                self.assertEqual(result["target_status"], "present")
                self.assertEqual(result["direct_edge_present"], expected)
                edges = [e for e in self.read(self.graph)["edges"] if e["from"] == start]
                self.assertEqual(result["outgoing_edges"], edges)
                self.assertEqual(result["matching_edges"], [e for e in edges if e["to"] == target])
                self.assertEqual(result["request"], {"start": start, "target": target,
                                 "relation_type": "requires", "direction": "outgoing"})

    def test_public_api_rejects_unsupported_depth_before_output(self):
        from learning_project.lab06 import query_paths
        from learning_project.workflow import WorkflowError
        for depth in [0, -1, 3, True, "2", None]:
            with self.subTest(depth=depth):
                out = self.root / f"invalid-depth-{type(depth).__name__}-{depth}.json"
                with self.assertRaises(WorkflowError):
                    query_paths(collection=self.collection, graph_path=self.graph, start="C-RET",
                                max_edges=depth, output=out)
                self.assertFalse(out.exists())

    def test_missing_start_differs_from_existing_leaf(self):
        for start, status in [("C-NOT-PRESENT", "absent"), ("C-MODEL", "present")]:
            out = self.root / f"empty-{start}.json"
            code, message = self.query(out, start=start, depth=2)
            self.assertEqual(code, 0, message)
            self.assertEqual(self.read(out)["start_status"], status)
            self.assertEqual(self.read(out)["paths"], [])
        out = self.root / "missing-target.json"
        self.assertEqual(self.direct(out, target="C-NOT-PRESENT")[0], 0)
        self.assertEqual(self.read(out)["target_status"], "absent")
        self.assertFalse(self.read(out)["direct_edge_present"])

    def test_queries_reject_changed_graph_or_collection_before_output(self):
        graph_bytes = self.graph.read_bytes()
        accepted = self.collection / "accepted.json"
        accepted_bytes = accepted.read_bytes()
        for damaged in [self.graph, accepted]:
            damaged.write_text("{}", encoding="utf-8")
            for name, operation in [("paths", self.query), ("direct", self.direct)]:
                out = self.root / f"bad-{damaged.name}-{name}.json"
                code, message = operation(out)
                self.assertEqual(code, 1, message)
                self.assertFalse(out.exists())
            self.graph.write_bytes(graph_bytes)
            accepted.write_bytes(accepted_bytes)

    def test_query_outputs_refuse_regular_and_symlink_collisions(self):
        outside = self.root / "outside.txt"
        outside.write_text("unchanged", encoding="utf-8")
        before = self.graph.read_bytes(), (self.collection / "accepted.json").read_bytes()
        for operation in [self.query, self.direct]:
            out = self.root / "collision.json"
            for kind in ["regular", "external", "dangling"]:
                with self.subTest(operation=operation.__name__, kind=kind):
                    if kind == "regular":
                        out.write_text("keep", encoding="utf-8")
                    else:
                        try:
                            out.symlink_to(outside if kind == "external" else self.root / "missing")
                        except OSError:
                            if __import__("os").name == "nt":
                                continue  # Existing native protected-writer tests own reparse behavior.
                            raise
                    code, message = operation(out)
                    self.assertEqual(code, 1, message)
                    self.assertEqual(outside.read_text(encoding="utf-8"), "unchanged")
                    if kind == "regular":
                        self.assertEqual(out.read_text(encoding="utf-8"), "keep")
                    else:
                        self.assertTrue(out.is_symlink())
                    out.unlink()
        self.assertEqual(before, (self.graph.read_bytes(), (self.collection / "accepted.json").read_bytes()))


if __name__ == "__main__":
    unittest.main()
