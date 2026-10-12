from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P

from .models import SourceBlock


class DocxExtractionError(RuntimeError):
    pass


def _lines(text: str) -> tuple[str, ...]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return tuple(line.strip() for line in normalized.splitlines() if line.strip())


def _table_row_text(row) -> str:
    cells = []
    for cell in row.cells:
        parts = _lines(cell.text)
        if parts:
            cells.append(" ".join(parts))
    return " | ".join(cells)


def extract_docx(path: Path) -> list[SourceBlock]:
    if path.suffix.casefold() != ".docx":
        raise DocxExtractionError(f"Unsupported source format: {path}")
    try:
        document = Document(path)
        pending: list[tuple[str, str]] = []
        for element in document.element.body.iterchildren():
            if isinstance(element, CT_P):
                text = Paragraph(element, document).text.strip()
                if text:
                    pending.append(("paragraph", text))
            elif isinstance(element, CT_Tbl):
                table = Table(element, document)
                for row in table.rows:
                    text = _table_row_text(row)
                    if text:
                        pending.append(("table_row", text))
    except DocxExtractionError:
        raise
    except Exception as exc:
        raise DocxExtractionError(f"Cannot extract {path}: {exc}") from exc

    if sum(1 for _, text in pending for character in text if not character.isspace()) < 20:
        raise DocxExtractionError(f"Insufficient text in {path}")

    return [
        SourceBlock(number, block_type, text, _lines(text))
        for number, (block_type, text) in enumerate(pending, start=1)
    ]
