# So sánh embedding node trên development

Đây là thử nghiệm trên bộ nhãn nháp, chưa đánh giá tập test hoặc Neo4j ANN.

| Model | Node | Token/window | Số window | Recall nhóm @1 | @3 | @5 | @10 | Node chính @5 | MRR@10 (1 nhóm) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| e5-small | 4534 | 512 | 4829 | 0.583 | 0.750 | 0.806 | 0.806 | 0.694 | 0.700 |
| minilm | 4534 | 128 | 11167 | 0.389 | 0.611 | 0.694 | 0.694 | 0.389 | 0.565 |

## Theo loại câu hỏi

| Model | Loại | Số câu có đáp án | Recall nhóm @5 | Đủ mọi nhóm @5 |
|---|---|---:|---:|---:|
| e5-small | direct | 3 | 1.000 | 1.000 |
| e5-small | multi | 2 | 0.750 | 0.500 |
| e5-small | natural | 13 | 0.769 | 0.769 |
| minilm | direct | 3 | 1.000 | 1.000 |
| minilm | multi | 2 | 0.250 | 0.000 |
| minilm | natural | 13 | 0.692 | 0.692 |

## Câu chưa lấy đủ bằng chứng ở top 5

### e5-small

- q001: Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không? — thiếu nhóm doc-01/chapter-III/section-1/article-17/clause-1
- q011: Tôi tổ chức đám cưới thì được nghỉ hưởng lương mấy ngày? — thiếu nhóm doc-01/chapter-VII/section-2/article-115/clause-1/point-a
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không? — thiếu nhóm doc-01/chapter-VI/article-98/clause-1/point-b
- q035: Nhà tuyển dụng bắt tôi đặt cọc tiền để bảo đảm thực hiện hợp đồng lao động có được không? — thiếu nhóm doc-01/chapter-III/section-1/article-17/clause-2

### minilm

- q001: Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không? — thiếu nhóm doc-01/chapter-III/section-1/article-17/clause-1
- q011: Tôi tổ chức đám cưới thì được nghỉ hưởng lương mấy ngày? — thiếu nhóm doc-01/chapter-VII/section-2/article-115/clause-1/point-a
- q022: Khi chưa bỏ lương cơ sở thì mức tham chiếu để tính BHXH bằng mức nào? — thiếu nhóm doc-06/chapter-I/article-5/clause-2
- q031: Nghỉ việc có phải hoàn trả chi phí đào tạo không? Cần xem trách nhiệm khi nghỉ trái luật và thỏa thuận đào tạo ở đâu? — thiếu nhóm doc-01/chapter-III/section-3/article-40/clause-3
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không? — thiếu nhóm doc-01/chapter-VI/article-98/clause-1/point-b, doc-08/chapter-II/article-17/clause-2
- q035: Nhà tuyển dụng bắt tôi đặt cọc tiền để bảo đảm thực hiện hợp đồng lao động có được không? — thiếu nhóm doc-01/chapter-III/section-1/article-17/clause-2


## Giao thức và giới hạn

- Tìm trên toàn bộ node Điều/Khoản/Điểm bằng cosine chính xác, không hạn chế ứng viên theo nhãn đáp án.
- Cả hai dùng cửa sổ token chồng lấn, chuẩn hóa vector cửa sổ, lấy trung bình có trọng số token mới rồi chuẩn hóa vector node.
- Đây là so sánh model cùng cấu hình độ dài gốc của từng model, không phải thí nghiệm chỉ thay trọng số model.
- Xem batch_size trong manifest: E5 giảm batch để phù hợp RAM. Không dùng thời gian encode hai lượt khác batch để kết luận tốc độ model trong điều kiện kiểm soát.
- E5 dùng passage: cho node và query: cho câu hỏi. MiniLM không dùng hai tiền tố này.
- Recall nhóm cho phép node tổ tiên nếu chứa nguyên văn bằng chứng; xem thêm node chính để tránh kết quả quá lạc quan.
- Câu multi cần xem all_groups_hit_rate, không chỉ có một đáp án đúng.
- Câu không trả lời được chỉ xuất chẩn đoán top-k; chưa chọn ngưỡng từ chối trên bộ quá nhỏ.
- Thời gian encode trong manifest là thời gian phần chạy của session; nếu resume không phải tổng thời gian từ đầu. Thời gian tải model được ghi riêng.
- Chưa kiểm tra sử dụng RAM đỉnh; chưa có reranker, graph traversal, sinh câu trả lời hoặc ghi Neo4j.
- Các file predictions.json chứa thứ hạng theo từng câu để phân tích lỗi; manifest.json lưu commit model và hash nội dung.

## Nguồn cấu hình model

- https://huggingface.co/intfloat/multilingual-e5-small
- https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
