# Test: text Điều v1 và v2

Bộ câu hỏi: 20 câu, split test, hash `d0815078c274`. Sinh tự động bởi `python -m legal_kg.retrieval_eval`.

| Cấu hình | Recall nhóm @1 | @3 | @5 | @10 | Node chính @5 | Đủ mọi nhóm @5 | MRR@10 (1 nhóm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| e5-small | 0.611 | 0.722 | 0.722 | 0.917 | 0.639 | 0.667 | 0.711 |
| e5-small/node-text-v2 | 0.611 | 0.806 | 0.861 | 0.944 | 0.778 | 0.833 | 0.717 |
| e5-base | 0.611 | 0.833 | 0.833 | 1.000 | 0.750 | 0.778 | 0.755 |
| e5-base/node-text-v2 | 0.611 | 0.806 | 0.806 | 0.889 | 0.778 | 0.778 | 0.719 |
| vn-embedding | 0.833 | 0.972 | 1.000 | 1.000 | 0.806 | 1.000 | 0.927 |
| vn-embedding/node-text-v2 | 0.583 | 0.750 | 0.833 | 0.944 | 0.833 | 0.833 | 0.707 |
| bge-m3 | 0.667 | 0.861 | 0.972 | 0.972 | 0.861 | 0.944 | 0.799 |
| bge-m3/node-text-v2 | 0.611 | 0.806 | 0.861 | 0.944 | 0.806 | 0.833 | 0.734 |

## So sánh cặp: group_recall@5, paired bootstrap CI 95%

| A | B | A − B | CI thấp | CI cao | Khác biệt có ý nghĩa |
|---|---|---:|---:|---:|---|
| e5-small | e5-small/node-text-v2 | -0.139 | -0.306 | +0.000 | không |
| e5-small | e5-base | -0.111 | -0.333 | +0.111 | không |
| e5-small | e5-base/node-text-v2 | -0.083 | -0.278 | +0.111 | không |
| e5-small | vn-embedding | -0.278 | -0.472 | -0.111 | có |
| e5-small | vn-embedding/node-text-v2 | -0.111 | -0.306 | +0.083 | không |
| e5-small | bge-m3 | -0.250 | -0.444 | -0.056 | có |
| e5-small | bge-m3/node-text-v2 | -0.139 | -0.361 | +0.056 | không |
| e5-small/node-text-v2 | e5-base | +0.028 | -0.194 | +0.250 | không |
| e5-small/node-text-v2 | e5-base/node-text-v2 | +0.056 | -0.111 | +0.222 | không |
| e5-small/node-text-v2 | vn-embedding | -0.139 | -0.306 | +0.000 | không |
| e5-small/node-text-v2 | vn-embedding/node-text-v2 | +0.028 | -0.167 | +0.222 | không |
| e5-small/node-text-v2 | bge-m3 | -0.111 | -0.278 | +0.000 | không |
| e5-small/node-text-v2 | bge-m3/node-text-v2 | +0.000 | -0.222 | +0.222 | không |
| e5-base | e5-base/node-text-v2 | +0.028 | -0.083 | +0.167 | không |
| e5-base | vn-embedding | -0.167 | -0.333 | -0.028 | có |
| e5-base | vn-embedding/node-text-v2 | +0.000 | -0.194 | +0.222 | không |
| e5-base | bge-m3 | -0.139 | -0.306 | +0.000 | không |
| e5-base | bge-m3/node-text-v2 | -0.028 | -0.194 | +0.139 | không |
| e5-base/node-text-v2 | vn-embedding | -0.194 | -0.389 | -0.056 | có |
| e5-base/node-text-v2 | vn-embedding/node-text-v2 | -0.028 | -0.250 | +0.194 | không |
| e5-base/node-text-v2 | bge-m3 | -0.167 | -0.333 | +0.000 | không |
| e5-base/node-text-v2 | bge-m3/node-text-v2 | -0.056 | -0.222 | +0.111 | không |
| vn-embedding | vn-embedding/node-text-v2 | +0.167 | +0.000 | +0.333 | không |
| vn-embedding | bge-m3 | +0.028 | +0.000 | +0.083 | không |
| vn-embedding | bge-m3/node-text-v2 | +0.139 | +0.000 | +0.306 | không |
| vn-embedding/node-text-v2 | bge-m3 | -0.139 | -0.333 | +0.028 | không |
| vn-embedding/node-text-v2 | bge-m3/node-text-v2 | -0.028 | -0.167 | +0.083 | không |
| bge-m3 | bge-m3/node-text-v2 | +0.111 | +0.000 | +0.278 | không |

## Theo loại câu hỏi

| Cấu hình | Loại | Số câu | Recall nhóm @5 | Node chính @5 | Đủ mọi nhóm @5 |
|---|---|---:|---:|---:|---:|
| e5-small | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-small | multi | 2 | 0.500 | 0.250 | 0.000 |
| e5-small | natural | 13 | 0.692 | 0.615 | 0.692 |
| e5-small/node-text-v2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-small/node-text-v2 | multi | 2 | 0.750 | 0.500 | 0.500 |
| e5-small/node-text-v2 | natural | 13 | 0.846 | 0.769 | 0.846 |
| e5-base | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-base | multi | 2 | 0.500 | 0.250 | 0.000 |
| e5-base | natural | 13 | 0.846 | 0.769 | 0.846 |
| e5-base/node-text-v2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-base/node-text-v2 | multi | 2 | 0.750 | 0.500 | 0.500 |
| e5-base/node-text-v2 | natural | 13 | 0.769 | 0.769 | 0.769 |
| vn-embedding | direct | 3 | 1.000 | 1.000 | 1.000 |
| vn-embedding | multi | 2 | 1.000 | 0.750 | 1.000 |
| vn-embedding | natural | 13 | 1.000 | 0.769 | 1.000 |
| vn-embedding/node-text-v2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| vn-embedding/node-text-v2 | multi | 2 | 1.000 | 1.000 | 1.000 |
| vn-embedding/node-text-v2 | natural | 13 | 0.769 | 0.769 | 0.769 |
| bge-m3 | direct | 3 | 1.000 | 1.000 | 1.000 |
| bge-m3 | multi | 2 | 0.750 | 0.750 | 0.500 |
| bge-m3 | natural | 13 | 1.000 | 0.846 | 1.000 |
| bge-m3/node-text-v2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| bge-m3/node-text-v2 | multi | 2 | 0.750 | 0.750 | 0.500 |
| bge-m3/node-text-v2 | natural | 13 | 0.846 | 0.769 | 0.846 |

## Câu có bằng chứng trong bảng/Phụ lục

| Cấu hình | Số câu | Recall nhóm @5 | Node chính @5 |
|---|---:|---:|---:|
| e5-small | 2 | 0.250 | 0.000 |
| e5-small/node-text-v2 | 2 | 1.000 | 0.750 |
| e5-base | 2 | 0.250 | 0.000 |
| e5-base/node-text-v2 | 2 | 0.500 | 0.250 |
| vn-embedding | 2 | 1.000 | 1.000 |
| vn-embedding/node-text-v2 | 2 | 0.500 | 0.500 |
| bge-m3 | 2 | 1.000 | 1.000 |
| bge-m3/node-text-v2 | 2 | 0.500 | 0.500 |

## Từ chối trả lời theo điểm top-1

Từ chối khi cosine top-1 < ngưỡng. Ngưỡng chọn trên dev: tối đa hóa từ chối đúng với ràng buộc từ chối nhầm câu có đáp án ≤ giới hạn; `—` nghĩa là không từ chối.

| Cấu hình | Ngưỡng | Từ chối đúng | Từ chối nhầm | Câu có đáp án | Câu không trả lời được |
|---|---:|---:|---:|---:|---:|
| e5-small | 0.888 | 1.000 | 0.056 | 18 | 2 |
| e5-small/node-text-v2 | 0.881 | 1.000 | 0.056 | 18 | 2 |
| e5-base | 0.838 | 0.500 | 0.000 | 18 | 2 |
| e5-base/node-text-v2 | 0.834 | 0.500 | 0.000 | 18 | 2 |
| vn-embedding | 0.470 | 1.000 | 0.000 | 18 | 2 |
| vn-embedding/node-text-v2 | 0.442 | 1.000 | 0.000 | 18 | 2 |
| bge-m3 | 0.579 | 0.500 | 0.000 | 18 | 2 |
| bge-m3/node-text-v2 | 0.579 | 0.500 | 0.000 | 18 | 2 |

## Encode

| Model | Thiết bị | Số window | Node nhiều cửa sổ | Token nội dung lớn nhất | RAM đỉnh (MB) | GPU đỉnh (MB) | Giây encode (session) |
|---|---|---:|---:|---:|---:|---:|---:|
| e5-small | Tesla T4 | 4829 | 219 | 4123 | 1985 | 468 | 19 |
| e5-small/node-text-v2 | Tesla T4 | 4588 | 52 | 1086 | 1926 | 473 | 14 |
| e5-base | Tesla T4 | 4829 | 219 | 4123 | 2583 | 1090 | 63 |
| e5-base/node-text-v2 | Tesla T4 | 4588 | 52 | 1086 | 2537 | 1096 | 50 |
| vn-embedding | Tesla T4 | 4534 | 0 | 4123 | 3691 | 2201 | 215 |
| vn-embedding/node-text-v2 | Tesla T4 | 4534 | 0 | 1086 | 3636 | 2201 | 167 |
| bge-m3 | Tesla T4 | 4534 | 0 | 4123 | 3709 | 2201 | 206 |
| bge-m3/node-text-v2 | Tesla T4 | 4534 | 0 | 1086 | 3642 | 2201 | 161 |

## Câu chưa lấy đủ bằng chứng ở top 5

### e5-small

- q004: Đang thử việc mà thấy không phù hợp, tôi có phải báo trước khi nghỉ không?
- q016: Thỏa thuận giữ bí mật kinh doanh có nhất thiết phải nằm ngay trong hợp đồng lao động không?
- q017: Theo Nghị định 293/2025, mức lương tối thiểu tháng và giờ của vùng II là bao nhiêu?
- q021: Nộp hồ sơ BHXH trực tiếp thì cơ quan BHXH có thể xác nhận bản sao sau khi đối chiếu bản chính không?
- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?
- q033: Tuổi nghỉ hưu trong điều kiện bình thường được Bộ luật Lao động quy định theo lộ trình nào và bảng tại Nghị định 135 ghi năm 2026 ra sao?

### e5-small/node-text-v2

- q004: Đang thử việc mà thấy không phù hợp, tôi có phải báo trước khi nghỉ không?
- q016: Thỏa thuận giữ bí mật kinh doanh có nhất thiết phải nằm ngay trong hợp đồng lao động không?
- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?

### e5-base

- q005: Tôi làm hợp đồng không xác định thời hạn, muốn nghỉ việc thì thường phải báo trước mấy ngày?
- q017: Theo Nghị định 293/2025, mức lương tối thiểu tháng và giờ của vùng II là bao nhiêu?
- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?
- q033: Tuổi nghỉ hưu trong điều kiện bình thường được Bộ luật Lao động quy định theo lộ trình nào và bảng tại Nghị định 135 ghi năm 2026 ra sao?

### e5-base/node-text-v2

- q004: Đang thử việc mà thấy không phù hợp, tôi có phải báo trước khi nghỉ không?
- q005: Tôi làm hợp đồng không xác định thời hạn, muốn nghỉ việc thì thường phải báo trước mấy ngày?
- q017: Theo Nghị định 293/2025, mức lương tối thiểu tháng và giờ của vùng II là bao nhiêu?
- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?

### vn-embedding

- (không có)

### vn-embedding/node-text-v2

- q007: Nếu công ty bố trí giờ làm theo ngày thì giờ làm bình thường tối đa bao nhiêu một ngày và một tuần?
- q016: Thỏa thuận giữ bí mật kinh doanh có nhất thiết phải nằm ngay trong hợp đồng lao động không?
- q017: Theo Nghị định 293/2025, mức lương tối thiểu tháng và giờ của vùng II là bao nhiêu?

### bge-m3

- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?

### bge-m3/node-text-v2

- q007: Nếu công ty bố trí giờ làm theo ngày thì giờ làm bình thường tối đa bao nhiêu một ngày và một tuần?
- q017: Theo Nghị định 293/2025, mức lương tối thiểu tháng và giờ của vùng II là bao nhiêu?
- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?

## Giao thức

- Tìm trên toàn bộ node Điều/Khoản/Điểm; chỉ dùng KG và embedding node, không BM25, không embed chunk.
- Recall nhóm cho phép node tổ tiên nếu chứa nguyên văn bằng chứng; node chính là chỉ số khắt khe hơn.
- Câu không trả lời được không tính vào Recall/MRR; chỉ dùng cho ngưỡng từ chối.
- CI 95% là paired bootstrap trên cùng câu hỏi, 10.000 mẫu, seed cố định.
- Nhãn do nhóm biên soạn và duyệt, chưa phải thẩm định của chuyên gia pháp lý.
- Nhãn v2: thêm 12 node đúng từ pooling mù; 2 do người duyệt tự quyết, 10 do người xác nhận nháp Claude. Nháp chưa xác nhận không bao giờ thành nhãn (xem `evaluation/summary.json`).
