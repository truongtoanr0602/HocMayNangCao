# Thiết kế pipeline tiền xử lý văn bản pháp luật DOCX

## 1. Mục tiêu

Thay nguồn đầu vào của pipeline từ tám PDF sang tám tệp DOCX trong `data/`,
giữ cách phân cấp và chunk theo Phần/Chương/Mục/Điều/Khoản/Điểm, đồng thời loại
bỏ hoàn toàn OCR khỏi luồng chạy chính. Đầu ra vẫn gồm JSONL tổng hợp, JSONL
theo tài liệu, dữ liệu trung gian và báo cáo QA.

Pipeline chỉ xử lý tám tài liệu 01–08 được khai báo trong manifest và không quét
`data/tuychon/`. File số 07 phải được chuyển một lần từ `.doc` sang `.docx` trước
khi chạy pipeline; định dạng `.doc` cũ không được hỗ trợ lúc chạy.

## 2. Nguồn dữ liệu

Manifest trỏ tới các tệp sau:

- `data/01_Bo_luat_Lao_dong_2019_45-2019-QH14.docx`
- `data/02_ND145-2020_Huong_dan_BLLD.docx`
- `data/03_TT10-2020_Noi_dung_Hop_dong_Lao_dong.docx`
- `data/04_ND293-2025_Luong_toi_thieu_2026.docx`
- `data/05_Luat_BHXH_2024_41-2024-QH15.docx`
- `data/06_ND158-2025_BHXH_bat_buoc.docx`
- `data/07_ND135-2020_Tuoi_nghi_huu.docx`
- `data/08_ND12-2022_Xu_phat_Lao_dong_BHXH.docx`

Các PDF được giữ để đối chiếu thủ công nhưng không được đọc bởi pipeline.

## 3. Kiến trúc và luồng dữ liệu

Luồng mới là:

`DOCX -> khối tài liệu -> khối đã làm sạch -> đơn vị pháp lý -> chunk -> JSONL`

### 3.1. Trích xuất DOCX

Một extractor DOCX dùng `python-docx` và duyệt phần tử XML thân tài liệu theo
thứ tự. Hai loại khối được hỗ trợ:

- đoạn văn (`w:p`), gồm nội dung các run theo thứ tự;
- bảng (`w:tbl`), gồm từng hàng và từng ô theo thứ tự đọc trái sang phải.

Mỗi đoạn văn có nội dung trở thành một khối. Với bảng, mỗi hàng trở thành một
khối văn bản; nội dung các ô được nối bằng dấu ` | ` để không làm mất ranh giới
cột. Các đoạn nằm bên trong ô không được phát lại lần thứ hai. Header/footer,
footnote, hình ảnh và textbox không thuộc thân tài liệu không được nhập vào nội
dung chính. Tài liệu không có đủ nội dung chữ làm lần chạy thất bại với thông báo
nêu đúng tệp.

Extractor trả về mô hình vị trí tổng quát theo khối, không giả lập trang Word.
Chỉ số khối bắt đầu từ 1 và ổn định khi nội dung DOCX không thay đổi.

### 3.2. Làm sạch và phân tích cấu trúc

Logic chuẩn hóa Unicode và nhận diện Phần/Chương/Mục/Điều/Khoản/Điểm hiện có
được tái sử dụng. Quy tắc làm sạch không còn suy luận header/footer lặp theo
trang; các phần này đã bị loại ở ranh giới extractor. Dòng rỗng, ký tự điều khiển
và khoảng trắng thừa vẫn bị loại. Nội dung bảng được giữ nguyên như khối văn
bản để không làm mất biểu mẫu hoặc phụ lục.

Parser phải hoạt động trên chuỗi khối liên tục và giữ chỉ số khối nguồn trên mọi
`SourceLine`. Các biến thể OCR chỉ còn được giữ để tương thích với dữ liệu cũ,
không phải đường xử lý chính.

### 3.3. Chunking

