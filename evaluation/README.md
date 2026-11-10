# Bộ câu hỏi đánh giá embedding node — nhãn v2 (đã duyệt pooling)

## Phạm vi

40 câu hỏi viết dựa trên corpus cố định gồm 8 văn bản, không phải bộ tư vấn pháp luật hiện hành. Câu hỏi và nhãn gốc do nhóm viết, không dùng LLM. Riêng bước duyệt pooling, Claude được dùng để **soạn nháp gợi ý**: nháp không bao giờ tự thành nhãn; một dòng chỉ thành nhãn khi có người tự quyết định hoặc bấm xác nhận nháp, và mỗi nhãn ghi `label_source` (`human` / `draft_confirmed`). `summary.json` báo số nhãn theo nguồn và số lần người quyết định khác nháp; báo cáo phải nêu rõ cách gán nhãn này. Không thay đổi graph hay Neo4j.

| Loại câu | Số lượng |
|---|---:|
| Diễn đạt tự nhiên | 26 |
| Tra cứu Điều/Khoản/Điểm trực tiếp | 6 |
| Cần nhiều nhóm bằng chứng | 4 |
| Không thể trả lời từ corpus | 4 |

Development: 20 câu. Test: 20 câu. Các câu dùng cùng Điều được giữ cùng tập; câu nhiều Điều được xét toàn bộ các Điều liên quan. Cả hai tập truy xuất trên cùng graph: đây là đánh giá câu hỏi mới trên corpus cố định, không phải đánh giá tổng quát hóa sang văn bản chưa thấy.

## File để đọc

- `questions_review.md`: đọc và duyệt câu hỏi, node bằng chứng và tiêu chí trả lời.
- `questions.jsonl`: toàn bộ 40 bản ghi cho chương trình.
- `dev.jsonl`: chọn model, cách xây input, top-k và ngưỡng từ chối trên tập này.
- `test.jsonl`: giữ lại để chấm sau khi đã cố định cấu hình; không dùng để tinh chỉnh.
- `summary.json`: thống kê và snapshot tương ứng.
- `build_questions.py`: nguồn câu hỏi biên soạn và bộ dựng/kiểm tra bằng chứng. Chạy lại bằng `python evaluation/build_questions.py`; thao tác này ghi lại các file xuất, vì vậy hãy sửa câu hỏi ở SEEDS thay vì chỉ sửa file JSONL.

## Ý nghĩa nhãn

Mỗi câu có `question_id`, `question`, `type`, `split`, `answerable`, snapshot và graph hash.

`evidence_groups` mô tả các nhóm bằng chứng cần thiết. Câu nhiều quy định phải lấy đủ các nhóm, không chỉ một node bất kỳ.

Trong mỗi nhóm:

- `primary_node_id`: node cụ thể được chọn làm nhãn chính.
- `acceptable_node_ids`: node chính và các node tổ tiên có body_text chứa nguyên văn dẫn chứng. Không tự chấp nhận mọi node cùng Điều. Đây là tập nhãn khởi đầu, chưa bảo đảm bao phủ mọi cách trả lời hợp lệ.
- `evidence_quote`: một dòng nguyên văn chứa nội dung dùng làm bằng chứng.
- `body_start`, `body_end`: offset Python trong body_text, không phải trong embedding_text hoặc DOCX.
- `source_chunk_ids`: các Chunk liên quan tới node để truy vết; không mặc định mọi Chunk đều chứa đúng câu dẫn chứng.

`answer_rubric` là yêu cầu chấm câu trả lời, không phải một đáp án pháp lý hoàn chỉnh. Đọc cả phần dẫn và node cha khi dẫn chứng ở Điểm quá ngắn. Trường `requires_human_review` là true: đã kiểm tra tính tồn tại của nguồn, chưa được người có chuyên môn duyệt độ đầy đủ pháp lý.

