# Tiền xử lý văn bản pháp luật từ DOCX

Pipeline xử lý đúng tám tệp DOCX `data/01...08`, không lấy `data/tuychon`, và
xuất JSONL theo cấu trúc Điều/Khoản/Điểm. PDF chỉ được giữ để đối chiếu và không
tham gia trích xuất; pipeline không dùng OCR.

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python -m legal_preprocessing.cli --output output/preprocessed --max-chars 6000
```

Kết quả chính là `output/preprocessed/legal_chunks.jsonl`. Thư mục
`by_document` chứa kết quả riêng, `intermediate` chứa `*.blocks.json` để đối
chiếu theo khối DOCX, và `qa_report.json`/`qa_report.md` chứa thống kê kiểm tra.

DOCX không lưu pagination ổn định. Vì vậy `page_start` và `page_end` luôn là
`null`; `paragraph_start` và `paragraph_end` là vị trí khối nguồn bắt đầu từ 1.
Khối có thể là một đoạn văn hoặc một hàng bảng. Trong hàng bảng, nội dung các ô
được nối bằng ` | `.

Pipeline chỉ hỗ trợ `.docx`. Tệp `.doc` cũ phải được chuyển sang `.docx` một lần
trước khi chạy.

## Schema v4: chia theo cấp nhỏ nhất, phụ lục, bảng và nguồn

- Tiêu đề độc lập `Phụ lục`, `Phụ lục I`, `Phụ lục II`... mở nhánh riêng dưới văn bản.
  Câu viện dẫn như `Phụ lục III ban hành kèm theo...` trong một điều không mở nhánh.
  Chương/Điều trong biểu mẫu phụ lục được giữ làm nội dung, không nhập vào cấu trúc điều chính.
- `chunk_type` có `preamble`, `article`, `clause`, `point`, `appendix`, `table`.
  Bảng tách thành đơn vị riêng, giữ ngữ cảnh Điều hoặc Phụ lục chứa bảng.
- `structure_path` là danh sách `{type, number, title}` dùng trực tiếp cho `legal_kg`.
  Phụ lục không đánh số dùng `block-N`, bảng dùng `block-N` tại khối bắt đầu, không giả lập số pháp lý.
- `source_spans` ghi `block_number`, `start`, `end` trong **khối sạch** và `chunk_start`, `chunk_end`
  trong chunk. Offset tính theo ký tự Python, đầu bao gồm/cuối không bao gồm; không phải byte hoặc vị trí Word.
- Bảng giữ `table_id`, `table_headers`, `table_rows` gồm số hàng, cells và cell_origins.
  Cột trống giữ nguyên vị trí. Ô gộp chỉ phát nội dung ở vị trí đầu; các vị trí phủ còn lại trống
  và trỏ về tọa độ `[hàng, cột]` bắt đầu từ 1. Header mặc định là hàng đầu và các hàng Word đánh dấu lặp.
  Bảng lồng được giữ trong nội dung ô cha, chưa tạo node riêng cho bảng lồng.
- Chunking luôn chia theo cấp nhỏ nhất của từng nhánh, kể cả điều rất ngắn.
  Điều không có Khoản giữ một chunk; Khoản không có Điểm giữ một chunk;
  Khoản có Điểm chia riêng từng Điểm. Số Điểm lặp ở Khoản khác có đường dẫn khác nhau.
  Tiêu đề và phần dẫn của Điều/Khoản đi cùng nội dung con, có span nguồn tương ứng.
  Sau khi chia theo cấu trúc mới áp dụng giới hạn ký tự: một đơn vị quá dài được tách tiếp
  theo dòng/câu/khoảng trắng hoặc cắt chuỗi, giữ cùng đường dẫn pháp lý trên mỗi mảnh.
  Nội dung dài không có cấu trúc con cũng có thể cần nhiều mảnh; không ghép hai đơn vị con khác nhau.
  Header bảng được giữ trong metadata mỗi chunk, không tự chèn lại vào text nguồn.
- `title` giữ nguyên tên văn bản từ manifest; `short_title` là alias tùy chọn, mặc định `null`.
  Cấu hình `DocumentSpec.short_title` trong `legal_preprocessing/manifest.py`; pipeline không gọi LLM.
- QA kiểm tra giới hạn ký tự, đường dẫn, span khớp khối sạch và đủ nội dung từ đơn vị parser đến chunk.
  Điều này không xác nhận tính chính xác/hiệu lực pháp lý của nguồn. Các cảnh báo parser cần đối chiếu thủ công.

Sau khi đổi cách chia hoặc metadata, chạy lại `python -m legal_kg.cli build`.
Snapshot/hash sẽ thay đổi; embedding và BM25 phải dùng cùng bộ chunk mới khi được triển khai.
