from pathlib import Path

from .models import DocumentSpec


DOCUMENTS = (
    DocumentSpec("doc-01", "Bộ luật Lao động 2019", "45/2019/QH14", "bộ luật", "data/01_Bo_luat_Lao_dong_2019_45-2019-QH14.docx"),
    DocumentSpec("doc-02", "Nghị định 145/2020/NĐ-CP", "145/2020/NĐ-CP", "nghị định", "data/02_ND145-2020_Huong_dan_BLLD.docx"),
    DocumentSpec("doc-03", "Thông tư 10/2020/TT-BLĐTBXH", "10/2020/TT-BLĐTBXH", "thông tư", "data/03_TT10-2020_Noi_dung_Hop_dong_Lao_dong.docx"),
    DocumentSpec("doc-04", "Nghị định 293/2025/NĐ-CP", "293/2025/NĐ-CP", "nghị định", "data/04_ND293-2025_Luong_toi_thieu_2026.docx"),
    DocumentSpec("doc-05", "Luật Bảo hiểm xã hội 2024", "41/2024/QH15", "luật", "data/05_Luat_BHXH_2024_41-2024-QH15.docx"),
    DocumentSpec("doc-06", "Nghị định 158/2025/NĐ-CP", "158/2025/NĐ-CP", "nghị định", "data/06_ND158-2025_BHXH_bat_buoc.docx"),
    DocumentSpec("doc-07", "Nghị định 135/2020/NĐ-CP", "135/2020/NĐ-CP", "nghị định", "data/07_ND135-2020_Tuoi_nghi_huu.docx"),
    DocumentSpec("doc-08", "Nghị định 12/2022/NĐ-CP", "12/2022/NĐ-CP", "nghị định", "data/08_ND12-2022_Xu_phat_Lao_dong_BHXH.docx"),
)


def validate_manifest(root: Path) -> tuple[DocumentSpec, ...]:
    for spec in DOCUMENTS:
        if not (root / spec.source_file).is_file():
            raise FileNotFoundError(f"Missing {spec.document_id}: {spec.source_file}")
    return DOCUMENTS
