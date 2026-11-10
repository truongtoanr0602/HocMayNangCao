"""Point saved dev runs at relabelled questions without re-encoding anything.

A run's rankings depend only on the question text, never on the labels. After pooling
review only label fields change (``evidence_groups``, ``label_version``, ``review_status``),
so a run made for the old question file stays valid: this tool checks that nothing else
changed, that the run really was made for the old file, then records the new hash and
recomputes the stored metrics. Test runs are refused: test labels are frozen before scoring.

    python -m legal_kg.relabel_runs --old <old dev.jsonl> [--questions evaluation/dev.jsonl]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .models import fingerprint
from .retrieval_eval import discover_runs, evaluate, load_run, per_question_values, read_jsonl, write_json

LABEL_FIELDS = frozenset({"evidence_groups", "label_version", "review_status"})


def check_label_only_change(old: list[dict], new: list[dict]) -> None:
    if [q["question_id"] for q in old] != [q["question_id"] for q in new]:
        raise ValueError("Question IDs or their order differ; re-run the benchmark instead")
    if {q.get("split") for q in old + new} != {"dev"}:
        raise ValueError("Only dev runs can be relabelled")
    for a, b in zip(old, new):
        changed = {k for k in set(a) | set(b) if a.get(k) != b.get(k)} - LABEL_FIELDS
        if changed:
            raise ValueError(f"{a['question_id']}: non-label fields changed: {sorted(changed)}")


def relabel_run(path: Path, old: list[dict], new: list[dict]) -> str:
    """Returns 'relabelled', 'current' (already on the new hash) or raises."""
    old_hash, new_hash = fingerprint(old), fingerprint(new)
    meta_path = next((path / n for n in ("run.json", "results.json") if (path / n).exists()), None)
    if meta_path is None:
        raise ValueError(f"{path}: no run.json/results.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("question_set_hash") == new_hash:
        return "current"
    if meta.get("question_set_hash") != old_hash:
        raise ValueError(f"{path}: run was not made for the old question file")
    rankings = load_run(path)["rankings"]
    if set(rankings) != {q["question_id"] for q in new}:
        raise ValueError(f"{path}: run does not cover exactly the question set")
    meta["question_set_hash"] = new_hash
    meta.setdefault("relabelled_from", []).append(old_hash)
    if "metrics" in meta:
        metrics = evaluate(new, rankings)
        metrics["by_type"] = {kind: evaluate([q for q in new if q["type"] == kind], rankings)
                              for kind in sorted({q["type"] for q in new if q["answerable"]})}
        meta["metrics"] = metrics
    if "per_question_group_recall_at_5" in meta:
        meta["per_question_group_recall_at_5"] = per_question_values(new, rankings)
    write_json(meta_path, meta)
    return "relabelled"


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--old", type=Path, required=True, help="Question file the runs were made for")
    parser.add_argument("--questions", type=Path, default=Path("evaluation/dev.jsonl"))
    parser.add_argument("--base", type=Path, default=Path("output/kg/embedding_benchmark"))
    parser.add_argument("--runs", type=Path, nargs="*", help="Default: every dev run below --base")
    args = parser.parse_args(argv)
    old, new = read_jsonl(args.old), read_jsonl(args.questions)
    check_label_only_change(old, new)
    paths = args.runs or [p for p in discover_runs(args.base)
                          if not {"pool", "test"} & set(p.relative_to(args.base).parts)]
    status = {str(p): relabel_run(p, old, new) for p in paths}
    print(json.dumps({"old_hash": fingerprint(old), "new_hash": fingerprint(new), "runs": status},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
