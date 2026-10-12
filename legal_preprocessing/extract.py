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


def _cell_text(cell) -> str:
    parts = []
    for element in cell._tc.iterchildren():
        if isinstance(element, CT_P):
            parts.extend(_lines(Paragraph(element, cell).text))
        elif isinstance(element, CT_Tbl):
            unique = set()
            for row in Table(element, cell).rows:
                values = []
                for nested in row.cells:
                    values.append(_cell_text(nested) if nested._tc not in unique else "")
                    unique.add(nested._tc)
                parts.append(" | ".join(values))
    return " ".join(parts)


def extract_docx(path: Path) -> list[SourceBlock]:
    if path.suffix.casefold() != ".docx":
        raise DocxExtractionError(f"Unsupported source format: {path}")
    try:
        document = Document(path)
        blocks: list[SourceBlock] = []
        for element in document.element.body.iterchildren():
            if isinstance(element, CT_P):
                text = Paragraph(element, document).text.strip()
                if text:
                    blocks.append(SourceBlock(len(blocks) + 1, "paragraph", text, _lines(text)))
            elif isinstance(element, CT_Tbl):
                table = Table(element, document)
                table_id = f"block-{len(blocks) + 1}"
                origins = {}
                rows = []
                headers = []
                for row_number, row in enumerate(table.rows, 1):
                    before = getattr(row, "grid_cols_before", 0)
                    cells, coordinates = [""] * before, [None] * before
                    for column, cell in enumerate(row.cells, before + 1):
                        origin = origins.get(cell._tc)
                        if origin is None:
                            origin = (row_number, column)
                            origins[cell._tc] = origin
                            cells.append(_cell_text(cell))
                        else:
                            cells.append("")
                        coordinates.append(origin)
                    while len(cells) < len(table.columns):
                        cells.append("")
                        coordinates.append(None)
                    if row_number == 1 or row._tr.xpath("./w:trPr/w:tblHeader[not(@w:val='0')]"):
                        headers.append(tuple(cells))
                    rows.append((row_number, tuple(cells), tuple(coordinates)))
                for row_number, cells, coordinates in rows:
                    text = " | ".join(cells)
                    # Keep empty rows as grid positions too; separators are meaningful.
                    if any(cells) or len(cells) > 1:
                        blocks.append(SourceBlock(len(blocks) + 1, "table_row", text, _lines(text),
                                                  table_id, row_number, cells, coordinates, tuple(headers)))
    except DocxExtractionError:
        raise
    except Exception as exc:
        raise DocxExtractionError(f"Cannot extract {path}: {exc}") from exc

    if sum(1 for block in blocks for character in block.raw_text if not character.isspace() and character != "|") < 20:
        raise DocxExtractionError(f"Insufficient text in {path}")

    return blocks
