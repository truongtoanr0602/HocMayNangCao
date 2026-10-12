# QUY TRÌNH CHUẨN BỊ DỮ LIỆU VÀ XỬ LÝ NHÃN CẤU TRÚC

**Nhóm 4**  
**Tháng 9 năm 2026**

## Tóm tắt

Báo cáo trình bày quy trình chuẩn bị tập dữ liệu gồm tám văn bản quy phạm pháp
luật trong lĩnh vực lao động và bảo hiểm xã hội. Nguồn đầu vào được chuẩn hóa về
định dạng DOCX nhằm khai thác trực tiếp nội dung chữ, hạn chế lỗi nhận dạng ký tự
và bảo toàn tốt hơn cấu trúc đoạn văn, bảng biểu. Pipeline lần lượt thực hiện:
trích xuất các khối nội dung theo thứ tự tài liệu, chuẩn hóa văn bản, khôi phục
cấu trúc pháp lý, chia đoạn theo Điều/Khoản và gắn siêu dữ liệu truy vết.

Kết quả thu được **672 chunk** từ **6.743 khối nguồn**, bao phủ **611 Điều** của
tám văn bản. Đầu ra vượt qua toàn bộ kiểm tra QA: đủ tám tài liệu, không có chunk
rỗng, không có `chunk_id` trùng, không chứa tài liệu ngoài phạm vi và mọi khoảng
vị trí nguồn đều hợp lệ. Bộ kiểm thử hiện gồm **28 trường hợp**, tất cả đều đạt.

## 1. Mục tiêu và phạm vi

Mục tiêu của bước tiền xử lý là chuyển các văn bản pháp luật ở định dạng DOCX
thành tập dữ liệu JSON Lines có cấu trúc, phù hợp cho truy hồi thông tin, xây dựng
Knowledge Graph và các bước học máy tiếp theo. Khác với văn bản thông thường, ý
nghĩa của một đoạn luật phụ thuộc mạnh vào vị trí trong Chương, Mục, Điều, Khoản
và Điểm. Vì vậy, pipeline ưu tiên bảo toàn đơn vị pháp lý thay vì chia hoàn toàn
theo một độ dài cố định.

Tập đầu vào gồm đúng tám tệp DOCX được khai báo tường minh trong manifest:

| ID | Văn bản | Số/ký hiệu |
|---|---|---|
| doc-01 | Bộ luật Lao động 2019 | 45/2019/QH14 |
| doc-02 | Nghị định hướng dẫn Bộ luật Lao động | 145/2020/NĐ-CP |
| doc-03 | Thông tư về nội dung hợp đồng lao động | 10/2020/TT-BLĐTBXH |
| doc-04 | Nghị định về lương tối thiểu năm 2026 | 293/2025/NĐ-CP |
| doc-05 | Luật Bảo hiểm xã hội 2024 | 41/2024/QH15 |
| doc-06 | Nghị định về bảo hiểm xã hội bắt buộc | 158/2025/NĐ-CP |
| doc-07 | Nghị định về tuổi nghỉ hưu | 135/2020/NĐ-CP |
| doc-08 | Nghị định xử phạt về lao động và bảo hiểm xã hội | 12/2022/NĐ-CP |

Các tài liệu trong `data/tuychon/` không thuộc tập dữ liệu chính. Pipeline không
quét thư mục đệ quy nên việc thêm tệp mới vào `data/` không làm thay đổi đầu ra
ngoài ý muốn.

Trong báo cáo này, “nhãn” là nhãn cấu trúc và metadata được xác định từ văn bản,
chẳng hạn Chương, Điều, danh sách Khoản, danh sách Điểm, loại chunk và vị trí khối
nguồn. Đây không phải là nhãn nội dung do người chú giải gán thủ công.

## 2. Tổng quan quy trình

Quy trình tiền xử lý phiên bản 2.0.0 gồm sáu bước:

