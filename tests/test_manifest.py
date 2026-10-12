from pathlib import Path

import pytest

from legal_preprocessing.manifest import DOCUMENTS, validate_manifest


def test_manifest_contains_exactly_eight_non_optional_documents():
    assert len(DOCUMENTS) == 8
    assert [item.document_id for item in DOCUMENTS] == [f"doc-{i:02d}" for i in range(1, 9)]
    assert all(item.source_file.startswith("data/") for item in DOCUMENTS)
    assert all("tuychon" not in item.source_file for item in DOCUMENTS)
    assert all(item.source_file.endswith(".docx") for item in DOCUMENTS)
    assert DOCUMENTS[6].source_file == "data/07_ND135-2020_Tuoi_nghi_huu.docx"


def test_validate_manifest_reports_first_missing_document(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="doc-01"):
        validate_manifest(tmp_path)
