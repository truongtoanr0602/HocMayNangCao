from legal_preprocessing.chunk import chunk_units
from legal_preprocessing.models import DocumentSpec, LegalUnit, SourceLine, StructureRef
import pytest


SPEC = DocumentSpec("doc-01", "Luật mẫu", "01/2026/QH", "luật", "data/01.pdf")


def article(*texts):
    lines = tuple(SourceLine(1, text) for text in texts)
    return LegalUnit("article", lines, 1, 1, article=StructureRef("1", "Phạm vi"), clause_ids=("1", "2"))


def test_short_article_with_one_clause_emits_a_clause():
    chunks = chunk_units(SPEC, [article("Điều 1. Phạm vi", "1. Nội dung")], max_chars=6000)
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "clause"
    assert chunks[0].split_reason is None


def test_long_article_splits_at_clause_and_keeps_article_metadata():
    unit = article("Điều 1. Phạm vi", "1. " + "A" * 80, "2. " + "B" * 80)
    chunks = chunk_units(SPEC, [unit], max_chars=110)
    assert len(chunks) == 2
    assert {chunk.article.number for chunk in chunks} == {"1"}
    assert [chunk.article_chunk_index for chunk in chunks] == [1, 2]
    assert all(chunk.split_reason is None and chunk.chunk_type == "clause" for chunk in chunks)
    assert chunk_units(SPEC, [unit], max_chars=110)[0].chunk_id == chunks[0].chunk_id


def test_docx_chunk_uses_block_range_and_null_pages():
    lines = (
        SourceLine(7, "Điều 1. Phạm vi"),
        SourceLine(9, "1. Nội dung"),
    )
    unit = LegalUnit("article", lines, 7, 9, article=StructureRef("1", "Phạm vi"))

    chunk = chunk_units(SPEC, [unit])[0]

    assert chunk.page_start is None
    assert chunk.page_end is None
    assert chunk.paragraph_start == 7
    assert chunk.paragraph_end == 9


def test_single_oversize_sentence_is_split_and_source_offsets_are_exact():
    text = "1. " + "ABCDE" * 100
    unit = article("Điều 1. Phạm vi", text)
    chunks = chunk_units(SPEC, [unit], max_chars=80)
    assert len(chunks) > 1
    assert all(c.char_count <= 80 for c in chunks)
    covered = set()
    for c in chunks:
        for span in c.source_spans:
            if span.start == 0 and span.end == len("Điều 1. Phạm vi"):
                continue
            assert c.text[span.chunk_start:span.chunk_end] == text[span.start:span.end]
            covered.update(range(span.start, span.end))
    assert covered == set(range(len(text)))


def test_sentence_fallback_preserves_each_original_block():
    lines = (SourceLine(1, "Điều 1. Phạm vi"), SourceLine(5, "1. " + "A" * 140), SourceLine(9, "B" * 150))
    chunks = chunk_units(SPEC, [LegalUnit("article", lines, 1, 9, article=StructureRef("1"))], max_chars=60)
    assert {s.block_number for c in chunks for s in c.source_spans} == {1, 5, 9}
    assert all(c.paragraph_end == max(s.block_number for s in c.source_spans) for c in chunks)


def test_heading_longer_than_limit_is_not_lost():
    heading = "Điều 1. " + "A" * 120
    chunks = chunk_units(SPEC, [article(heading, "1. Nội dung")], max_chars=25)
    assert all(c.char_count <= 25 for c in chunks)
    assert "".join(c.text for c in chunks).replace("\n", "") == heading + "1. Nội dung"


@pytest.mark.parametrize("limit", [0, -1, True])
def test_invalid_chunk_limit_is_rejected(limit):
    with pytest.raises(ValueError):
        chunk_units(SPEC, [article("Điều 1. Phạm vi")], max_chars=limit)


def test_split_clause_does_not_emit_number_prefix_as_a_separate_chunk():
    chunks = chunk_units(SPEC, [article("Điều 1. Phạm vi", "1. " + "A" * 300)], max_chars=80)
    assert not chunks[0].text.endswith("1. ")
