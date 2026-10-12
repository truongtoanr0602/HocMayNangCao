# Thiết kế pipeline trích xuất Knowledge Graph pháp luật

## 1. Mục tiêu và phạm vi

Hệ thống đọc các chunk đã tiền xử lý từ
`output/preprocessed/legal_chunks.jsonl`, trích xuất thực thể và quan hệ pháp
lý, kiểm tra kết quả, lưu dấu vết dưới dạng JSONL và nạp dữ liệu vào Neo4j.
Ollama và Neo4j chạy bằng Docker Compose; Ollama sử dụng GPU NVIDIA.

Phiên bản đầu tiên xử lý theo batch và chỉ sử dụng tám văn bản trong manifest
hiện tại. Pipeline không OCR lại, không sửa nội dung chunk và không thay đổi
pipeline tiền xử lý hiện có.

## 2. Nguyên tắc thiết kế

1. Cấu trúc văn bản là dữ liệu xác định: Document, Part, Chapter, Section,
   Article, Clause và Point được tạo từ metadata hiện có, không giao cho LLM.
2. Regex xử lý các dữ liệu có mẫu ổn định như viện dẫn điều khoản, thời lượng,
   tỷ lệ và thời hạn.
3. LLM chỉ xử lý thực thể và quan hệ ngữ nghĩa khó xác định bằng luật.
4. Không ghi trực tiếp kết quả chưa kiểm tra vào Neo4j.
5. Mọi thực thể và quan hệ ngữ nghĩa phải truy ngược được về chunk, trang,
   điều khoản và đoạn bằng chứng.
6. Chạy lại cùng dữ liệu không tạo node hoặc relationship trùng lặp.
7. Model, prompt và kết quả được định phiên bản để có thể tái lập và so sánh.

## 3. Kiến trúc

```text
legal_chunks.jsonl
        |
        v
Structure/Rule Extractor
        |
        v
Ollama Semantic Extractor
        |
        v
Validator + Normalizer
        |
        +--> kg_extractions.jsonl
        +--> rejected_extractions.jsonl
        |
        v
Neo4j Loader
        |
        v
Knowledge Graph
```

Các thành phần Python được đặt trong package `legal_kg`, độc lập với
`legal_preprocessing`. CLI có ba lệnh:

- `extract`: đọc chunk, trích xuất, kiểm tra và xuất JSONL;
- `load`: đọc JSONL hợp lệ và nạp Neo4j;
- `run`: thực hiện lần lượt `extract` và `load`.

## 4. Ontology phiên bản đầu

### 4.1 Node cấu trúc

- `LegalDocument`
- `Part`
- `Chapter`
- `Section`
- `Article`
- `Clause`
- `Point`
- `Chunk`

Quan hệ cấu trúc gồm `CONTAINS` và `HAS_CHUNK`. Mỗi node dùng một `id` ổn
định tạo từ `document_id` và số cấu trúc. Không tạo node cho cấp không xuất
hiện trong metadata.

### 4.2 Node ngữ nghĩa

- `Provision`: mệnh đề pháp lý trung gian;
- `Subject`;
- `Right`;
- `Obligation`;
- `Prohibition`;
- `Condition`;
- `ContractType`;
- `Procedure`;
- `Deadline`;
- `Duration`;
- `Rate`;
- `Benefit`;
- `Penalty`;
- `Authority`;
- `LegalConcept`.

`Provision` giữ ngữ cảnh của một quy định để không làm mất điều kiện, ngoại lệ
hoặc định lượng khi mô hình hóa. Quan hệ ngữ nghĩa hợp lệ:

