from legal_preprocessing.qa import validate_chunks
from legal_preprocessing.chunk import chunk_units
from legal_preprocessing.models import DocumentSpec, SourceBlock
from legal_preprocessing.parse import parse_legal_units


def test_validation_rejects_duplicate_ids_and_empty_text():
    rows = [
        {"chunk_id": "same", "document_id": "a", "source_file": "data/a.pdf", "text": "ok"},
        {"chunk_id": "same", "document_id": "b", "source_file": "data/b.pdf", "text": ""},
    ]
    checks = validate_chunks(rows, expected_documents=2)
    assert checks["unique_chunk_ids"] is False
    assert checks["nonempty_text"] is False


def test_validation_rejects_non_docx_sources_and_invalid_paragraph_ranges():
    rows = [{
        "chunk_id": "one", "document_id": "a", "source_file": "data/a.pdf", "text": "ok",
        "paragraph_start": 3, "paragraph_end": 2,
    }]

    checks = validate_chunks(rows, expected_documents=1)

    assert checks["docx_sources"] is False
    assert checks["valid_paragraph_ranges"] is False


def test_qa_checks_chunk_limit_and_exact_source_spans():
    block = SourceBlock(1, "paragraph", "Điều 1. Nội dung pháp luật", ("Điều 1. Nội dung pháp luật",))
    spec = DocumentSpec("doc", "Luật", "01", "luật", "law.docx")
    rows = [c.to_dict() for c in chunk_units(spec, parse_legal_units([block]).units)]
    source = {"doc": {1: block.raw_text}}
    assert all(validate_chunks(rows, 1, max_chars=6000, source_blocks=source).values())
    assert not validate_chunks(rows, 1, max_chars=10, source_blocks=source)["within_max_chars"]
    rows[0]["source_spans"][0]["start"] = 1
    assert not validate_chunks(rows, 1, source_blocks=source)["valid_source_spans"]


def test_qa_rejects_appendix_under_article():
    row = {"chunk_id": "c", "document_id": "d", "source_file": "a.docx", "text": "Nội dung",
           "paragraph_start": 1, "paragraph_end": 1,
           "structure_path": [{"type": "article", "number": "1", "title": ""},
                              {"type": "appendix", "number": "I", "title": ""}]}
    assert not validate_chunks([row], 1)["valid_structure_paths"]
