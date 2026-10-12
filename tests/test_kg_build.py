import copy
import json
from pathlib import Path

import pytest

from legal_kg.build import build_graph
from legal_kg.models import Edge, GraphPayload, Node


def row(chunk_id="c1", **changes):
    value = {
        "chunk_id": chunk_id, "document_id": "doc-01", "title": "Văn bản",
        "document_number": "01/2026", "document_type": "luật", "source_file": "data/a.docx",
        "part": None, "chapter": {"number": "I", "title": "Chương đầu"},
        "section": {"number": "1", "title": "Mục đầu"},
        "article": {"number": "10", "title": "Điều mười"},
        "chunk_type": "article", "article_chunk_index": 1, "chunk_index": 1,
        "text": "Nội dung nguồn", "paragraph_start": 1, "paragraph_end": 3,
        "page_start": None, "page_end": None, "clause_ids": ["1", "2"], "point_ids": ["a"],
        "processing_version": "2.0.0",
    }
    value.update(changes)
    return value


def test_split_chunks_share_article_without_inventing_clause_point_nodes():
    graph = build_graph([row(), row("c2", chunk_type="clause_group", article_chunk_index=2, chunk_index=2)])
    articles = [n for n in graph.nodes if n.label == "Article"]
    assert len(articles) == 1
    assert articles[0].id == "doc-01/chapter-I/section-1/article-10"
    links = [e for e in graph.edges if e.type == "HAS_CHUNK"]
    assert {(e.source, e.target) for e in links} == {(articles[0].id, "c1"), (articles[0].id, "c2")}
    assert not any(n.label in {"Clause", "Point", "Provision"} for n in graph.nodes)
    assert next(n for n in graph.nodes if n.id == "c1").properties["clause_ids"] == ["1", "2"]


def test_missing_levels_and_preamble_are_preserved():
    graph = build_graph([row(chapter=None, section=None), row("intro", chapter=None, section=None,
                        article=None, chunk_type="preamble", article_chunk_index=None, chunk_index=2)])
    assert {(e.source, e.target, e.type) for e in graph.edges} == {
        ("doc-01", "doc-01/article-10", "CONTAINS"),
        ("doc-01/article-10", "c1", "HAS_CHUNK"), ("doc-01", "intro", "HAS_CHUNK"),
    }


def test_section_numbers_are_scoped_to_chapter():
    graph = build_graph([row(), row("c2", chapter={"number": "II", "title": "Chương hai"},
                                  article={"number": "11", "title": "Điều khác"})])
    assert {n.id for n in graph.nodes if n.label == "Section"} == {
        "doc-01/chapter-I/section-1", "doc-01/chapter-II/section-1",
    }


def test_explicit_appendix_path_overrides_stale_legacy_article():
    graph = build_graph([row(structure_path=[
        {"type": "appendix", "number": "I", "title": "Địa bàn"},
        {"type": "table", "number": "block-100", "title": "Các vùng"},
    ])])
    assert not any(n.label == "Article" for n in graph.nodes)
    assert ("doc-01/appendix-I/table-block-100", "c1", "HAS_CHUNK") in {
        (e.source, e.target, e.type) for e in graph.edges
    }
    assert not graph.warnings


def test_hashes_and_graph_are_stable_but_change_when_input_changes():
    rows = [row(), row("c2", chunk_index=2)]
    before = copy.deepcopy(rows)
    a = build_graph(rows)
    assert a.to_dict() == build_graph(list(reversed(rows))).to_dict()
    assert rows == before
    assert a.source_hash != build_graph([row(text="Thay đổi nội dung")]).source_hash
    assert GraphPayload.from_dict(json.loads(json.dumps(a.to_dict()))).to_dict() == a.to_dict()


@pytest.mark.parametrize("rows", [[], [row(), row()], [row(article=None)],
    [row(paragraph_start=0)], [row(text=" ")], [row(clause_ids="1")],
    [row(structure_path=[{"type": "Provision", "number": "1", "title": ""}])],
    [row(structure_path=[{"type": "article", "number": "1", "title": ""},
                         {"type": "appendix", "number": "I", "title": ""}])]])
def test_invalid_input_is_rejected(rows):
    with pytest.raises(ValueError):
        build_graph(rows)


def test_conflicting_structure_metadata_is_rejected():
    with pytest.raises(ValueError, match="Conflicting"):
        build_graph([row(), row("c2", article={"number": "10", "title": "Tên mâu thuẫn"})])


def test_payload_tampering_is_rejected_before_loading():
    data = build_graph([row()]).to_dict()
    data["nodes"][0]["label"] = "UntrustedLabel"
    with pytest.raises(ValueError):
        GraphPayload.from_dict(data)


@pytest.mark.parametrize("field,value", [("text", ""), ("metadata_mode", None),
    ("paragraph_start", 0), ("source_file", ""), ("document_id", "other-doc")])
def test_rehashed_artifact_with_invalid_chunk_metadata_is_rejected(field, value):
    original = build_graph([row(structure_path=[])])
    nodes = tuple(Node(n.id, n.label, {**n.properties, field: value}) if n.label == "Chunk" else n
                  for n in original.nodes)
    malformed = GraphPayload(original.source_hash, nodes, original.edges)
    with pytest.raises(ValueError):
        GraphPayload.from_dict(malformed.to_dict())


def test_rehashed_artifact_with_reversed_hierarchy_is_rejected():
    original = build_graph([row(structure_path=[
        {"type": "part", "number": "I", "title": "Phần"},
        {"type": "article", "number": "1", "title": "Điều"},
    ])])
    part = next(n for n in original.nodes if n.label == "Part")
    article = next(n for n in original.nodes if n.label == "Article")
    malformed = GraphPayload(original.source_hash, original.nodes, (
        Edge("doc-01", article.id, "CONTAINS"), Edge(article.id, part.id, "CONTAINS"),
        Edge(part.id, "c1", "HAS_CHUNK"),
    ))
    with pytest.raises(ValueError, match="hierarchy"):
        GraphPayload.from_dict(malformed.to_dict())


def test_malformed_legacy_structure_reports_validation_error():
    with pytest.raises(ValueError, match="chapter"):
        build_graph([row(chapter="I")])


def test_real_corpus_preserves_every_chunk_and_reports_legacy_limitations():
    rows = [json.loads(s) for s in Path("output/preprocessed/legal_chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    graph = build_graph(rows)
    chunks = [n for n in graph.nodes if n.label == "Chunk"]
    assert {n.id for n in chunks} == {r["chunk_id"] for r in rows}
    assert sum(n.properties["chunk_type"] == "clause_group" for n in chunks) == 48
    assert len([e for e in graph.edges if e.type == "HAS_CHUNK"]) == len(rows)
    assert any("legacy" in w.lower() for w in graph.warnings)
    assert any("7ba9c209da88cd49877a" in w for w in graph.warnings)