Chiến lược chunk không đổi: ưu tiên một Điều, sau đó chia theo Khoản và câu khi
vượt `max_chars`. Mọi chunk con kế thừa metadata cấu trúc và khoảng khối nguồn.
`chunk_id` tiếp tục được tính từ định danh tài liệu, Điều, chỉ số chunk trong Điều
và nội dung chuẩn hóa, nên ổn định qua các lần chạy trên cùng nguồn.

## 4. Schema và truy vết

Các trường hiện có được giữ để giảm tác động tới mã sử dụng JSONL:

- `page_start`, `page_end`: luôn là `null` đối với nguồn DOCX;
- `paragraph_start`, `paragraph_end`: chỉ số khối đầu/cuối trong thân DOCX;
- các trường tài liệu, cấu trúc, chunk và nội dung giữ nguyên ý nghĩa hiện tại.

Tên `paragraph_*` được giữ theo yêu cầu tương thích nghiệp vụ, nhưng chỉ số này
bao gồm cả hàng bảng; tài liệu intermediate ghi rõ `block_type` là `paragraph`
hoặc `table_row` để đối chiếu. Không điền số trang giả và không dùng pagination
do Word render vì kết quả phụ thuộc font, driver máy in và phiên bản Word.

## 5. Dữ liệu trung gian và QA

Mỗi `intermediate/doc-XX.blocks.json` chứa danh sách khối thô, khối sạch và các
khối bị loại, gồm ít nhất `block_number`, `block_type` và `text`. Các tệp
`.pages.json` cũ không còn được tạo bởi pipeline DOCX.

Báo cáo QA thay thống kê trang bằng số khối và bổ sung:

- số đoạn văn và số hàng bảng;
- số ký tự thô/sạch;
- số Điều và số chunk;
- danh sách cảnh báo parser;
- kiểm tra đủ tám tài liệu, không có chunk rỗng hoặc ID trùng;
- kiểm tra mọi `source_file` có đuôi `.docx` và không thuộc `data/tuychon/`;
- kiểm tra khoảng `paragraph_start/paragraph_end` hợp lệ.

Ghi đầu ra vẫn dùng file tạm rồi thay thế. Nếu một DOCX thiếu, hỏng hoặc không có
đủ chữ, toàn bộ lần chạy thất bại trước khi thay file tổng hợp.

## 6. Chuyển file số 07

`07_ND135-2020_Tuoi_nghi_huu.doc` được chuyển một lần sang DOCX bằng Microsoft
Word hoặc LibreOffice và lưu cạnh file cũ. File DOCX sau chuyển đổi được kiểm tra
có thể mở bằng `python-docx` và có nội dung chữ trước khi manifest được đổi.
Pipeline không tự khởi động Word/LibreOffice và không tự chuyển đổi `.doc` trong
mỗi lần chạy, nhằm giữ môi trường chạy đơn giản và tái lập.

## 7. Kiểm thử và tiêu chí chấp nhận

Kiểm thử theo TDD bao phủ:

1. DOCX có đoạn văn được đọc đúng thứ tự.
2. DOCX có bảng giữ thứ tự hàng/ô và không lặp nội dung ô.
3. Header/footer không xuất hiện trong nội dung trích xuất.
4. DOCX rỗng hoặc hỏng báo lỗi có tên tệp.
5. Manifest chứa đúng tám `.docx` và loại `data/tuychon/`.
6. Pipeline phát sinh `blocks.json`, JSONL theo tài liệu, JSONL tổng và QA.
7. Mọi chunk DOCX có `page_start/page_end = null` và khoảng paragraph hợp lệ.
8. Các số Điều trong từng tài liệu liên tục theo tiêu chí QA hiện hành.
9. Chạy trên tám tài liệu thật hoàn tất và báo cáo QA có trạng thái `passed`.

## 8. Ngoài phạm vi

- OCR và trích xuất PDF trong luồng chạy chính.
- Hỗ trợ trực tiếp `.doc`, `.odt` hoặc tài liệu trong `data/tuychon/`.
- Pagination giống giao diện Microsoft Word.
- Trích xuất nội dung từ ảnh, textbox, chú thích hoặc tracked changes đã xóa.
- Thay đổi logic Knowledge Graph trong `legal_preprocessing/extractor.py`.
