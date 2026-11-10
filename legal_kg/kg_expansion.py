"""Pipeline P2: expand dense node seeds along the KG under a fixed context budget.

Seeds are the top dense nodes. Each seed adds its parent Article and the Article/Clause/
Point nodes one hop away over REFERS_TO/GUIDES/DETAILS in either direction. P1 (dense
only) and P2 are cut by the same budget (node count and body_text characters), so P2
cannot win just by returning more context. Optionally a DirectRouter result is put first.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

from .models import SEMANTIC_EDGES, GraphPayload, fingerprint
from .retrieval_eval import read_jsonl, write_json
from .router import DirectRouter

UNIT_LABELS = {"Article", "Clause", "Point"}
DEFAULTS = {"seeds": 5, "decay": 0.9, "max_nodes": 10, "max_chars": 12_000}


class Neighbourhood:
    """Parent-Article and one-hop semantic neighbours among Article/Clause/Point nodes."""

    def __init__(self, graph: GraphPayload):
        graph.validate()
        self.labels = {n.id: n.label for n in graph.nodes}
        self.parent = {}
        self.related = defaultdict(set)
        for edge in graph.edges:
            if edge.type == "CONTAINS":
                self.parent[edge.target] = edge.source
            elif edge.type in SEMANTIC_EDGES and {self.labels[edge.source], self.labels[edge.target]} <= UNIT_LABELS:
                self.related[edge.source].add(edge.target)
                self.related[edge.target].add(edge.source)

    def article(self, node: str) -> str | None:
        current = self.parent.get(node)
        while current is not None and self.labels[current] != "Article":
            current = self.parent.get(current)
        return current

    def expansions(self, node: str) -> list[str]:
        """Parent Article first, then semantic neighbours in stable ID order."""
        found = [] if self.labels[node] == "Article" else [a for a in [self.article(node)] if a]
        return found + sorted(self.related[node])


def apply_budget(ranked: list[tuple[str, float]], chars: dict[str, int], *,
                 max_nodes: int, max_chars: int) -> list[tuple[str, float]]:
    """Keep ranked nodes in order while both limits hold; a node that does not fit is skipped."""
    kept, used, seen = [], 0, set()
    for node, score in ranked:
        if node in seen:
            continue
        seen.add(node)
        if used + chars[node] > max_chars:
            continue
        kept.append((node, score))
        used += chars[node]
        if len(kept) == max_nodes:
            break
    return kept


def expand(dense: list[tuple[str, float]], neighbourhood: Neighbourhood, *, seeds: int, decay: float,
           candidates: set[str]) -> list[tuple[str, float]]:
    """Seeds, then their expansions (seed score × decay, seed order on ties), then remaining dense."""
    head = dense[:seeds]
    seen = {node for node, _ in head}
    added = []
    for order, (seed, score) in enumerate(head):
        for node in neighbourhood.expansions(seed):
            if node in candidates and node not in seen:
                seen.add(node)
                added.append((score * decay, order, node))
    added.sort(key=lambda item: (-item[0], item[1]))
    tail = [(node, score) for node, score in dense[seeds:] if node not in seen]
    return head + [(node, score) for score, _, node in added] + tail


def _write_run(path: Path, name: str, predictions: list[dict], meta: dict) -> None:
    write_json(path / "predictions.json", predictions)
    write_json(path / "run.json", {"name": name, **meta})


def run(args) -> dict:
    graph = GraphPayload.from_dict(json.loads(args.graph.read_text(encoding="utf-8")))
    records = read_jsonl(args.corpus)
    chars = {r["node_id"]: len(r["body_text"]) for r in records}
    if {(r["snapshot_id"], r["graph_hash"]) for r in records} != {(graph.source_hash, graph.graph_hash)}:
        raise ValueError("Node texts and graph come from different snapshots")
    base = json.loads((args.run / "results.json").read_text(encoding="utf-8"))
    questions = {q["question_id"]: q for q in read_jsonl(args.questions)}
    if fingerprint(list(questions.values())) != base["question_set_hash"]:
        raise ValueError("Dense run was produced for a different question set")
    dense_predictions = json.loads((args.run / "predictions.json").read_text(encoding="utf-8"))
    neighbourhood = Neighbourhood(graph)
    router = DirectRouter(graph)
    budget = {"max_nodes": args.max_nodes, "max_chars": args.max_chars}
    meta = {"question_set_hash": base["question_set_hash"], "dense_run": base["model"],
            "snapshot_id": graph.source_hash, "graph_hash": graph.graph_hash,
            "parameters": {"seeds": args.seeds, "decay": args.decay, **budget}}
    outputs = {"p1-budget": [], "p2": [], "router-p2": []}
    routed = {}
    for prediction in dense_predictions:
        dense = [(n["node_id"], n["score"]) for n in prediction["top_nodes"]]
        if len(dense) < args.max_nodes:
            raise ValueError("Dense ranking is shallower than the node budget")
        p2 = expand(dense, neighbourhood, seeds=args.seeds, decay=args.decay, candidates=set(chars))
        direct = [n for n in router.route(questions[prediction["question_id"]]["question"]) if n in chars]
        routed[prediction["question_id"]] = direct
        # Routed nodes lead with the top dense score so abstention still uses the dense signal.
        top = dense[0][1]
        ranked = {"p1-budget": dense, "p2": p2, "router-p2": [(n, top) for n in direct] + p2}
        for name, items in ranked.items():
            kept = apply_budget(items, chars, **budget)
            outputs[name].append({"question_id": prediction["question_id"],
                                  "top_nodes": [{"node_id": n, "score": s} for n, s in kept],
                                  "context_chars": sum(chars[n] for n, _ in kept)})
    for name, predictions in outputs.items():
        _write_run(args.run / name, f"{base['model']}/{name}", predictions, meta)
    direct = [q for q in questions.values() if q["type"] == "direct"]
    exact = sum(routed[q["question_id"]] == [g["primary_node_id"] for g in q["evidence_groups"]] for q in direct)
    false_routes = sum(bool(routed[q["question_id"]]) for q in questions.values() if q["type"] != "direct")
    report = {"router": {"direct_questions": len(direct), "exact_primary_routes": exact,
                         "routed_non_direct": false_routes, "routes": routed}, **meta}
    write_json(args.run / "expansion_report.json", report)
    return report


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True, help="Dense run directory with results/predictions.json")
    parser.add_argument("--graph", type=Path, default=Path("output/kg/structural_graph.json"))
    parser.add_argument("--corpus", type=Path, default=Path("output/kg/embedding_text/node_texts.jsonl"))
    parser.add_argument("--questions", type=Path, default=Path("evaluation/dev.jsonl"))
    parser.add_argument("--seeds", type=int, default=DEFAULTS["seeds"])
    parser.add_argument("--decay", type=float, default=DEFAULTS["decay"])
    parser.add_argument("--max-nodes", type=int, default=DEFAULTS["max_nodes"])
    parser.add_argument("--max-chars", type=int, default=DEFAULTS["max_chars"])
    args = parser.parse_args(argv)
    if args.seeds < 1 or args.max_nodes < 1 or args.max_chars < 1 or not 0 < args.decay <= 1:
        parser.error("Invalid budget or decay")
    report = run(args)
    print(json.dumps({k: v for k, v in report["router"].items() if k != "routes"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
