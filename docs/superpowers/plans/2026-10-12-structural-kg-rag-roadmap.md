# Structural KG–RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng trợ lý với embedding, BM25 và KG cấu trúc từ DOCX; không dùng LLM dựng KG.

**Architecture:** Tiền xử lý xuất chunk và cấu trúc nguồn. Embedding/BM25 tìm chunk; Neo4j tra định danh và mở rộng ngữ cảnh; LLM trả lời từ bằng chứng. Hoàn thành từng mốc độc lập, không triển khai toàn bộ roadmap trong một lần.

**Tech Stack:** Python, python-docx, pytest hiện có; dự kiến Neo4j cho cấu trúc, Qdrant cho vector, BM25 cục bộ và Ollama cho sinh câu trả lời. Chọn model embedding sau thử nghiệm tiếng Việt, chưa cố định model hoặc kích thước vector.

**Spec:** Yêu cầu trong hội thoại: nhánh 1 embedding, nhánh 2 keyword, nhánh 3 KG cấu trúc; giữ pipeline DOCX theo `docs/superpowers/specs/2026-09-13-docx-legal-preprocessing-design.md`. Thiết kế KG ngày 2026-09-11 mô tả hướng ngữ nghĩa cũ, cần thay bằng spec mới trước triển khai KG.

## Global Constraints

- Không gọi LLM để tạo node/cạnh cấu trúc; không suy diễn quan hệ quyền/nghĩa vụ.
- Giữ nguyên nguồn DOCX/PDF và nội dung pháp luật; mọi sửa phân loại phải truy vết được.
- Dùng cùng snapshot dữ liệu và chunk_id cho cả ba nhánh; thay nội dung/chia chunk phải tái tạo cả ba chỉ mục.
- Không dựng Khoản–Điểm từ các danh sách độc lập thiếu quan hệ cha–con.
- Không mặc định quy định còn hiệu lực chỉ vì có trong corpus.
- Workspace hiện không có Git repository; không yêu cầu commit khi chưa thiết lập Git.

## Trạng thái đã kiểm tra ngày 2026-10-12

- 28 test qua; 8 tài liệu, 672 chunk: 595 article, 48 clause_group, 29 preamble.
- extractor.py và run_batch.py không còn tồn tại; dữ liệu extraction_results, json_KG và thiết kế KG ngữ nghĩa cũ còn tồn tại.
- Chưa có package legal_kg, loader Neo4j, embedding, BM25, API hoặc giao diện trong danh sách file đã quét.
- requirements.txt chỉ có python-docx và pytest.
- 23 cảnh báo QA; trạng thái passed chưa kiểm tra đúng ngữ cảnh phụ lục hay giới hạn kích thước.
- Parser không có cấp Appendix/Table; phụ lục địa bàn doc-04 đang nằm dưới Điều 5.
- Chunk doc-07/7ba9c209da88cd49877a dài 15240 ký tự, gắn Điều 9.
- Sentence fallback gộp dòng và dùng block cuối, làm mất độ chính xác truy vết; clause_ids/point_ids chưa giữ quan hệ cha–con.

## Review Focus

- Phụ lục và biểu mẫu có số Điều riêng không được nhập thành Điều của văn bản chính (Task 1).
- Một câu/dòng dài hơn giới hạn vẫn phải tách và giữ nguồn (Task 1).
- Preamble và phụ lục không có Article vẫn phải được nạp, không rơi chunk (Task 2).
- Cùng số Mục ở hai Chương không được gộp node (Task 2).
- Chỉ mục cũ sau tái chia chunk phải được phát hiện trước truy xuất (Task 3).

---

### Task 1: Ổn định cấu trúc nguồn và chunking — ưu tiên triển khai đầu tiên

**Files:** Modify `legal_preprocessing/models.py`, `extract.py`, `parse.py`, `chunk.py`, `pipeline.py`, `qa.py`; tests tương ứng trong `tests/`; Create `docs/superpowers/specs/2026-10-12-structural-kg-design.md`.

