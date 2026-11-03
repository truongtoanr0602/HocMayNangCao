# Thử nghiệm embedding node

## Chạy lại

```powershell
python -m pip install -r requirements-embedding.txt
python -m legal_kg.embedding_benchmark --model minilm
python -m legal_kg.embedding_benchmark --model e5-small --batch-size 4
python evaluation/summarize_benchmark.py
```

Chạy từ thư mục gốc. Model chạy CPU, mặc định 4 thread, batch 16. Lần đầu tải trọng số công khai từ Hugging Face; nội dung node được xử lý cục bộ, không gửi tới API embedding. Không cần thay mật khẩu hoặc cấu hình Neo4j.

Lượt E5 dùng batch 4 do RAM trống thấp khi chạy với cửa sổ dài; MiniLM dùng batch 16. Điểm truy xuất vẫn so trên cùng candidate/câu hỏi, nhưng thời gian hai lượt không phải so sánh tốc độ có kiểm soát cùng batch.

Chương trình chỉ chấp nhận câu hỏi có split=dev. Không đọc evaluation/test.jsonl. Vector được tạo cho tất cả 4534 node để tập ứng viên giống nhau, không chỉ các node đáp án.

## Phương pháp

1. Xác thực hash embedding_text, graph hash/snapshot câu hỏi và tập ứng viên. Tải model theo snapshot commit đã phân giải, tắt trust_remote_code.
2. Tokenize toàn bộ embedding_text, không cắt phần cuối. Dành chỗ cho special tokens và tiền tố của model.
3. Chia dãy token theo ngân sách thực tế của model, chồng lấn 24 token. Mỗi cửa sổ E5 nhận tiền tố passage:, câu hỏi nhận query:. MiniLM không dùng tiền tố. Native token budget khác nhau giữa hai model, vì vậy kết quả so sánh cấu hình model + xử lý văn bản.
4. Mỗi cửa sổ được model mã hóa thành vector; chuẩn hóa L2 vector cửa sổ. Gộp trung bình có trọng số là số token mới được cửa sổ bao phủ, rồi chuẩn hóa L2 lần nữa để có một vector cho node. Không dùng vector câu hỏi trong quá trình tạo vector node.
5. Trung bình vector là baseline minh bạch, có thể làm loãng một quy định nhỏ trong Điều dài. Cửa sổ được tạo theo toàn bộ embedding_text; phần địa chỉ/phần dẫn không được lặp trên mọi cửa sổ. Truy xuất đa vector hoặc nhắc lại ngữ cảnh là những cấu hình khác cần đánh giá sau.
6. Encode câu hỏi không cắt token. Nếu vượt giới hạn, dừng để xử lý rõ ràng. Cosine được tính bằng tích vô hướng hai vector chuẩn hóa.
7. Tìm top 10 trên toàn bộ node. Thứ tự bằng điểm được xử lý ổn định theo thứ tự candidate. Chưa duyệt graph hoặc dùng reranker để giữ baseline rõ ràng.

Không thể so sánh trực tiếp tọa độ vector giữa hai model dù cùng 384 chiều. Mỗi model có tập vector riêng; câu hỏi phải được mã hóa bởi đúng model tương ứng.

## Đầu ra mỗi model

- `manifest.json`: model ID, commit revision, phiên bản thư viện, hash đầu vào, chính sách gộp, giới hạn token, số cửa sổ và thời gian encode.
- `node_vectors.npy`: ma trận vector node chuẩn hóa; thứ tự hàng nằm trong config.candidate_ids của manifest.
- `checkpoint.npz`: tổng vector trung gian và vị trí tiếp tục. Chỉ tiếp tục khi cache key khớp toàn bộ cấu hình.
- `results.json`: metric tổng hợp và theo loại câu; thời gian tải model, encode query và tìm kiếm.
- `predictions.json`: top 10 node và cosine cho từng câu, gồm câu không trả lời được để phân tích lỗi.

Các file npy/npz được gitignore vì là artifact tái tạo được. Không xóa hoặc ghi vector này vào Neo4j tự động.

## Diễn giải kết quả

Recall nhóm là trung bình theo câu: phần nhóm bằng chứng tìm được ở top k. Node tổ tiên chỉ được chấp nhận nếu bộ nhãn cho phép. Primary-group recall đánh giá khắt khe hơn theo node chính. All-groups hit rate đo tỷ lệ câu lấy đủ bằng chứng, đặc biệt cho câu multi. MRR chỉ tính câu một nhóm bằng chứng và giới hạn top 10.

Câu không trả lời được không tính vào Recall/MRR. Chương trình chưa chọn ngưỡng từ chối, vì 2 câu âm development không đủ để đánh giá chắc chắn. Kết quả luôn có top-k không có nghĩa có đáp án.

Thời gian khi resume chỉ là phần chạy của session được ghi rõ, không được trình bày như tổng thời gian encode. Thời gian query đo theo batch, chưa phải độ trễ một request phục vụ thực tế. Chưa đo RAM đỉnh hoặc benchmark Neo4j ANN.

Nhãn còn ở trạng thái draft_corpus_checked. Kết quả development giúp chọn cấu hình sơ bộ, chưa chứng minh độ chính xác pháp lý hoặc chất lượng trả lời cuối cùng. Không dùng tập test để tinh chỉnh.
