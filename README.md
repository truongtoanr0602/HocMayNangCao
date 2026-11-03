# Trợ lý tư vấn pháp luật lao động — Hybrid KG–RAG

Dự án xây dựng trợ lý kết hợp embedding, tìm kiếm keyword và đồ thị cấu trúc văn bản pháp luật.
Hiện đã có pipeline tiền xử lý 8 văn bản DOCX và module `legal_kg` dựng cấu trúc,
nối viện dẫn/hướng dẫn/quy định chi tiết có dẫn chứng, không gọi LLM.
Embedding, BM25 và lớp trả lời hội thoại chưa được triển khai.

## Chạy tại thư mục gốc

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python -m legal_preprocessing.cli
python -m legal_kg.cli build
python -m legal_kg.cli search --title "BLLĐ 2019"
python -m legal_kg.cli inspect --chunk-id 00e7045e70338c40ac64
```

## Tài liệu

- [Tiền xử lý DOCX](README-preprocessing.md)
- [KG cấu trúc, cấu hình Neo4j và kiểm thử tích hợp](README-kg.md)
- [Kế hoạch triển khai](docs/superpowers/plans/2026-10-12-structural-kg-rag-roadmap.md)
- [Thiết kế KG cấu trúc](docs/superpowers/specs/2026-10-12-structural-kg-design.md)

## Trạng thái và giới hạn

Snapshot tiền xử lý v4 hiện có 3.689 chunk; graph có 8.432 node và 10.816 cạnh.
Mỗi nhánh chia ở cấp nhỏ nhất: Điều không có Khoản → Điều; Khoản không có Điểm → Khoản;
Khoản có Điểm → từng Điểm. Phần dẫn của Điều/Khoản được giữ cùng nội dung con.
Phụ lục tách khỏi Điều chính; bảng giữ cột trống, tọa độ ô gộp và tiêu đề.
Chunk không vượt 6.000 ký tự, có `structure_path` và `source_spans` để đối chiếu nguồn.
Loader dùng `load` bình thường cho snapshot này; cờ `--allow-legacy-metadata` chỉ dành cho dữ liệu cũ.
KG có node Khoản/Điểm và các cạnh `REFERS_TO`, `GUIDES`, `DETAILS` ở cấp đơn vị và văn bản.
208 cảnh báo viện dẫn chưa xác định được đích được giữ trong graph để đối chiếu.
Các quy tắc không bao phủ mọi cách diễn đạt và chưa kiểm chứng hiệu lực pháp lý tự động.
Chunk giữ `title`, `short_title` tùy chọn; tra cứu hỗ trợ cả tên gốc và tên rút gọn.
Kiểm thử Neo4j thật được bật riêng, yêu cầu server đang chạy.

`data/` chứa nguồn, `output/` chứa artifact hiện có; kết quả trích xuất ngữ nghĩa cũ trong
`json_KG/` và `output/preprocessed/extraction_results*.jsonl` không được module KG cấu trúc sử dụng.
Không đưa mật khẩu `.env` vào Git; tham khảo `.env.example` để cấu hình local.
