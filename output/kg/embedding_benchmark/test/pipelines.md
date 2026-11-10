# Test: P1 / P2 / router+P2 (ngân sách 10 node, 12.000 ký tự)

Bộ câu hỏi: 20 câu, split test, hash `d0815078c274`. Sinh tự động bởi `python -m legal_kg.retrieval_eval`.

| Cấu hình | Recall nhóm @1 | @3 | @5 | @10 | Node chính @5 | Đủ mọi nhóm @5 | MRR@10 (1 nhóm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| e5-small/p1-budget | 0.611 | 0.722 | 0.722 | 0.861 | 0.639 | 0.667 | 0.705 |
| e5-small/p2 | 0.611 | 0.722 | 0.778 | 0.944 | 0.639 | 0.722 | 0.721 |
| e5-small/router-p2 | 0.611 | 0.722 | 0.778 | 0.944 | 0.639 | 0.722 | 0.721 |
| e5-base/p1-budget | 0.611 | 0.833 | 0.833 | 1.000 | 0.750 | 0.778 | 0.767 |
| e5-base/p2 | 0.611 | 0.833 | 0.833 | 0.944 | 0.750 | 0.778 | 0.760 |
| e5-base/router-p2 | 0.611 | 0.833 | 0.833 | 0.944 | 0.750 | 0.778 | 0.760 |
| vn-embedding/p1-budget | 0.833 | 0.972 | 1.000 | 1.000 | 0.806 | 1.000 | 0.927 |
| vn-embedding/p2 | 0.833 | 0.972 | 1.000 | 1.000 | 0.806 | 1.000 | 0.927 |
| vn-embedding/router-p2 | 0.833 | 0.972 | 1.000 | 1.000 | 0.806 | 1.000 | 0.927 |
| bge-m3/p1-budget | 0.667 | 0.861 | 0.972 | 0.972 | 0.861 | 0.944 | 0.799 |
| bge-m3/p2 | 0.667 | 0.861 | 0.972 | 1.000 | 0.861 | 0.944 | 0.799 |
| bge-m3/router-p2 | 0.667 | 0.861 | 0.972 | 1.000 | 0.861 | 0.944 | 0.799 |

## So sánh cặp: group_recall@5, paired bootstrap CI 95%

| A | B | A − B | CI thấp | CI cao | Khác biệt có ý nghĩa |
|---|---|---:|---:|---:|---|
| e5-small/p1-budget | e5-small/p2 | -0.056 | -0.167 | +0.000 | không |
| e5-small/p1-budget | e5-small/router-p2 | -0.056 | -0.167 | +0.000 | không |
| e5-small/p1-budget | e5-base/p1-budget | -0.111 | -0.333 | +0.111 | không |
| e5-small/p1-budget | e5-base/p2 | -0.111 | -0.333 | +0.111 | không |
| e5-small/p1-budget | e5-base/router-p2 | -0.111 | -0.333 | +0.111 | không |
| e5-small/p1-budget | vn-embedding/p1-budget | -0.278 | -0.472 | -0.111 | có |
| e5-small/p1-budget | vn-embedding/p2 | -0.278 | -0.472 | -0.111 | có |
| e5-small/p1-budget | vn-embedding/router-p2 | -0.278 | -0.472 | -0.111 | có |
| e5-small/p1-budget | bge-m3/p1-budget | -0.250 | -0.444 | -0.056 | có |
| e5-small/p1-budget | bge-m3/p2 | -0.250 | -0.444 | -0.056 | có |
| e5-small/p1-budget | bge-m3/router-p2 | -0.250 | -0.444 | -0.056 | có |
| e5-small/p2 | e5-small/router-p2 | +0.000 | +0.000 | +0.000 | không |
| e5-small/p2 | e5-base/p1-budget | -0.056 | -0.222 | +0.111 | không |
| e5-small/p2 | e5-base/p2 | -0.056 | -0.222 | +0.111 | không |
| e5-small/p2 | e5-base/router-p2 | -0.056 | -0.222 | +0.111 | không |
| e5-small/p2 | vn-embedding/p1-budget | -0.222 | -0.417 | -0.056 | có |
| e5-small/p2 | vn-embedding/p2 | -0.222 | -0.417 | -0.056 | có |
| e5-small/p2 | vn-embedding/router-p2 | -0.222 | -0.417 | -0.056 | có |
| e5-small/p2 | bge-m3/p1-budget | -0.194 | -0.389 | -0.028 | có |
| e5-small/p2 | bge-m3/p2 | -0.194 | -0.389 | -0.028 | có |
| e5-small/p2 | bge-m3/router-p2 | -0.194 | -0.389 | -0.028 | có |
| e5-small/router-p2 | e5-base/p1-budget | -0.056 | -0.222 | +0.111 | không |
| e5-small/router-p2 | e5-base/p2 | -0.056 | -0.222 | +0.111 | không |
| e5-small/router-p2 | e5-base/router-p2 | -0.056 | -0.222 | +0.111 | không |
| e5-small/router-p2 | vn-embedding/p1-budget | -0.222 | -0.417 | -0.056 | có |
| e5-small/router-p2 | vn-embedding/p2 | -0.222 | -0.417 | -0.056 | có |
| e5-small/router-p2 | vn-embedding/router-p2 | -0.222 | -0.417 | -0.056 | có |
| e5-small/router-p2 | bge-m3/p1-budget | -0.194 | -0.389 | -0.028 | có |
| e5-small/router-p2 | bge-m3/p2 | -0.194 | -0.389 | -0.028 | có |
| e5-small/router-p2 | bge-m3/router-p2 | -0.194 | -0.389 | -0.028 | có |
| e5-base/p1-budget | e5-base/p2 | +0.000 | +0.000 | +0.000 | không |
| e5-base/p1-budget | e5-base/router-p2 | +0.000 | +0.000 | +0.000 | không |
| e5-base/p1-budget | vn-embedding/p1-budget | -0.167 | -0.333 | -0.028 | có |
| e5-base/p1-budget | vn-embedding/p2 | -0.167 | -0.333 | -0.028 | có |
| e5-base/p1-budget | vn-embedding/router-p2 | -0.167 | -0.333 | -0.028 | có |
| e5-base/p1-budget | bge-m3/p1-budget | -0.139 | -0.306 | +0.000 | không |
| e5-base/p1-budget | bge-m3/p2 | -0.139 | -0.306 | +0.000 | không |
| e5-base/p1-budget | bge-m3/router-p2 | -0.139 | -0.306 | +0.000 | không |
| e5-base/p2 | e5-base/router-p2 | +0.000 | +0.000 | +0.000 | không |
| e5-base/p2 | vn-embedding/p1-budget | -0.167 | -0.333 | -0.028 | có |
| e5-base/p2 | vn-embedding/p2 | -0.167 | -0.333 | -0.028 | có |
| e5-base/p2 | vn-embedding/router-p2 | -0.167 | -0.333 | -0.028 | có |
| e5-base/p2 | bge-m3/p1-budget | -0.139 | -0.306 | +0.000 | không |
| e5-base/p2 | bge-m3/p2 | -0.139 | -0.306 | +0.000 | không |
| e5-base/p2 | bge-m3/router-p2 | -0.139 | -0.306 | +0.000 | không |
| e5-base/router-p2 | vn-embedding/p1-budget | -0.167 | -0.333 | -0.028 | có |
| e5-base/router-p2 | vn-embedding/p2 | -0.167 | -0.333 | -0.028 | có |
| e5-base/router-p2 | vn-embedding/router-p2 | -0.167 | -0.333 | -0.028 | có |
| e5-base/router-p2 | bge-m3/p1-budget | -0.139 | -0.306 | +0.000 | không |
| e5-base/router-p2 | bge-m3/p2 | -0.139 | -0.306 | +0.000 | không |
| e5-base/router-p2 | bge-m3/router-p2 | -0.139 | -0.306 | +0.000 | không |
| vn-embedding/p1-budget | vn-embedding/p2 | +0.000 | +0.000 | +0.000 | không |
| vn-embedding/p1-budget | vn-embedding/router-p2 | +0.000 | +0.000 | +0.000 | không |
| vn-embedding/p1-budget | bge-m3/p1-budget | +0.028 | +0.000 | +0.083 | không |
| vn-embedding/p1-budget | bge-m3/p2 | +0.028 | +0.000 | +0.083 | không |
| vn-embedding/p1-budget | bge-m3/router-p2 | +0.028 | +0.000 | +0.083 | không |
| vn-embedding/p2 | vn-embedding/router-p2 | +0.000 | +0.000 | +0.000 | không |
| vn-embedding/p2 | bge-m3/p1-budget | +0.028 | +0.000 | +0.083 | không |
| vn-embedding/p2 | bge-m3/p2 | +0.028 | +0.000 | +0.083 | không |
| vn-embedding/p2 | bge-m3/router-p2 | +0.028 | +0.000 | +0.083 | không |
| vn-embedding/router-p2 | bge-m3/p1-budget | +0.028 | +0.000 | +0.083 | không |
| vn-embedding/router-p2 | bge-m3/p2 | +0.028 | +0.000 | +0.083 | không |
| vn-embedding/router-p2 | bge-m3/router-p2 | +0.028 | +0.000 | +0.083 | không |
| bge-m3/p1-budget | bge-m3/p2 | +0.000 | +0.000 | +0.000 | không |
| bge-m3/p1-budget | bge-m3/router-p2 | +0.000 | +0.000 | +0.000 | không |
| bge-m3/p2 | bge-m3/router-p2 | +0.000 | +0.000 | +0.000 | không |

## Theo loại câu hỏi

| Cấu hình | Loại | Số câu | Recall nhóm @5 | Node chính @5 | Đủ mọi nhóm @5 |
|---|---|---:|---:|---:|---:|
| e5-small/p1-budget | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-small/p1-budget | multi | 2 | 0.500 | 0.250 | 0.000 |
| e5-small/p1-budget | natural | 13 | 0.692 | 0.615 | 0.692 |
| e5-small/p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-small/p2 | multi | 2 | 0.500 | 0.250 | 0.000 |
| e5-small/p2 | natural | 13 | 0.769 | 0.615 | 0.769 |
| e5-small/router-p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-small/router-p2 | multi | 2 | 0.500 | 0.250 | 0.000 |
| e5-small/router-p2 | natural | 13 | 0.769 | 0.615 | 0.769 |
| e5-base/p1-budget | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-base/p1-budget | multi | 2 | 0.500 | 0.250 | 0.000 |
| e5-base/p1-budget | natural | 13 | 0.846 | 0.769 | 0.846 |
| e5-base/p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-base/p2 | multi | 2 | 0.500 | 0.250 | 0.000 |
| e5-base/p2 | natural | 13 | 0.846 | 0.769 | 0.846 |
| e5-base/router-p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| e5-base/router-p2 | multi | 2 | 0.500 | 0.250 | 0.000 |
| e5-base/router-p2 | natural | 13 | 0.846 | 0.769 | 0.846 |
| vn-embedding/p1-budget | direct | 3 | 1.000 | 1.000 | 1.000 |
| vn-embedding/p1-budget | multi | 2 | 1.000 | 0.750 | 1.000 |
| vn-embedding/p1-budget | natural | 13 | 1.000 | 0.769 | 1.000 |
| vn-embedding/p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| vn-embedding/p2 | multi | 2 | 1.000 | 0.750 | 1.000 |
| vn-embedding/p2 | natural | 13 | 1.000 | 0.769 | 1.000 |
| vn-embedding/router-p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| vn-embedding/router-p2 | multi | 2 | 1.000 | 0.750 | 1.000 |
| vn-embedding/router-p2 | natural | 13 | 1.000 | 0.769 | 1.000 |
| bge-m3/p1-budget | direct | 3 | 1.000 | 1.000 | 1.000 |
| bge-m3/p1-budget | multi | 2 | 0.750 | 0.750 | 0.500 |
| bge-m3/p1-budget | natural | 13 | 1.000 | 0.846 | 1.000 |
| bge-m3/p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| bge-m3/p2 | multi | 2 | 0.750 | 0.750 | 0.500 |
| bge-m3/p2 | natural | 13 | 1.000 | 0.846 | 1.000 |
| bge-m3/router-p2 | direct | 3 | 1.000 | 1.000 | 1.000 |
| bge-m3/router-p2 | multi | 2 | 0.750 | 0.750 | 0.500 |
| bge-m3/router-p2 | natural | 13 | 1.000 | 0.846 | 1.000 |

## Câu có bằng chứng trong bảng/Phụ lục

| Cấu hình | Số câu | Recall nhóm @5 | Node chính @5 |
|---|---:|---:|---:|
| e5-small/p1-budget | 2 | 0.250 | 0.000 |
| e5-small/p2 | 2 | 0.250 | 0.000 |
| e5-small/router-p2 | 2 | 0.250 | 0.000 |
| e5-base/p1-budget | 2 | 0.250 | 0.000 |
| e5-base/p2 | 2 | 0.250 | 0.000 |
| e5-base/router-p2 | 2 | 0.250 | 0.000 |
| vn-embedding/p1-budget | 2 | 1.000 | 1.000 |
| vn-embedding/p2 | 2 | 1.000 | 1.000 |
| vn-embedding/router-p2 | 2 | 1.000 | 1.000 |
| bge-m3/p1-budget | 2 | 1.000 | 1.000 |
| bge-m3/p2 | 2 | 1.000 | 1.000 |
| bge-m3/router-p2 | 2 | 1.000 | 1.000 |

## Từ chối trả lời theo điểm top-1

Từ chối khi cosine top-1 < ngưỡng. Ngưỡng chọn trên dev: tối đa hóa từ chối đúng với ràng buộc từ chối nhầm câu có đáp án ≤ giới hạn; `—` nghĩa là không từ chối.

| Cấu hình | Ngưỡng | Từ chối đúng | Từ chối nhầm | Câu có đáp án | Câu không trả lời được |
|---|---:|---:|---:|---:|---:|
| e5-small/p1-budget | 0.888 | 1.000 | 0.056 | 18 | 2 |
| e5-small/p2 | 0.888 | 1.000 | 0.056 | 18 | 2 |
| e5-small/router-p2 | 0.888 | 1.000 | 0.056 | 18 | 2 |
| e5-base/p1-budget | 0.838 | 0.500 | 0.000 | 18 | 2 |
| e5-base/p2 | 0.838 | 0.500 | 0.000 | 18 | 2 |
| e5-base/router-p2 | 0.838 | 0.500 | 0.000 | 18 | 2 |
| vn-embedding/p1-budget | 0.470 | 1.000 | 0.000 | 18 | 2 |
| vn-embedding/p2 | 0.470 | 1.000 | 0.000 | 18 | 2 |
| vn-embedding/router-p2 | 0.470 | 1.000 | 0.000 | 18 | 2 |
| bge-m3/p1-budget | 0.579 | 0.500 | 0.000 | 18 | 2 |
| bge-m3/p2 | 0.579 | 0.500 | 0.000 | 18 | 2 |
| bge-m3/router-p2 | 0.579 | 0.500 | 0.000 | 18 | 2 |

## Câu chưa lấy đủ bằng chứng ở top 5

### e5-small/p1-budget

- q004: Đang thử việc mà thấy không phù hợp, tôi có phải báo trước khi nghỉ không?
- q016: Thỏa thuận giữ bí mật kinh doanh có nhất thiết phải nằm ngay trong hợp đồng lao động không?
- q017: Theo Nghị định 293/2025, mức lương tối thiểu tháng và giờ của vùng II là bao nhiêu?
- q021: Nộp hồ sơ BHXH trực tiếp thì cơ quan BHXH có thể xác nhận bản sao sau khi đối chiếu bản chính không?
- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?
- q033: Tuổi nghỉ hưu trong điều kiện bình thường được Bộ luật Lao động quy định theo lộ trình nào và bảng tại Nghị định 135 ghi năm 2026 ra sao?

### e5-small/p2

- q016: Thỏa thuận giữ bí mật kinh doanh có nhất thiết phải nằm ngay trong hợp đồng lao động không?
- q017: Theo Nghị định 293/2025, mức lương tối thiểu tháng và giờ của vùng II là bao nhiêu?
- q021: Nộp hồ sơ BHXH trực tiếp thì cơ quan BHXH có thể xác nhận bản sao sau khi đối chiếu bản chính không?
- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?
- q033: Tuổi nghỉ hưu trong điều kiện bình thường được Bộ luật Lao động quy định theo lộ trình nào và bảng tại Nghị định 135 ghi năm 2026 ra sao?

### e5-small/router-p2

- q016: Thỏa thuận giữ bí mật kinh doanh có nhất thiết phải nằm ngay trong hợp đồng lao động không?
- q017: Theo Nghị định 293/2025, mức lương tối thiểu tháng và giờ của vùng II là bao nhiêu?
- q021: Nộp hồ sơ BHXH trực tiếp thì cơ quan BHXH có thể xác nhận bản sao sau khi đối chiếu bản chính không?
- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?
- q033: Tuổi nghỉ hưu trong điều kiện bình thường được Bộ luật Lao động quy định theo lộ trình nào và bảng tại Nghị định 135 ghi năm 2026 ra sao?

### e5-base/p1-budget

- q005: Tôi làm hợp đồng không xác định thời hạn, muốn nghỉ việc thì thường phải báo trước mấy ngày?
- q017: Theo Nghị định 293/2025, mức lương tối thiểu tháng và giờ của vùng II là bao nhiêu?
- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?
- q033: Tuổi nghỉ hưu trong điều kiện bình thường được Bộ luật Lao động quy định theo lộ trình nào và bảng tại Nghị định 135 ghi năm 2026 ra sao?

### e5-base/p2

- q005: Tôi làm hợp đồng không xác định thời hạn, muốn nghỉ việc thì thường phải báo trước mấy ngày?
- q017: Theo Nghị định 293/2025, mức lương tối thiểu tháng và giờ của vùng II là bao nhiêu?
- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?
- q033: Tuổi nghỉ hưu trong điều kiện bình thường được Bộ luật Lao động quy định theo lộ trình nào và bảng tại Nghị định 135 ghi năm 2026 ra sao?

### e5-base/router-p2

- q005: Tôi làm hợp đồng không xác định thời hạn, muốn nghỉ việc thì thường phải báo trước mấy ngày?
- q017: Theo Nghị định 293/2025, mức lương tối thiểu tháng và giờ của vùng II là bao nhiêu?
- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?
- q033: Tuổi nghỉ hưu trong điều kiện bình thường được Bộ luật Lao động quy định theo lộ trình nào và bảng tại Nghị định 135 ghi năm 2026 ra sao?

### vn-embedding/p1-budget

- (không có)

### vn-embedding/p2

- (không có)

### vn-embedding/router-p2

- (không có)

### bge-m3/p1-budget

- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?

### bge-m3/p2

- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?

### bge-m3/router-p2

- q032: Lao động nữ nuôi con dưới 12 tháng có quyền nghỉ trong giờ làm thế nào, và Nghị định 145 hướng dẫn thời gian đó ra sao?

## Giao thức

- Tìm trên toàn bộ node Điều/Khoản/Điểm; chỉ dùng KG và embedding node, không BM25, không embed chunk.
- Recall nhóm cho phép node tổ tiên nếu chứa nguyên văn bằng chứng; node chính là chỉ số khắt khe hơn.
- Câu không trả lời được không tính vào Recall/MRR; chỉ dùng cho ngưỡng từ chối.
- CI 95% là paired bootstrap trên cùng câu hỏi, 10.000 mẫu, seed cố định.
- Nhãn do nhóm biên soạn và duyệt, chưa phải thẩm định của chuyên gia pháp lý.
- Nhãn v2: thêm 12 node đúng từ pooling mù; 2 do người duyệt tự quyết, 10 do người xác nhận nháp Claude. Nháp chưa xác nhận không bao giờ thành nhãn (xem `evaluation/summary.json`).