```text
8 tệp DOCX được khai báo trong manifest
                  ↓
Trích xuất đoạn văn và hàng bảng theo thứ tự tài liệu
                  ↓
Chuẩn hóa Unicode, khoảng trắng và dấu câu
                  ↓
Khôi phục Phần – Chương – Mục – Điều – Khoản – Điểm
                  ↓
Chia chunk theo cấu trúc pháp lý và gắn metadata
                  ↓
JSONL tổng hợp, JSONL theo tài liệu, blocks.json và báo cáo QA
```

Mỗi khối có một `block_number` bắt đầu từ 1. Chỉ số này được duy trì xuyên suốt
quá trình làm sạch, phân tích và chia chunk, cho phép truy ngược từ một dòng JSONL
về đoạn văn hoặc hàng bảng tương ứng trong DOCX.

## 3. Chuẩn bị và trích xuất dữ liệu DOCX

### 3.1. Chuẩn hóa định dạng nguồn

Tám tài liệu được lưu dưới định dạng `.docx`. Riêng Nghị định 135/2020/NĐ-CP ban
đầu ở định dạng `.doc` cũ đã được chuyển một lần sang DOCX. Việc chuyển đổi không
được thực hiện tự động trong mỗi lần chạy nhằm tránh phụ thuộc vào Microsoft Word
hoặc LibreOffice trên môi trường triển khai.

Manifest lưu đầy đủ `document_id`, tên văn bản, số/ký hiệu, loại văn bản và đường
dẫn nguồn. Pipeline kiểm tra sự tồn tại của cả tám tệp trước khi xử lý; nếu thiếu
một tệp, lần chạy dừng với thông báo chỉ rõ tài liệu bị thiếu.

### 3.2. Trích xuất đoạn văn và bảng

Thư viện `python-docx` được sử dụng để đọc phần thân tài liệu. Extractor duyệt
trực tiếp các phần tử XML theo thứ tự xuất hiện, nhờ đó giữ được quan hệ giữa đoạn
văn và bảng thay vì đọc riêng hai tập nội dung.

Hai loại khối được tạo:

- `paragraph`: một đoạn văn có nội dung trong thân DOCX;
- `table_row`: một hàng bảng, trong đó nội dung các ô được nối bằng ` | ` theo thứ
  tự từ trái sang phải.

Header và footer không được đưa vào nội dung chính. Đoạn nằm trong ô bảng không
bị phát lại như một đoạn độc lập, tránh trùng lặp dữ liệu. Một tài liệu rỗng, hỏng
hoặc có ít hơn 20 ký tự không phải khoảng trắng bị từ chối thay vì sinh đầu ra
không có giá trị.

### 3.3. Truy vết vị trí trong DOCX

DOCX không lưu số trang ổn định; kết quả phân trang phụ thuộc phông chữ, phiên bản
Word và thiết bị in. Vì vậy pipeline không tạo số trang giả:

- `page_start` và `page_end` luôn nhận `null`;
- `paragraph_start` và `paragraph_end` lưu khối nguồn đầu và cuối của chunk;
- `block_type` trong file trung gian cho biết khối là đoạn văn hay hàng bảng.

Tên `paragraph_start/end` được giữ để tương thích nghiệp vụ, nhưng phạm vi này có
thể bao gồm cả các hàng bảng.

## 4. Làm sạch và chuẩn hóa văn bản

Mỗi dòng được chuẩn hóa Unicode NFC, thay khoảng trắng không ngắt bằng khoảng
trắng thường, loại ký tự điều khiển và gộp khoảng trắng liên tiếp. Khoảng trắng
thừa trước dấu câu được loại bỏ; sau dấu `;`, `:`, `!` và `?` được bổ sung khoảng
trắng khi cần. Các biểu thức pháp lý như `5,5%`, số hiệu văn bản, ngày tháng, số
Khoản và ký hiệu Điểm được giữ nguyên.

Khác với pipeline theo trang, quy trình DOCX không cần suy luận header/footer từ
các dòng lặp ở lề trang vì extractor chỉ đọc thân tài liệu. Khối rỗng sau chuẩn
hóa được ghi vào `removed_blocks` cùng vị trí, lý do và nội dung ban đầu. Trong
lần chạy hiện tại không có khối nào bị loại.

