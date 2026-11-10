import importlib.util
import json
from pathlib import Path

import pytest

from legal_kg.models import fingerprint

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "evaluation" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_questions = load("build_questions")
pool_candidates = load("pool_candidates")

NODES = {"n1": {"label": "Clause", "body_text": "1. Người lao động được nghỉ 05 ngày."},
         "n2": {"label": "Point", "body_text": "a) Nội dung khác."},
         "gold": {"label": "Clause", "body_text": "Nhãn gốc."}}


def questions():
    return [{"question_id": "q1", "split": "dev", "type": "natural", "question": "Nghỉ mấy ngày?",
             "answerable": True, "evidence_groups": [{"primary_node_id": "gold", "acceptable_node_ids": ["gold"]}]},
            {"question_id": "q2", "split": "test", "type": "unanswerable", "question": "Thời tiết?",
             "answerable": False, "evidence_groups": []}]


def test_pool_rows_exclude_labelled_nodes_hide_models_and_keep_decisions():
    pools = [{"nodes": {"q1": ["gold", "n1"], "q2": ["n2"]}}, {"nodes": {"q1": ["n2", "n1"]}}]
    existing = {("q1", "n1"): {"decision": "relevant", "group_index": 0, "evidence_quote": "nghỉ 05 ngày"}}
    rows = pool_candidates.collect(questions(), pools, NODES, existing)
    assert {(r["question_id"], r["node_id"]) for r in rows} == {("q1", "n1"), ("q1", "n2"), ("q2", "n2")}
    assert all("model" not in r and "score" not in r for r in rows)
    kept = next(r for r in rows if r["node_id"] == "n1")
    assert kept["decision"] == "relevant" and kept["group_index"] == 0
    assert rows == pool_candidates.collect(questions(), pools, NODES, existing)  # deterministic order


def test_reviewed_pool_adds_verbatim_evidence_and_promotes_labels_to_v2():
    qs = questions()
    rows = [{"question_id": "q1", "node_id": "n1", "decision": "relevant", "group_index": 0,
             "evidence_quote": "nghỉ 05 ngày"},
            {"question_id": "q1", "node_id": "n2", "decision": "not_relevant"}]
    assert build_questions.apply_pooling(qs, NODES, rows) == ("v2", 0)
    group = qs[0]["evidence_groups"][0]
    assert group["acceptable_node_ids"] == ["gold", "n1"]
    assert group["pooled_additions"] == [{"node_id": "n1", "evidence_quote": "nghỉ 05 ngày"}]
    assert build_questions.apply_pooling(questions(), NODES, rows + [
        {"question_id": "q1", "node_id": "x", "decision": None}]) == ("v1", 1)


@pytest.mark.parametrize("row,message", [
    ({"question_id": "q1", "node_id": "n1", "decision": "relevant", "group_index": 0,
      "evidence_quote": "không có trong node"}, "verbatim"),
    ({"question_id": "q1", "node_id": "n1", "decision": "relevant", "group_index": 3,
      "evidence_quote": "nghỉ 05 ngày"}, "group_index"),
    ({"question_id": "q2", "node_id": "n2", "decision": "relevant", "group_index": 0,
      "evidence_quote": "Nội dung"}, "unanswerable"),
    ({"question_id": "q1", "node_id": "n1", "decision": "maybe"}, "Unknown"),
])
def test_invalid_reviews_are_rejected(row, message):
    with pytest.raises(ValueError, match=message):
        build_questions.apply_pooling(questions(), NODES, [row])


def test_test_split_requires_matching_frozen_config(tmp_path):
    pytest.importorskip("numpy")
    from legal_kg.embedding_benchmark import check_frozen, record_test_run
    test_questions = [q for q in questions() if q["split"] == "test"]
    with pytest.raises(ValueError, match="frozen-config"):
        check_frozen(None, test_questions, "e5-small")
    frozen = tmp_path / "frozen.json"
    frozen.write_text(json.dumps({"test_question_hash": fingerprint(test_questions), "models": ["e5-small"]}))
    assert check_frozen(frozen, test_questions, "e5-small")["models"] == ["e5-small"]
    with pytest.raises(ValueError, match="not part"):
        check_frozen(frozen, test_questions, "bge-m3")
    with pytest.raises(ValueError, match="differ"):
        check_frozen(frozen, questions(), "e5-small")
    assert [record_test_run(tmp_path, "e5-small") for _ in range(2)] == [1, 2]
