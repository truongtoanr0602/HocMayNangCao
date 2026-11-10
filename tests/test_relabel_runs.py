import json

import pytest

from legal_kg.models import fingerprint
from legal_kg.relabel_runs import check_label_only_change, relabel_run


def questions(acceptable):
    return [{"question_id": "q1", "split": "dev", "type": "natural", "question": "Nghỉ mấy ngày?",
             "answerable": True, "label_version": "v1",
             "evidence_groups": [{"primary_node_id": "gold", "acceptable_node_ids": acceptable}]}]


def write_run(path, meta, name="results.json"):
    path.mkdir()
    (path / "predictions.json").write_text(json.dumps([{"question_id": "q1", "top_nodes": [
        {"node_id": "other", "score": 0.9}, {"node_id": "gold", "score": 0.8}]}]), encoding="utf-8")
    (path / name).write_text(json.dumps(meta), encoding="utf-8")


def test_relabel_recomputes_metrics_and_records_the_old_hash(tmp_path):
    old, new = questions(["gold"]), questions(["gold", "other"])
    new[0]["label_version"] = "v2"
    check_label_only_change(old, new)
    run = tmp_path / "run"
    write_run(run, {"question_set_hash": fingerprint(old), "metrics": {}, "per_question_group_recall_at_5": {}})
    assert relabel_run(run, old, new) == "relabelled"
    meta = json.loads((run / "results.json").read_text(encoding="utf-8"))
    assert meta["question_set_hash"] == fingerprint(new) and meta["relabelled_from"] == [fingerprint(old)]
    assert meta["metrics"]["by_k"]["1"]["group_recall_macro"] == 1.0  # "other" now counts at rank 1
    assert relabel_run(run, old, new) == "current"


def test_relabel_refuses_text_changes_foreign_runs_and_test_split(tmp_path):
    old = questions(["gold"])
    changed = questions(["gold"])
    changed[0]["question"] = "Câu khác?"
    with pytest.raises(ValueError, match="non-label"):
        check_label_only_change(old, changed)
    test = questions(["gold"])
    test[0]["split"] = "test"
    with pytest.raises(ValueError, match="dev"):
        check_label_only_change(test, test)
    run = tmp_path / "run"
    write_run(run, {"question_set_hash": "something-else"}, "run.json")
    with pytest.raises(ValueError, match="old question file"):
        relabel_run(run, old, questions(["gold", "other"]))
