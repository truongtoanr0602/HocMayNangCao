import pytest

from legal_kg.embedding_text import reconstruct, prepare_records
from legal_kg.build import build_graph
from test_leaf_chunks import make_chunks


def test_reconstruct_deduplicates_offsets_not_equal_text():
    blocks = {1: "abcdef", 2: "abcdef"}
    spans = [(1, 0, 4), (1, 2, 6), (1, 0, 4), (2, 0, 6)]
    assert reconstruct(blocks, spans) == "abcdef\nabcdef"
    with pytest.raises(ValueError):
        reconstruct(blocks, [(1, 0, 20)])


def test_preparation_restores_article_and_context_without_sibling_points():
    texts = ["Điều 1. Phạm vi", "Dẫn chung:", "1. Trường hợp:",
             "a) Nội dung A", "b) Nội dung B", "2. Nội dung C"]
    rows = [c.to_dict() for c in make_chunks(*texts, limit=45)]
    graph = build_graph(rows)
    blocks = {"law": dict(enumerate(texts, 1))}
    records = prepare_records(graph, rows, blocks)
    article = next(r for r in records if r["label"] == "Article")
    assert article["body_text"] == "\n".join(texts)
    point = next(r for r in records if r["label"] == "Point" and r["number"] == "a")
    assert "1. Trường hợp:" in point["embedding_text"]
    assert "Dẫn chung:" in point["embedding_text"]
    assert "b) Nội dung B" not in point["embedding_text"]
    assert point["body_text"] == "a) Nội dung A"
    assert point["source_chunk_ids"] and point["source_spans"]
    assert len({r["node_id"] for r in records}) == len(records)


def test_source_mismatch_is_rejected():
    rows = [c.to_dict() for c in make_chunks("Điều 1. Phạm vi", "1. Nội dung")]
    graph = build_graph(rows)
    with pytest.raises(ValueError, match="Source mismatch"):
        prepare_records(graph, rows, {"law": {1: "X" * 15, 2: "1. Nội dung"}})


def test_v2_article_with_clauses_keeps_heading_and_lead_in_only():
    texts = ["Điều 1. Phạm vi", "Dẫn chung:", "1. Trường hợp:", "a) Nội dung A", "2. Nội dung C"]
    rows = [c.to_dict() for c in make_chunks(*texts, limit=45)]
    graph = build_graph(rows)
    blocks = {"law": dict(enumerate(texts, 1))}
    v1 = {r["node_id"]: r for r in prepare_records(graph, rows, blocks)}
    v2 = {r["node_id"]: r for r in prepare_records(graph, rows, blocks, "v2")}
    article = next(k for k, r in v2.items() if r["label"] == "Article")
    assert v2[article]["body_text"] == "Điều 1. Phạm vi\nDẫn chung:"
    assert v2[article]["embedding_version"] == "node-text-v2"
    assert v1[article]["body_text"] == "\n".join(texts)
    # Clause and Point records do not change between versions.
    assert all(v1[k]["embedding_text"] == v2[k]["embedding_text"] for k in v1 if k != article)
    with pytest.raises(ValueError):
        prepare_records(graph, rows, blocks, "v3")


def test_v2_article_without_clauses_keeps_full_text():
    texts = ["Điều 2. Hiệu lực", "Nghị định có hiệu lực từ ngày ký."]
    rows = [c.to_dict() for c in make_chunks(*texts)]
    graph = build_graph(rows)
    records = prepare_records(graph, rows, {"law": dict(enumerate(texts, 1))}, "v2")
    article = next(r for r in records if r["label"] == "Article")
    assert article["body_text"] == "\n".join(texts)
