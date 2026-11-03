import json
from dataclasses import replace

from legal_kg.build import build_graph
from legal_kg.cli import main
from legal_kg.titles import TitleIndex
from test_leaf_chunks import SPEC, make_chunks


def test_alias_and_original_title_both_retrieve_same_chunks_without_llm():
    rows = [c.to_dict() for c in make_chunks("Điều 1. Nội dung", "A", spec=replace(SPEC, short_title="LM 2026"))]
    graph = build_graph(rows)
    index = TitleIndex(graph)
    result = index.lookup("  lm 2026  ")
    assert result == index.lookup("LUAT MAU 2026") == index.lookup("01/2026/QH15")
    assert result[0]["title"] == SPEC.title and result[0]["query_title"] == "LM 2026"
    assert result[0]["chunk_ids"] == [rows[0]["chunk_id"]]
    chunk = next(n for n in graph.nodes if n.label == "Chunk")
    assert chunk.properties["title"] == SPEC.title and chunk.properties["short_title"] == "LM 2026"


def test_missing_alias_falls_back_and_alias_collisions_return_all_documents():
    chunks = make_chunks("Điều 1. Nội dung", "A")
    graph = build_graph([c.to_dict() for c in chunks])
    assert TitleIndex(graph).lookup(SPEC.title)[0]["query_title"] == SPEC.title
    rows = [c.to_dict() for c in make_chunks("Điều 1. Nội dung", "A", spec=replace(SPEC, short_title="Mẫu"))]
    rows += [c.to_dict() for c in make_chunks("Điều 1. Nội dung", "B", spec=replace(SPEC, document_id="law2", short_title="Mẫu"))]
    assert len(TitleIndex(build_graph(rows)).lookup("Mẫu")) == 2


def test_offline_search_command(tmp_path, capsys):
    graph = build_graph([c.to_dict() for c in make_chunks("Điều 1. Nội dung", "A")])
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(graph.to_dict()), encoding="utf-8")
    assert main(["search", "--input", str(path), "--title", SPEC.title]) == 0
    assert json.loads(capsys.readouterr().out)[0]["document_id"] == "law"
