import json

from legal_preprocessing.models import SourceBlock
from legal_preprocessing.pipeline import run_pipeline


def test_pipeline_emits_eight_documents_and_excludes_optional_files(tmp_path):
    def fake_extract(_path):
        return [SourceBlock(1, "paragraph", "Điều 1. Phạm vi áp dụng\n1. Nội dung pháp luật", ("Điều 1. Phạm vi áp dụng", "1. Nội dung pháp luật"))]

    output = tmp_path / "output"
    report = run_pipeline(tmp_path, output, 6000, extractor=fake_extract, validate_sources=False)
    rows = [json.loads(line) for line in (output / "legal_chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len({row["document_id"] for row in rows}) == 8
    assert all("tuychon" not in row["source_file"] for row in rows)
    assert len(list((output / "by_document").glob("*.jsonl"))) == 8
    assert (output / "intermediate" / "doc-01.blocks.json").is_file()
    assert not (output / "intermediate" / "doc-01.pages.json").exists()
    assert (output / "qa_report.json").is_file()
    assert (output / "qa_report.md").is_file()
    assert report["global"]["document_count"] == 8
    assert all(row["page_start"] is None and row["page_end"] is None for row in rows)
    assert all(row["paragraph_start"] == 1 and row["paragraph_end"] == 1 for row in rows)
