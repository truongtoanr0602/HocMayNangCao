from __future__ import annotations

from dataclasses import dataclass
import re

from .models import LegalUnit, SourceBlock, SourceLine, StructureRef


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
    preamble: list[SourceLine] = []
    article_lines: list[SourceLine] = []
    article_ref: StructureRef | None = None
    article_state: dict[str, StructureRef | None] = {}
    clauses: list[str] = []
    points: list[str] = []
    warnings: list[str] = []
    last_article_number: str | None = None
    last_chapter_index: int | None = None

    def flush_article() -> None:
        nonlocal article_lines, article_ref, clauses, points
        if not article_lines or article_ref is None:
            return
        units.append(LegalUnit(
            "article", tuple(article_lines), article_lines[0].block_number,
            article_lines[-1].block_number, article_state.get("part"),
            article_state.get("chapter"), article_state.get("section"), article_ref,
            tuple(dict.fromkeys(clauses)), tuple(dict.fromkeys(points)),
        ))
        article_lines, article_ref, clauses, points = [], None, [], []

    def flush_preamble() -> None:
        nonlocal preamble
        if preamble:
            units.append(LegalUnit("preamble", tuple(preamble), preamble[0].block_number, preamble[-1].block_number,
                                   state["part"], state["chapter"], state["section"]))
            preamble = []

    for block in blocks:
        for text in block.lines:
            text = text.strip()
            if not text:
                continue
            if pending_level:
                state[pending_level] = StructureRef(state[pending_level].number, text)  # type: ignore[union-attr]
                pending_level = None
                continue
            chapter_match = _CHAPTER.match(text)
            if chapter_match:
                flush_article()
                flush_preamble()
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
                    flush_article()
                    flush_preamble()
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
                    source_line = SourceLine(block.block_number, text)
                    (preamble if article_ref is None else article_lines).append(source_line)
                    continue
                if article_match.group(1) or not text.lstrip(" |_-.¬").casefold().startswith("điều"):
                    warnings.append(f"OCR article label normalized at block {block.block_number}: {text[:40]}")
                flush_article()
                flush_preamble()
                article_ref = StructureRef(candidate, article_match.group(3).strip())
                last_article_number = candidate
                article_state = dict(state)
                article_lines = [SourceLine(block.block_number, text)]
                continue
            source_line = SourceLine(block.block_number, text)
            if article_ref is None:
                preamble.append(source_line)
            else:
                article_lines.append(source_line)
                clause_match = _CLAUSE.match(text)
                point_match = _POINT.match(text)
                if clause_match:
                    clauses.append(clause_match.group(1))
                elif point_match:
                    points.append(point_match.group(1).lower())
    flush_article()
    flush_preamble()
    if not any(unit.unit_type == "article" for unit in units):
        warnings.append("No Article headings recognized")
    return ParseResult(tuple(units), tuple(warnings))
