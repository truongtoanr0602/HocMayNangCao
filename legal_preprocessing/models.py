from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DocumentSpec:
    document_id: str
    title: str
    document_number: str
    document_type: str
    source_file: str
    short_title: str | None = None


@dataclass(frozen=True)
class SourceBlock:
    block_number: int
    block_type: str
    raw_text: str
    lines: tuple[str, ...]
    table_id: str | None = None
    row_number: int | None = None
    cells: tuple[str, ...] = ()
    cell_origins: tuple[tuple[int, int] | None, ...] = ()
    table_headers: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class StructureRef:
    number: str
    title: str = ""


@dataclass(frozen=True)
class SourceLine:
    block_number: int
    text: str
    start: int = 0
    clause_id: str | None = None
    point_id: str | None = None


@dataclass(frozen=True)
class StructurePathEntry:
    type: str
    number: str
    title: str = ""


@dataclass(frozen=True)
class SourceSpan:
    block_number: int
    start: int
    end: int
    chunk_start: int
    chunk_end: int


@dataclass(frozen=True)
class LegalUnit:
    unit_type: str
    lines: tuple[SourceLine, ...]
    paragraph_start: int
    paragraph_end: int
    part: StructureRef | None = None
    chapter: StructureRef | None = None
    section: StructureRef | None = None
    article: StructureRef | None = None
    clause_ids: tuple[str, ...] = ()
    point_ids: tuple[str, ...] = ()
    structure_path: tuple[StructurePathEntry, ...] | None = None
    table_id: str | None = None
    table_headers: tuple[tuple[str, ...], ...] = ()
    table_rows: tuple[dict, ...] = ()


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    title: str
    document_number: str
    document_type: str
    source_file: str
    page_start: int | None
    page_end: int | None
    paragraph_start: int
    paragraph_end: int
    part: StructureRef | None
    chapter: StructureRef | None
    section: StructureRef | None
    article: StructureRef | None
    clause_ids: tuple[str, ...]
    point_ids: tuple[str, ...]
    chunk_type: str
    chunk_index: int
    article_chunk_index: int | None
    text: str
    char_count: int
    token_estimate: int
    split_reason: str | None
    processing_version: str
    structure_path: tuple[StructurePathEntry, ...] = ()
    source_spans: tuple[SourceSpan, ...] = ()
    table_id: str | None = None
    table_headers: tuple[tuple[str, ...], ...] = ()
    table_rows: tuple[dict, ...] = ()
    short_title: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["clause_ids"] = list(self.clause_ids)
        value["point_ids"] = list(self.point_ids)
        value["structure_path"] = [asdict(entry) for entry in self.structure_path]
        value["source_spans"] = [asdict(span) for span in self.source_spans]
        value["table_headers"] = [list(cells) for cells in self.table_headers]
        value["table_rows"] = list(self.table_rows)
        return value
