import json
from pathlib import Path
import re


OUTPUT = Path("output/preprocessed/legal_chunks.jsonl")


def load_rows():
    return [json.loads(line) for line in OUTPUT.read_text(encoding="utf-8").splitlines()]


def test_real_output_has_eight_valid_traceable_documents():
    rows = load_rows()
    assert {row["document_id"] for row in rows} == {f"doc-{number:02d}" for number in range(1, 9)}
    assert len(rows) == len({row["chunk_id"] for row in rows})
    assert all(row["text"].strip() and row["char_count"] == len(row["text"]) for row in rows)
    assert all(row["page_start"] is None and row["page_end"] is None for row in rows)
    assert all(1 <= row["paragraph_start"] <= row["paragraph_end"] for row in rows)
    assert all("tuychon" not in row["source_file"] for row in rows)
    assert all(row["source_file"].endswith(".docx") for row in rows)


def test_real_output_article_numbers_are_contiguous_per_document():
    rows = load_rows()
    for document_id in {row["document_id"] for row in rows}:
        numbers = {
            int(re.match(r"\d+", row["article"]["number"]).group())
            for row in rows if row["document_id"] == document_id and row["article"]
        }
        assert numbers == set(range(min(numbers), max(numbers) + 1)), document_id


def test_real_output_article_chunk_indexes_are_contiguous():
    rows = load_rows()
    groups = {}
    for row in rows:
        if row["article"]:
            key = (row["document_id"], row["article"]["number"])
            groups.setdefault(key, []).append(row["article_chunk_index"])
    assert all(indexes == list(range(1, len(indexes) + 1)) for indexes in groups.values())


def test_real_output_appendices_are_separate_from_main_articles():
    rows = load_rows()
    expected = {"doc-02": 6, "doc-03": 1, "doc-04": 1, "doc-06": 2, "doc-07": 3}
    for document_id, count in expected.items():
        appendix_rows = [r for r in rows if r["document_id"] == document_id and r["structure_path"]
                         and r["structure_path"][0]["type"] == "appendix"]
        assert len({r["structure_path"][0]["number"] for r in appendix_rows}) == count
        assert all(r["article"] is None and r["chapter"] is None for r in appendix_rows)
    bac_ninh = [r for r in rows if r["document_id"] == "doc-04" and "Bắc Ninh" in r["text"]]
    assert bac_ninh
    assert all(r["structure_path"][0]["type"] == "appendix" for r in bac_ninh)


def test_real_output_spans_match_clean_source_and_chunks_are_bounded():
    rows = load_rows()
    sources = {}
    for document_id in {r["document_id"] for r in rows}:
        data = json.loads((OUTPUT.parent / "intermediate" / f"{document_id}.blocks.json").read_text(encoding="utf-8"))
        sources[document_id] = {b["block_number"]: b["text"] for b in data["clean_blocks"]}
    for row in rows:
        assert row["char_count"] <= 6000
        spans = row["source_spans"]
        assert spans
        for span in spans:
            source = sources[row["document_id"]][span["block_number"]]
            assert row["text"][span["chunk_start"]:span["chunk_end"]] == source[span["start"]:span["end"]]


def test_real_table_chunks_keep_headers_and_grid_metadata():
    tables = [r for r in load_rows() if r["chunk_type"] == "table"]
    assert tables
    for row in tables:
        assert row["structure_path"][-1]["type"] == "table"
        assert row["table_headers"] and row["table_rows"]
        assert all(len(r["cells"]) == len(r["cell_origins"]) for r in row["table_rows"])
