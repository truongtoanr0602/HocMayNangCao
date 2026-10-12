from docx import Document
import pytest

from legal_preprocessing.extract import DocxExtractionError, extract_docx


def test_extract_docx_preserves_body_paragraph_order_and_excludes_margins(tmp_path):
    path = tmp_path / "law.docx"
    document = Document()
    document.sections[0].header.paragraphs[0].text = "HEADER"
    document.sections[0].footer.paragraphs[0].text = "FOOTER"
    document.add_paragraph("Điều 1. Phạm vi")
    document.add_paragraph("1. Nội dung")
    document.save(path)

    blocks = extract_docx(path)

    assert [(block.block_number, block.block_type, block.raw_text) for block in blocks] == [
        (1, "paragraph", "Điều 1. Phạm vi"),
        (2, "paragraph", "1. Nội dung"),
    ]


def test_extract_docx_preserves_table_position_without_duplication(tmp_path):
    path = tmp_path / "table.docx"
    document = Document()
    document.add_paragraph("Trước bảng")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Ô A"
    table.cell(0, 1).text = "Ô B"
    document.add_paragraph("Sau bảng")
    document.save(path)

    blocks = extract_docx(path)

    assert [(block.block_type, block.raw_text) for block in blocks] == [
        ("paragraph", "Trước bảng"),
        ("table_row", "Ô A | Ô B"),
        ("paragraph", "Sau bảng"),
    ]
    assert "\n".join(block.raw_text for block in blocks).count("Ô A") == 1


def test_extract_docx_rejects_effectively_empty_document(tmp_path):
    path = tmp_path / "empty.docx"
    Document().save(path)

    with pytest.raises(DocxExtractionError, match="Insufficient text"):
        extract_docx(path)


def test_extract_docx_reports_corrupt_document_path(tmp_path):
    path = tmp_path / "broken.docx"
    path.write_bytes(b"not a docx package")

    with pytest.raises(DocxExtractionError, match="broken.docx"):
        extract_docx(path)


def test_tables_keep_empty_columns_merge_positions_and_headers(tmp_path):
    path = tmp_path / "merged.docx"
    document = Document()
    table = document.add_table(rows=3, cols=3)
    for index, value in enumerate(("Tên", "Cột giữa", "Giá trị")):
        table.cell(0, index).text = value
    table.cell(1, 0).merge(table.cell(1, 1)).text = "Ô gộp"
    table.cell(1, 2).text = "100"
    table.cell(2, 0).text = "Hàng cuối"
    table.cell(2, 2).text = "200"
    document.save(path)
    blocks = extract_docx(path)
    assert blocks[1].raw_text == "Ô gộp |  | 100"
    assert blocks[2].raw_text == "Hàng cuối |  | 200"
    assert blocks[1].cells == ("Ô gộp", "", "100")
    assert blocks[1].table_id == blocks[2].table_id
    assert blocks[1].row_number == 2
    assert blocks[2].table_headers == (("Tên", "Cột giữa", "Giá trị"),)


def test_vertical_merge_is_emitted_once_without_losing_column(tmp_path):
    path = tmp_path / "vertical.docx"
    document = Document()
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).merge(table.cell(1, 0)).text = "Chủ thể chung"
    table.cell(0, 1).text = "Dòng đầu"
    table.cell(1, 1).text = "Dòng sau"
    document.save(path)
    blocks = extract_docx(path)
    assert [b.raw_text for b in blocks] == ["Chủ thể chung | Dòng đầu", " | Dòng sau"]
