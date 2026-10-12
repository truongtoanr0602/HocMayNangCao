from legal_preprocessing.chunk import chunk_units
from legal_preprocessing.models import DocumentSpec, LegalUnit, SourceLine, StructureRef


SPEC = DocumentSpec("doc-01", "Luật mẫu", "01/2026/QH", "luật", "data/01.pdf")


def article(*texts):
    lines = tuple(SourceLine(1, text) for text in texts)
    return LegalUnit("article", lines, 1, 1, article=StructureRef("1", "Phạm vi"), clause_ids=("1", "2"))


def test_short_article_stays_whole():
    chunks = chunk_units(SPEC, [article("Điều 1. Phạm vi", "1. Nội dung")], max_chars=6000)
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "article"
    assert chunks[0].split_reason is None


def test_long_article_splits_at_clause_and_keeps_article_metadata():
    unit = article("Điều 1. Phạm vi", "1. " + "A" * 80, "2. " + "B" * 80)
    chunks = chunk_units(SPEC, [unit], max_chars=110)
    assert len(chunks) == 2
    assert {chunk.article.number for chunk in chunks} == {"1"}
    assert [chunk.article_chunk_index for chunk in chunks] == [1, 2]
    assert all(chunk.split_reason == "max_size_clause" for chunk in chunks)
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
