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
