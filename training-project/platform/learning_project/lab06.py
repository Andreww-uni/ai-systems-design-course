"""Reviewed graph preparation; commands never infer semantic acceptance."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .lab04 import _write_new_output
from .workflow import WorkflowError

DEFAULT_INPUT = Path(__file__).resolve().parents[2] / "cases" / "lab06" / "graph-preparation.json"


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkflowError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkflowError(f"Expected a JSON object at {path}.")
    return data


def _write(path: Path, data: dict) -> Path:
    if os.path.lexists(path):
        raise WorkflowError(f"Output already exists at {path}.")
    _write_new_output(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return path


def _proposal_structure(source: dict) -> dict:
    concepts = {c["id"]: c for c in source["concepts"]}
    fragments = {f["id"]: f for f in source["fragments"]}
    mentions = {m["id"]: m for m in source["mentions"]}
    result = {}
    for p in source["proposals"]:
        endpoints = [mentions.get(p.get(key)) for key in ("from_mention", "to_mention")]
        supports = p.get("support_fragment_ids")
        valid_support = isinstance(supports, list) and bool(supports) and all(
            isinstance(fid, str) and fid in fragments and
            all(isinstance(fragments[fid].get("provenance", {}).get(k), str) and fragments[fid]["provenance"][k].strip()
                for k in ("source_id", "version", "location")) for fid in supports)
        valid_mentions = all(m and m["fragment_id"] in fragments and
                             fragments[m["fragment_id"]]["text"][m["start"]:m["end"]] == m["text"] for m in endpoints)
        if p.get("type") != "requires" or not valid_support or not valid_mentions:
            raise WorkflowError(f"{p['id']} fails the graph schema or source-location rules.")
        resolved_endpoints = [m for m in endpoints if m is not None]
        if any(m["proposed_concept_id"] is None for m in resolved_endpoints):
            result[p["id"]] = "unresolved endpoint"
        elif all(m["proposed_concept_id"] in concepts and concepts[m["proposed_concept_id"]]["type"] == "Concept" for m in resolved_endpoints):
            result[p["id"]] = "conforms"
        else:
            raise WorkflowError(f"{p['id']} endpoint must reference an accepted concept, not a source fragment.")
    return result


def _accepted(review: dict) -> dict:
    source = _read(DEFAULT_INPUT)
    if review.get("reviewed_input") != source:
        raise WorkflowError("Reviewed input differs from the supplied proposals; inspect the exact input again.")
    if review.get("authorize") is not True or not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        raise WorkflowError("An identified human reviewer must explicitly authorize the exact reviewed changes.")
    if review.get("proposal_structure") != _proposal_structure(source):
        raise WorkflowError("Structural evidence differs from the supplied proposals.")
    concepts = {c["id"] for c in source["concepts"]}
    for field, items in [("mention_reviews", source["mentions"]), ("relation_reviews", source["proposals"])]:
        decisions = review.get(field)
        if not isinstance(decisions, dict) or set(decisions) != {x["id"] for x in items}:
            raise WorkflowError(f"Complete exactly the supplied {field} entries.")
        for key, value in decisions.items():
            if not isinstance(value, dict) or not isinstance(value.get("rationale"), str) or not value["rationale"].strip():
                raise WorkflowError(f"{key} needs an explicit human rationale.")
    associations = []
    for m in source["mentions"]:
        resolution = review["mention_reviews"][m["id"]]
        if set(resolution) != {"outcome", "concept_id", "rationale"}:
            raise WorkflowError(f"{m['id']} has invalid resolution fields.")
        outcome, cid = resolution.get("outcome"), resolution.get("concept_id")
        if outcome not in ("match", "unresolved") or (outcome == "match" and (not isinstance(cid, str) or cid not in concepts)) or (outcome == "unresolved" and cid is not None):
            raise WorkflowError(f"{m['id']} needs a match to an accepted concept or an unresolved outcome.")
        if resolution["outcome"] == "match":
            associations.append({"mention_id": m["id"], "fragment_id": m["fragment_id"],
                                 "concept_id": resolution["concept_id"], "start": m["start"], "end": m["end"]})
    matches = {a["mention_id"]: a["concept_id"] for a in associations}
    relations = []
    for p in source["proposals"]:
        decision = review["relation_reviews"][p["id"]]
        resolved = p["from_mention"] in matches and p["to_mention"] in matches
        if set(decision) != {"decision", "rationale"} or decision.get("decision") not in (("accept", "reject") if resolved else ("blocked",)):
            raise WorkflowError(f"{p['id']} needs accept/reject for resolved endpoints or blocked for an unresolved endpoint.")
        if decision["decision"] == "accept":
            relations.append({"id": p["relation_id"], "type": p["type"],
                              "from": matches[p["from_mention"]], "to": matches[p["to_mention"]],
                              "support_fragment_ids": p["support_fragment_ids"],
                              "qualification": p["qualification"]})
    return {"collection_version": source["collection_version"], "review": review,
            "concepts": source["concepts"], "fragments": source["fragments"],
            "mention_associations": associations, "relations": relations}


def apply_graph_review(*, review_path: Path, collection: Path) -> Path:
    return _write(collection / "accepted.json", _accepted(_read(review_path)))


def _compiled(collection: Path) -> dict:
    accepted = _read(collection / "accepted.json")
    if not isinstance(accepted.get("review"), dict) or accepted != _accepted(accepted["review"]):
        raise WorkflowError("Accepted collection differs from the exact authorized review.")
    return {"collection_version": accepted["collection_version"],
            "nodes": accepted["concepts"],
            "edges": [{"relation_record_id": r["id"], **{k: v for k, v in r.items() if k != "id"}}
                      for r in accepted["relations"]],
            "fragments": accepted["fragments"], "mention_associations": accepted["mention_associations"]}


def compile_graph(*, collection: Path, output: Path) -> Path:
    return _write(output, _compiled(collection))


def verify_graph(*, collection: Path, graph_path: Path) -> dict:
    expected = _compiled(collection)
    if _read(graph_path) != expected:
        raise WorkflowError("Compiled graph differs from the accepted collection.")
    return {"nodes": len(expected["nodes"]), "edges": len(expected["edges"])}


def _query_graph(collection: Path, graph_path: Path) -> dict:
    graph = _read(graph_path)
    if graph != _compiled(collection):
        raise WorkflowError("Compiled graph differs from the accepted collection.")
    return graph


def _bounded_paths(graph: dict, start: str, max_edges: int) -> list[dict]:
    if type(max_edges) is not int or max_edges not in (1, 2):
        raise WorkflowError("Maximum path length must be one or two edges for the teaching route.")
    paths = []

    def visit(ids: list[str], edges: list[dict]) -> None:
        # At the limit, do not inspect the frontier's possible continuation.
        eligible = None if len(edges) == max_edges else [
            e for e in graph["edges"] if e["from"] == ids[-1] and e["type"] == "requires" and e["to"] not in ids]
        if edges:
            paths.append({"concept_ids": ids,
                          "relation_record_ids": [e["relation_record_id"] for e in edges],
                          "support_fragment_ids": [e["support_fragment_ids"] for e in edges],
                          "qualifications": [e["qualification"] for e in edges],
                          "extension_status": "depth limit: continuation not inspected" if eligible is None
                                              else "extended" if eligible else "no eligible outgoing requires edge"})
        for edge in eligible or []:
            visit([*ids, edge["to"]], [*edges, edge])

    visit([start], [])
    return sorted(paths, key=lambda p: (len(p["relation_record_ids"]), p["concept_ids"], p["relation_record_ids"]))


def query_paths(*, collection: Path, graph_path: Path, start: str, max_edges: int, output: Path) -> Path:
    graph = _query_graph(collection, graph_path)
    paths = _bounded_paths(graph, start, max_edges)
    return _write(output, {"collection_version": graph["collection_version"],
                  "request": {"start": start, "relation_type": "requires", "direction": "outgoing",
                              "max_edges": max_edges, "cycle_policy": "no repeated node within a path"},
                  "start_status": "present" if any(n["id"] == start for n in graph["nodes"]) else "absent",
                  "paths": paths})


def inspect_direct_edge(*, collection: Path, graph_path: Path, start: str, target: str, output: Path) -> Path:
    graph = _query_graph(collection, graph_path)
    nodes = {n["id"] for n in graph["nodes"]}
    outgoing = sorted([e for e in graph["edges"] if e["from"] == start and e["type"] == "requires"],
                      key=lambda e: (e["to"], e["relation_record_id"]))
    matches = [e for e in outgoing if e["to"] == target]
    return _write(output, {"collection_version": graph["collection_version"],
                  "request": {"start": start, "target": target, "relation_type": "requires", "direction": "outgoing"},
                  "start_status": "present" if start in nodes else "absent",
                  "target_status": "present" if target in nodes else "absent",
                  "outgoing_edges": outgoing, "matching_edges": matches, "direct_edge_present": bool(matches)})


def prepare_graph_review(*, output: Path) -> Path:
    source = _read(DEFAULT_INPUT)
    return _write(output, {
        "reviewed_input": source,
        "proposal_structure": _proposal_structure(source),
        "reviewer": "",
        "authorize": False,
        "mention_reviews": {m["id"]: {"outcome": "pending", "concept_id": None, "rationale": ""}
                            for m in source["mentions"]},
        "relation_reviews": {p["id"]: {"decision": "pending", "rationale": ""}
                             for p in source["proposals"]},
    })