**Interfaces:** Giữ `parse_legal_units(blocks) -> ParseResult` và `chunk_units(spec, units, max_chars=6000) -> list[Chunk]`. Bổ sung `structure_path` là danh sách phần tử `{type, number, title}` có thứ tự; `source_spans` là danh sách `{block_number, start, end}` với offset trên text khối sạch. Giữ các trường cũ để tương thích; không tự tạo Clause/Point chi tiết ở mốc này.

- [ ] Viết spec KG cấu trúc, quy tắc Appendix/Table, phân biệt biểu mẫu/điều trích dẫn với điều chính; xác minh ranh giới trên DOCX thật.
- [ ] Viết test phụ lục không thuộc Điều cuối, biểu mẫu không ghi đè Điều chính, continuation giữ đường dẫn nguồn và một dòng dài hơn 6000 vẫn tách được; chạy test mới để xác nhận thất bại.
- [ ] Giữ định danh bảng và ô, kể cả ô rỗng; xử lý ô gộp tránh lặp nội dung. Không suy đoán số bảng khi nguồn không có: dùng vị trí nguồn ổn định.
- [ ] Sửa parser/chunker để giữ đường dẫn cấu trúc và source_spans; không gán cả đoạn tách về block cuối. QA báo lỗi khi vượt max_chars hoặc đường dẫn trái ngữ cảnh đã xác định.
- [ ] Chạy `python -m pytest -q`, tái sinh vào thư mục output mới bằng CLI, kiểm tra phụ lục doc-04/doc-07 rồi mới dùng snapshot mới. Số chunk có thể thay đổi; không khóa cứng 672.

### Task 2: Dựng và nạp KG cấu trúc

**Files:** Create `legal_kg/__init__.py`, `models.py`, `build.py`, `repository.py`, `cli.py`; `tests/test_kg_build.py`, `tests/test_kg_repository.py`; cấu hình Neo4j trong `compose.yaml`, `.env.example`; thêm driver vào requirements.

**Interfaces:** `build_graph(rows: list[dict]) -> GraphPayload`; payload có nodes/edges và source snapshot hash. `load_graph(payload: GraphPayload, repository) -> LoadReport`. CLI `python -m legal_kg.cli build --input <jsonl> --output <graph.json>` và `load --input <graph.json>`.

- [ ] Test cây có/không có cấp tùy chọn, hai chương có Mục 1 riêng, article và clause_group cùng Điều, preamble không có Điều và phụ lục độc lập; chạy xác nhận thất bại.
- [ ] Tạo LegalDocument/Part/Chapter/Section/Article/Appendix/Table/Chunk theo đường dẫn đã kiểm tra; CONTAINS nối cấu trúc, HAS_CHUNK nối đơn vị gần nhất tới chunk. Không tạo Provision hay quan hệ ngữ nghĩa.
- [ ] Test repository bằng fake: constraint ID, MERGE tham số hóa, rollback khi batch lỗi, nạp lại không tăng bản ghi; triển khai loader và báo cáo số chunk/ID không nạp được.
- [ ] Integration với Neo4j: mọi chunk snapshot được nạp đúng một node; truy ngược từ chunk về văn bản, lấy các chunk cùng đơn vị theo thứ tự; nạp hai lần không tăng số node/cạnh. Snapshot mới dùng database riêng hoặc cơ chế thay snapshot có kiểm soát, tránh dữ liệu cũ lẫn mới.

### Task 3: Chỉ mục và truy xuất văn bản

**Files:** Create `legal_retrieval/models.py`, `corpus.py`, `bm25.py`, `embeddings.py`, `vector_store.py`; `tests/test_retrieval.py`; `evaluation/questions.jsonl`.

**Interfaces:** `SearchHit(chunk_id: str, score: float, channel: str)`; hai retriever có `search(query: str, limit: int) -> list[SearchHit]`. Manifest chỉ mục chứa corpus hash, model/revision, dimension và preprocessing version.

