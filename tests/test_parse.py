from legal_preprocessing.models import SourceBlock
from legal_preprocessing.parse import parse_legal_units


def pages(*groups):
    return [SourceBlock(i, "paragraph", "\n".join(lines), tuple(lines)) for i, lines in enumerate(groups, 1)]


def test_article_inherits_hierarchy_and_collects_clauses_and_points():
    result = parse_legal_units(pages((
        "Chương II", "HỢP ĐỒNG LAO ĐỘNG", "Điều 12. Nội dung hợp đồng",
        "1. Họ và tên;", "a) Công việc;", "b) Địa điểm.", "2. Thời hạn.",
    )))
    article = next(unit for unit in result.units if unit.unit_type == "article")
    assert article.chapter.number == "II"
    assert article.chapter.title == "HỢP ĐỒNG LAO ĐỘNG"
    assert article.article.number == "12"
    assert article.article.title == "Nội dung hợp đồng"
    assert article.clause_ids == ("1", "2")
    assert article.point_ids == ("a", "b")


def test_article_continues_across_page_and_preamble_is_retained():
    result = parse_legal_units(pages(
        ("QUỐC HỘI", "Điều 1. Phạm vi", "1. Quy định đầu"),
        ("a) Nội dung tiếp;", "2. Quy định cuối"),
    ))
    assert result.units[0].unit_type == "preamble"
    article = result.units[1]
    assert (article.paragraph_start, article.paragraph_end) == (1, 2)
    assert article.point_ids == ("a",)


def test_parser_accepts_common_ocr_variant_of_article_label():
    result = parse_legal_units(pages(("Điền 3. Giải thích từ ngữ", "1. Người lao động"),))
    article = next(unit for unit in result.units if unit.unit_type == "article")
    assert article.article.number == "3"
    assert result.warnings


def test_parser_accepts_leading_ocr_margin_noise():
    result = parse_legal_units(pages(("| Điều 1. Phạm vi", "l Tủ Điều 2. Đối tượng"),))
    assert [unit.article.number for unit in result.units if unit.article] == ["1", "2"]


def test_parser_rejects_article_reference_that_breaks_heading_sequence():
    result = parse_legal_units(pages((
        "Điều 1. Phạm vi", "Điều 151 và khoản 4 Điều 177 của Bộ luật này.",
        "Điều 2. Đối tượng",
    ),))
    articles = [unit for unit in result.units if unit.article]
    assert [unit.article.number for unit in articles] == ["1", "2"]
    assert "Điều 151" in "\n".join(line.text for line in articles[0].lines)


def test_parser_normalizes_noisy_roman_chapter_labels_up_to_xix():
    result = parse_legal_units(pages((
        "| Chương I", "QUY ĐỊNH CHUNG", "Điều 1. Điều một",
        "¬¬ Chương H", "CHƯƠNG HAI", "Điều 2. Điều hai",
        "Chương TH", "CHƯƠNG BA", "Điều 3. Điều ba",
        ".__ Chương IV", "CHƯƠNG BỐN", "Điều 4. Điều bốn",
        "Chương V", "CHƯƠNG NĂM", "Điều 5. Điều năm",
        "Chương VI |", "CHƯƠNG SÁU", "Điều 6. Điều sáu",
        "Chương VH", "CHƯƠNG BẢY", "Điều 7. Điều bảy",
        "Chương VIH", "CHƯƠNG TÁM", "Điều 8. Điều tám",
        "Chương IX", "CHƯƠNG CHÍN", "Điều 9. Điều chín",
        "ChươngX.", "CHƯƠNG MƯỜI", "Điều 10. Điều mười",
        "Chương XI", "CHƯƠNG MƯỜI MỘT", "Điều 11. Điều mười một",
        "Chương XH", "CHƯƠNG MƯỜI HAI", "Điều 12. Điều mười hai",
        "Chương XI ¬¬", "CHƯƠNG MƯỜI BA", "Điều 13. Điều mười ba",
        "Chương XIV", "CHƯƠNG MƯỜI BỐN", "Điều 14. Điều mười bốn",
        "| | Chương XV |", "CHƯƠNG MƯỜI LĂM", "Điều 15. Điều mười lăm",
        "Chương XVI", "CHƯƠNG MƯỜI SÁU", "Điều 16. Điều mười sáu",
        "Chương XVI ằ ¬", "CHƯƠNG MƯỜI BẢY", "Điều 17. Điều mười bảy",
        "Chương XVIII", "CHƯƠNG MƯỜI TÁM", "Điều 18. Điều mười tám",
        "Chương XIX", "CHƯƠNG MƯỜI CHÍN", "Điều 19. Điều mười chín",
    )))

    article_chapters = [unit.chapter.number for unit in result.units if unit.article]
    assert article_chapters == [
        "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
        "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX",
    ]
    assert any("OCR chapter label normalized" in warning for warning in result.warnings)


def test_parser_accepts_margin_noise_and_ocr_labels_from_nd145():
    result = parse_legal_units(pages((
        "- Ch\u01b0\u01a1ng I", "CHAPTER ONE", "\u0110i\u1ec1u 1. One",
        "\u201e Ch\u01b0\u01a1ng II", "CHAPTER TWO", "\u0110i\u1ec1u 2. Two",
        "Ch\u01b0\u01a1ngIH _", "CHAPTER THREE", "\u0110i\u1ec1u 3. Three",
        "Ch\u01b0\u01a1ng IV", "CHAPTER FOUR", "\u0110i\u1ec1u 4. Four",
        "- Ch\u01b0\u01a1ngV _", "CHAPTER FIVE", "\u0110i\u1ec1u 5. Five",
        "Ch\u01b0\u01a1ng VI", "CHAPTER SIX", "\u0110i\u1ec1u 6. Six",
        "` \u00ac Ch\u01b0\u01a1ngVII -", "CHAPTER SEVEN", "\u0110i\u1ec1u 7. Seven",
        "l Ch\u01b0\u01a1ng VIH l", "CHAPTER EIGHT", "\u0110i\u1ec1u 8. Eight",
        "- Ch\u01b0\u01a1ng J1 - \u201e", "CHAPTER NINE", "\u0110i\u1ec1u 9. Nine",
    )))

    article_chapters = [unit.chapter.number for unit in result.units if unit.article]
    assert article_chapters == ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
    ninth_article = next(unit for unit in result.units if unit.article and unit.article.number == "9")
    assert ninth_article.chapter.title == "CHAPTER NINE"


def test_parser_retains_originating_block_range():
    result = parse_legal_units([
        SourceBlock(1, "paragraph", "Chương I", ("Chương I",)),
        SourceBlock(2, "paragraph", "QUY ĐỊNH CHUNG", ("QUY ĐỊNH CHUNG",)),
        SourceBlock(3, "paragraph", "Điều 1. Phạm vi", ("Điều 1. Phạm vi",)),
        SourceBlock(4, "paragraph", "1. Nội dung", ("1. Nội dung",)),
    ])

    article = next(unit for unit in result.units if unit.article)
    assert (article.paragraph_start, article.paragraph_end) == (3, 4)
    assert [line.block_number for line in article.lines] == [3, 4]
