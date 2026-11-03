# Chuẩn bị nội dung embedding node

Chạy từ thư mục gốc: `python -m legal_kg.embedding_text`.

Module: `legal_kg/embedding_text.py`. Kiểm thử: `tests/test_embedding_text.py`.
Đây là bước chuẩn bị văn bản, chưa tạo vector và không ghi vào Neo4j.

## Đầu ra

- `node_texts.jsonl`: toàn bộ 4534 bản ghi Điều/Khoản/Điểm.
- `samples.json`: 29 mẫu, gồm các loại node, từng văn bản, trường hợp ngắn/dài.
- `report.json`: số lượng, độ dài và trạng thái xử lý.
- `source_verification.json`: kiểm tra lại việc trích xuất/làm sạch trực tiếp cả 8 DOCX; tất cả khớp intermediate hiện có. Đây không thay thế thẩm định thủ công ranh giới pháp lý.

## Phương pháp đã triển khai

1. Đọc graph qua GraphPayload để xác thực schema và graph_hash. Đối chiếu tập Chunk, text và structure_path với JSONL; từ chối dữ liệu không khớp.
2. Kiểm tra mỗi source_span: lát cắt trong Chunk phải khớp lát cắt trong khối nguồn sạch.
3. Gom Chunk theo đường dẫn node. Với Điều, hợp các khoảng nguồn trùng/chồng lấn trong cùng block, rồi sắp theo block và offset để tái dựng toàn văn. Hai đoạn giống nhau ở vị trí nguồn khác nhau vẫn được giữ, tránh loại nhầm quy định lặp hợp lệ. Các hàng bảng có trong nhánh được giữ theo text nguồn.
4. Với Khoản/Điểm, dùng title hiện có đã chứa nội dung và yêu cầu nó xuất hiện nguyên vẹn trong nguồn tái dựng. Điều dùng toàn văn tái dựng, không dùng riêng Article.title.
5. Bổ sung tên/số hiệu văn bản và đường dẫn Phần/Chương/Mục/Điều/Khoản/Điểm. Khoản/Điểm nhận phần dẫn Điều trước Khoản/Điểm đầu tiên. Điểm nhận thêm phần dẫn Khoản trước Điểm đầu tiên. Không đưa nội dung các Điểm anh em vào ngữ cảnh Điểm.
6. Tạo embedding_text từ địa chỉ, phần dẫn và body_text; giữ riêng từng thành phần để kiểm tra.
7. Lưu hash của nội dung, phiên bản node-text-v1, snapshot, graph_hash, Chunk và các khoảng nguồn. source_spans là các khoảng nguồn dùng xác thực/ngữ cảnh, không phải ánh xạ offset từng ký tự của embedding_text. Địa chỉ và nhãn hiển thị là phần định dạng bổ sung.

## Kết quả và giới hạn

611 Điều, 2095 Khoản, 1828 Điểm; không có embedding_text rỗng.
15 bản ghi có embedding_text trên 6000 ký tự sau khi thêm ngữ cảnh; dài nhất 16578 ký tự. Không cắt nội dung và không dùng số ký tự làm giới hạn token. Mọi bản ghi đều cần kiểm tra bằng tokenizer sau khi chọn model.

Khoản/Điểm sử dụng nội dung title đã có. Nếu bảng được parser đặt trực tiếp dưới Điều thay vì dưới Khoản/Điểm, bảng có trong nội dung Điều nhưng không tự được gán sang Khoản/Điểm. Bản ghi Khoản có cảnh báo bảo thủ về giới hạn bảng; cần duyệt các nhánh chứa bảng trước khi khẳng định nội dung đầy đủ cho mọi loại node.

Đầu ra là artifact riêng. File graph, JSONL đầu vào, DOCX và Neo4j không bị sửa.

## Bước tạo vector tiếp theo

Chọn model embedding hỗ trợ tiếng Việt sau đánh giá trên bộ câu hỏi có bằng chứng chuẩn. Dùng tokenizer thật để đo độ dài. Node vượt giới hạn phải chia thành nhiều phần có metadata hoặc dùng một chiến lược tổng hợp được đánh giá; không bật truncation âm thầm. Không coi một vector trung bình là tự động bảo toàn mọi quy định.

Mã hóa embedding_text theo đúng quy ước document của model; mã hóa câu hỏi theo quy ước query của cùng model. Vector có cùng dimension và không gian biểu diễn mới được so sánh. Nếu model yêu cầu prefix hoặc chuẩn hóa vector thì áp dụng đúng cả lúc lập chỉ mục và truy vấn.

Lưu vector cùng model/revision, dimension, phiên bản nội dung và snapshot trong Neo4j; tạo vector index theo bản Neo4j đang dùng. Query vector tìm node ứng viên, sau đó Cypher lấy cha/con/viện dẫn, loại bằng chứng lặp rồi chuyển cho LLM trả lời có nguồn. Câu có địa chỉ pháp lý rõ ràng vẫn dùng tra cứu trực tiếp.

Đánh giá Recall@k của bằng chứng và chất lượng dẫn nguồn; so sánh node vector search với node vector search kết hợp graph traversal trên cùng bộ câu hỏi và ngân sách ngữ cảnh.
