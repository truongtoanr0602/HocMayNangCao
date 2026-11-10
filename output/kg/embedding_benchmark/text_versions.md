# Text Điều v1 và v2 trên development (nhãn v1, tạm thời)

Bộ câu hỏi: 20 câu, split dev, hash `6f737bb26c61`. Sinh tự động bởi `python -m legal_kg.retrieval_eval`.

| Cấu hình | Recall nhóm @1 | @3 | @5 | @10 | Node chính @5 | Đủ mọi nhóm @5 | MRR@10 (1 nhóm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| e5-small | 0.583 | 0.750 | 0.750 | 0.806 | 0.694 | 0.722 | 0.698 |
| e5-small/node-text-v2 | 0.583 | 0.778 | 0.833 | 0.917 | 0.778 | 0.833 | 0.733 |
| e5-base | 0.583 | 0.833 | 0.833 | 0.917 | 0.750 | 0.833 | 0.738 |
| e5-base/node-text-v2 | 0.583 | 0.833 | 0.889 | 0.889 | 0.778 | 0.889 | 0.752 |
| vn-embedding | 0.833 | 0.972 | 1.000 | 1.000 | 0.917 | 1.000 | 0.938 |
| vn-embedding/node-text-v2 | 0.750 | 0.972 | 0.972 | 1.000 | 0.972 | 0.944 | 0.906 |
| bge-m3 | 0.639 | 0.889 | 0.889 | 0.972 | 0.861 | 0.889 | 0.812 |
| bge-m3/node-text-v2 | 0.639 | 0.889 | 0.889 | 0.972 | 0.861 | 0.889 | 0.823 |

## So sánh cặp: group_recall@5, paired bootstrap CI 95%

| A | B | A − B | CI thấp | CI cao | Khác biệt có ý nghĩa |
|---|---|---:|---:|---:|---|
| e5-small | e5-small/node-text-v2 | -0.083 | -0.250 | +0.056 | không |
| e5-small | e5-base | -0.083 | -0.250 | +0.056 | không |
| e5-small | e5-base/node-text-v2 | -0.139 | -0.333 | +0.028 | không |
| e5-small | vn-embedding | -0.250 | -0.444 | -0.056 | có |
| e5-small | vn-embedding/node-text-v2 | -0.222 | -0.444 | -0.056 | có |
| e5-small | bge-m3 | -0.139 | -0.389 | +0.083 | không |
| e5-small | bge-m3/node-text-v2 | -0.139 | -0.389 | +0.083 | không |
| e5-small/node-text-v2 | e5-base | +0.000 | -0.167 | +0.167 | không |
| e5-small/node-text-v2 | e5-base/node-text-v2 | -0.056 | -0.167 | +0.000 | không |
| e5-small/node-text-v2 | vn-embedding | -0.167 | -0.333 | +0.000 | không |
| e5-small/node-text-v2 | vn-embedding/node-text-v2 | -0.139 | -0.306 | +0.000 | không |
| e5-small/node-text-v2 | bge-m3 | -0.056 | -0.222 | +0.111 | không |
| e5-small/node-text-v2 | bge-m3/node-text-v2 | -0.056 | -0.222 | +0.111 | không |
| e5-base | e5-base/node-text-v2 | -0.056 | -0.167 | +0.000 | không |
| e5-base | vn-embedding | -0.167 | -0.333 | +0.000 | không |
| e5-base | vn-embedding/node-text-v2 | -0.139 | -0.306 | +0.000 | không |
| e5-base | bge-m3 | -0.056 | -0.222 | +0.111 | không |
| e5-base | bge-m3/node-text-v2 | -0.056 | -0.222 | +0.111 | không |
| e5-base/node-text-v2 | vn-embedding | -0.111 | -0.278 | +0.000 | không |
| e5-base/node-text-v2 | vn-embedding/node-text-v2 | -0.083 | -0.222 | +0.000 | không |
| e5-base/node-text-v2 | bge-m3 | +0.000 | -0.167 | +0.167 | không |
| e5-base/node-text-v2 | bge-m3/node-text-v2 | +0.000 | -0.167 | +0.167 | không |
| vn-embedding | vn-embedding/node-text-v2 | +0.028 | +0.000 | +0.083 | không |
| vn-embedding | bge-m3 | +0.111 | +0.000 | +0.278 | không |
| vn-embedding | bge-m3/node-text-v2 | +0.111 | +0.000 | +0.278 | không |
| vn-embedding/node-text-v2 | bge-m3 | +0.083 | +0.000 | +0.222 | không |
| vn-embedding/node-text-v2 | bge-m3/node-text-v2 | +0.083 | +0.000 | +0.222 | không |
| bge-m3 | bge-m3/node-text-v2 | +0.000 | +0.000 | +0.000 | không |

## Theo loại câu hỏi

| Cấu hình | Loại | Số câu | Recall nhóm @5 | Node chính @5 | Đủ mọi nhóm @5 |
|---|---|---:|---:|---:|---:|
| e5-small | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-small | multi | 2 | 0.750 | 0.250 | 0.500 |
| e5-small | natural | 13 | 0.692 | 0.692 | 0.692 |
| e5-small/node-text-v2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-small/node-text-v2 | multi | 2 | 0.500 | 0.500 | 0.500 |
| e5-small/node-text-v2 | natural | 13 | 0.846 | 0.769 | 0.846 |
| e5-base | direct | 3 | 1.000 | 0.667 | 1.000 |
| e5-base | multi | 2 | 0.500 | 0.250 | 0.500 |
| e5-base | natural | 13 | 0.846 | 0.846 | 0.846 |
| e5-base/node-text-v2 | direct | 3 | 1.000 | 0.667 | 1.000 |
| e5-base/node-text-v2 | multi | 2 | 0.500 | 0.500 | 0.500 |
| e5-base/node-text-v2 | natural | 13 | 0.923 | 0.846 | 0.923 |
| vn-embedding | direct | 3 | 1.000 | 1.000 | 1.000 |
| vn-embedding | multi | 2 | 1.000 | 0.250 | 1.000 |
| vn-embedding | natural | 13 | 1.000 | 1.000 | 1.000 |
| vn-embedding/node-text-v2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| vn-embedding/node-text-v2 | multi | 2 | 0.750 | 0.750 | 0.500 |
| vn-embedding/node-text-v2 | natural | 13 | 1.000 | 1.000 | 1.000 |
| bge-m3 | direct | 3 | 0.667 | 0.667 | 0.667 |
| bge-m3 | multi | 2 | 0.500 | 0.250 | 0.500 |
| bge-m3 | natural | 13 | 1.000 | 1.000 | 1.000 |
| bge-m3/node-text-v2 | direct | 3 | 0.667 | 0.667 | 0.667 |
| bge-m3/node-text-v2 | multi | 2 | 0.500 | 0.250 | 0.500 |
| bge-m3/node-text-v2 | natural | 13 | 1.000 | 1.000 | 1.000 |

## Từ chối trả lời theo điểm top-1

Từ chối khi cosine top-1 < ngưỡng. Ngưỡng chọn trên dev: tối đa hóa từ chối đúng với ràng buộc từ chối nhầm câu có đáp án ≤ giới hạn; `—` nghĩa là không từ chối.

| Cấu hình | Ngưỡng | Từ chối đúng | Từ chối nhầm | Câu có đáp án | Câu không trả lời được |
|---|---:|---:|---:|---:|---:|
| e5-small | 0.888 | 1.000 | 0.056 | 18 | 2 |
| e5-small/node-text-v2 | 0.881 | 1.000 | 0.056 | 18 | 2 |
| e5-base | 0.838 | 1.000 | 0.000 | 18 | 2 |
| e5-base/node-text-v2 | 0.834 | 1.000 | 0.000 | 18 | 2 |
| vn-embedding | 0.470 | 1.000 | 0.056 | 18 | 2 |
| vn-embedding/node-text-v2 | 0.442 | 1.000 | 0.000 | 18 | 2 |
| bge-m3 | 0.579 | 1.000 | 0.000 | 18 | 2 |
| bge-m3/node-text-v2 | 0.579 | 1.000 | 0.000 | 18 | 2 |

## Encode

| Model | Thiết bị | Số window | Node nhiều cửa sổ | Token nội dung lớn nhất | RAM đỉnh (MB) | GPU đỉnh (MB) | Giây encode (session) |
|---|---|---:|---:|---:|---:|---:|---:|
| e5-small | Tesla T4 | 4829 | 219 | 4123 | 1930 | 729 | 19 |
| e5-small/node-text-v2 | Tesla T4 | 4588 | 52 | 1086 | 1926 | 471 | 14 |
| e5-base | Tesla T4 | 4829 | 219 | 4123 | 2539 | 1605 | 62 |
| e5-base/node-text-v2 | Tesla T4 | 4588 | 52 | 1086 | 2538 | 1605 | 50 |
| vn-embedding | Tesla T4 | 4534 | 0 | 4123 | 3690 | 2902 | 215 |
| vn-embedding/node-text-v2 | Tesla T4 | 4534 | 0 | 1086 | 3638 | 2725 | 167 |
| bge-m3 | Tesla T4 | 4534 | 0 | 4123 | 3709 | 2902 | 206 |
| bge-m3/node-text-v2 | Tesla T4 | 4534 | 0 | 1086 | 3645 | 2725 | 161 |

## Câu chưa lấy đủ bằng chứng ở top 5

### e5-small

- q001: Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không?
- q006: Làm thêm vào ngày nghỉ hằng tuần thì tiền lương ít nhất bằng bao nhiêu phần trăm?
- q011: Tôi tổ chức đám cưới thì được nghỉ hưởng lương mấy ngày?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?
- q035: Nhà tuyển dụng bắt tôi đặt cọc tiền để bảo đảm thực hiện hợp đồng lao động có được không?

### e5-small/node-text-v2

- q001: Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không?
- q011: Tôi tổ chức đám cưới thì được nghỉ hưởng lương mấy ngày?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### e5-base

- q001: Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không?
- q006: Làm thêm vào ngày nghỉ hằng tuần thì tiền lương ít nhất bằng bao nhiêu phần trăm?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### e5-base/node-text-v2

- q001: Công ty yêu cầu giữ bản gốc bằng đại học khi nhận việc có được không?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### vn-embedding

- (không có)

### vn-embedding/node-text-v2

- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### bge-m3

- q029: Điểm b khoản 1 Điều 52 Luật BHXH 2024 quy định số ngày nghỉ tối đa khi thai từ đủ 5 đến dưới 13 tuần như thế nào?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

### bge-m3/node-text-v2

- q029: Điểm b khoản 1 Điều 52 Luật BHXH 2024 quy định số ngày nghỉ tối đa khi thai từ đủ 5 đến dưới 13 tuần như thế nào?
- q034: Quy định trả lương làm thêm ngày nghỉ hằng tuần nằm ở đâu và Nghị định 12 có quy định xử phạt việc trả thiếu lương làm thêm không?

## Giao thức

- Tìm trên toàn bộ node Điều/Khoản/Điểm; chỉ dùng KG và embedding node, không BM25, không embed chunk.
- Recall nhóm cho phép node tổ tiên nếu chứa nguyên văn bằng chứng; node chính là chỉ số khắt khe hơn.
- Câu không trả lời được không tính vào Recall/MRR; chỉ dùng cho ngưỡng từ chối.
- CI 95% là paired bootstrap trên cùng câu hỏi, 10.000 mẫu, seed cố định.
- Nhãn do nhóm biên soạn và duyệt, chưa phải thẩm định của chuyên gia pháp lý.
