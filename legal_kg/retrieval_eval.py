"""Score saved retrieval runs against evidence-group labels; no model or Neo4j needed.

A *run* is a directory holding ``predictions.json``: one record per question with
``question_id`` and ``top_nodes`` (``[{node_id, score}]`` in rank order). Embedding
benchmarks, KG expansion and the direct router all write this format, so one scorer
covers every pipeline. Metric definitions match the original benchmark exactly.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import sys

from .models import fingerprint

KS = (1, 3, 5, 10)
PRIMARY_METRIC = ("group_recall", 5)
BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 0


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def question_scores(question: dict, ranking: list[str], ks=KS) -> dict:
    """Per-question hits: group recall, primary-node recall, all-groups hit and reciprocal rank."""
    groups = question["evidence_groups"]
    if not groups:
        raise ValueError(f"Answerable question without evidence groups: {question['question_id']}")
    by_k = {}
    for k in ks:
        top = set(ranking[:k])
        hits = [bool(top & set(g["acceptable_node_ids"])) for g in groups]
        by_k[str(k)] = {
            "group_recall": sum(hits) / len(groups),
            "primary_recall": sum(g["primary_node_id"] in top for g in groups) / len(groups),
            "all_groups": float(all(hits)),
        }
    reciprocal = None
    if len(groups) == 1:
        acceptable = set(groups[0]["acceptable_node_ids"])
        reciprocal = next((1 / rank for rank, node in enumerate(ranking[:max(ks)], 1) if node in acceptable), 0.0)
    return {"by_k": by_k, "reciprocal_rank": reciprocal}


def _mean(values):
    return sum(values) / len(values)


def evaluate(questions: list[dict], rankings: dict[str, list[str]], ks=KS) -> dict:
    """Macro-average metrics over answerable questions; unanswerable ones are only counted."""
    answerable = [q for q in questions if q["answerable"]]
    if not answerable:
        raise ValueError("No answerable questions")
    scored = [question_scores(q, rankings[q["question_id"]], ks) for q in answerable]
    output = {"answerable_questions": len(answerable),
              "unanswerable_questions": len(questions) - len(answerable), "by_k": {}}
    for k in ks:
        rows = [s["by_k"][str(k)] for s in scored]
        output["by_k"][str(k)] = {
            "group_recall_macro": _mean([r["group_recall"] for r in rows]),
            "primary_group_recall_macro": _mean([r["primary_recall"] for r in rows]),
            "all_groups_hit_rate": _mean([r["all_groups"] for r in rows]),
        }
    reciprocal = [s["reciprocal_rank"] for s in scored if s["reciprocal_rank"] is not None]
    output["single_group_mrr_at_max_k"] = _mean(reciprocal) if reciprocal else None
    return output


def per_question_values(questions: list[dict], rankings: dict[str, list[str]],
                        metric=PRIMARY_METRIC) -> dict[str, float]:
    name, k = metric
    return {q["question_id"]: question_scores(q, rankings[q["question_id"]], (k,))["by_k"][str(k)][name]
            for q in questions if q["answerable"]}


def _percentile(sorted_values, fraction):
    position = (len(sorted_values) - 1) * fraction
    low, high = math.floor(position), math.ceil(position)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def paired_bootstrap(first: dict[str, float], second: dict[str, float], *,
                     samples: int = BOOTSTRAP_SAMPLES, seed: int = BOOTSTRAP_SEED) -> dict:
    """95% percentile CI of mean(first - second), resampling the same questions for both."""
    if set(first) != set(second) or not first:
        raise ValueError("Paired bootstrap needs the same non-empty question set")
    keys = sorted(first)
    differences = [first[k] - second[k] for k in keys]
    generator = random.Random(seed)
    n = len(differences)
    means = sorted(sum(differences[generator.randrange(n)] for _ in range(n)) / n for _ in range(samples))
    return {"mean_difference": _mean(differences), "ci_low": _percentile(means, 0.025),
            "ci_high": _percentile(means, 0.975), "questions": n, "samples": samples, "seed": seed}


def choose_threshold(entries: list[tuple[float, bool]], max_false_refusal: float = 0.10) -> dict:
    """Pick a top-1 score threshold: refuse when score < threshold.

    Maximise correct refusals on unanswerable questions while refusing at most
    ``max_false_refusal`` of answerable ones. ``threshold=None`` means never refuse;
    it is the fallback when no positive threshold satisfies the constraint.
    """
    positives = [s for s, answerable in entries if answerable]
    negatives = [s for s, answerable in entries if not answerable]
    if not positives:
        raise ValueError("Threshold selection needs answerable questions")
    best = {"threshold": None, "false_refusal_rate": 0.0,
            "correct_refusal_rate": 0.0 if negatives else None}
    for candidate in sorted({s for s, _ in entries}):
        false_rate = sum(s < candidate for s in positives) / len(positives)
        if false_rate > max_false_refusal:
            break
        correct_rate = sum(s < candidate for s in negatives) / len(negatives) if negatives else None
        if negatives and correct_rate > best["correct_refusal_rate"]:
            best = {"threshold": candidate, "false_refusal_rate": false_rate, "correct_refusal_rate": correct_rate}
    best.update({"max_false_refusal": max_false_refusal, "answerable": len(positives),
                 "unanswerable": len(negatives)})
    return best


def apply_threshold(entries: list[tuple[float, bool]], threshold: float | None) -> dict:
    positives = [s for s, answerable in entries if answerable]
    negatives = [s for s, answerable in entries if not answerable]
    refuse = (lambda s: False) if threshold is None else (lambda s: s < threshold)
    return {"threshold": threshold,
            "false_refusal_rate": sum(map(refuse, positives)) / len(positives) if positives else None,
            "correct_refusal_rate": sum(map(refuse, negatives)) / len(negatives) if negatives else None,
            "answerable": len(positives), "unanswerable": len(negatives)}


def load_run(path: Path) -> dict:
    predictions = json.loads((path / "predictions.json").read_text(encoding="utf-8"))
    meta = {}
    for name in ("run.json", "results.json"):
        if (path / name).exists():
            meta = json.loads((path / name).read_text(encoding="utf-8"))
            break
    return {"name": meta.get("name") or meta.get("model") or path.name, "path": str(path), "meta": meta,
            "rankings": {p["question_id"]: [n["node_id"] for n in p["top_nodes"]] for p in predictions},
            "top1": {p["question_id"]: (p["top_nodes"][0]["score"] if p["top_nodes"] else -math.inf)
                     for p in predictions}}


def discover_runs(base: Path) -> list[Path]:
    """Every directory below base that holds predictions.json, in stable order."""
    return sorted(p.parent for p in base.rglob("predictions.json"))


def check_run(run: dict, questions: list[dict]) -> None:
    ids = {q["question_id"] for q in questions}
    if set(run["rankings"]) != ids:
        raise ValueError(f"Run {run['name']} does not cover exactly the question set")
    expected = run["meta"].get("question_set_hash")
    if expected and expected != fingerprint(questions):
        raise ValueError(f"Run {run['name']} was produced for a different question set")


def compare(questions: list[dict], runs: list[dict], *, metric=PRIMARY_METRIC,
            max_false_refusal: float = 0.10, thresholds: dict[str, float | None] | None = None) -> dict:
    """Metrics, per-type and per-flag breakdowns, pairwise bootstrap CIs and abstention per run."""
    for run in runs:
        check_run(run, questions)
    if len({r["name"] for r in runs}) != len(runs):
        raise ValueError("Run names must be unique")
    kinds = sorted({q["type"] for q in questions if q["answerable"]})
    flagged = [q for q in questions if q["answerable"] and q.get("evidence_in_table_or_appendix")]
    report = {"question_set_hash": fingerprint(questions), "question_count": len(questions),
              "splits": sorted({q.get("split") for q in questions}), "primary_metric": list(metric),
              "runs": {}, "pairwise": []}
    values = {}
    for run in runs:
        rankings = run["rankings"]
        entries = [(run["top1"][q["question_id"]], q["answerable"]) for q in questions]
        if thresholds is None:
            abstention = choose_threshold(entries, max_false_refusal)
        else:
            abstention = apply_threshold(entries, thresholds.get(run["name"]))
        values[run["name"]] = per_question_values(questions, rankings, metric)
        report["runs"][run["name"]] = {
            "path": run["path"], "metrics": evaluate(questions, rankings),
            "by_type": {kind: evaluate([q for q in questions if q["type"] == kind], rankings) for kind in kinds},
            "table_or_appendix": evaluate(flagged, rankings) if flagged else None,
            "per_question": values[run["name"]], "abstention": abstention,
            "manifest": ({k: run["meta"]["manifest"].get(k) for k in
                          ("window_count", "multiwindow_nodes", "max_content_tokens", "peak_rss_mb",
                           "peak_gpu_mb", "encode_seconds_this_session")}
                         | {"device": run["meta"]["manifest"].get("config", {}).get("device", "cpu"),
                            "gpu": run["meta"]["manifest"].get("config", {}).get("gpu")})
                        if run["meta"].get("manifest") else None,
        }
    names = [r["name"] for r in runs]
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            report["pairwise"].append({"first": first, "second": second,
                                       **paired_bootstrap(values[first], values[second])})
    return report


def _fmt(value):
    return "—" if value is None else f"{value:.3f}"


def render_markdown(report: dict, questions: list[dict], title: str) -> str:
    name, k = report["primary_metric"]
    lines = [f"# {title}", "",
             f"Bộ câu hỏi: {report['question_count']} câu, split {', '.join(map(str, report['splits']))}, "
             f"hash `{report['question_set_hash'][:12]}`. Sinh tự động bởi `python -m legal_kg.retrieval_eval`.", "",
             "| Cấu hình | Recall nhóm @1 | @3 | @5 | @10 | Node chính @5 | Đủ mọi nhóm @5 | MRR@10 (1 nhóm) |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for run_name, run in report["runs"].items():
        m = run["metrics"]
        lines.append(f"| {run_name} | " + " | ".join(_fmt(m["by_k"][str(x)]["group_recall_macro"]) for x in KS)
                     + f" | {_fmt(m['by_k']['5']['primary_group_recall_macro'])}"
                     f" | {_fmt(m['by_k']['5']['all_groups_hit_rate'])} | {_fmt(m['single_group_mrr_at_max_k'])} |")
    lines += ["", f"## So sánh cặp: {name}@{k}, paired bootstrap CI 95%", "",
              "| A | B | A − B | CI thấp | CI cao | Khác biệt có ý nghĩa |", "|---|---|---:|---:|---:|---|"]
    for pair in report["pairwise"]:
        significant = "có" if pair["ci_low"] > 0 or pair["ci_high"] < 0 else "không"
        lines.append(f"| {pair['first']} | {pair['second']} | {pair['mean_difference']:+.3f} | "
                     f"{pair['ci_low']:+.3f} | {pair['ci_high']:+.3f} | {significant} |")
    lines += ["", "## Theo loại câu hỏi", "",
              "| Cấu hình | Loại | Số câu | Recall nhóm @5 | Node chính @5 | Đủ mọi nhóm @5 |",
              "|---|---|---:|---:|---:|---:|"]
    for run_name, run in report["runs"].items():
        for kind, m in run["by_type"].items():
            row = m["by_k"]["5"]
            lines.append(f"| {run_name} | {kind} | {m['answerable_questions']} | {_fmt(row['group_recall_macro'])} | "
                         f"{_fmt(row['primary_group_recall_macro'])} | {_fmt(row['all_groups_hit_rate'])} |")
    if any(run["table_or_appendix"] for run in report["runs"].values()):
        lines += ["", "## Câu có bằng chứng trong bảng/Phụ lục", "",
                  "| Cấu hình | Số câu | Recall nhóm @5 | Node chính @5 |", "|---|---:|---:|---:|"]
        for run_name, run in report["runs"].items():
            m = run["table_or_appendix"]
            lines.append(f"| {run_name} | {m['answerable_questions']} | {_fmt(m['by_k']['5']['group_recall_macro'])} | "
                         f"{_fmt(m['by_k']['5']['primary_group_recall_macro'])} |")
    lines += ["", "## Từ chối trả lời theo điểm top-1", "",
              "Từ chối khi cosine top-1 < ngưỡng. Ngưỡng chọn trên dev: tối đa hóa từ chối đúng với ràng buộc "
              "từ chối nhầm câu có đáp án ≤ giới hạn; `—` nghĩa là không từ chối.", "",
              "| Cấu hình | Ngưỡng | Từ chối đúng | Từ chối nhầm | Câu có đáp án | Câu không trả lời được |",
              "|---|---:|---:|---:|---:|---:|"]
    for run_name, run in report["runs"].items():
        a = run["abstention"]
        lines.append(f"| {run_name} | {_fmt(a['threshold'])} | {_fmt(a['correct_refusal_rate'])} | "
                     f"{_fmt(a['false_refusal_rate'])} | {a['answerable']} | {a['unanswerable']} |")
    manifests = {n: r["manifest"] for n, r in report["runs"].items() if r["manifest"]}
    if manifests:
        lines += ["", "## Encode", "", "| Model | Thiết bị | Số window | Node nhiều cửa sổ | Token nội dung lớn nhất | "
                  "RAM đỉnh (MB) | GPU đỉnh (MB) | Giây encode (session) |", "|---|---|---:|---:|---:|---:|---:|---:|"]
        for run_name, m in manifests.items():
            device = m["gpu"] or m["device"]
            lines.append(f"| {run_name} | {device} | {m['window_count']} | {m['multiwindow_nodes']} | "
                         f"{m['max_content_tokens']} | "
                         f"{'—' if m['peak_rss_mb'] is None else round(m['peak_rss_mb'])} | "
                         f"{'—' if m['peak_gpu_mb'] is None else round(m['peak_gpu_mb'])} | "
                         f"{'—' if m['encode_seconds_this_session'] is None else round(m['encode_seconds_this_session'])} |")
    by_id = {q["question_id"]: q for q in questions}
    lines += ["", "## Câu chưa lấy đủ bằng chứng ở top 5", ""]
    for run_name, run in report["runs"].items():
        missed = [qid for qid, value in run["per_question"].items() if value < 1]
        lines += [f"### {run_name}", ""] + [
            f"- {qid}: {by_id[qid]['question']}" for qid in missed] + ([""] if missed else ["- (không có)", ""])
    lines += ["## Giao thức", "",
              "- Tìm trên toàn bộ node Điều/Khoản/Điểm; chỉ dùng KG và embedding node, không BM25, không embed chunk.",
              "- Recall nhóm cho phép node tổ tiên nếu chứa nguyên văn bằng chứng; node chính là chỉ số khắt khe hơn.",
              "- Câu không trả lời được không tính vào Recall/MRR; chỉ dùng cho ngưỡng từ chối.",
              "- CI 95% là paired bootstrap trên cùng câu hỏi, 10.000 mẫu, seed cố định.",
              "- Nhãn do nhóm biên soạn và duyệt, chưa phải thẩm định của chuyên gia pháp lý.", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--questions", type=Path, default=Path("evaluation/dev.jsonl"))
    parser.add_argument("--runs", type=Path, nargs="*",
                        help="Run directories; default: every predictions.json below --base")
    parser.add_argument("--base", type=Path, default=Path("output/kg/embedding_benchmark"))
    parser.add_argument("--output", type=Path, default=Path("output/kg/embedding_benchmark/comparison.md"))
    parser.add_argument("--json", type=Path, default=Path("output/kg/embedding_benchmark/comparison.json"))
    parser.add_argument("--title", default="So sánh retrieval node trên development")
    parser.add_argument("--max-false-refusal", type=float, default=0.10)
    parser.add_argument("--frozen-config", type=Path,
                        help="Required for test questions: applies the dev thresholds frozen there")
    args = parser.parse_args(argv)
    questions = read_jsonl(args.questions)
    splits = {q.get("split") for q in questions}
    thresholds = None
    if splits == {"test"}:
        if args.frozen_config is None or not args.frozen_config.exists():
            raise SystemExit("Test scoring needs --frozen-config (thresholds and hashes fixed on dev)")
        frozen = json.loads(args.frozen_config.read_text(encoding="utf-8"))
        if frozen["test_question_hash"] != fingerprint(questions):
            raise SystemExit("Test questions differ from the frozen configuration")
        thresholds = frozen["abstention_thresholds"]
    elif splits != {"dev"}:
        raise SystemExit("Questions must be a single split: dev, or test with --frozen-config")
    paths = args.runs or [p for p in discover_runs(args.base) if p.parent == args.base]
    if not paths:
        raise SystemExit("No runs found")
    report = compare(questions, [load_run(p) for p in paths], max_false_refusal=args.max_false_refusal,
                     thresholds=thresholds)
    write_json(args.json, report)
    write_text(args.output, render_markdown(report, questions, args.title))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
