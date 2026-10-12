from legal_preprocessing.clean import clean_blocks, normalize_text
from legal_preprocessing.models import SourceBlock


def make_block(number, block_type, *lines):
    return SourceBlock(number, block_type, "\n".join(lines), tuple(lines))


def test_normalize_text_preserves_legal_numbers_and_punctuation():
    assert normalize_text("Điều  12 .  Mức  5,5% ") == "Điều 12. Mức 5,5%"


def test_clean_blocks_preserves_source_number_and_table_separator():
    result = clean_blocks([make_block(4, "table_row", "Mức | 5,5%")])

    assert result.blocks[0].block_number == 4
    assert result.blocks[0].block_type == "table_row"
    assert result.blocks[0].lines == ("Mức | 5,5%",)


def test_clean_blocks_records_empty_control_only_block():
    result = clean_blocks([make_block(8, "paragraph", "\x00\t")])

    assert result.blocks == ()
    assert result.removed_blocks[0].block_number == 8
    assert result.removed_blocks[0].reason == "empty_after_normalization"
