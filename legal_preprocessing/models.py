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


@dataclass(frozen=True)
class SourceBlock:
    block_number: int
    block_type: str
    raw_text: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class StructureRef:
    number: str
    title: str = ""


@dataclass(frozen=True)
class SourceLine:
    block_number: int
    text: str


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

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["clause_ids"] = list(self.clause_ids)
        value["point_ids"] = list(self.point_ids)
        return value