- [ ] Chuẩn bị 30–50 câu hỏi có căn cứ chuẩn, gồm diễn đạt đời thường, số Điều, địa bàn, phụ lục, câu thiếu dữ kiện và ngoài phạm vi. Ghi nhãn từ nguồn đã kiểm tra; tách development/evaluation trước tinh chỉnh.
- [ ] Test BM25 với tên địa bàn/số văn bản, dấu tiếng Việt và kết quả rỗng; triển khai baseline BM25 trước để kiểm tra corpus và câu hỏi nhanh.
- [ ] So sánh một số ứng viên embedding trên development set trước chọn model; test adapter bằng fake, kiểm tra dimension và batch.
- [ ] Nạp Qdrant với chunk_id nguyên gốc trong payload; nếu cần UUID point thì ánh xạ xác định. Kiểm tra số chunk và từ chối truy xuất khi snapshot hash không khớp KG/BM25.

### Task 4: Hybrid retrieval và context

**Files:** Create `legal_retrieval/hybrid.py`, `graph_context.py`, `context.py`; `tests/test_hybrid.py`, `tests/test_context.py`.

**Interfaces:** `retrieve(query: str, limit: int) -> list[SearchHit]`; `build_context(hits, token_budget: int) -> ContextBundle` chứa evidence_id, chunk_id, text và citation metadata.

- [ ] Test loại trùng, thứ hạng xác định, nhánh rỗng và giới hạn token; triển khai RRF cho embedding/BM25, không cộng trực tiếp điểm khác thang đo.
- [ ] Tra trực tiếp metadata khi người dùng nêu rõ văn bản + Điều; số Điều thiếu văn bản có thể mơ hồ.
- [ ] Mở rộng bằng KG trong cùng đơn vị nguồn và giới hạn token; không lấy toàn chương mặc định. Không coi quan hệ cấu trúc là quan hệ hướng dẫn/sửa đổi.
- [ ] Với địa bàn–vùng–mức lương: giữ hàng bảng/tiêu đề và bằng chứng phân loại; nếu cần tra cứu chính xác thì bổ sung bảng ánh xạ được kiểm duyệt, không giả định KG cấu trúc đã cung cấp logic đó.
- [ ] Test câu hỏi lương tối thiểu Bắc Ninh cần được phép hỏi xã/phường; không sinh một mức duy nhất từ tên tỉnh khi chưa đủ căn cứ.

### Task 5: Trả lời, API và đánh giá

**Files:** Create `legal_assistant/service.py`, `llm.py`, `citations.py`, `api.py`; `tests/test_assistant.py`; `evaluation/run.py`; tài liệu chạy dự án.

**Interfaces:** `answer(question: str, history: list[dict]) -> AnswerResult` có answer, citations và clarification; LLM transport được tiêm để test không cần Ollama.

- [ ] Bổ sung metadata nguồn chính thức và hiệu lực đã kiểm chứng; không áp dụng lọc thời gian từ dữ liệu chưa xác minh.
- [ ] Test ngữ cảnh rỗng, citation không tồn tại, câu hỏi thiếu dữ kiện, yêu cầu vượt corpus và nội dung nguồn giống chỉ dẫn; triển khai prompt grounded và kiểm tra ID citation.
- [ ] Xây API và giao diện chat tối thiểu sau khi pipeline truy xuất chạy được; hiển thị căn cứ và cho xem đoạn nguồn.
- [ ] Đánh giá embedding; embedding+BM25; embedding+BM25+KG trên cùng bộ câu hỏi, model và ngân sách ngữ cảnh. Đo Recall@k, độ đúng/đủ, citation, hỏi lại và latency. Với câu trả lời cần người kiểm duyệt, không chỉ tự chấm bằng LLM.

## Dọn dữ liệu cũ

