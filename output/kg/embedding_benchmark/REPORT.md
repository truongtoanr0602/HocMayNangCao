# Báo cáo đánh giá embedding node KG (issue #11)

Phạm vi: chỉ đánh giá **truy xuất**. Hệ thống dùng KG và embedding node Điều/Khoản/Điểm (4534 node,
snapshot `1d10ded4…`), không dùng BM25 và không embed chunk. Câu trả lời do LLM sinh theo `answer_rubric`
sẽ được chấm ở giai đoạn sau.

## Tóm tắt

- Cấu hình được chốt trên dev trước khi chạy test (`evaluation/frozen_config.json`): model **e5-base**, text Điều v1,
  pipeline P1, ngưỡng từ chối lấy từ dev. Split test được chạy **đúng một lần** cho mọi cấu hình
  (`test/test_runs.json`, `text-v2/test/test_runs.json`). Vector node dùng lại đúng bản đã chấm trên dev
  (cache hit, cùng revision model, cùng môi trường Colab T4).
- Trên test, e5-base đạt group Recall@5 **0.833** (Recall@1 0.611, node chính @5 0.750, MRR 0.755).
- **Phát hiện chính:** trên test, vn-embedding tốt hơn e5-base **có ý nghĩa thống kê**: Recall@5 1.000 so với 0.833,
  CI 95% của chênh lệch [+0.028, +0.333]. Trên dev, khác biệt này không có ý nghĩa vì tập dev quá nhỏ, nên quy tắc
  "chênh trong CI thì chọn model nhẹ hơn" đã chọn e5-base. Đây là kết quả của một quy tắc chọn trên bộ dev chỉ có
  18 câu có đáp án, không phải lỗi đo. Cấu hình **không** được sửa sau khi xem test.
- Text Điều v2 và mở rộng KG (P2, router+P2) không cải thiện Recall@5 trên test ở model nào. Text v2 còn làm giảm
  Recall@5 của vn-embedding (−0.167) và bge-m3 (−0.111), nên quyết định giữ text v1 được xác nhận.

## Thiết lập

| Mục | Giá trị |
|---|---|
| Câu hỏi | 40 câu: dev 20, test 20. Mỗi split có 18 câu có đáp án và 2 câu không trả lời được. Các câu cùng Điều nằm cùng split |
| Nhãn | v2: nhãn gốc do nhóm viết, cộng thêm pooling mù top-10 của 5 bộ truy xuất (801 dòng duyệt, 32 node đúng được thêm) |
| Chỉ số chính | group Recall@5 (một nhóm bằng chứng được tính là trúng khi có ID nằm trong `acceptable_node_ids`) |
| Thống kê | CI 95% paired bootstrap, 10.000 mẫu, seed 0 |
| Từ chối | Từ chối khi cosine top-1 < ngưỡng. Ngưỡng chọn trên dev sao cho từ chối nhầm ≤ 10% |
| Môi trường | Colab Tesla T4, float32, tắt TF32, torch 2.14.1, transformers 5.22.1, sentence-transformers 5.7.0 |

## Kết quả test (P1, text v1)

| Model | Recall@1 | @3 | @5 | @10 | Node chính @5 | Đủ mọi nhóm @5 | MRR@10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| e5-small | 0.611 | 0.722 | 0.722 | 0.917 | 0.639 | 0.667 | 0.711 |
| **e5-base (M)** | 0.611 | 0.833 | 0.833 | 1.000 | 0.750 | 0.778 | 0.755 |
| vn-embedding | 0.833 | 0.972 | 1.000 | 1.000 | 0.806 | 1.000 | 0.927 |
| bge-m3 | 0.667 | 0.861 | 0.972 | 0.972 | 0.861 | 0.944 | 0.799 |

Chênh lệch Recall@5 theo cặp (A − B, CI 95%):

| A − B | Chênh | CI | Có ý nghĩa |
|---|---:|---|---|
| vn-embedding − e5-base | +0.167 | [+0.028, +0.333] | có |
| bge-m3 − e5-base | +0.139 | [0.000, +0.306] | không |
| vn-embedding − bge-m3 | +0.028 | [0.000, +0.083] | không |
| vn-embedding − e5-small | +0.278 | [+0.111, +0.472] | có |
| bge-m3 − e5-small | +0.250 | [+0.056, +0.444] | có |
| e5-base − e5-small | +0.111 | [−0.111, +0.333] | không |

So với dev (nhãn v2), Recall@5 là: e5-small 0.806, e5-base 0.917, vn-embedding 1.000, bge-m3 0.889.
e5-base giảm từ 0.917 xuống 0.833 trên test; bge-m3 tăng từ 0.889 lên 0.972. vn-embedding đạt 1.000 ở cả hai split,
nên Recall@5 đã chạm trần: với 18 câu, chỉ số này không còn phân biệt được vn-embedding với các model khác ở phía trên.
Các chỉ số khắt khe hơn của vn-embedding vẫn còn khoảng cách tới trần: Recall@1 0.833, node chính @5 0.806.

Theo loại câu (Recall@5): mọi model đều đạt 1.000 trên 3 câu direct. Với 2 câu multi, e5-small và e5-base đạt 0.500,
bge-m3 0.750, vn-embedding 1.000. Hai câu có bằng chứng trong bảng/Phụ lục (q017, q033) là điểm yếu rõ nhất
của e5: Recall@5 0.250, so với 1.000 của vn-embedding và bge-m3. Câu trượt của e5-base: q005, q017, q032, q033.

