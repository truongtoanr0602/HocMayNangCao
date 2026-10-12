from __future__ import annotations

from collections import Counter
from statistics import median


def validate_chunks(rows: list[dict], expected_documents: int = 8) -> dict[str, bool]:
    ids = [row.get("chunk_id") for row in rows]
    documents = {row.get("document_id") for row in rows}
    return {
        "expected_document_count": len(documents) == expected_documents,
        "unique_chunk_ids": len(ids) == len(set(ids)),
        "nonempty_text": all(bool(str(row.get("text", "")).strip()) for row in rows),
        "optional_files_excluded": all("tuychon" not in str(row.get("source_file", "")) for row in rows),
        "docx_sources": all(str(row.get("source_file", "")).casefold().endswith(".docx") for row in rows),
        "valid_paragraph_ranges": all(
            isinstance(row.get("paragraph_start"), int)
            and isinstance(row.get("paragraph_end"), int)
            and 1 <= row["paragraph_start"] <= row["paragraph_end"]
            for row in rows
        ),
    }


def document_metrics(spec, raw_blocks, clean_result, parse_result, chunks) -> dict:
    lengths = [chunk.char_count for chunk in chunks]
    return {
        "document_id": spec.document_id,
        "source_file": spec.source_file,
        "block_count": len(raw_blocks),
        "paragraph_count": sum(block.block_type == "paragraph" for block in raw_blocks),
        "table_row_count": sum(block.block_type == "table_row" for block in raw_blocks),
        "raw_char_count": sum(len(block.raw_text) for block in raw_blocks),
        "clean_char_count": sum(len(block.raw_text) for block in clean_result.blocks),
        "removed_block_count": len(clean_result.removed_blocks),
        "article_count": sum(unit.unit_type == "article" for unit in parse_result.units),
        "chunk_count": len(chunks),
        "chunk_chars": {"min": min(lengths), "median": median(lengths), "max": max(lengths)} if lengths else None,
        "split_reasons": dict(Counter(chunk.split_reason or "none" for chunk in chunks)),
        "warnings": list(clean_result.warnings + parse_result.warnings),
    }


def render_markdown(report: dict) -> str:
    lines = ["# Báo cáo QA tiền xử lý", "", f"- Số văn bản: {report['global']['document_count']}",
             f"- Số chunk: {report['global']['chunk_count']}", f"- Trạng thái: {report['global']['status']}", "",
             "| ID | Khối | Điều | Chunk | Cảnh báo |", "|---|---:|---:|---:|---:|"]
    for item in report["documents"]:
        lines.append(f"| {item['document_id']} | {item['block_count']} | {item['article_count']} | {item['chunk_count']} | {len(item['warnings'])} |")
    return "\n".join(lines) + "\n"
