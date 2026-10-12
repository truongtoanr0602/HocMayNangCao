from __future__ import annotations

from collections import Counter
from statistics import median


def _valid_path(row: dict) -> bool:
    path = row.get("structure_path")
    levels = ("part", "chapter", "section", "article", "appendix", "table")
    if not isinstance(path, list):
        return False
    previous = -1
    for entry in path:
        if (not isinstance(entry, dict) or entry.get("type") not in levels
                or not isinstance(entry.get("number"), str) or not entry["number"]
                or not isinstance(entry.get("title"), str)):
            return False
        rank = levels.index(entry["type"])
        if rank <= previous or (entry["type"] == "appendix" and previous != -1):
            return False
        previous = rank
    article = next((entry["number"] for entry in path if entry["type"] == "article"), None)
    if article != (row.get("article") or {}).get("number"):
        return False
    if row.get("table_id") and (not path or path[-1]["type"] != "table" or path[-1]["number"] != row["table_id"]):
        return False
    return True


def _valid_spans(row: dict, source_blocks: dict | None) -> bool:
    spans, text = row.get("source_spans"), row.get("text", "")
    if not isinstance(spans, list) or not spans or not isinstance(text, str):
        return False
    cursor = 0
    block_numbers = []
    for index, span in enumerate(spans):
        if not isinstance(span, dict) or any(type(span.get(k)) is not int for k in
                ("block_number", "start", "end", "chunk_start", "chunk_end")):
            return False
        block_number = span["block_number"]
        if (block_number < 1 or not 0 <= span["start"] < span["end"]
                or not span["chunk_start"] == cursor < span["chunk_end"] <= len(text)
                or span["end"] - span["start"] != span["chunk_end"] - span["chunk_start"]):
            return False
        if source_blocks is not None:
            block = source_blocks.get(row.get("document_id"), {}).get(block_number)
            if (block is None or span["end"] > len(block)
                    or block[span["start"]:span["end"]] != text[span["chunk_start"]:span["chunk_end"]]):
                return False
        block_numbers.append(block_number)
        cursor = span["chunk_end"]
        if index + 1 < len(spans):
            if text[cursor:cursor + 1] != "\n":
                return False
            cursor += 1
    return (cursor == len(text) and row.get("paragraph_start") == min(block_numbers)
            and row.get("paragraph_end") == max(block_numbers))


def _source_coverage(parse_result, chunks) -> bool:
    intervals = {}
    for chunk in chunks:
        for span in chunk.source_spans:
            intervals.setdefault(span.block_number, []).append((span.start, span.end))
    for unit in parse_result.units:
        for line in unit.lines:
            cursor, end = line.start, line.start + len(line.text)
            for start, stop in sorted(intervals.get(line.block_number, [])):
                if start > cursor:
                    break
                cursor = max(cursor, stop)
                if cursor >= end:
                    break
            if cursor < end:
                return False
    return True


def validate_chunks(rows: list[dict], expected_documents: int = 8, *, max_chars: int = 6000,
                    source_blocks: dict | None = None) -> dict[str, bool]:
    ids = [row.get("chunk_id") for row in rows]
    documents = {row.get("document_id") for row in rows}
    return {
        "expected_document_count": len(documents) == expected_documents,
        "unique_chunk_ids": len(ids) == len(set(ids)),
        "nonempty_text": all(bool(str(row.get("text", "")).strip()) for row in rows),
        "optional_files_excluded": all("tuychon" not in str(row.get("source_file", "")) for row in rows),
        "docx_sources": all(str(row.get("source_file", "")).casefold().endswith(".docx") for row in rows),
        "within_max_chars": all(isinstance(row.get("text"), str) and len(row["text"]) <= max_chars for row in rows),
        "valid_structure_paths": all(_valid_path(row) for row in rows),
        "valid_source_spans": all(_valid_spans(row, source_blocks) for row in rows),
        "valid_paragraph_ranges": all(
            type(row.get("paragraph_start")) is int
            and type(row.get("paragraph_end")) is int
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
        "article_count": len({unit.article.number for unit in parse_result.units if unit.article}),
        "appendix_count": len({entry.number for unit in parse_result.units for entry in (unit.structure_path or ())
                               if entry.type == "appendix"}),
        "table_count": len({unit.table_id for unit in parse_result.units if unit.table_id}),
        "source_content_preserved": _source_coverage(parse_result, chunks),
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
