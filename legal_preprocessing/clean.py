from __future__ import annotations

from dataclasses import dataclass, replace
import re
import unicodedata

from .models import SourceBlock


@dataclass(frozen=True)
class RemovedBlock:
    block_number: int
    reason: str
    text: str


@dataclass(frozen=True)
class CleanResult:
    blocks: tuple[SourceBlock, ...]
    removed_blocks: tuple[RemovedBlock, ...]
    warnings: tuple[str, ...] = ()


_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\u00a0", " ")
    text = _CONTROL_RE.sub("", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = re.sub(r"([;:!?])(?=\S)", r"\1 ", text)
    return text


def clean_blocks(blocks: list[SourceBlock] | tuple[SourceBlock, ...]) -> CleanResult:
    cleaned = []
    removed = []
    for block in blocks:
        lines = tuple(line for raw in block.lines if (line := normalize_text(raw)))
        if not lines:
            removed.append(RemovedBlock(block.block_number, "empty_after_normalization", block.raw_text))
            continue
        cleaned.append(replace(block, raw_text="\n".join(lines), lines=lines,
                               cells=tuple(normalize_text(cell) for cell in block.cells),
                               table_headers=tuple(tuple(normalize_text(cell) for cell in header)
                                                   for header in block.table_headers)))
    return CleanResult(tuple(cleaned), tuple(removed))
