# KG cấu trúc văn bản pháp luật

`legal_kg` dựng cấu trúc từ metadata JSONL rồi nối viện dẫn có dẫn chứng giữa các đơn vị/văn bản.
Các quy tắc chạy trực tiếp trên corpus, không gọi LLM/Ollama.
Nhánh này hỗ trợ truy vết và lấy ngữ cảnh; embedding và BM25 sẽ dùng cùng `chunk_id` ở giai đoạn sau.

## 1. Tạo và kiểm tra graph không cần Docker

Chạy tại thư mục gốc dự án:

```powershell
python -m legal_kg.cli build
python -m legal_kg.cli inspect --chunk-id 00e7045e70338c40ac64
```

Mặc định đọc `output/preprocessed/legal_chunks.jsonl`, xuất atomically thành
`output/kg/structural_graph.json`. Có thể đổi bằng `--input` và `--output`.
Lệnh `inspect` trả đường dẫn từ văn bản tới đơn vị chứa chunk, các chunk cùng đơn vị theo thứ tự,
quan hệ đi vào/đi ra của các node trên đường dẫn, node liên quan và cảnh báo.

Node: `LegalDocument`, `Part`, `Chapter`, `Section`, `Article`, `Clause`, `Point`, `Appendix`, `Table`, `Chunk`.
Quan hệ: `CONTAINS` giữa các đơn vị cấu trúc; `HAS_CHUNK` từ đơn vị gần nhất tới chunk.
Các cấp thiếu được bỏ qua. `article` và `clause_group` đều được gắn, không lọc mất điều dài.
`preamble` được nối vào cấp gần nhất trong metadata, hoặc văn bản nếu không có cấp nào.

ID cấu trúc dùng đầy đủ đường dẫn, ví dụ `doc-01/chapter-VII/section-2/article-111`;
ID Chunk giữ nguyên JSONL. Khoản/Điểm có node riêng khi xuất hiện trong `structure_path`,
ví dụ `doc-01/chapter-II/article-12/clause-1/point-a`.
Metadata cũ chỉ có `clause_ids`/`point_ids` được giữ làm thuộc tính, không suy đoán node từ các danh sách này.

## 2. Tiền xử lý v4, graph legal-kg-v2 và tương thích dữ liệu cũ

Snapshot hiện tại có `structure_path` đến cấp Khoản/Điểm, phụ lục và bảng được tách riêng;
3.689 chunk đều không vượt 6000 ký tự. Bảng giữ tiêu đề, ô trống và tọa độ ô gộp.
Graph mới dùng `legal-kg-v2`; vẫn đọc được artifact cấu trúc `structural-kg-v1` với hash cũ.
KG lưu `source_spans_json`, `table_headers_json`, `table_rows_json` trên node Chunk để giữ
metadata lồng nhau mà Neo4j không hỗ trợ trực tiếp làm property.

Khi đọc đầu ra v2, metadata cũ chưa tách phụ lục/bảng và có thể gắn nội dung phụ lục vào Điều cuối.
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

Các type hỗ trợ: `part`, `chapter`, `section`, `article`, `clause`, `point`, `appendix`, `table`.
Appendix bắt đầu nhánh riêng dưới văn bản; table có thể nằm dưới appendix hoặc đơn vị chính.
`structure_path: []` nghĩa là chunk trực tiếp thuộc văn bản. Trường này phải đến từ bước tiền xử lý đã kiểm tra;
chỉ thêm trường không đủ chứng minh cấu trúc đã đúng. Parser/chunking thuộc `legal_preprocessing`.

## 3. Khởi động Neo4j và nạp dữ liệu

### Bản cài Windows local

Máy hiện được cài Neo4j Community 5.26.32 tại
`%LOCALAPPDATA%/Programs/Neo4j/neo4j-community-5.26.32`, chạy bằng Java đã có trên máy.
Database lưu tại thư mục `data` của bản cài này. Bản cài Windows và Docker là hai database riêng.
Nếu dùng bản Windows, giữ các cổng 7474/7687 cho bản này.

