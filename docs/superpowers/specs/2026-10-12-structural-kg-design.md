# Thiết kế legal_kg cấu trúc — phiên bản đầu

## Mục tiêu đã thống nhất

Embedding tìm ngữ nghĩa, keyword tìm thuật ngữ/định danh, KG lưu cấu trúc và bổ sung ngữ cảnh.
legal_kg không gọi LLM, không tạo Provision, Right, Obligation hay quan hệ ngữ nghĩa.
Thiết kế này thay hướng KG ngữ nghĩa trong `2026-09-11-legal-kg-extraction-design.md` đối với luồng mới.

## Phạm vi triển khai

Package riêng đọc JSONL, dựng graph JSON kiểm tra offline, nạp Neo4j và tra theo chunk_id.
Không sửa nguồn DOCX, parser, chunker hoặc tái sinh các chỉ mục tìm kiếm trong lần triển khai này.
Task 1 của roadmap chưa hoàn thành: hỗ trợ dữ liệu cũ bằng cảnh báo rõ ràng và chỉ nạp Neo4j khi
người chạy chọn `--allow-legacy-metadata`. Đây là graph thử nghiệm phản ánh metadata, không xác nhận phụ lục đã đúng.

## Cấu trúc và ID

- LegalDocument → Part → Chapter → Section → Article, bỏ cấp không có.
- LegalDocument → Appendix → Table; Table cũng có thể thuộc đơn vị chính.
- CONTAINS nối đơn vị; HAS_CHUNK nối đơn vị gần nhất tới Chunk.
- Mọi chunk được gắn một lần, gồm preamble, article và clause_group.
- ID cấu trúc có phạm vi đầy đủ; chunk_id nguyên gốc; chưa dựng Clause/Point.
- `structure_path` rõ ràng ưu tiên metadata cũ; đường dẫn sai thứ tự hoặc label lạ bị từ chối.

## Validation và khả năng tái lập

Từ chối input rỗng, ID trùng, text rỗng, vị trí nguồn sai, metadata mâu thuẫn, graph có orphan/cycle,
đầu cạnh thiếu hoặc nhãn ngoài allowlist. Chunk dài >6000 được giữ và cảnh báo.
source_hash là SHA256 của dòng nguồn sắp theo chunk_id; graph_hash bao phủ nội dung artifact.
Build atomically, không ghi đè input. Input thứ tự khác nhau tạo cùng graph/hash.

## Neo4j

KGNode dùng khóa duy nhất (snapshot_id, id); KGSnapshot dùng id=source_hash, có graph_hash và state.
Mỗi lần nạp một transaction cho dữ liệu, chia batch payload. Constraint được tạo riêng trước transaction.
Nạp lại graph không sinh trùng. Không ghi đè graph khác trong cùng snapshot; không xóa snapshot cũ.
Tra cứu yêu cầu snapshot rõ ràng và chỉ đọc snapshot ready. Không suy ra hiệu lực pháp lý từ snapshot.

## Thành phần

- models.py: schema và validation artifact.
- build.py: dựng graph và inspect offline.
- repository.py: transaction Neo4j và context lookup.
- cli.py: build/inspect/load/lookup, ghi atomically, báo lỗi exit code 1.
- compose.yaml/.env.example/README-kg.md: cấu hình chạy local, hướng dẫn và giới hạn.

## Tiêu chí kiểm tra

Test cấu trúc tùy chọn, scope Mục giữa các Chương, mọi loại chunk, phụ lục explicit path,
metadata sai, hash/roundtrip, rollback, snapshot isolation, CLI và toàn bộ corpus thực tế.
Integration test Neo4j thật opt-in; không báo đã xác minh server thật khi Docker chưa chạy.

## Quyết định phạm vi

Người dùng yêu cầu dựng legal_kg sau khi xem roadmap. Triển khai module hiện tại trước bước sửa
tiền xử lý, giữ cảnh báo và chặn load mặc định với metadata cũ. Chi phí: graph thử nghiệm vẫn phản ánh
sai ngữ cảnh sẵn có nếu người chạy chủ động nạp legacy; phải sửa preprocessing và tạo snapshot mới trước dùng tư vấn.