Không thực hiện xóa trong lần lập kế hoạch này. extractor.py/run_batch.py đã vắng mặt, không cần tạo lại. Các extraction_results*.jsonl, log clause_group_48 và json_KG còn lại không thuộc pipeline mới; đối chiếu giá trị lưu trữ trước dọn. Đánh dấu thiết kế ngữ nghĩa cũ là superseded khi spec cấu trúc hoàn thành; sửa tham chiếu extractor.py còn sót trong tài liệu. models/tessdata không còn phục vụ luồng DOCX nhưng không cần xóa để triển khai mốc đầu.

## Handoff

Triển khai Task 1 trước, xác nhận dữ liệu rồi Task 2. Task 3–5 là roadmap, cần kế hoạch riêng chi tiết khi đạt mốc trước. Chưa chọn model embedding, chưa giả định Neo4j/Qdrant/Ollama đang chạy. Không sửa code hoặc dữ liệu nguồn trong lần quét/lập kế hoạch này.

## Nhật ký triển khai legal_kg

- Theo yêu cầu tiếp theo của người dùng, triển khai Task 2 thành module độc lập trước khi sửa tiền xử lý.
- Ruling: Task 1 vẫn chưa hoàn thành; build phản ánh metadata cũ và cảnh báo, load mặc định từ chối legacy trừ khi chọn `--allow-legacy-metadata`. Chi phí nếu dùng bản thử nghiệm làm căn cứ: phụ lục có thể còn bị gắn vào Điều cuối. Cần sửa preprocessing và tạo snapshot mới trước tích hợp tư vấn.
- Đã tạo `legal_kg/{models,build,repository,cli}.py`, Compose, cấu hình mẫu, README và spec cấu trúc.
- Test mới chạy thất bại khi module còn thiếu, sau đó qua; test rollback/isolation dùng transaction double, không thay thế kiểm thử Neo4j thật.
- Final review: reviewer độc lập phát hiện validation artifact thiếu trường bắt buộc và thứ tự cấp. Đã tái hiện bằng test thất bại, sửa validation và chạy lại toàn suite.
- Final fixed: validation artifact và metadata legacy sai kiểu — 7 test RED→GREEN.
- Final fixed: stdout cp1252 trên Windows không in được tiếng Việt — subprocess regression test RED→GREEN, CLI inspect chạy thật exit 0.
- Verification: `python -m pytest -q` → 60 passed, 1 skipped; `python -m legal_kg.cli build` → 1414 node, 1406 cạnh, 672 chunk; Compose config hợp lệ.
- Chưa nạp Neo4j thật: Docker Desktop Linux engine không chạy. Integration opt-in còn skipped; không đánh dấu Task 2 hoàn tất phần integration.
- Không xóa dữ liệu, không sửa DOCX hoặc `legal_chunks.jsonl`, không tạo commit vì workspace không có Git.
## Cập nhật tiền xử lý v3 — 2026-10-12

- Đã hoàn thành sửa phân loại phụ lục, bảng và chunking trên 8 DOCX; các ghi chú legacy trong nhật ký trước mô tả snapshot v2.
- Phụ lục có đường dẫn riêng; tham chiếu phụ lục trong thân Điều không mở nhánh mới. Bảng giữ cột trống, tiêu đề và vị trí ô gộp.
- Chunk tối đa 6.000 ký tự, có source_spans đối chiếu với nguồn đã làm sạch; QA kiểm tra độ phủ nội dung đã phân tích.
- Đã tái tạo output/preprocessed và output/kg/structural_graph.json: 803 chunk, 1.623 node, 1.615 cạnh; graph không còn cảnh báo metadata legacy.
- Kiểm tra cuối: python -m pytest -q → 78 passed, 1 skipped. Review độc lập không phát hiện vấn đề quan trọng.
- Chưa kiểm thử tích hợp Neo4j thật vì Docker engine chưa chạy. Chưa commit hoặc push các thay đổi này.
