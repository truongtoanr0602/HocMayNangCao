# Trợ lý tư vấn pháp luật lao động — Hybrid KG–RAG

Dự án xây dựng trợ lý kết hợp embedding, tìm kiếm keyword và đồ thị cấu trúc văn bản pháp luật.
Hiện đã có pipeline tiền xử lý 8 văn bản DOCX và module `legal_kg` dựng graph từ metadata, không gọi LLM.
Embedding, BM25 và lớp trả lời hội thoại chưa được triển khai.

## Chạy tại thư mục gốc

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python -m legal_kg.cli build
python -m legal_kg.cli inspect --chunk-id 4b93eeaf2c2dce28ba84
```

## Tài liệu

- [Tiền xử lý DOCX](README-preprocessing.md)
- [KG cấu trúc, cấu hình Neo4j và kiểm thử tích hợp](README-kg.md)
- [Kế hoạch triển khai](docs/superpowers/plans/2026-10-12-structural-kg-rag-roadmap.md)
- [Thiết kế KG cấu trúc](docs/superpowers/specs/2026-10-12-structural-kg-design.md)

## Trạng thái và giới hạn

Snapshot tiền xử lý v3 hiện có 803 chunk; graph có 1.623 node và 1.615 cạnh.
Phụ lục tách khỏi Điều chính; bảng giữ cột trống, tọa độ ô gộp và tiêu đề.
Chunk không vượt 6.000 ký tự, có `structure_path` và `source_spans` để đối chiếu nguồn.
Loader dùng `load` bình thường cho snapshot này; cờ `--allow-legacy-metadata` chỉ dành cho dữ liệu cũ.
Chưa mô hình hóa Khoản–Điểm hoặc kiểm chứng hiệu lực pháp lý tự động.
Kiểm thử Neo4j thật được bật riêng, yêu cầu server đang chạy.

`data/` chứa nguồn, `output/` chứa artifact hiện có; kết quả trích xuất ngữ nghĩa cũ trong
`json_KG/` và `output/preprocessed/extraction_results*.jsonl` không được module KG cấu trúc sử dụng.
Không đưa mật khẩu `.env` vào Git; tham khảo `.env.example` để cấu hình local.