Các câu không trả lời được gồm thiếu dữ liệu nghiệp vụ/cá nhân và ngoài lĩnh vực. Không gán node liên quan giả. Những câu này chưa đánh giá được đầy đủ tình huống gần lĩnh vực nhưng corpus thiếu quy định; nên bổ sung sau khi rà soát chuyên môn.

## Cách chấm đề xuất

1. Chấm 36 câu có đáp án: Recall@k theo nhóm bằng chứng ở k=1,3,5,10. Một nhóm được tìm thấy khi kết quả chứa một ID trong acceptable_node_ids. Tính thêm tỷ lệ tìm đủ mọi nhóm cho câu multi.
2. Báo cáo riêng tỷ lệ trúng node chính để việc trả về toàn Điều không che lấp khả năng tìm Khoản/Điểm cụ thể. Có thể báo cáo MRR cho câu một nhóm bằng chứng.
3. Chấm riêng kết quả vector search ban đầu và tập bằng chứng sau graph traversal, giữ cùng ngân sách truy xuất/ngữ cảnh.
4. Không đưa 4 câu ngoài phạm vi vào Recall/MRR vì không có node đúng. Chấm khả năng từ chối hoặc báo thiếu bằng chứng, đồng thời đo từ chối nhầm trên câu có đáp án. Vector search luôn có hàng xóm không đồng nghĩa corpus có đáp án.
5. Chấm riêng câu trực tiếp và câu tự nhiên. Câu trực tiếp có thể đi qua tra cứu định danh trong hệ thống cuối, nhưng khi so model embedding cần giữ cùng giao thức.
6. Đánh giá câu trả lời theo: đủ các ý, đúng điều kiện/ngoại lệ, dẫn nguồn hỗ trợ kết luận, không bịa thông tin. Cần người duyệt; trích dẫn khớp chuỗi không chứng minh suy luận đúng.

## Giới hạn và bước duyệt

Đây là bộ nhỏ, được viết sau khi đọc văn bản, chưa đại diện cho toàn bộ phân bố câu hỏi người dùng. Số câu giữa các văn bản chưa cân bằng, đặc biệt Nghị định 12/2022 mới xuất hiện trong một câu multi. Một số câu trong cùng Điều có từ ngữ gần nhau; đã giữ cùng split để giảm rò rỉ. Nhãn v2 đã pooling top-10 của 5 bộ truy xuất (4 model chung môi trường + minilm) cho cả 40 câu: duyệt 801 dòng, thêm 32 node đúng; bằng chứng đúng nằm ngoài mọi top-10 vẫn có thể bị bỏ sót.

Trước khi công bố kết quả: duyệt questions_review.md, thêm bằng chứng thay thế có căn cứ, chốt phiên bản, sau đó chỉ điều chỉnh trên development. Nếu thay corpus/embedding_text phải kiểm tra lại toàn bộ nhãn và hash.

## Quy trình đánh giá embedding node (issue #1–#11)

Phạm vi: chỉ KG + embedding node Điều/Khoản/Điểm; không BM25, không embed chunk. Chạy từ thư mục gốc.