Số ký tự sạch có thể chênh nhẹ so với số ký tự thô do thao tác chuẩn hóa khoảng
trắng và dấu câu. Pipeline không tự sửa từ vựng hoặc diễn giải lại nội dung pháp
luật.

## 5. Khôi phục cấu trúc pháp lý

### 5.1. Cơ chế phân tích

Parser đọc các dòng theo thứ tự và duy trì trạng thái cấu trúc hiện hành. Khi gặp
Phần, Chương, Mục hoặc Tiểu mục, trạng thái tương ứng được cập nhật. Khi gặp một
Điều mới, Điều trước đó được kết thúc và lưu cùng bản sao của đường dẫn cấu trúc
đang có hiệu lực.

Các dòng bắt đầu bằng số và dấu `.` hoặc `)` được nhận diện là Khoản. Các dòng
bắt đầu bằng chữ cái và dấu `.` hoặc `)` được nhận diện là Điểm. Nội dung trước
Điều đầu tiên được gắn loại `preamble`; nội dung không khớp một nhãn mới được giữ
trong đơn vị hợp lệ gần nhất thay vì bị loại bỏ.

### 5.2. Các nhãn cấu trúc

| Nhãn | Kiểu dữ liệu | Ý nghĩa |
|---|---|---|
| `part` | object/null | Phần hiện hành, gồm `number` và `title` |
| `chapter` | object/null | Chương hiện hành, gồm `number` và `title` |
| `section` | object/null | Mục hoặc Tiểu mục hiện hành |
| `article` | object/null | Điều gốc; nhận `null` với nội dung ngoài Điều |
| `clause_ids` | list[string] | Các số Khoản xuất hiện trong chunk |
| `point_ids` | list[string] | Các ký hiệu Điểm xuất hiện trong chunk |
| `chunk_type` | string | `preamble`, `article` hoặc `clause_group` |

Các object cấu trúc sử dụng dạng `{"number": "...", "title": "..."}`. Trường
không có giá trị nhận `null` hoặc danh sách rỗng; pipeline không tự suy diễn một
nhãn không xuất hiện trong nguồn.

### 5.3. Ngăn nhận diện Điều giả

Phụ lục, biểu mẫu và câu viện dẫn có thể chứa cụm bắt đầu giống tiêu đề Điều. Một
ứng viên chỉ được chấp nhận khi có dạng nhãn phù hợp và số Điều tiếp tục chuỗi
hợp lý của văn bản chính. Ứng viên lùi số hoặc nhảy quá xa được giữ như nội dung
thường và sinh cảnh báo `Rejected Article-like reference`.

Cơ chế này đặc biệt cần thiết đối với doc-02, vì các biểu mẫu đính kèm có hệ
thống Điều riêng từ Điều 1. Nếu chấp nhận các nhãn này, cấu trúc 115 Điều của nghị
định chính sẽ bị trộn với cấu trúc hợp đồng hoặc quyết định mẫu.

Parser vẫn giữ một số mẫu nhận diện dung sai cho ký tự bất thường nhằm tương
thích với những DOCX được chuyển đổi từ nguồn cũ. Cảnh báo được đưa vào báo cáo
QA thay vì âm thầm sửa nội dung pháp luật.

## 6. Chia chunk và gắn metadata

Đơn vị ưu tiên là một Điều hoàn chỉnh. Ngưỡng cấu hình mặc định là 6.000 ký tự.
Nếu Điều vượt ngưỡng, pipeline nhóm nội dung theo ranh giới Khoản. Khi một nhóm
vẫn quá dài, bộ chia sử dụng ranh giới câu. Tiêu đề và metadata Điều gốc được lặp
lại trong mọi chunk con để bảo toàn ngữ cảnh khi truy hồi độc lập.

`chunk_id` là 20 ký tự hexa đầu của SHA-256 tính từ định danh tài liệu, đơn vị
cấu trúc, chỉ số chunk trong Điều và nội dung chuẩn hóa. Vì vậy cùng nguồn, cấu
hình và phiên bản xử lý sẽ tạo cùng định danh.

### 6.1. Schema JSONL

