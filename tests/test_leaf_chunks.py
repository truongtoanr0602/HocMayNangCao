from dataclasses import replace

from legal_preprocessing.chunk import chunk_units
from legal_preprocessing.models import DocumentSpec, SourceBlock
from legal_preprocessing.parse import parse_legal_units
from legal_preprocessing.qa import validate_chunks


SPEC = DocumentSpec("law", "Luật mẫu 2026", "01/2026/QH15", "luật", "law.docx")


def make_chunks(*texts, spec=SPEC, limit=6000):
    blocks = [SourceBlock(i, "paragraph", text, (text,)) for i, text in enumerate(texts, 1)]
    units = parse_legal_units(blocks).units
    return chunk_units(spec, units, limit)


def test_each_branch_uses_its_deepest_level_and_keeps_parent_context():
    chunks = make_chunks("Điều 1. Phạm vi", "Phần dẫn chung:", "1. Trường hợp:",
                         "a) Trường hợp A", "b) Trường hợp B", "2. Trường hợp C", "Điều 2. Hiệu lực", "Áp dụng ngay.")
    assert [c.chunk_type for c in chunks] == ["point", "point", "clause", "article"]
    assert [(c.clause_ids, c.point_ids) for c in chunks[:3]] == [(('1',), ('a',)), (('1',), ('b',)), (('2',), ())]
    assert chunks[0].text == "Điều 1. Phạm vi\nPhần dẫn chung:\n1. Trường hợp:\na) Trường hợp A"
    assert "b)" not in chunks[0].text and "a)" not in chunks[1].text
    assert [(p.type, p.number) for p in chunks[1].structure_path][-2:] == [("clause", "1"), ("point", "b")]
    assert all(validate_chunks([c.to_dict() for c in chunks], 1).values())


def test_repeated_point_letters_are_scoped_to_their_clause():
    chunks = make_chunks("Điều 1. Phạm vi", "1. Nhóm một:", "a) A", "2. Nhóm hai:", "a) B")
    assert len(chunks) == 2
    assert chunks[0].structure_path != chunks[1].structure_path
    assert chunks[0].chunk_id != chunks[1].chunk_id


def test_oversized_point_never_merges_with_another_leaf_and_keeps_exact_spans():
    texts = ("Điều 1. Phạm vi", "1. Trường hợp:", "a) " + "A" * 240, "b) B")
    chunks = make_chunks(*texts, limit=70)
    assert len(chunks) > 2
    assert all(c.char_count <= 70 and c.chunk_type == "point" for c in chunks)
    assert all(len(c.point_ids) == 1 for c in chunks)
    covered = {i: set() for i in range(1, len(texts) + 1)}
    for chunk in chunks:
        for span in chunk.source_spans:
            assert chunk.text[span.chunk_start:span.chunk_end] == texts[span.block_number - 1][span.start:span.end]
            covered[span.block_number].update(range(span.start, span.end))
    assert all(covered[i] == set(range(len(text))) for i, text in enumerate(texts, 1))


def test_original_and_optional_short_title_are_kept_in_each_chunk():
    spec = replace(SPEC, short_title="Luật mẫu")
    chunk = make_chunks("Điều 1. Phạm vi", "Nội dung", spec=spec)[0].to_dict()
    assert chunk["title"] == SPEC.title
    assert chunk["short_title"] == "Luật mẫu"
    assert make_chunks("Điều 1. Phạm vi")[0].to_dict()["short_title"] is None


def test_clause_and_point_titles_keep_full_own_content_before_size_splitting():
    from legal_kg.build import build_graph

    point = ("a) " + "Nội dung điểm. " * 20).strip()
    clause = "1. Các trường hợp:\n" + point + "\nb) Trường hợp B"
    chunks = make_chunks("Điều 1. Phạm vi", "Dẫn chung", "1. Các trường hợp:",
                         point, "b) Trường hợp B", "2. Nội dung khoản hai", limit=100)
    graph = build_graph([c.to_dict() for c in chunks])
    titles = {(n.label, n.properties.get("number")): n.properties.get("title")
              for n in graph.nodes if n.label in {"Clause", "Point"}}
    assert titles == {("Clause", "1"): clause, ("Clause", "2"): "2. Nội dung khoản hai",
                      ("Point", "a"): point, ("Point", "b"): "b) Trường hợp B"}
