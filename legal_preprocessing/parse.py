from __future__ import annotations

from dataclasses import dataclass
import re

from .models import LegalUnit, SourceBlock, SourceLine, StructureRef, StructurePathEntry


@dataclass(frozen=True)
class ParseResult:
    units: tuple[LegalUnit, ...]
    warnings: tuple[str, ...] = ()


_LEVELS = {
    "part": re.compile(r"^PHẦN\s+(\S+)(?:[.:-]\s*(.*))?$", re.I),
    "section": re.compile(r"^(?:MỤC|TIỂU MỤC)\s+(\S+)(?:[.:-]\s*(.*))?$", re.I),
}
_ROMAN_CHAPTERS = (
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
    "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX",
)
_CHAPTER = re.compile(
    r"^(?:[\s|¬_ˆằ.`„—\-]|[lI1](?=\s)){0,16}CHƯƠNG\s*([A-Z0-9]{1,5})"
    r"(?:\s*[.:-]\s*(.*?))?(?:\s+\S+){0,2}\s*$",
    re.I,
)
_ARTICLE = re.compile(r"^(.{0,8}?)ĐI(?:ỀU|ÊU|ỀN|ỂU)\s+(\d+[A-ZĐ]?)\s*[.:-]\s*(.*)$", re.I)
_CLAUSE = re.compile(r"^(\d+)\s*[.)]\s+\S")
_POINT = re.compile(r"^([a-zđ])\s*[.)]\s+\S", re.I)
_APPENDIX = re.compile(r"^PHỤ\s+LỤC(?:\s+([IVXLCDM]+|\d+))?(?:\s*[.:-]\s*(.*))?$", re.I)


def _normalize_chapter_number(raw_number: str, last_index: int | None) -> tuple[str, bool]:
    """Map a noisy OCR chapter label into the supported I--XIX range."""
    raw_number = raw_number.upper()
    raw_index = _ROMAN_CHAPTERS.index(raw_number) if raw_number in _ROMAN_CHAPTERS else None

    if last_index is None:
        return (raw_number, False) if raw_index is not None else ("I", True)

    expected_index = last_index + 1
    if expected_index >= len(_ROMAN_CHAPTERS):
        return (raw_number, False) if raw_index is not None else (_ROMAN_CHAPTERS[-1], True)

    if raw_index is not None and raw_index > last_index:
        return raw_number, raw_index != expected_index

    return _ROMAN_CHAPTERS[expected_index], True


