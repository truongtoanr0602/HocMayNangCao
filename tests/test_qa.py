from legal_preprocessing.qa import validate_chunks


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