| Bước | Lệnh | Ghi chú |
|---|---|---|
| E0. Biên soạn ~120 câu | sửa `SEEDS`, rồi `python evaluation/build_questions.py --enforce-composition` | Cơ cấu 70 natural / 15 direct / 20 multi / 15 unanswerable, ≥ 10 câu bằng chứng trong bảng/Phụ lục (cờ tự gắn), dev/test chia đều theo nhóm Điều |
| E1. Encode + chạy dev | Khuyến nghị GPU: mở `evaluation/colab_encode.ipynb` trên Colab (T4), upload `colab_bundle.zip`, tải `colab_results.zip` về và giải nén vào thư mục gốc. Trên CPU: `python -m legal_kg.embedding_benchmark --model <key> --threads 8` với key `e5-small`, `e5-base`, `bge-m3`, `vn-embedding` | Mọi model phải encode trong cùng môi trường (thiết bị nằm trong cache key, float32, tắt TF32); notebook chạy luôn text v2 và pool dev/test. Vector node được cache; đổi câu hỏi chỉ encode lại câu hỏi |
| E2. Pooling mù | `--pool-only --questions evaluation/dev.jsonl` và `--pool-only --questions evaluation/test.jsonl` cho mỗi model, rồi `python evaluation/pool_candidates.py output/kg/embedding_benchmark/pool/*/*/pool.json` và `python evaluation/build_pooling_page.py` | Nhóm duyệt trên trang dùng chung [Duyệt nhãn pooling](https://claude.ai/artifact/NiV9WdBgPurnibuLnUTxTT) (sinh từ `evaluation/pooling_review_page/`); quyết định lưu chung. Bấm "Tạo nháp cho mọi câu chưa có" để Claude soạn gợi ý (collection `drafts`, prompt trong `draft.js`, ghi model đã trả lời); người duyệt xác nhận hoặc sửa từng dòng, hoặc xác nhận hàng loạt các nháp "không liên quan" của một câu sau khi đọc lướt. Đưa về repo: `python evaluation/import_pooling_decisions.py <file tải từ trang hoặc bản đọc từ kho>`, rồi `build_questions.py` → `label_version` = v2 khi duyệt hết; sau đó `python -m legal_kg.relabel_runs --old <dev.jsonl cũ>` gắn các run dev sang nhãn mới (chỉ khi chỉ trường nhãn thay đổi) và chạy lại `retrieval_eval`. Câu bị báo "cần sửa" giữ ở trạng thái chờ đến khi sửa `SEEDS` |
| E3. Chọn model M | `python -m legal_kg.retrieval_eval` | Recall nhóm @5, CI 95% paired bootstrap; chênh trong CI → chọn model nhẹ/nhanh hơn |
| E4. Text Điều v2 | `python -m legal_kg.embedding_text --article-mode v2`, rồi benchmark M với `--corpus output/kg/embedding_text_v2/node_texts.jsonl --output output/kg/embedding_benchmark/text-v2` | So v1/v2 bằng `retrieval_eval --runs …` |
| E5. P2 + router | `python -m legal_kg.kg_expansion --run output/kg/embedding_benchmark/<M>` | Sinh `p1-budget`, `p2`, `router-p2` cùng ngân sách 10 node / 12.000 ký tự |
| E6. Ngưỡng từ chối | có sẵn trong báo cáo `retrieval_eval` | Chọn trên dev: từ chối nhầm ≤ 10% |
| E7. Chốt | `python evaluation/freeze_config.py --selected-model … --models … --text-version … --pipeline … --comparisons … --rationale "…"` | Cần nhãn v2; ghi `evaluation/frozen_config.json` |
| E8. Test một lần | `python evaluation/build_colab_bundle.py` → mở `evaluation/colab_test.ipynb` trên Colab T4, upload `colab_test_bundle.zip`, tải `colab_test_results.zip` về và giải nén vào thư mục gốc (benchmark chạy với `--questions evaluation/test.jsonl --require-cache`: revision model ghim theo file chốt, vector node dùng lại đúng bản dev); `python -m legal_kg.kg_expansion --run output/kg/embedding_benchmark/test/<model> --questions evaluation/test.jsonl`; rồi `retrieval_eval --questions evaluation/test.jsonl --frozen-config evaluation/frozen_config.json --runs …` | Bị chặn nếu chưa chốt hoặc hash không khớp; số lần chạy test ghi trong `output/kg/embedding_benchmark/test/test_runs.json` |
| E9. Neo4j | `python -m legal_kg.cli load-embeddings --run output/kg/embedding_benchmark/<M>` rồi `python -m legal_kg.cli check-ann --run …` | Cần `NEO4J_PASSWORD` trong biến môi trường tiến trình |

Đổi trường câu hỏi hoặc nhãn làm đổi hash bộ câu hỏi; các run cũ khi đó bị `retrieval_eval` từ chối và cần chạy lại bước encode câu hỏi (vector node vẫn dùng cache).
