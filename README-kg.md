# KG cấu trúc văn bản pháp luật

`legal_kg` dựng graph trực tiếp từ metadata JSONL, không gọi LLM/Ollama.
Nhánh này hỗ trợ truy vết và lấy ngữ cảnh; embedding và BM25 sẽ dùng cùng `chunk_id` ở giai đoạn sau.

## 1. Tạo và kiểm tra graph không cần Docker

Chạy tại thư mục gốc dự án:

```powershell
python -m legal_kg.cli build
python -m legal_kg.cli inspect --chunk-id 4b93eeaf2c2dce28ba84
```

Mặc định đọc `output/preprocessed/legal_chunks.jsonl`, xuất atomically thành
`output/kg/structural_graph.json`. Có thể đổi bằng `--input` và `--output`.
Lệnh `inspect` trả đường dẫn từ văn bản tới đơn vị chứa chunk, các chunk cùng đơn vị theo thứ tự và cảnh báo.

Node: `LegalDocument`, `Part`, `Chapter`, `Section`, `Article`, `Appendix`, `Table`, `Chunk`.
Quan hệ: `CONTAINS` giữa các đơn vị cấu trúc; `HAS_CHUNK` từ đơn vị gần nhất tới chunk.
Các cấp thiếu được bỏ qua. `article` và `clause_group` đều được gắn, không lọc mất điều dài.
`preamble` được nối vào cấp gần nhất trong metadata, hoặc văn bản nếu không có cấp nào.

ID cấu trúc dùng đầy đủ đường dẫn, ví dụ `doc-01/chapter-VII/section-2/article-111`;
ID Chunk giữ nguyên JSONL. `clause_ids`/`point_ids` là thuộc tính, không tạo node Khoản/Điểm khi chưa có quan hệ cha–con đáng tin cậy.

## 2. Giới hạn dữ liệu hiện tại

Metadata cũ chưa tách phụ lục/bảng và có thể gắn nội dung phụ lục vào Điều cuối.
Module không sửa hay suy đoán nội dung nguồn. Graph xuất ra là bản phản ánh metadata để kiểm tra,
không phải xác nhận cấu trúc pháp luật đã đúng. Cảnh báo `Legacy metadata` được ghi trong graph và in khi build/inspect.
Chunk dài hơn 6000 ký tự cũng được cảnh báo, không bỏ hoặc tự chia lại trong KG.

Đầu vào mới có thể cung cấp `structure_path` rõ ràng, được ưu tiên hơn các trường cũ:

```json
[
  {"type": "appendix", "number": "I", "title": "Danh mục địa bàn"},
  {"type": "table", "number": "block-100", "title": "Các vùng"}
]
```

Các type hỗ trợ: `part`, `chapter`, `section`, `article`, `appendix`, `table`.
Appendix bắt đầu nhánh riêng dưới văn bản; table có thể nằm dưới appendix hoặc đơn vị chính.
`structure_path: []` nghĩa là chunk trực tiếp thuộc văn bản. Trường này phải đến từ bước tiền xử lý đã kiểm tra;
chỉ thêm trường không đủ chứng minh cấu trúc đã đúng. Chưa triển khai sửa parser/chunking trong module này.

## 3. Khởi động Neo4j và nạp dữ liệu

Cài driver, bật Docker Desktop rồi đặt mật khẩu trong phiên PowerShell:

```powershell
python -m pip install -r requirements.txt
$env:NEO4J_PASSWORD = 'your-local-password'
docker compose up -d neo4j
docker compose ps
```

Mật khẩu cần ít nhất 8 ký tự. Docker Compose cũng có thể đọc `.env` tạo từ `.env.example`,
nhưng CLI Python chỉ đọc biến môi trường của tiến trình. Không đưa mật khẩu vào Git.
Neo4j Browser: http://localhost:7474, user `neo4j`.

Với dữ liệu hiện tại, chỉ nạp bản thử nghiệm sau khi đọc cảnh báo:

```powershell
python -m legal_kg.cli load --allow-legacy-metadata
```

Sau khi tiền xử lý cung cấp `structure_path` đúng cho toàn corpus, dùng `load` không cần cờ này.
Loader kiểm tra graph trước khi ghi; không nhận label/relationship ngoài allowlist.
Các tham số kết nối: `--uri`, `--user`, `--database` hoặc `NEO4J_URI`, `NEO4J_USER`, `NEO4J_DATABASE`.
Password chỉ lấy qua `NEO4J_PASSWORD`.

Các truy vấn ghi được chia payload theo `--batch-size` (mặc định 500), nhưng toàn graph commit
trong **một transaction**. Lỗi nạp rollback toàn bộ dữ liệu lần nạp; constraint schema có thể vẫn tồn tại.
Thiết kế này phù hợp corpus nhỏ hiện tại, chưa phải loader cho hàng triệu node.

## 4. Snapshot và truy vấn

`source_hash` được tính từ toàn bộ dòng nguồn theo thứ tự chunk_id; đổi nội dung/metadata sẽ đổi hash.
`graph_hash` kiểm tra tính toàn vẹn artifact, không phải chữ ký xác thực.
Neo4j dùng constraint `(snapshot_id, id)` trên `KGNode`; mỗi snapshot độc lập,
nạp lại graph không nhân đôi node/cạnh. Graph khác nhưng cùng source_hash bị từ chối.
Snapshot cũ không bị xóa và không tự chọn snapshot mới nhất khi truy vấn.

Lấy hash từ kết quả build hoặc file JSON:

```powershell
$kgGraph = Get-Content -Raw -Encoding UTF8 output/kg/structural_graph.json | ConvertFrom-Json
python -m legal_kg.cli lookup --snapshot $kgGraph.source_hash --chunk-id 4b93eeaf2c2dce28ba84
```

Trong Neo4j Browser, truyền tham số `snapshot` bằng source_hash tương ứng:

```cypher
MATCH (a:Article)-[:HAS_CHUNK]->(c:Chunk)
WHERE c.snapshot_id = $snapshot AND c.id = '4b93eeaf2c2dce28ba84'
RETURN a, c;
```

Luôn dùng cùng snapshot với embedding/BM25. Lookup trả các chunk cùng đơn vị để lớp context
chọn tiếp theo ngân sách token; chưa tích hợp xếp hạng hoặc LLM.

## 5. Kiểm thử

```powershell
python -m pytest -q
```

Test mặc định không cần Docker. Kiểm thử Neo4j thật dùng database thử nghiệm và chỉ xóa các snapshot
UUID do chính test tạo:

```powershell
$env:LEGAL_KG_INTEGRATION = '1'
python -m pytest tests/test_kg_integration.py -q
Remove-Item Env:LEGAL_KG_INTEGRATION
```

Tham khảo API transaction và Docker theo tài liệu chính thức:
[Neo4j Python transactions](https://neo4j.com/docs/python-manual/current/transactions/),
[Neo4j Docker](https://neo4j.com/docs/operations-manual/current/docker/introduction/).
