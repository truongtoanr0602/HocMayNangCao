# Kiểm tra nội dung Điều/Khoản/Điểm trước embedding

Ngày kiểm tra: 2026-11-03. Chỉ kiểm tra artifact; không sửa graph hoặc Neo4j.

Snapshot: `1d10ded4d2cfbf1b63efa639a7d8e36499eb0f99cf053e8ceefd3b1077b471c1`.

## Kết quả

| Loại | Số node | Title rỗng | Trung vị ký tự title | Dài nhất |
|---|---:|---:|---:|---:|
| Article | 611 | 0 | 44 | 301 |
| Clause | 2095 | 0 | 248 | 4021 |
| Point | 1828 | 0 | 143 | 2192 |

- Tổng 4534 node có đúng một cha cấu trúc, có Chunk nguồn theo đường dẫn và cùng document_id với cha.
- Metadata title của node khớp structure_path trong JSONL.
- Các source_spans của 3689 Chunk khớp lát cắt trong clean_blocks.
- Title Khoản/Điểm xuất hiện liên tục trong nội dung tái dựng từ hợp các source_spans của Chunk cùng nhánh.
- Có 116 nhóm trùng title, gồm 299 node: 28 nhóm Điều, 17 nhóm Khoản, 71 nhóm Điểm. Trùng câu chữ không đồng nghĩa trùng node hoặc sai dữ liệu.
- Article.title chỉ là tiêu đề, không phải toàn văn Điều. Tái dựng nội dung Điều từ hợp các span nguồn cho thấy 12 Điều trên 6000 ký tự; dài nhất 16147 ký tự tại doc-08/chapter-IV/article-42.

## Điều kiện chuẩn bị embedding

1. Tạo embedding_text riêng, không dùng Article.title như toàn văn Điều.
2. Bổ sung tên văn bản, địa chỉ pháp lý, tiêu đề Điều và phần dẫn cần thiết cho Khoản/Điểm; ví dụ `a) Ốm đau;` hoặc `4. Sa thải.` không đủ ngữ cảnh khi đứng riêng.
3. Giữ các node có câu chữ giống nhau theo địa chỉ pháp lý riêng, tránh loại trùng toàn cục theo title.
4. Quy định xử lý Điều dài theo tokenizer thực tế của model; 6000 ký tự chỉ là mốc khảo sát, không phải giới hạn token.
5. Khi tái dựng Điều phải giữ thứ tự span, loại phần ngữ cảnh lặp, bao gồm các bảng liên quan; không nối thẳng text các Chunk.

## Giới hạn

Đây là kiểm tra nhất quán artifact graph/JSONL/khối sạch, chưa kiểm tra lại Neo4j đang chạy. Không phải đối chiếu thủ công toàn bộ 8 DOCX, không chứng nhận parser đã nhận diện đúng mọi ranh giới Điều/Khoản/Điểm hoặc nội dung không bị gán nhầm từ đầu. Cần đối chiếu mẫu với DOCX gốc, đặc biệt vùng bảng và các Điều dài, trước khi xác nhận chất lượng ngữ nghĩa cuối cùng.

Chi tiết từng node, nhóm trùng và danh sách Điều dài nằm trong `audit.json`.
