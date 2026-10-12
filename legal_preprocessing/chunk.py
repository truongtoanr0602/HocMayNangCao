from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from hashlib import sha256
import json
from math import ceil
import re

from . import __version__
from .models import Chunk, DocumentSpec, LegalUnit, SourceLine, SourceSpan, StructurePathEntry


_CLAUSE = re.compile(r"^(\d+)\s*[.)]\s+")
_POINT = re.compile(r"^([a-zđ])\s*[.)]\s+", re.I)
_ARTICLE_HEADING = re.compile(r"^.{0,8}ĐI(?:ỀU|ÊU|ỀN|ỂU)\s+\d", re.I)
_SENTENCE = re.compile(r"(?<!\d)[.!?;]\s+")


def _size(lines: list[SourceLine] | tuple[SourceLine, ...]) -> int:
    return sum(len(line.text) for line in lines) + max(0, len(lines) - 1)


def _split_line(line: SourceLine, limit: int) -> list[SourceLine]:
    pieces = []
    offset = 0
    while offset < len(line.text):
        remaining = line.text[offset:]
        cut = len(remaining)
        if cut > limit:
            window = remaining[:limit]
            boundaries = [m.end() for m in _SENTENCE.finditer(window)]
            cut = boundaries[-1] if boundaries else window.rfind(" ") + 1
            if cut <= 0 or (not boundaries and cut < limit // 2):
                cut = limit
        pieces.append(replace(line, text=remaining[:cut], start=line.start + offset))
        offset += cut
    return pieces


def _groups(unit: LegalUnit, max_chars: int) -> tuple[list[list[SourceLine]], str | None]:
    if _size(unit.lines) <= max_chars:
        return [list(unit.lines)], None
    heading = list(unit.lines[:1]) if (unit.unit_type == "article" and unit.lines
              and _ARTICLE_HEADING.match(unit.lines[0].text)
              and len(unit.lines[0].text) + 1 < max_chars) else []
    bodies: list[list[SourceLine]] = []
    current: list[SourceLine] = []
    for line in unit.lines[len(heading):]:
        if unit.unit_type in {"article", "appendix"} and _CLAUSE.match(line.text) and current:
            bodies.append(current)
            current = []
        current.append(line)
    if current:
        bodies.append(current)
    groups: list[list[SourceLine]] = []
    current = list(heading)
    body_budget = max_chars - (_size(heading) + 1 if heading else 0)

    def flush() -> None:
        nonlocal current
        if len(current) > len(heading):
            groups.append(current)
        current = list(heading)

    for body in bodies:
        if _size(current + body) <= max_chars:
            current.extend(body)
            continue
        flush()
        if _size(heading + body) <= max_chars:
            current.extend(body)
            continue
        # Keep source blocks and offsets even when a single row or sentence is oversized.
        for line in body:
            for piece in _split_line(line, body_budget):
                if _size(current + [piece]) > max_chars:
                    flush()
                current.append(piece)
    flush()
    reason = "max_size_clause" if unit.unit_type == "article" and len(bodies) > 1 else "max_size_sentence"
    if unit.unit_type == "table":
        reason = "max_size_table"
    return groups, reason


def _path(unit: LegalUnit) -> tuple[StructurePathEntry, ...]:
    if unit.structure_path is not None:
        return unit.structure_path
    return tuple(StructurePathEntry(kind, ref.number, ref.title) for kind in
                 ("part", "chapter", "section", "article") if (ref := getattr(unit, kind)))


def chunk_units(spec: DocumentSpec, units: list[LegalUnit] | tuple[LegalUnit, ...], max_chars: int = 6000) -> list[Chunk]:
    if type(max_chars) is not int or max_chars < 1:
        raise ValueError("max_chars must be a positive integer")
    chunks: list[Chunk] = []
    article_indexes: dict[str, int] = defaultdict(int)
    path_indexes: dict[str, int] = defaultdict(int)
    for unit in units:
        if not unit.lines:
            continue
        groups, split_reason = _groups(unit, max_chars)
        structure_path = _path(unit)
        path_key = json.dumps([(p.type, p.number) for p in structure_path], ensure_ascii=False)
        for lines in groups:
            text = "\n".join(line.text for line in lines)
            if not text.strip():
                continue
            clauses = tuple(dict.fromkeys(line.clause_id or match.group(1) for line in lines
                            if (match := _CLAUSE.match(line.text)) or line.clause_id)) if unit.article else ()
            points = tuple(dict.fromkeys(line.point_id or match.group(1).lower() for line in lines
                           if (match := _POINT.match(line.text)) or line.point_id)) if unit.article else ()
            if unit.article:
                article_indexes[unit.article.number] += 1
                article_index = article_indexes[unit.article.number]
            else:
                article_index = None
            path_indexes[path_key] += 1
            identity = unit.article.number if unit.unit_type == "article" and unit.article else path_key
            identity_index = article_index if unit.unit_type == "article" and unit.article else path_indexes[path_key]
            digest = sha256(f"{spec.document_id}|{identity}|{identity_index}|{text}".encode("utf-8")).hexdigest()[:20]
            chunk_type = "clause_group" if unit.unit_type == "article" and len(groups) > 1 else unit.unit_type
            spans = []
            offset = 0
            for line in lines:
                spans.append(SourceSpan(line.block_number, line.start, line.start + len(line.text),
                                        offset, offset + len(line.text)))
                offset += len(line.text) + 1
            source_blocks = {line.block_number for line in lines}
            chunks.append(Chunk(
                digest, spec.document_id, spec.title, spec.document_number, spec.document_type,
                spec.source_file, None, None,
                min(source_blocks), max(source_blocks),
                unit.part, unit.chapter, unit.section, unit.article, clauses, points, chunk_type,
                len(chunks) + 1, article_index, text, len(text), ceil(len(text) / 3),
                split_reason, __version__, structure_path, tuple(spans), unit.table_id, unit.table_headers,
                tuple(row for row in unit.table_rows if row["block_number"] in source_blocks),
            ))
    return chunks
