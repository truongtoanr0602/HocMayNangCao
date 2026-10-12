from __future__ import annotations

from hashlib import sha256
from math import ceil
import re

from . import __version__
from .models import Chunk, DocumentSpec, LegalUnit, SourceLine


_CLAUSE = re.compile(r"^(\d+)\s*[.)]\s+")
_POINT = re.compile(r"^([a-zđ])\s*[.)]\s+", re.I)
_SENTENCE = re.compile(r"(?<=[.!?;])\s+(?=[A-ZÀ-ỸĐ\d])")


def _groups(unit: LegalUnit, max_chars: int) -> tuple[list[list[SourceLine]], str | None]:
    if sum(len(line.text) + 1 for line in unit.lines) <= max_chars:
        return [list(unit.lines)], None
    heading = unit.lines[:1] if unit.unit_type == "article" else ()
    bodies: list[list[SourceLine]] = []
    current: list[SourceLine] = []
    for line in unit.lines[len(heading):]:
        if _CLAUSE.match(line.text) and current:
            bodies.append(current)
            current = []
        current.append(line)
    if current:
        bodies.append(current)
    packed: list[list[SourceLine]] = []
    current = []
    heading_size = sum(len(line.text) + 1 for line in heading)
    for body in bodies:
        candidate_size = heading_size + sum(len(line.text) + 1 for line in current + body)
        if current and candidate_size > max_chars:
            packed.append(list(heading) + current)
            current = []
        current.extend(body)
    if current:
        packed.append(list(heading) + current)
    # Sentence fallback for a single oversized group.
    final: list[list[SourceLine]] = []
    for group in packed:
        if sum(len(line.text) + 1 for line in group) <= max_chars:
            final.append(group)
            continue
        head = list(heading)
        text = " ".join(line.text for line in group[len(heading):])
        pieces = _SENTENCE.split(text)
        buffer = ""
        for piece in pieces:
            if buffer and heading_size + len(buffer) + len(piece) + 1 > max_chars:
                final.append(head + [SourceLine(group[-1].block_number, buffer)])
                buffer = ""
            buffer = f"{buffer} {piece}".strip()
        if buffer:
            final.append(head + [SourceLine(group[-1].block_number, buffer)])
    return final, "max_size_clause" if len(bodies) > 1 else "max_size_sentence"


def chunk_units(spec: DocumentSpec, units: list[LegalUnit] | tuple[LegalUnit, ...], max_chars: int = 6000) -> list[Chunk]:
    chunks: list[Chunk] = []
    for unit in units:
        groups, split_reason = _groups(unit, max_chars)
        for local_index, lines in enumerate(groups, start=1):
            text = "\n".join(line.text for line in lines).strip()
            clauses = tuple(dict.fromkeys(match.group(1) for line in lines if (match := _CLAUSE.match(line.text))))
            points = tuple(dict.fromkeys(match.group(1).lower() for line in lines if (match := _POINT.match(line.text))))
            article_index = local_index if unit.article else None
            identity = unit.article.number if unit.article else unit.unit_type
            digest = sha256(f"{spec.document_id}|{identity}|{article_index}|{text}".encode("utf-8")).hexdigest()[:20]
            chunk_type = unit.unit_type if len(groups) == 1 else "clause_group"
            chunks.append(Chunk(
                digest, spec.document_id, spec.title, spec.document_number, spec.document_type,
                spec.source_file, None, None,
                min(line.block_number for line in lines), max(line.block_number for line in lines),
                unit.part, unit.chapter, unit.section, unit.article, clauses, points, chunk_type,
                len(chunks) + 1, article_index, text, len(text), ceil(len(text) / 3),
                split_reason, __version__,
            ))
    return chunks
