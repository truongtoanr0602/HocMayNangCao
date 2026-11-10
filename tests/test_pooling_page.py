import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "evaluation" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


page = load("build_pooling_page")
importer = load("import_pooling_decisions")

NODES = {
    "doc-01/article-5/clause-1/point-%C4%91": {
        "label": "Point", "body_text": "đ) Nghỉ hằng tuần </script> ít nhất 200%;",
        "embedding_text": "Văn bản: Bộ luật Lao động 2019\nSố hiệu: 45/2019/QH14\nĐịa chỉ: Điều 5 > Khoản 1 > Điểm đ\nNội dung:\n..."},
    "gold": {"label": "Clause", "body_text": "1. Gốc.",
             "embedding_text": "Văn bản: Luật\nĐịa chỉ: Điều 1 > Khoản 1\nNội dung:\n1. Gốc."},
}
QUESTIONS = [
    {"question_id": "q1", "split": "dev", "type": "natural", "question": "Bao nhiêu?", "answer_rubric": "Nêu mức.",
     "answerable": True, "evidence_groups": [{"primary_node_id": "gold", "acceptable_node_ids": ["gold"],
                                              "evidence_quote": "1. Gốc."}]},
    {"question_id": "q2", "split": "test", "type": "unanswerable", "question": "Thời tiết?", "answer_rubric": "Từ chối.",
     "answerable": False, "evidence_groups": []},
]
ROWS = [{"question_id": "q1", "node_id": "doc-01/article-5/clause-1/point-%C4%91", "decision": None},
        {"question_id": "q2", "node_id": "gold", "decision": None}]


@pytest.mark.parametrize("node", ["doc-01/article-5/clause-1/point-%C4%91", "doc-08/chapter-II/article-17/clause-2"])
def test_doc_ids_round_trip_and_use_only_db_path_characters(node):
    value = page.doc_id("q006", node)
    assert page.parse_doc_id(value) == ("q006", node)
    assert all(c.isalnum() or c in "_-.~:@+" for c in value) and "/" not in value


def test_page_data_is_blind_complete_and_safe_to_embed():
    data = page.page_data(QUESTIONS, ROWS, NODES)
    assert set(data) == {"source_hash", "questions", "rows", "nodes"}
    assert all(set(r) == {"q", "n"} for r in data["rows"])
    point = data["nodes"]["doc-01/article-5/clause-1/point-%C4%91"]
    assert point["text"] == NODES["doc-01/article-5/clause-1/point-%C4%91"]["body_text"]  # full text, not cut
    assert point["address"] == "Điều 5 > Khoản 1 > Điểm đ" and point["document"] == "Bộ luật Lao động 2019"
    html = page.render(data, "<p>x</p><script type=\"application/json\">__DATA__</script>")
    assert html.count("</script>") == 1  # the node's own "</script>" is escaped
    embedded = json.loads(html.split('json">', 1)[1].rsplit("</script>", 1)[0])
    assert embedded == data
    for word in ("score", "model", "rank"):
        assert f'"{word}' not in html
    with pytest.raises(ValueError):
        page.page_data(QUESTIONS, ROWS + [{"question_id": "q1", "node_id": "missing"}], NODES)


def test_merge_takes_latest_and_turns_flags_into_pending_rows():
    decisions = [
        {"question_id": "q1", "node_id": ROWS[0]["node_id"], "decision": "not_relevant", "group_index": None,
         "evidence_quote": None, "reviewer_note": None, "updated_at": "2026-11-10T01:00:00Z"},
        {"question_id": "q1", "node_id": ROWS[0]["node_id"], "decision": "relevant", "group_index": 0,
         "evidence_quote": "ít nhất 200%", "reviewer_note": "NĐ nhắc lại", "updated_at": "2026-11-10T02:00:00Z"},
        {"question_id": "q2", "node_id": "gold", "decision": "flag_question", "group_index": None,
         "evidence_quote": None, "reviewer_note": "trả lời được", "updated_at": "2026-11-10T03:00:00Z"},
        {"question_id": "q9", "node_id": "x", "decision": "not_relevant", "group_index": None,
         "evidence_quote": None, "reviewer_note": None, "updated_at": ""},
    ]
    merged, flagged, unknown = importer.merge(ROWS, decisions)
    assert merged[0]["decision"] == "relevant" and merged[0]["evidence_quote"] == "ít nhất 200%"
    assert merged[1]["decision"] is None and merged[1]["reviewer_note"].startswith(importer.FLAG_NOTE)
    assert flagged == ["q2"] and unknown == [("q9", "x")]
    assert ROWS[0]["decision"] is None  # input rows untouched


def test_records_are_read_from_exports_store_dumps_and_jsonl(tmp_path):
    node = ROWS[0]["node_id"]
    body = {"decision": "not_relevant", "updated_at": "t"}
    export = tmp_path / "export.json"
    export.write_text(json.dumps({"rows": [{"question_id": "q1", "node_id": node, **body}]}), encoding="utf-8")
    dump = tmp_path / "dump.json"
    dump.write_text(json.dumps([{"id": page.doc_id("q1", node), "data": body}]), encoding="utf-8")
    lines = tmp_path / "rows.jsonl"
    lines.write_text(json.dumps({"question_id": "q1", "node_id": node, **body}) + "\n", encoding="utf-8")
    for path in (export, dump, lines):
        records = [importer.normalise(r, page.parse_doc_id) for r in importer.read_records(path)]
        assert [(r["question_id"], r["node_id"], r["decision"]) for r in records] == [("q1", node, "not_relevant")]


def test_merge_records_label_source_and_draft_suggestion():
    decisions = [importer.normalise({"question_id": "q1", "node_id": ROWS[0]["node_id"], "decision": "not_relevant",
                                     "source": "draft_confirmed", "draft_suggestion": "not_relevant"}, page.parse_doc_id)]
    merged, _, _ = importer.merge(ROWS, decisions)
    assert merged[0]["label_source"] == "draft_confirmed" and merged[0]["draft_suggestion"] == "not_relevant"
    human = importer.normalise({"question_id": "q1", "node_id": ROWS[0]["node_id"], "decision": "relevant"}, page.parse_doc_id)
    assert human["source"] == "human"
    with pytest.raises(ValueError, match="source"):
        importer.normalise({"question_id": "q1", "node_id": "x", "decision": "relevant", "source": "claude"}, page.parse_doc_id)


def test_draft_helpers_pass_their_node_checks():
    import shutil
    import subprocess
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    result = subprocess.run([node, str(ROOT / "tests" / "js" / "pooling_draft.test.js")],
                            capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
    assert result.returncode == 0, result.stderr


def test_page_inlines_draft_helpers_and_rejects_script_breakouts():
    data = page.page_data(QUESTIONS, ROWS, NODES)
    html = page.render(data, "<script>__DRAFT_JS__</script>__DATA__", "window.PoolingDraft = {};")
    assert "window.PoolingDraft" in html and "__DRAFT_JS__" not in html
    with pytest.raises(ValueError):
        page.render(data, "<script>__DRAFT_JS__</script>__DATA__", "x = '</script>';")