| Trường | Kiểu | Mô tả |
|---|---|---|
| `chunk_id` | string | Định danh ổn định và duy nhất của chunk |
| `document_id` | string | Định danh từ `doc-01` đến `doc-08` |
| `title` | string | Tên văn bản |
| `document_number` | string | Số/ký hiệu chính thức |
| `document_type` | string | Bộ luật, luật, nghị định hoặc thông tư |
| `source_file` | string | Đường dẫn tương đối đến DOCX nguồn |
| `page_start`, `page_end` | null | Giữ để tương thích schema; DOCX không có số trang ổn định |
| `paragraph_start` | integer | Khối nguồn đầu tiên của chunk |
| `paragraph_end` | integer | Khối nguồn cuối cùng của chunk |
| `part` | object/null | Phần hiện hành |
| `chapter` | object/null | Chương hiện hành |
| `section` | object/null | Mục/Tiểu mục hiện hành |
| `article` | object/null | Điều gốc |
| `clause_ids` | list[string] | Các Khoản trong chunk |
| `point_ids` | list[string] | Các Điểm trong chunk |
| `chunk_type` | string | Loại chunk |
| `chunk_index` | integer | Thứ tự chunk trong tài liệu, bắt đầu từ 1 |
| `article_chunk_index` | integer/null | Thứ tự chunk con trong Điều |
| `text` | string | Nội dung đã chuẩn hóa |
| `char_count` | integer | Độ dài thực tế của `text` |
| `token_estimate` | integer | Ước lượng `ceil(char_count / 3)` |
| `split_reason` | string/null | `max_size_clause`, `max_size_sentence` hoặc `null` |
| `processing_version` | string | Phiên bản pipeline; hiện tại là `2.0.0` |

### 6.2. Các tệp đầu ra

Pipeline tạo các thành phần sau trong `output/preprocessed/`:

- `legal_chunks.jsonl`: tập hợp chunk của cả tám văn bản;
- `by_document/doc-XX.jsonl`: chunk riêng cho từng văn bản;
- `intermediate/doc-XX.blocks.json`: khối thô, khối sạch và khối bị loại;
- `qa_report.json`: số liệu và kết quả kiểm tra có cấu trúc;
- `qa_report.md`: bảng QA tóm tắt để đọc nhanh.

JSONL được ghi qua tệp tạm, đọc kiểm tra lại và chỉ thay thế tệp đích khi toàn bộ
dòng đều là JSON object hợp lệ.

## 7. Kết quả thực nghiệm

### 7.1. Thống kê theo tài liệu

| ID | Khối | Đoạn văn | Hàng bảng | Ký tự sạch | Điều | Chunk | Cảnh báo |
|---|---:|---:|---:|---:|---:|---:|---:|
| doc-01 | 1.364 | 1.363 | 1 | 187.977 | 220 | 232 | 3 |
| doc-02 | 1.734 | 1.546 | 188 | 234.724 | 115 | 129 | 19 |
| doc-03 | 325 | 323 | 2 | 33.020 | 12 | 17 | 0 |
| doc-04 | 175 | 168 | 7 | 29.160 | 5 | 10 | 0 |
| doc-05 | 1.182 | 1.179 | 3 | 181.915 | 141 | 148 | 0 |
| doc-06 | 579 | 564 | 15 | 115.487 | 45 | 52 | 1 |
| doc-07 | 361 | 93 | 268 | 26.367 | 9 | 12 | 0 |
| doc-08 | 1.023 | 1.021 | 2 | 177.624 | 64 | 72 | 0 |
| **Tổng** | **6.743** | **6.257** | **486** | **986.274** | **611** | **672** | **23** |

Tổng số Điều theo từng văn bản lần lượt tạo thành các khoảng liên tục: 1–220,
1–115, 1–12, 1–5, 1–141, 1–45, 1–9 và 1–64. Đây là một kiểm tra quan trọng để
phát hiện tiêu đề Điều bị bỏ sót hoặc bị nhận diện sai.

### 7.2. Kết quả QA

Các kiểm tra toàn cục đều đạt:

| Kiểm tra | Kết quả |
|---|---|
| Đủ tám `document_id` | Đạt |
| `chunk_id` duy nhất | Đạt |
| Không có chunk rỗng | Đạt |
| Không lấy tài liệu trong `data/tuychon/` | Đạt |
| Mọi nguồn đều là DOCX | Đạt |
| Mọi khoảng `paragraph_start/end` hợp lệ | Đạt |
| JSONL đọc lại độc lập | Đạt |
| 28 kiểm thử tự động | 28/28 đạt |

Có 23 cảnh báo parser: 3 ở doc-01, 19 ở doc-02 và 1 ở doc-06. Phần lớn là các
tiêu đề Điều nằm trong nội dung viện dẫn, phụ lục, mẫu quyết định hoặc mẫu hợp
đồng. Các ứng viên này bị từ chối có chủ đích để không phá vỡ chuỗi Điều của văn
bản chính. Một cảnh báo Chương ở doc-02 phản ánh nhãn nguồn bất thường được chuẩn
hóa theo trình tự cấu trúc.

## 8. Hạn chế

Thứ nhất, `paragraph_start/end` là chỉ số khối logic, không phải số trang hiển
thị trong Microsoft Word. Khi nội dung hoặc cấu trúc bảng của DOCX thay đổi, chỉ
số khối ở phía sau vị trí sửa đổi cũng có thể thay đổi.

Thứ hai, mỗi hàng bảng được biểu diễn tuyến tính bằng dấu ` | `. Cách biểu diễn
này giữ được thứ tự ô nhưng không mô tả ô gộp, độ rộng cột hoặc quan hệ tiêu đề
phức tạp. Doc-07 có 268 hàng bảng nên chịu ảnh hưởng rõ nhất của giới hạn này.

Thứ ba, ngưỡng 6.000 ký tự hiện là mục tiêu chia, chưa phải giới hạn cứng. Chunk
lớn nhất của doc-07 có 15.240 ký tự do một nhóm nội dung bảng dài không có ranh
giới câu phù hợp để tách tiếp. Nếu mô hình phía sau có cửa sổ ngữ cảnh nhỏ, cần
bổ sung chiến lược chia theo hàng bảng hoặc giới hạn ký tự cứng.

Thứ tư, parser dựa trên mẫu tiêu đề và tính liên tục của số Điều. Cách làm phù hợp
với tám văn bản chính nhưng cần điều chỉnh nếu xử lý riêng phụ lục có hệ thống
Điều độc lập, văn bản sửa đổi có hậu tố Điều phức tạp hoặc một trích đoạn không
bắt đầu từ đầu văn bản.

Cuối cùng, pipeline chỉ chuẩn hóa biểu diễn; không tự sửa từ ngữ pháp luật. Sai
sót có sẵn trong DOCX nguồn sẽ tiếp tục xuất hiện trong trường `text` và cần được
đối chiếu với văn bản chính thức nếu tác vụ yêu cầu độ chính xác từng ký tự.

## 9. Kết luận

Pipeline phiên bản 2.0.0 đã chuyển tám tài liệu pháp luật DOCX thành tập JSONL có
cấu trúc và khả năng truy vết theo khối nguồn. Việc đọc trực tiếp đoạn văn và
bảng giúp loại bỏ phụ thuộc vào nhận dạng ảnh, đồng thời cải thiện đáng kể tính
ổn định của nội dung tiếng Việt. Chiến lược chunk theo cấu trúc bảo toàn ngữ cảnh
Điều/Khoản tốt hơn cách chia độ dài cố định, còn schema thống nhất tạo điều kiện
cho truy hồi, xây dựng Knowledge Graph và huấn luyện mô hình ở các bước tiếp theo.

Kết quả hiện tại gồm 672 chunk, bao phủ đủ 611 Điều của tám văn bản và vượt qua
toàn bộ kiểm tra QA. Các cảnh báo còn lại đã được lưu minh bạch để phục vụ rà
soát; hạn chế đáng chú ý nhất là các bảng dài cần một chiến lược chia chuyên biệt
nếu đầu ra được đưa vào mô hình có giới hạn ngữ cảnh thấp.