## Text Điều v2 và mở rộng KG trên test

| Cấu hình | Recall@5 v1 | Recall@5 v2 | v2 − v1 (CI) |
|---|---:|---:|---|
| e5-small | 0.722 | 0.861 | +0.139 [0.000, +0.306] |
| e5-base | 0.833 | 0.806 | −0.028 [−0.167, +0.083] |
| vn-embedding | 1.000 | 0.833 | −0.167 [−0.333, 0.000] |
| bge-m3 | 0.972 | 0.861 | −0.111 [−0.278, 0.000] |

P2 (mở rộng một bước trên KG) và router+P2 dùng cùng ngân sách 10 node / 12.000 ký tự. Trên test, chúng không đổi
Recall@5 của e5-base, vn-embedding và bge-m3; e5-small tăng 0.722 → 0.778 (không có ý nghĩa). Router định tuyến đúng
3/3 câu direct và không định tuyến nhầm câu nào khác. Tuy vậy, các câu direct vốn đã đạt 1.000 bằng tìm kiếm dense,
nên router không làm tăng chỉ số. Chi tiết: `test/pipelines.md`, `test/text_versions.md`.

## Từ chối trả lời (ngưỡng chốt trên dev)

| Model | Ngưỡng | Từ chối đúng (2 câu) | Từ chối nhầm (18 câu) |
|---|---:|---:|---:|
| e5-small | 0.888 | 2/2 | 1/18 |
| e5-base (M) | 0.838 | 1/2 | 0/18 |
| vn-embedding | 0.470 | 2/2 | 0/18 |
| bge-m3 | 0.579 | 1/2 | 0/18 |

Mỗi split chỉ có 2 câu không trả lời được, nên các tỷ lệ từ chối trên đây rất bất định.

## Chi phí

| Model | Chiều | Số window | Node nhiều cửa sổ | Encode node trên T4 | RAM đỉnh | GPU đỉnh | Encode 20 câu hỏi |
|---|---:|---:|---:|---:|---:|---:|---:|
| e5-small | 384 | 4829 | 219 | 19 s | 1.9 GB | 0.5 GB | 0.76 s |
| e5-base | 768 | 4829 | 219 | 62 s | 2.5 GB | 1.1 GB | 0.41 s |
| vn-embedding | 1024 | 4534 | 0 | 215 s | 3.6 GB | 2.2 GB | 0.56 s |
| bge-m3 | 1024 | 4534 | 0 | 206 s | 3.6 GB | 2.2 GB | 0.46 s |

e5 có cửa sổ 512 token nên 219 node phải cắt thành nhiều cửa sổ. vn-embedding và bge-m3 có cửa sổ 8192 token nên
mỗi node nằm gọn trong một cửa sổ. Encode node chỉ cần làm một lần cho mỗi snapshot.

## Neo4j

Vector của cả 4 model đã được nạp vào snapshot `1d10ded4…`, mỗi model một thuộc tính `embedding_<model>` và một
index cosine. Với M = e5-base, độ khớp top-10 giữa vector index (HNSW, overfetch 10) và cosine chính xác là **0.965**
trên 20 câu dev; 15/20 câu khớp hoàn toàn (`e5-base/ann_check.json`). Các model khác: e5-small 0.99,
vn-embedding 0.975, bge-m3 0.945.

## Giới hạn

- Bộ câu hỏi nhỏ: 18 câu có đáp án mỗi split. Chênh lệch cỡ một câu (0.056) nằm trong nhiễu. Quy tắc chọn model
  trên dev không đủ lực thống kê để tách e5-base khỏi vn-embedding.
- Nhãn do nhóm biên soạn và duyệt, **không** phải thẩm định của chuyên gia pháp lý. Ở bước pooling, Claude soạn nháp
  gợi ý; 748/801 dòng là nháp được người xác nhận, 53 dòng do người tự quyết, và người khác nháp 1/762 lần.
  Nháp chưa xác nhận không bao giờ thành nhãn. Bằng chứng đúng nằm ngoài top-10 của cả 5 bộ truy xuất vẫn có thể bị bỏ sót.
- Câu hỏi được viết sau khi đọc văn bản, nên chưa đại diện cho phân bố câu hỏi thật của người dùng.
  Chỉ có 2 câu bảng/Phụ lục và 4 câu multi.
- Thứ hạng có thể đảo khi cosine của hai node chỉ chênh khoảng 0.001: chỉ nâng phiên bản thư viện đã làm e5-small
  đổi một câu trên dev.

## Bước tiếp theo đề xuất

Split test hiện tại đã được dùng. Nếu đổi model M sang vn-embedding dựa trên kết quả này, con số 1.000 trên test
**không còn** là ước lượng không thiên lệch cho cấu hình mới. Cách làm đúng:

1. Mở rộng bộ câu hỏi lên khoảng 120 câu (issue #3), ưu tiên câu multi, câu bảng/Phụ lục và câu không trả lời được.
2. Chọn lại model trên dev mới (lớn hơn), chốt cấu hình, rồi chạy một lần trên **câu test mới**. 20 câu test hiện tại
   nên được báo cáo riêng như dữ liệu đã dùng.

Số liệu đầy đủ: `test/comparison.md`, `test/pipelines.md`, `test/text_versions.md` (test) và `comparison.md`,
`pipelines.md`, `text_versions.md` (dev).
