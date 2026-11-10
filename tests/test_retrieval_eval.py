import json

import pytest

from legal_kg.models import fingerprint
from legal_kg.retrieval_eval import (apply_threshold, check_run, choose_threshold, compare, evaluate,
                                     load_run, paired_bootstrap, question_scores, render_markdown)


def question(qid, groups, answerable=True, kind="natural"):
    return {"question_id": qid, "question": f"Câu {qid}?", "type": kind, "split": "dev",
            "answerable": answerable,
            "evidence_groups": [{"primary_node_id": g[0], "acceptable_node_ids": list(g)} for g in groups]}


QUESTIONS = [question("one", [("a", "parent")]), question("two", [("b",), ("c",)], kind="multi"),
             question("none", [], answerable=False, kind="unanswerable")]


def test_question_scores_separate_primary_ancestor_and_all_groups():
    scores = question_scores(QUESTIONS[0], ["parent", "a"], ks=(1, 2))
    assert scores["by_k"]["1"] == {"group_recall": 1.0, "primary_recall": 0.0, "all_groups": 1.0}
    assert scores["reciprocal_rank"] == 1.0
    multi = question_scores(QUESTIONS[1], ["b", "x", "c"], ks=(1, 3))
    assert multi["by_k"]["1"]["group_recall"] == .5 and multi["by_k"]["1"]["all_groups"] == 0
    assert multi["by_k"]["3"]["all_groups"] == 1 and multi["reciprocal_rank"] is None


def test_evaluate_ignores_unanswerable_and_rejects_empty_answerable_set():
    result = evaluate(QUESTIONS, {"one": ["a"], "two": ["b", "c"], "none": ["a"]}, ks=(1, 2))
    assert result["answerable_questions"] == 2 and result["unanswerable_questions"] == 1
    assert result["by_k"]["2"]["all_groups_hit_rate"] == 1
    with pytest.raises(ValueError):
        evaluate([QUESTIONS[2]], {"none": []})


def test_paired_bootstrap_is_deterministic_and_brackets_the_mean():
    first = {str(i): float(i % 2) for i in range(20)}
    second = {str(i): 0.0 for i in range(20)}
    result = paired_bootstrap(first, second, samples=2000, seed=7)
    assert result == paired_bootstrap(first, second, samples=2000, seed=7)
    assert result["mean_difference"] == .5
    assert 0 < result["ci_low"] < .5 < result["ci_high"] < 1
    same = paired_bootstrap(first, first, samples=100)
    assert same["ci_low"] == same["ci_high"] == 0
    with pytest.raises(ValueError):
        paired_bootstrap(first, {"0": 1.0})


def test_threshold_maximises_correct_refusals_within_false_refusal_limit():
    entries = [(.9, True)] * 9 + [(.5, True), (.4, False), (.6, False)]
    chosen = choose_threshold(entries, max_false_refusal=.10)
    # .9 refuses only the .5 answerable question (10%, allowed) and both negatives.
    assert chosen["threshold"] == .9
    assert chosen["false_refusal_rate"] == .1 and chosen["correct_refusal_rate"] == 1
    # A stricter limit keeps the largest threshold with no false refusal.
    strict = choose_threshold(entries, max_false_refusal=0)
    assert strict["threshold"] == .5 and strict["correct_refusal_rate"] == .5
    assert apply_threshold(entries, .6)["false_refusal_rate"] == .1
    assert apply_threshold(entries, None)["false_refusal_rate"] == 0


def test_threshold_falls_back_to_never_refusing_when_constraint_cannot_hold():
    entries = [(.3, True), (.9, True), (.8, False)]
    chosen = choose_threshold(entries, max_false_refusal=0)
    assert chosen["threshold"] is None and chosen["correct_refusal_rate"] == 0


def write_run(path, name, rankings, questions=QUESTIONS):
    path.mkdir()
    predictions = [{"question_id": qid, "top_nodes": [{"node_id": n, "score": 1 - i / 10}
                                                      for i, n in enumerate(nodes)]}
                   for qid, nodes in rankings.items()]
    (path / "predictions.json").write_text(json.dumps(predictions), encoding="utf-8")
    (path / "run.json").write_text(json.dumps({"name": name, "question_set_hash": fingerprint(questions)}),
                                   encoding="utf-8")
    return load_run(path)


def test_compare_reports_runs_pairs_and_markdown(tmp_path):
    good = write_run(tmp_path / "good", "good", {"one": ["a"], "two": ["b", "c"], "none": ["z"]})
    weak = write_run(tmp_path / "weak", "weak", {"one": ["z"], "two": ["b"], "none": ["a"]})
    report = compare(QUESTIONS, [good, weak])
    assert report["runs"]["good"]["per_question"] == {"one": 1.0, "two": 1.0}
    assert report["pairwise"][0]["mean_difference"] == .75
    text = render_markdown(report, QUESTIONS, "Thử")
    assert "| good |" in text and "paired bootstrap" in text and "pooling" not in text
    pooled = [dict(q, evidence_groups=[dict(g, pooled_additions=[{"node_id": "x", "label_source": "draft_confirmed"}])
                                       for g in q["evidence_groups"]]) for q in QUESTIONS]
    assert "0 do người duyệt tự quyết, 3 do người xác nhận nháp Claude" in render_markdown(report, pooled, "Thử")


def test_check_run_rejects_other_question_sets(tmp_path):
    run = write_run(tmp_path / "r", "r", {"one": ["a"]})
    with pytest.raises(ValueError, match="exactly"):
        check_run(run, QUESTIONS)
    run = write_run(tmp_path / "s", "s", {q["question_id"]: ["a"] for q in QUESTIONS}, questions=QUESTIONS[:1])
    with pytest.raises(ValueError, match="different question set"):
        check_run(run, QUESTIONS)
