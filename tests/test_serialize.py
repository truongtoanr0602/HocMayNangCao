import json

from legal_preprocessing.serialize import read_and_validate_jsonl, write_jsonl_atomic


def test_jsonl_round_trip_preserves_vietnamese_and_explicit_null(tmp_path):
    path = tmp_path / "out.jsonl"
    row = {"chunk_id": "x", "text": "Điều 1. Phạm vi", "article": None}
    write_jsonl_atomic(path, [row])
    assert read_and_validate_jsonl(path) == [row]
    assert "Điều 1" in path.read_text(encoding="utf-8")
    assert json.loads(path.read_text(encoding="utf-8"))["article"] is None