Khởi động lại sau khi tắt máy, và mở giao diện xem KG:

```powershell
powershell -NoProfile -File scripts/start-neo4j.ps1 -OpenBrowser
```

Mở http://localhost:7474/browser/, kết nối `bolt://localhost:7687`, user `neo4j`,
mật khẩu là giá trị `NEO4J_PASSWORD` trong `.env` tại thư mục gốc dự án.
Script chạy Neo4j dưới tài khoản Windows hiện tại; chưa đăng ký Windows service tự chạy khi khởi động máy.
Các câu lệnh xem KG đã được lưu ở `output/kg/view_queries.cypher`.
Chạy dòng `:param snapshot` trước, rồi chạy từng truy vấn và chọn chế độ Graph trong Browser.

Node Khoản/Điểm có `title` chứa đầy đủ nội dung nguồn của đơn vị đó, gồm số/ký hiệu;
Khoản bao gồm cả các Điểm con. Tiêu đề được giữ đầy đủ cả khi chunk bị chia nhỏ.
Caption vẫn dùng số/ký hiệu để cây dễ đọc. Trong Neo4j Browser, chạy `:style`,
chọn Upload và nhập `output/kg/neo4j-browser.grass`. Style đặt nhãn `Điều 35`, `Khoản 1`,
`Điểm a`, `Chunk 123` bằng các thuộc tính đã có, đồng thời phân biệt màu theo loại node.
Trong bảng Results overview, kéo nhãn chung `KGNode` xuống dưới các nhãn cụ thể như
`Article`, `Clause`, `Point`, `Chunk`: Browser ưu tiên nhãn đứng trước khi node có nhiều nhãn.
Sau đó chạy lại truy vấn xem cây. Thao tác chỉ đổi cách hiển thị trong Browser.
Tham khảo [hướng dẫn styling của Neo4j](https://neo4j.com/docs/browser/operations/browser-styling/).

Bản ZIP được lấy từ [Neo4j Deployment Center](https://neo4j.com/deployment-center/);
tham khảo [hướng dẫn cài Windows](https://neo4j.com/docs/operations-manual/current/installation/windows/).

### Chạy qua Docker

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

Với snapshot hiện tại:

```powershell
python -m legal_kg.cli load
```

Chỉ dùng `--allow-legacy-metadata` nếu chủ động nạp snapshot cũ để thử nghiệm sau khi đọc cảnh báo.
Loader kiểm tra graph trước khi ghi; không nhận label/relationship ngoài allowlist.
Các tham số kết nối: `--uri`, `--user`, `--database` hoặc `NEO4J_URI`, `NEO4J_USER`, `NEO4J_DATABASE`.
Password chỉ lấy qua `NEO4J_PASSWORD`.

Các truy vấn ghi được chia payload theo `--batch-size` (mặc định 500), nhưng toàn graph commit
trong **một transaction**. Lỗi nạp rollback toàn bộ dữ liệu lần nạp; constraint schema có thể vẫn tồn tại.
Thiết kế này phù hợp corpus nhỏ hiện tại, chưa phải loader cho hàng triệu node.

## 4. Snapshot và truy vấn

`source_hash` được tính từ phiên bản schema, phiên bản quy tắc nối viện dẫn và toàn bộ dòng nguồn
theo thứ tự chunk_id; đổi các giá trị này sẽ tạo snapshot khác, giữ snapshot cũ để đối chiếu.
`graph_hash` kiểm tra tính toàn vẹn artifact, không phải chữ ký xác thực.
Neo4j dùng constraint `(snapshot_id, id)` trên `KGNode`; mỗi snapshot độc lập,
nạp lại graph không nhân đôi node/cạnh. Graph khác nhưng cùng source_hash bị từ chối.
Snapshot cũ không bị xóa và không tự chọn snapshot mới nhất khi truy vấn.

Lấy hash từ kết quả build hoặc file JSON:

```powershell
$kgGraph = Get-Content -Raw -Encoding UTF8 output/kg/structural_graph.json | ConvertFrom-Json
python -m legal_kg.cli lookup --snapshot $kgGraph.source_hash --chunk-id 00e7045e70338c40ac64
```

Trong Neo4j Browser, truyền tham số `snapshot` bằng source_hash tương ứng:

```cypher
MATCH (parent:KGNode)-[:HAS_CHUNK]->(c:Chunk)
WHERE c.snapshot_id = $snapshot AND parent.snapshot_id = $snapshot
  AND c.id = '00e7045e70338c40ac64'
RETURN parent, c;
```

Luôn dùng cùng snapshot với embedding/BM25. Lookup trả các chunk cùng đơn vị và quan hệ
liên quan để lớp context chọn tiếp theo ngân sách token; chưa tích hợp xếp hạng hoặc LLM.

## 5. Viện dẫn, hướng dẫn và quy định chi tiết

Các cạnh ngữ nghĩa được tạo sau khi đã dựng đủ node của toàn corpus:

| Cạnh | Chiều |
|---|---|
| `REFERS_TO` | Đơn vị viện dẫn → đơn vị/văn bản được viện dẫn |
| `GUIDES` | Đơn vị/văn bản hướng dẫn → đơn vị/văn bản được hướng dẫn |
| `DETAILS` | Đơn vị/văn bản quy định chi tiết → đơn vị/văn bản được quy định chi tiết |

Quan hệ viện dẫn/hướng dẫn/quy định chi tiết giữa các đơn vị ở hai văn bản còn được tổng hợp thành
cạnh cùng loại giữa hai `LegalDocument`, giữ nguyên chiều và dẫn chứng. Truy vấn cạnh đi vào để tìm
văn bản/điều hướng dẫn cho văn bản/điều đang xét:

```cypher
MATCH (guide:LegalDocument)-[r:GUIDES|DETAILS]->(law:LegalDocument)
WHERE law.snapshot_id = $snapshot AND guide.snapshot_id = $snapshot AND law.id = 'doc-01'
RETURN guide.title, type(r), r.evidence_json;
```

Để hiển thị đủ 8 văn bản cùng các viện dẫn, dùng câu dưới sau khi đặt `$snapshot` bằng
dòng `:param snapshot` trong `output/kg/view_queries.cypher`:

```cypher
MATCH (d:LegalDocument {snapshot_id: $snapshot})
OPTIONAL MATCH (d)-[r:REFERS_TO|GUIDES|DETAILS]->(other:LegalDocument {snapshot_id: $snapshot})
RETURN d, r, other;
```

`OPTIONAL MATCH` giữ cả văn bản không có cạnh đi ra. Chỉ lọc `GUIDES`/`DETAILS` sẽ chỉ hiện
6 văn bản trong corpus này: NĐ 293/2025 và NĐ 12/2022 có các cạnh viện dẫn `REFERS_TO`.
Snapshot hiện tại có 8 node văn bản và 16 cạnh giữa văn bản: 9 `REFERS_TO`, 3 `GUIDES`, 4 `DETAILS`.
Luôn chọn snapshot hiện tại; truy vấn toàn database có thể hiển thị thêm các bản dựng cũ.

Mỗi cạnh có `evidence_json`: danh sách `{chunk_id, quote, method}`. `quote` phải xuất hiện
nguyên văn trong chunk nguồn; `method` là `rule` hoặc `explicit`. Loader kiểm tra dẫn chứng
và lưu thuộc tính này trên cạnh Neo4j. Quan hệ ngữ nghĩa không tham gia tính cha–con cấu trúc.

Bộ quy tắc nhận diện tên/số hiệu, Điều/Khoản/Điểm, danh sách số và cách viết chủ động/bị động.
Số hiệu/năm được dùng để phân biệt phiên bản; dẫn Luật BHXH 2014 không được tự nối vào Luật BHXH 2024.
Tên luật không kèm phiên bản cũng không được tự gán vào phiên bản có năm mới hơn văn bản nguồn.
Đây là bộ lọc bảo thủ cho viện dẫn thiếu thông tin; số hiệu/năm được ghi rõ trong dẫn chứng vẫn được ưu tiên,
chẳng hạn văn bản nguồn đã được sửa đổi. Luật BHXH 2024 có các viện dẫn Bộ luật Lao động 2019,
được giữ ở cấp đơn vị và tổng hợp thành cạnh `REFERS_TO` giữa hai văn bản.
Đích thiếu hoặc không rõ được giữ thành cảnh báo `Unresolved reference`, không tạo node thay thế.
Đây là trích xuất theo mẫu câu, chưa bao phủ mọi cách diễn đạt, sửa đổi/thay thế hoặc hiệu lực pháp lý.

Với cú pháp chưa được nhận diện, có thể bổ sung trường `references` trong dòng chunk đã đối chiếu:

```json
{
  "references": [{
    "type": "DETAILS",
    "target": {"document_id": "doc-01", "article": "169"},
    "evidence": "Nghị định này quy định chi tiết Điều 169 của Bộ luật Lao động về tuổi nghỉ hưu."
  }]
}
```

`target` có thể thêm `clause`, `point`; các số được ghi bằng chuỗi. Nếu bỏ `source`,
nguồn là đơn vị trực tiếp chứa chunk; có thể cung cấp địa chỉ `source` theo cùng cấu trúc.
Địa chỉ chỉ có `document_id` chỉ văn bản. `evidence` phải nằm trong `text`; đích phải tồn tại
trong corpus. Có thể dùng LLM để đề xuất metadata này ở bước biên tập riêng rồi đối chiếu nguồn;
pipeline hiện tại không tự gọi LLM và không tự suy luận quan hệ khi không có dẫn chứng.

## 6. Tiêu đề gốc và tiêu đề rút gọn

Chunk và node văn bản giữ cả `title` và `short_title` tùy chọn. `query_title` dùng
`short_title` nếu có, nếu không dùng `title`. Alias được cấu hình tại
`DocumentSpec.short_title` trong `legal_preprocessing/manifest.py`, ví dụ `BLLĐ 2019`.
Tên gốc và số hiệu vẫn tra cứu được khi có alias; alias trùng trả về tất cả văn bản phù hợp.

```powershell
python -m legal_kg.cli search --title "BLLĐ 2019"
python -m legal_kg.cli search --title "Bộ luật Lao động 2019"
python -m legal_kg.cli search-db --snapshot $kgGraph.source_hash --title "BLLĐ 2019"
```

`search` tra cứu chính xác tên/alias/số hiệu đã chuẩn hóa và trả `chunk_ids`, không cần Neo4j.
Trong ứng dụng, tạo `TitleIndex(graph)` một lần để tái sử dụng dictionary cho nhiều lượt tra cứu.
`search-db` dùng index ghép `(snapshot_id, query_title_key)`, `(snapshot_id, title_key)` và
`(snapshot_id, document_number)`, được tạo khi `load`. Cả hai hỗ trợ tên không dấu/khác hoa thường.
`search-db` trả node văn bản; dùng cấu trúc `CONTAINS`/`HAS_CHUNK` để lấy nội dung.

Alias giúp thêm cách gọi và thu hẹp tập văn bản; việc rút ngắn chuỗi tự nó không bảo đảm truy vấn nhanh hơn.
Tốc độ phụ thuộc index và cách retrieval. Chưa có benchmark tốc độ hoặc lớp embedding/BM25.
Với tám văn bản hiện tại, alias khai báo rõ trong manifest dễ kiểm tra và không tốn chi phí LLM.

## 7. Kiểm thử

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
