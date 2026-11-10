# P1 / P2 / router+P2 trên development (ngân sách 10 node, 12.000 ký tự; nhãn v1, tạm thời)

Bộ câu hỏi: 20 câu, split dev, hash `6f737bb26c61`. Sinh tự động bởi `python -m legal_kg.retrieval_eval`.

| Cấu hình | Recall nhóm @1 | @3 | @5 | @10 | Node chính @5 | Đủ mọi nhóm @5 | MRR@10 (1 nhóm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| e5-small/p1-budget | 0.583 | 0.806 | 0.806 | 0.861 | 0.750 | 0.778 | 0.719 |
| e5-small/p2 | 0.583 | 0.750 | 0.806 | 0.861 | 0.750 | 0.778 | 0.714 |
| e5-small/router-p2 | 0.583 | 0.750 | 0.806 | 0.861 | 0.750 | 0.778 | 0.714 |
| e5-base/p1-budget | 0.583 | 0.833 | 0.833 | 0.889 | 0.750 | 0.833 | 0.749 |
| e5-base/p2 | 0.583 | 0.833 | 0.833 | 0.917 | 0.750 | 0.833 | 0.750 |
| e5-base/router-p2 | 0.583 | 0.833 | 0.833 | 0.917 | 0.806 | 0.833 | 0.750 |
| vn-embedding/p1-budget | 0.833 | 0.972 | 1.000 | 1.000 | 0.917 | 1.000 | 0.938 |
| vn-embedding/p2 | 0.833 | 0.972 | 1.000 | 1.000 | 0.917 | 1.000 | 0.938 |
| vn-embedding/router-p2 | 0.889 | 0.972 | 1.000 | 1.000 | 0.917 | 1.000 | 0.969 |
| bge-m3/p1-budget | 0.639 | 0.889 | 0.889 | 0.972 | 0.861 | 0.889 | 0.812 |
| bge-m3/p2 | 0.639 | 0.889 | 0.889 | 0.917 | 0.861 | 0.889 | 0.802 |
| bge-m3/router-p2 | 0.694 | 0.944 | 0.944 | 0.972 | 0.917 | 0.944 | 0.865 |

## So sánh cặp: group_recall@5, paired bootstrap CI 95%

| A | B | A − B | CI thấp | CI cao | Khác biệt có ý nghĩa |
|---|---|---:|---:|---:|---|
| e5-small/p1-budget | e5-small/p2 | +0.000 | +0.000 | +0.000 | không |
| e5-small/p1-budget | e5-small/router-p2 | +0.000 | +0.000 | +0.000 | không |
| e5-small/p1-budget | e5-base/p1-budget | -0.028 | -0.167 | +0.083 | không |
| e5-small/p1-budget | e5-base/p2 | -0.028 | -0.167 | +0.083 | không |
| e5-small/p1-budget | e5-base/router-p2 | -0.028 | -0.167 | +0.083 | không |
| e5-small/p1-budget | vn-embedding/p1-budget | -0.194 | -0.389 | -0.055 | có |
| e5-small/p1-budget | vn-embedding/p2 | -0.194 | -0.389 | -0.055 | có |
| e5-small/p1-budget | vn-embedding/router-p2 | -0.194 | -0.389 | -0.055 | có |
| e5-small/p1-budget | bge-m3/p1-budget | -0.083 | -0.306 | +0.139 | không |
| e5-small/p1-budget | bge-m3/p2 | -0.083 | -0.306 | +0.139 | không |
| e5-small/p1-budget | bge-m3/router-p2 | -0.139 | -0.333 | +0.028 | không |
| e5-small/p2 | e5-small/router-p2 | +0.000 | +0.000 | +0.000 | không |
| e5-small/p2 | e5-base/p1-budget | -0.028 | -0.167 | +0.083 | không |
| e5-small/p2 | e5-base/p2 | -0.028 | -0.167 | +0.083 | không |
| e5-small/p2 | e5-base/router-p2 | -0.028 | -0.167 | +0.083 | không |
| e5-small/p2 | vn-embedding/p1-budget | -0.194 | -0.389 | -0.055 | có |
| e5-small/p2 | vn-embedding/p2 | -0.194 | -0.389 | -0.055 | có |
| e5-small/p2 | vn-embedding/router-p2 | -0.194 | -0.389 | -0.055 | có |
| e5-small/p2 | bge-m3/p1-budget | -0.083 | -0.306 | +0.139 | không |
| e5-small/p2 | bge-m3/p2 | -0.083 | -0.306 | +0.139 | không |
| e5-small/p2 | bge-m3/router-p2 | -0.139 | -0.333 | +0.028 | không |
| e5-small/router-p2 | e5-base/p1-budget | -0.028 | -0.167 | +0.083 | không |
| e5-small/router-p2 | e5-base/p2 | -0.028 | -0.167 | +0.083 | không |
| e5-small/router-p2 | e5-base/router-p2 | -0.028 | -0.167 | +0.083 | không |
| e5-small/router-p2 | vn-embedding/p1-budget | -0.194 | -0.389 | -0.055 | có |
| e5-small/router-p2 | vn-embedding/p2 | -0.194 | -0.389 | -0.055 | có |
| e5-small/router-p2 | vn-embedding/router-p2 | -0.194 | -0.389 | -0.055 | có |
| e5-small/router-p2 | bge-m3/p1-budget | -0.083 | -0.306 | +0.139 | không |
| e5-small/router-p2 | bge-m3/p2 | -0.083 | -0.306 | +0.139 | không |
| e5-small/router-p2 | bge-m3/router-p2 | -0.139 | -0.333 | +0.028 | không |
| e5-base/p1-budget | e5-base/p2 | +0.000 | +0.000 | +0.000 | không |
| e5-base/p1-budget | e5-base/router-p2 | +0.000 | +0.000 | +0.000 | không |
| e5-base/p1-budget | vn-embedding/p1-budget | -0.167 | -0.333 | +0.000 | không |
| e5-base/p1-budget | vn-embedding/p2 | -0.167 | -0.333 | +0.000 | không |
| e5-base/p1-budget | vn-embedding/router-p2 | -0.167 | -0.333 | +0.000 | không |
| e5-base/p1-budget | bge-m3/p1-budget | -0.056 | -0.222 | +0.111 | không |
| e5-base/p1-budget | bge-m3/p2 | -0.056 | -0.222 | +0.111 | không |
| e5-base/p1-budget | bge-m3/router-p2 | -0.111 | -0.278 | +0.000 | không |
| e5-base/p2 | e5-base/router-p2 | +0.000 | +0.000 | +0.000 | không |
| e5-base/p2 | vn-embedding/p1-budget | -0.167 | -0.333 | +0.000 | không |
| e5-base/p2 | vn-embedding/p2 | -0.167 | -0.333 | +0.000 | không |
| e5-base/p2 | vn-embedding/router-p2 | -0.167 | -0.333 | +0.000 | không |
| e5-base/p2 | bge-m3/p1-budget | -0.056 | -0.222 | +0.111 | không |
| e5-base/p2 | bge-m3/p2 | -0.056 | -0.222 | +0.111 | không |
| e5-base/p2 | bge-m3/router-p2 | -0.111 | -0.278 | +0.000 | không |
| e5-base/router-p2 | vn-embedding/p1-budget | -0.167 | -0.333 | +0.000 | không |
| e5-base/router-p2 | vn-embedding/p2 | -0.167 | -0.333 | +0.000 | không |
| e5-base/router-p2 | vn-embedding/router-p2 | -0.167 | -0.333 | +0.000 | không |
| e5-base/router-p2 | bge-m3/p1-budget | -0.056 | -0.222 | +0.111 | không |
| e5-base/router-p2 | bge-m3/p2 | -0.056 | -0.222 | +0.111 | không |
| e5-base/router-p2 | bge-m3/router-p2 | -0.111 | -0.278 | +0.000 | không |
| vn-embedding/p1-budget | vn-embedding/p2 | +0.000 | +0.000 | +0.000 | không |
| vn-embedding/p1-budget | vn-embedding/router-p2 | +0.000 | +0.000 | +0.000 | không |
| vn-embedding/p1-budget | bge-m3/p1-budget | +0.111 | +0.000 | +0.278 | không |
| vn-embedding/p1-budget | bge-m3/p2 | +0.111 | +0.000 | +0.278 | không |
| vn-embedding/p1-budget | bge-m3/router-p2 | +0.056 | +0.000 | +0.167 | không |
| vn-embedding/p2 | vn-embedding/router-p2 | +0.000 | +0.000 | +0.000 | không |
| vn-embedding/p2 | bge-m3/p1-budget | +0.111 | +0.000 | +0.278 | không |
| vn-embedding/p2 | bge-m3/p2 | +0.111 | +0.000 | +0.278 | không |
| vn-embedding/p2 | bge-m3/router-p2 | +0.056 | +0.000 | +0.167 | không |
| vn-embedding/router-p2 | bge-m3/p1-budget | +0.111 | +0.000 | +0.278 | không |
| vn-embedding/router-p2 | bge-m3/p2 | +0.111 | +0.000 | +0.278 | không |
| vn-embedding/router-p2 | bge-m3/router-p2 | +0.056 | +0.000 | +0.167 | không |
| bge-m3/p1-budget | bge-m3/p2 | +0.000 | +0.000 | +0.000 | không |
| bge-m3/p1-budget | bge-m3/router-p2 | -0.056 | -0.167 | +0.000 | không |
| bge-m3/p2 | bge-m3/router-p2 | -0.056 | -0.167 | +0.000 | không |

## Theo loại câu hỏi

| Cấu hình | Loại | Số câu | Recall nhóm @5 | Node chính @5 | Đủ mọi nhóm @5 |
|---|---|---:|---:|---:|---:|
| e5-small/p1-budget | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-small/p1-budget | multi | 2 | 0.750 | 0.250 | 0.500 |
| e5-small/p1-budget | natural | 13 | 0.769 | 0.769 | 0.769 |
| e5-small/p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-small/p2 | multi | 2 | 0.750 | 0.250 | 0.500 |
| e5-small/p2 | natural | 13 | 0.769 | 0.769 | 0.769 |
| e5-small/router-p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-small/router-p2 | multi | 2 | 0.750 | 0.250 | 0.500 |
| e5-small/router-p2 | natural | 13 | 0.769 | 0.769 | 0.769 |
| e5-base/p1-budget | direct | 3 | 1.000 | 0.667 | 1.000 |
| e5-base/p1-budget | multi | 2 | 0.500 | 0.250 | 0.500 |
| e5-base/p1-budget | natural | 13 | 0.846 | 0.846 | 0.846 |
| e5-base/p2 | direct | 3 | 1.000 | 0.667 | 1.000 |
| e5-base/p2 | multi | 2 | 0.500 | 0.250 | 0.500 |
| e5-base/p2 | natural | 13 | 0.846 | 0.846 | 0.846 |
| e5-base/router-p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-base/router-p2 | multi | 2 | 0.500 | 0.250 | 0.500 |
| e5-base/router-p2 | natural | 13 | 0.846 | 0.846 | 0.846 |
| vn-embedding/p1-budget | direct | 3 | 1.000 | 1.000 | 1.000 |
| vn-embedding/p1-budget | multi | 2 | 1.000 | 0.250 | 1.000 |
| vn-embedding/p1-budget | natural | 13 | 1.000 | 1.000 | 1.000 |
| vn-embedding/p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| vn-embedding/p2 | multi | 2 | 1.000 | 0.250 | 1.000 |
| vn-embedding/p2 | natural | 13 | 1.000 | 1.000 | 1.000 |
| vn-embedding/router-p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| vn-embedding/router-p2 | multi | 2 | 1.000 | 0.250 | 1.000 |
| vn-embedding/router-p2 | natural | 13 | 1.000 | 1.000 | 1.000 |
| bge-m3/p1-budget | direct | 3 | 0.667 | 0.667 | 0.667 |
| bge-m3/p1-budget | multi | 2 | 0.500 | 0.250 | 0.500 |
| bge-m3/p1-budget | natural | 13 | 1.000 | 1.000 | 1.000 |
| bge-m3/p2 | direct | 3 | 0.667 | 0.667 | 0.667 |
| bge-m3/p2 | multi | 2 | 0.500 | 0.250 | 0.500 |
| bge-m3/p2 | natural | 13 | 1.000 | 1.000 | 1.000 |
| bge-m3/router-p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| bge-m3/router-p2 | multi | 2 | 0.500 | 0.250 | 0.500 |
| bge-m3/router-p2 | natural | 13 | 1.000 | 1.000 | 1.000 |

## Từ chối trả lời theo điểm top-1

Từ chối khi cosine top-1 < ngưỡng. Ngưỡng chọn trên dev: tối đa hóa từ chối đúng với ràng buộc từ chối nhầm câu có đáp án ≤ giới hạn; `—` nghĩa là không từ chối.

| Cấu hình | Ngưỡng | Từ chối đúng | Từ chối nhầm | Câu có đáp án | Câu không trả lời được |
|---|---:|---:|---:|---:|---:|
| e5-small/p1-budget | 0.888 | 1.000 | 0.056 | 18 | 2 |
| e5-small/p2 | 0.888 | 1.000 | 0.056 | 18 | 2 |
| e5-small/router-p2 | 0.888 | 1.000 | 0.056 | 18 | 2 |
| e5-base/p1-budget | 0.838 | 1.000 | 0.000 | 18 | 2 |
| e5-base/p2 | 0.838 | 1.000 | 0.000 | 18 | 2 |
| e5-base/router-p2 | 0.838 | 1.000 | 0.000 | 18 | 2 |
| vn-embedding/p1-budget | 0.470 | 1.000 | 0.056 | 18 | 2 |
| vn-embedding/p2 | 0.470 | 1.000 | 0.056 | 18 | 2 |
| vn-embedding/router-p2 | 0.470 | 1.000 | 0.056 | 18 | 2 |
| bge-m3/p1-budget | 0.579 | 1.000 | 0.000 | 18 | 2 |
| bge-m3/p2 | 0.579 | 1.000 | 0.000 | 18 | 2 |
| bge-m3/router-p2 | 0.579 | 1.000 | 0.000 | 18 | 2 |

## Câu chưa lấy đủ bằng chứng ở top 5

### e5-small/p1-budget

- q001: Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không?
- q006: Làm thêm vào ngày nghỉ hằng tuần thì tiền lương ít nhất bằng bao nhiêu phần trăm?
- q011: Tôi tổ chức đám cưới thì được nghỉ hưởng lương mấy ngày?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### e5-small/p2

- q001: Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không?
- q006: Làm thêm vào ngày nghỉ hằng tuần thì tiền lương ít nhất bằng bao nhiêu phần trăm?
- q011: Tôi tổ chức đám cưới thì được nghỉ hưởng lương mấy ngày?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### e5-small/router-p2

- q001: Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không?
- q006: Làm thêm vào ngày nghỉ hằng tuần thì tiền lương ít nhất bằng bao nhiêu phần trăm?
- q011: Tôi tổ chức đám cưới thì được nghỉ hưởng lương mấy ngày?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### e5-base/p1-budget

- q001: Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không?
- q006: Làm thêm vào ngày nghỉ hằng tuần thì tiền lương ít nhất bằng bao nhiêu phần trăm?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### e5-base/p2

- q001: Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không?
- q006: Làm thêm vào ngày nghỉ hằng tuần thì tiền lương ít nhất bằng bao nhiêu phần trăm?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### e5-base/router-p2

- q001: Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không?
- q006: Làm thêm vào ngày nghỉ hằng tuần thì tiền lương ít nhất bằng bao nhiêu phần trăm?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### vn-embedding/p1-budget

- (không có)

### vn-embedding/p2

- (không có)

### vn-embedding/router-p2

- (không có)

### bge-m3/p1-budget

- q029: Điểm b khoản 1 Điều 52 Luật BHXH 2024 quy định số ngày nghỉ tối đa khi thai từ đủ 5 đến dưới 13 tuần như thế nào?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### bge-m3/p2

- q029: Điểm b khoản 1 Điều 52 Luật BHXH 2024 quy định số ngày nghỉ tối đa khi thai từ đủ 5 đến dưới 13 tuần như thế nào?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### bge-m3/router-p2

- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

## Giao thức

- Tìm trên toàn bộ node Điều/Khoản/Điểm; chỉ dùng KG và embedding node, không BM25, không embed chunk.
- Recall nhóm cho phép node tổ tiên nếu chứa nguyên văn bằng chứng; node chính là chỉ số khắt khe hơn.
- Câu không trả lời được không tính vào Recall/MRR; chỉ dùng cho ngưỡng từ chối.
- CI 95% là paired bootstrap trên cùng câu hỏi, 10.000 mẫu, seed cố định.
- Nhãn do nhóm biên soạn và duyệt, chưa phải thẩm định của chuyên gia pháp lý.
