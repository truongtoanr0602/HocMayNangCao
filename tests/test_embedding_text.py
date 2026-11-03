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