- `STATES` từ Article, Clause, Point hoặc Chunk đến Provision;
- `APPLIES_TO` từ Provision đến Subject;
- `GRANTS_RIGHT` từ Provision đến Right;
- `IMPOSES_OBLIGATION` từ Provision đến Obligation;
- `PROHIBITS` từ Provision đến Prohibition;
- `HAS_CONDITION` từ Provision đến Condition;
- `HAS_PROCEDURE` từ Provision đến Procedure;
- `HAS_DEADLINE` từ Provision đến Deadline;
- `HAS_DURATION` từ Provision đến Duration;
- `HAS_RATE` từ Provision đến Rate;
- `GRANTS_BENEFIT` từ Provision đến Benefit;
- `HAS_PENALTY` từ Provision đến Penalty;
- `ENFORCED_BY` từ Provision đến Authority;
- `CONCERNS` từ Provision đến ContractType hoặc LegalConcept;
- `EXCEPTION_TO` giữa hai Provision;
- `REFERENCES` giữa các node cấu trúc pháp lý.

Validator dùng danh sách domain/range trên làm allowlist. Nhãn hoặc quan hệ
ngoài ontology bị từ chối.

## 5. Định dạng trao đổi và lưu dấu vết

Mỗi dòng `kg_extractions.jsonl` tương ứng với một chunk:

```json
{
  "chunk_id": "stable-chunk-id",
  "document_id": "doc-01",
  "source": {
    "page_start": 1,
    "page_end": 1,
    "article": "113",
    "clause_ids": ["1"]
  },
  "input_hash": "sha256",
  "model": "qwen3:8b",
  "prompt_version": "kg-v1",
  "entities": [
    {
      "id": "e1",
      "type": "Subject",
      "text": "người lao động",
      "normalized_name": "người lao động",
      "start": 0,
      "end": 15
    }
  ],
  "relations": [
    {
      "subject_id": "p1",
      "predicate": "APPLIES_TO",
      "object_id": "e1",
      "evidence": "người lao động ...",
      "confidence": 0.9
    }
  ],
  "status": "accepted"
}
```

Pydantic kiểm tra schema. `input_hash` được tính từ nội dung chunk, model,
prompt version và ontology version. Kết quả có cùng hash được tái sử dụng.
JSONL bị từ chối lưu nguyên lỗi, chunk ID và phản hồi thô đã giới hạn kích
thước trong `rejected_extractions.jsonl` để kiểm tra thủ công.

## 6. Trích xuất và kiểm tra

### 6.1 Trích xuất xác định

Structure extractor tạo cây văn bản từ metadata. Rule extractor nhận diện:

- viện dẫn `Điều`, `khoản`, `điểm`;
- thời lượng theo giờ, ngày, tháng, năm;
- tỷ lệ phần trăm;
- thời hạn và ngày hiệu lực.

Kết quả luật và kết quả LLM cùng dùng một schema, nhưng trường `method` phân
biệt `metadata`, `regex` và `llm`.

### 6.2 Trích xuất bằng Ollama

Model mặc định là `qwen3:8b`, cấu hình bằng `OLLAMA_MODEL`. Request sử dụng
JSON Schema, `temperature=0`, timeout hữu hạn và số lần retry hữu hạn. Prompt
yêu cầu:

- chỉ dùng nhãn trong ontology;
- không lặp lại cấu trúc Chương/Điều đã có trong metadata;
- `text` và `evidence` phải là chuỗi nguyên văn trong chunk;
- trả danh sách rỗng khi không có thông tin;
- không bổ sung kiến thức ngoài đoạn đầu vào.

Pipeline mặc định xử lý một chunk mỗi request. Concurrency cấu hình được,
nhưng giá trị mặc định là 1 để tránh quá tải GPU phổ thông.

### 6.3 Validation và chuẩn hóa

Một dòng chỉ được chấp nhận khi:

1. JSON đúng schema;
2. entity ID là duy nhất trong chunk;
3. mọi đầu quan hệ tham chiếu entity hoặc provision tồn tại;
4. type của hai đầu phù hợp domain/range;
5. `0 <= confidence <= 1`;
6. entity span khớp chính xác với `text`;
7. evidence xuất hiện nguyên văn trong chunk;
8. metadata nguồn khớp chunk đầu vào.