def parse_legal_units(blocks: list[SourceBlock] | tuple[SourceBlock, ...]) -> ParseResult:
    state: dict[str, StructureRef | None] = {"part": None, "chapter": None, "section": None}
    pending_level: str | None = None
    units: list[LegalUnit] = []
    buffer: list[SourceLine] = []
    buffer_kind = "preamble"
    buffer_path: tuple[StructurePathEntry, ...] = ()
    buffer_table: SourceBlock | None = None
    table_rows: list[dict] = []
    article_ref: StructureRef | None = None
    appendix_ref: StructureRef | None = None
    clause_id: str | None = None
    point_id: str | None = None
    warnings: list[str] = []
    last_article_number: str | None = None
    last_chapter_index: int | None = None

    def path() -> tuple[StructurePathEntry, ...]:
        if appendix_ref:
            return (StructurePathEntry("appendix", appendix_ref.number, appendix_ref.title),)
        refs = [(kind, ref) for kind, ref in state.items() if ref]
        if article_ref:
            refs.append(("article", article_ref))
        return tuple(StructurePathEntry(kind, ref.number, ref.title) for kind, ref in refs)

    def flush() -> None:
        nonlocal buffer, table_rows
        if buffer:
            units.append(LegalUnit(
                buffer_kind, tuple(buffer), buffer[0].block_number, buffer[-1].block_number,
                state["part"], state["chapter"], state["section"], article_ref,
                tuple(dict.fromkeys(line.clause_id for line in buffer if line.clause_id)),
                tuple(dict.fromkeys(line.point_id for line in buffer if line.point_id)),
                buffer_path, buffer_table.table_id if buffer_table else None,
                buffer_table.table_headers if buffer_table else (), tuple(table_rows),
            ))
        buffer, table_rows = [], []

    def append(line: SourceLine, kind: str, current_path: tuple[StructurePathEntry, ...]) -> None:
        nonlocal buffer_kind, buffer_path
        if buffer and (buffer_kind != kind or buffer_path != current_path):
            flush()
        buffer_kind, buffer_path = kind, current_path
        buffer.append(line)

    for block_index, block in enumerate(blocks):
        if block.block_type == "table_row":
            table_id = block.table_id or (buffer_table.table_id if buffer_table else f"block-{block.block_number}")
            if buffer_kind != "table" or buffer_table is None or buffer_table.table_id != table_id:
                flush()
                # Synthetic blocks in tests/older extractors may not have a table ID.
                from dataclasses import replace
                buffer_table = replace(block, table_id=table_id)
            current_path = path() + (StructurePathEntry("table", table_id, f"Bảng tại khối {table_id.removeprefix('block-')}"),)
            table_rows.append({"block_number": block.block_number, "row_number": block.row_number,
                               "cells": list(block.cells), "cell_origins": list(block.cell_origins)})
            cursor = 0
            for text in block.lines:
                start = block.raw_text.find(text, cursor)
                if start < 0:
                    raise ValueError(f"Cannot locate table line in source block {block.block_number}")
                cursor = start + len(text)
                append(SourceLine(block.block_number, text, start, clause_id, point_id), "table", current_path)
            continue
        if buffer_kind == "table":
            flush()
            buffer_table = None
        cursor = 0
        for text in block.lines:
            text = text.strip()
            if not text:
                continue
            start = block.raw_text.find(text, cursor)
            if start < 0:
                raise ValueError(f"Cannot locate line in source block {block.block_number}")
            cursor = start + len(text)
            source_line = SourceLine(block.block_number, text, start, clause_id, point_id)
            appendix_match = _APPENDIX.fullmatch(text)
            if appendix_match:
                flush()
                number = appendix_match.group(1) or f"block-{block.block_number}"
                title = appendix_match.group(2) or text
                if not appendix_match.group(2) and block_index + 1 < len(blocks):
                    following = blocks[block_index + 1]
                    candidate = following.lines[0] if following.lines else ""
                    if (following.block_type == "paragraph" and candidate and not candidate.startswith("(")
                            and not _APPENDIX.fullmatch(candidate) and any(c.isalpha() for c in candidate)):
                        title = candidate
                appendix_ref = StructureRef(number, title)
                state = {"part": None, "chapter": None, "section": None}
                article_ref = None
                clause_id = point_id = None
                pending_level = None
                append(SourceLine(block.block_number, text, start), "appendix", path())
                continue
            if appendix_ref:
                # Keep headings inside forms as content, not main-document Articles/Chapters.
                if re.match(r"^Mẫu\s+số\s+\d", text, re.I) and buffer:
                    flush()
                append(SourceLine(block.block_number, text, start), "appendix", path())
                continue
            if pending_level:
                state[pending_level] = StructureRef(state[pending_level].number, text)  # type: ignore[union-attr]
                pending_level = None
                continue
            chapter_match = _CHAPTER.match(text)
            if chapter_match:
                flush()
                article_ref = None
                clause_id = point_id = None
                raw_number = chapter_match.group(1)
                chapter_number, normalized = _normalize_chapter_number(raw_number, last_chapter_index)
                inline_title = (chapter_match.group(2) or "").strip()
                if not any(character.isalnum() for character in inline_title):
                    inline_title = ""
                state["chapter"] = StructureRef(chapter_number, inline_title)
                state["section"] = None
                last_chapter_index = _ROMAN_CHAPTERS.index(chapter_number)
                if normalized:
                    warnings.append(
                        f"OCR chapter label normalized at block {block.block_number}: "
                        f"{text[:60]} -> Chương {chapter_number}"
                    )
                if not inline_title:
                    pending_level = "chapter"
                continue
            matched_level = False
            for level, pattern in _LEVELS.items():
                match = pattern.match(text)
                if match:
                    flush()
                    article_ref = None
                    clause_id = point_id = None
                    state[level] = StructureRef(match.group(1), (match.group(2) or "").strip())
                    if level == "part":
                        state["chapter"] = state["section"] = None
                    if not state[level].title:
                        pending_level = level
                    matched_level = True
                    break
            if matched_level:
                continue
            article_match = _ARTICLE.match(text)
            if article_match:
                candidate = article_match.group(2)
                candidate_base = int(re.match(r"\d+", candidate).group())
                last_base = int(re.match(r"\d+", last_article_number).group()) if last_article_number else None
                valid_sequence = ((last_base is None) or
                                  (last_base is not None and
                                   (candidate_base == last_base and candidate != last_article_number or
                                    last_base < candidate_base <= last_base + 3)))
                if not valid_sequence:
                    warnings.append(f"Rejected Article-like reference at block {block.block_number}: {text[:60]}")
                    append(source_line, "article" if article_ref else "preamble", path())
                    continue
                if article_match.group(1) or not text.lstrip(" |_-.¬").casefold().startswith("điều"):
                    warnings.append(f"OCR article label normalized at block {block.block_number}: {text[:40]}")
                flush()
                article_ref = StructureRef(candidate, article_match.group(3).strip())
                last_article_number = candidate
                clause_id = point_id = None
                append(SourceLine(block.block_number, text, start), "article", path())
                continue
            if article_ref:
                clause_match = _CLAUSE.match(text)
                point_match = _POINT.match(text)
                if clause_match:
                    clause_id, point_id = clause_match.group(1), None
                elif point_match:
                    point_id = point_match.group(1).lower()
            append(SourceLine(block.block_number, text, start, clause_id, point_id),
                   "article" if article_ref else "preamble", path())
    flush()
    if not any(unit.unit_type == "article" for unit in units):
        warnings.append("No Article headings recognized")
    return ParseResult(tuple(units), tuple(warnings))