Chuẩn hóa ban đầu gồm Unicode NFC, khoảng trắng, chữ thường để tạo khóa và
từ điển alias có phiên bản. Không tự gộp các khái niệm có phạm vi pháp lý khác
nhau, ví dụ `người lao động` và `người lao động chưa thành niên`.

## 7. Mô hình Neo4j

Neo4j dùng labeled property graph. Constraint duy nhất được tạo cho thuộc tính
`id` của từng label chính. Index được tạo cho `normalized_name`, `chunk_id`,
`document_id` và số điều khi có ích cho truy vấn.

Loader dùng transaction theo batch và câu lệnh `MERGE` với ID ổn định. Node
được `MERGE` trước, relationship được `MERGE` sau. Relationship ngữ nghĩa lưu:

- `id` ổn định;
- `chunk_id`;
- `evidence`;
- `confidence`;
- `method`;
- `model`;
- `prompt_version`.

Nếu một batch lỗi, transaction đó rollback và loader báo chính xác danh sách
chunk chưa nạp. Pipeline không xóa dữ liệu Neo4j hiện hữu.

## 8. Docker Compose và cấu hình

Compose cung cấp hai service:

- `neo4j`, công khai cổng `7474` và `7687`, có health check và volume dữ liệu;
- `ollama`, công khai cổng `11434`, yêu cầu GPU NVIDIA, có health check và
  volume model.

Thông tin cấu hình lấy từ `.env` và cung cấp `.env.example` không chứa bí mật:

```dotenv
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change-me
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
KG_PROMPT_VERSION=kg-v1
KG_CONCURRENCY=1
```

Model được tải bằng lệnh thiết lập riêng sau khi container khỏe. Không tự động
tải model mỗi lần khởi động. Tài liệu nêu rõ yêu cầu Docker Desktop, NVIDIA
driver và khả năng GPU passthrough.

## 9. CLI và khả năng phục hồi

CLI nhận đường dẫn input/output, giới hạn số chunk để chạy thử, model,
concurrency và tùy chọn tiếp tục từ cache. Các lỗi cấu hình, Ollama không sẵn
sàng, model chưa tải, schema sai hoặc Neo4j không kết nối được phải trả exit
code khác 0 với thông báo có hành động khắc phục.

`extract` luôn ghi atomically. `load` chỉ đọc những dòng `status=accepted` và
không gọi LLM. Vì vậy có thể kiểm tra hoặc sửa tập trích xuất trước khi nạp.

## 10. Kiểm thử và tiêu chí hoàn thành

Unit test không phụ thuộc Docker và dùng fake transport/repository được tiêm
qua interface. Kiểm thử bao phủ:

- tạo graph cấu trúc từ metadata có và không có các cấp tùy chọn;
- regex cho viện dẫn, duration, deadline và rate;
- parse phản hồi đúng/sai schema;
- phát hiện span hoặc evidence không tồn tại;
- kiểm tra domain/range;
- cache theo hash;
- retry lỗi tạm thời nhưng không retry lỗi validation;
- sinh payload Neo4j và tính id ổn định;
- chạy lại loader không tạo dữ liệu trùng;
- hành vi ba lệnh CLI.

Integration test Neo4j/Ollama thật được đánh dấu riêng và không nằm trong bộ
test mặc định. Smoke test hoàn thành khi:

1. Compose khởi động và hai service healthy;
2. `extract --limit 3` tạo ba dòng hợp lệ hoặc ghi rõ dòng bị từ chối;
3. `load` hoàn tất;
4. chạy `load` lần hai không tăng số node/relationship;
5. truy vấn Neo4j trả được đường dẫn từ Document đến Provision và thực thể;
6. toàn bộ test hiện có vẫn qua.

## 11. Ngoài phạm vi phiên bản đầu

- Fine-tune PhoBERT hoặc Qwen;
- giao diện kiểm duyệt trực quan;
- tự động sửa văn bản OCR;
- suy luận pháp lý hoặc tạo câu trả lời cuối;
- đồng bộ xóa node khi nguồn bị xóa;
- triển khai production nhiều máy hoặc phân quyền người dùng Neo4j.
