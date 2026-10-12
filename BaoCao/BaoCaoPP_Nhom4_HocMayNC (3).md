TRƯỜNG ĐẠI HỌC XÂY DỰNG HÀ NỘI KHOA CÔNG NGHỆTHÔNG TIN 

### **BÁO CÁO BÀI TẬP LỚN** 

#### **NHÓM 4** 

## **NGHIÊN CỨU, XÂY DỰNG TRỢLÝ ẢO TƯ VẤN PHÁP LAO LUẬT ĐỘNG DỰA TRÊN THỨC KẾT ĐỒTHỊTRI HỢP RAG, NLP VÀ LLM** 

**Giảng viên hướng dẫn:** . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 

##### **Sinh viên thực hiện:** 

- Trần An Bình 

- - Nguyễn Bá Nam . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 

- - Đào Đăng Quang - Trương Quốc Toản 

**Lớp: 68CS1** . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 

– Hà Nội 2026 

# **Mục lục** 

|**1**<br>**ĐỀ**|**XUẤT ĐỀTÀI NHÓM 4**|**2**|
|---|---|---|
|1.1|Tên đềtài . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>2|
|1.2|Lý do lựa chọn đềtài . . . . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>2|
|1.3|Mục tiêu đềtài . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>2|
|1.4|Phạm vi . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>2|
|**2**<br>**PH**|**ƯƠNG PHÁP ĐỀXUẤT**|**4**|
|2.1|Tổng quan phương pháp . . . . . . . . . . . . . . . . . . . . . . . . . <br>|. . . .<br>4|
|2.2|Thu thập dữliệu và chuẩn hoá<br>. . . . . . . . . . . . . . . . . . . . .|. . . .<br>4|
||2.2.1<br>Nguồn dữliệu . . . . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>4|
||2.2.2<br>Tiền xửlý . . . . . . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>5|
|2.3|Xây dựng kho tri thức kép . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>6|
||2.3.1<br>Kho vector phục vụtìm kiếm ngữnghĩa trên Qdrant<br>. . . . .|. . . .<br>6|
||2.3.2<br>Đồthịtri thức pháp luật trên Neo4j<br>. . . . . . . . . . . . . .|. . . .<br>6|
|2.4|Pipeline NLP tiếng Việt . . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>7|
||2.4.1<br>Tách từvà chuẩn hoá câu hỏi . . . . . . . . . . . . . . . . . .|. . . .<br>7|
||2.4.2<br>Phân loại ý định<br>. . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>7|
||2.4.3<br>Trích xuất thực thểpháp lý . . . . . . . . . . . . . . . . . . .|. . . .<br>8|
|2.5|Hybrid Retrieval: Kết hợp 3 kênh truy xuất<br>. . . . . . . . . . . . . .|. . . .<br>8|
||2.5.1<br>Semantic retrieval . . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>8|
||2.5.2<br>Keyword retrieval . . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>8|
||2.5.3<br>Graph retrieval . . . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>8|
||2.5.4<br>Hợp nhất và xếp hạng<br>. . . . . . . . . . . . . . . . . . . . . .|. . . .<br>8|
|2.6|Xây dựng ngữcảnh và Prompt<br>. . . . . . . . . . . . . . . . . . . . .|. . . .<br>8|
|2.7|Sinh câu trảlời bằng LLM . . . . . . . . . . . . . . . . . . . . . . . .|. . . .<br>9|



1 

# **Chương 1 ĐỀXUẤT ĐỀTÀI NHÓM 4** 

### **1.1 Tên đềtài** 

Nghiên cứu, xây dựng trợlý ảo tư vấn pháp luật lao động dựa trên đồthịtri thức kết hợp với RAG, xửlý ngôn ngữtựnhiên NLP và mô hình ngôn ngữlớn LLM 

### **1.2 Lý do lựa chọn đềtài** 

Bộluật Lao động 2019 là văn bản pháp luật cốt lõi điều chỉnh quan hệlao động tại Việt Nam. Văn bản có hiệu lực từngày 01/01/2021 và được triển khai cùng nhiều nghịđịnh, thông tư hướng dẫn. Khi tra cứu, người dùng không chỉcần tìm đúng điều khoản mà còn phải xác định mối liên hệgiữa luật, nghịđịnh, chủthể, điều kiện, ngoại lệvà thủtục áp dụng. Vì vậy, một hệthống chỉtìm kiếm theo từkhóa hoặc chỉsửdụng LLM có thểgặp khó khăn trong việc bảo đảm tính chính xác, tính cập nhật và khảnăng trích dẫn cơ sởpháp lý. 

Đềtài nhóm được tham khảo từbài Báo cáo cuối kỳGR1: Ứng dụng Chatbot AI trong tư vấn pháp luật, Project I, Trường Đại học Bách khoa Hà Nội, 2025. Tuy nhiên, thu hẹp miền ứng dụng vào pháp luật lao động. 

### **1.3 Mục tiêu đềtài** 

- Cho phép người dùng đặt câu hỏi bằng tiếng Việt tựnhiên vềcác vấn đềpháp luật lao động thường gặp. 

- Hệthống truy xuất đúng các điều, khoản, văn bản hướng dẫn có liên quan. 

- Kết hợp tìm kiếm ngữnghĩa, tìm kiếm từkhoá và truy xuất đồthịtri thức đểtăng độchính xác và bao phủngữcảnh. 

- Sửdụng LLM đểtổng hợp câu trảlời, trích dẫn nguồn và hạn chếhiện tượng sinh văn bản không có căn cứ. 

- Từkiến trúc này, có thểmởrộng sang các bộluật khác trong tương lai. 

### **1.4 Phạm vi** 

Dựán tập trung vào bộluật lao động năm 2019 và 1 sốthông tư, nghịđịnh có liên quan. Chức năng hỏi đáp tập trung vào 5 nhóm chủđềchính: 

2 

1. Hợp đồng lao động. 

2. Tiền lương và tiền lương làm thêm giờ. 

3. Thời giờlàm việc và nghỉngơi. 

4. Kỷluật lao động và trách nhiệm vật chất. 

5. Bảo hiểm xã hội cơ bản gắn với quan hệlao động. 

Hệthống chỉcó vai trò hỗtrợtra cứu và cung cấp thông tin tham khảo, không thay thếý kiến tư vấn của luật sư hoặc cơ quan có thẩm quyền. 

3 

# **Chương 2 PHƯƠNG PHÁP ĐỀXUẤT** 

### **2.1 Tổng quan phương pháp** 

Phương pháp của đềtài được xây dựng theo kiến trúc Hybrid KG-RAG. Cùng 1 câu hỏi từ người dùng, hệthống xửlý qua Pipeline NLP, sau đó đi qua 3 kênh truy xuất: 

- Tìm kiếm ngữnghĩa trên vector database 

- Tìm kiếm từkhoá 

- Truy vấn Knowledge Graph 

Kết quảcủa 3 kênh này sẽđược hợp nhất, xếp hạng và đưa vào LLM đểsinh câu trảlời. 

### **2.2 Thu thập dữliệu và chuẩn hoá** 

#### **2.2.1 Nguồn dữliệu** 

Nguồn dữliệu được thu thập từcác trang pháp luật chính thống như `https://vanban. chinhphu.vn/` hay `https://luatvietnam.vn/` . Bao gồm bộluật Lao động 2019 và các nghị định, thông tư hướng dẫn thuộc phạm vi đềtài. 

Các văn bản được thu thập làm nguồn dữliệu cho dựán: 

- `01_Bo_luat_Lao_dong_2019_45-2019-QH14` 

- `02_ND145-2020_Huong_dan_BLLD` 

- `03_TT10-2020_Noi_dung_Hop_dong_Lao_dong` 

- `04_ND293-2025_Luong_toi_thieu_2026` 

- `05_Luat_BHXH_2024_41-2024-QH15` 

- `06_ND158-2025_BHXH_bat_buoc` 

- `07_ND135-2020_Tuoi_nghi_huu` 

- `08_ND12-2022_Xu_phat_Lao_dong_BHXH` 

4 



<!-- Start of picture text -->
Cau hoi ngwoi ding<br><!-- End of picture text -->



<!-- Start of picture text -->
NLP Tiéng Viet<br>Tach tir - Intent -Entity<br>Qdrant Tim kiém theo keyword Cypher trén Neodj<br>Tim kiém ngifnghia- er 7 Truy vandé thi<br><!-- End of picture text -->



<!-- Start of picture text -->
Xép_ Hophang nhatngir& canh<br>Béi canh truy van +<br>Mau Iei nhac<br>LLM sinh cau tra Idi<br><!-- End of picture text -->

Cau tra loi + trich dan nguén + canh bao pham vi tu van 



<!-- Start of picture text -->
PDF SCAN PDF co Text Layer<br>Cai dat Tesseract OCR Trich xuat tryve tiep van ban tu<br>. file bang thu vién pypdf<br>Tai model nhan dang tiéng Viét<br>vie.traineddata<br><!-- End of picture text -->

- **Subject** : Chủthể: người lao động, người sửdụng lao động, lao động nước ngoài,... 

- **RightObligation** : Quyền, nghĩa vụ. 

- **Procedure** : Thủtục 

- **Condition** : Điều kiện áp dụng 

- **LegalTopic** : Chủđề: hợp đồng, lương, BHXH, kỷluật,... 

Các quan hệđềxuất: 

|**Quan hệ**|**Ý nghĩa**|
|---|---|
|CONTAINS|Văn bản chứa điều/khoản|
|REGULATES|Điều luật điều chỉnh một chủđề|
|APPLIES_TO|Quy định áp dụng cho chủthể|
|REQUIRES|Quy định yêu cầu điều kiện|
|GUIDED_BY|Luật/điều được hướng dẫn bởi văn bản khác|
|AMENDED_BY|Văn bản/điều được sửa đổi bởi văn bản khác|
|RELATED_TO|Quan hệliên quan vềnội dung pháp lý|



Bảng 2.1: Các quan hệtrong Đồthịtri thức 

Đồthịcho phép hệthống trảlời câu hỏi từngười dùng qua nhiều bước suy luận và truy vấn, từđó lần theo các quan hệvà truy xuất điều luật, văn bản hướng dẫn có liên quan. 

### **2.4 Pipeline NLP tiếng Việt** 

#### **2.4.1 Tách từvà chuẩn hoá câu hỏi** 

Do tiếng Việt có đặc trưng khoảng trắng không luôn tương ứng với ranh giới từ. Hệthống cần sửdụng VnCoreNLP đểtách từvà annotation cơ bản. 

Kết quảtiền xửlý này được dùng làm đầu vào cho module phân loại ý định và trích xuất thực thể. 

#### **2.4.2 Phân loại ý định** 

Ý định của người dùng được phân loại về6 nhóm nghiệp vụchính hay gặp: 

- `contract_termination` : Chấm dứt hợp đồng, nghỉviệc, đơn phương nghỉ 

- `overtime_pay` : Làm thêm giờ, tăng ca, tiền tăng ca 

- `annual_leave` : Nghỉphép, nghỉhàng năm 

- `disciplinary_dismissal` : Sa thải, kỷluật 

- `social_insurance` : BHXH, lương hưu, thai sản 

- `other` : Nhóm khác với 5 nhóm trên 

Ban đầu, có thểrule-base từcác rule trên. Sau này, có thểxây dựng mô hình PhoBERT để fine-tuning khi thu thập hoặc gen được câu hỏi. Có thểbỏqua bước này nếu không đủthời gian. 

7 

#### **2.4.3 Trích xuất thực thểpháp lý** 

Entity extraction nhằm nhận diện những thông tin có ảnh hưởng trực tiếp tới quy định được áp dụng như: loại hợp đồng, thời gian làm việc, sốgiờlàm thêm, tuổi của người lao động,... Các thực thểnày được chuẩn hóa và dùng đểtạo điều kiện lọc khi truy vấn Knowledge Graph hoặc vector database. 

VnCoreNLP NER có thểnhận diện được người, tổchức, đối tượng nhưng không thểtự hiểu các thực thểpháp lý chuyên ngành. Vì vậy ban đầu, có thểdùng regex, từđiển hoặc rule base. 

### **2.5 Hybrid Retrieval: Kết hợp 3 kênh truy xuất** 

#### **2.5.1 Semantic retrieval** 

Câu hỏi được embedding và so sánh với vector của các chunk khác trên Qdrant. Phù hợp khi người dùng diễn đạt khác từngữcủa văn bản luật nhưng cùng ngữnghĩa. 

#### **2.5.2 Keyword retrieval** 

Sửdụng phương pháp BM25: tìm kiếm từkhoá dựa trên TF-IDF. Có lợi khi câu hỏi chứa cụm pháp lý đặc trưng, sốđiều, tên văn bản pháp luật hay từngữcó độchính xác cao. 

#### **2.5.3 Graph retrieval** 

Từintent và entity đã nhận diện, hệthống xây dựng truy vấn Cypher đểtìm các node và các quan hệliên quan trên Neo4j. Kết quảkhông chỉtrảvềđiều luật trực tiếp mà còn trả vềcác văn bản hướng dẫn, các điều, khoản có liên quan. 

#### **2.5.4 Hợp nhất và xếp hạng** 

Ba tập kết quảđược chuẩn hoá điểm và hợp nhất. Tạo ra 1 hàm điểm tổng quát được biểu diễn như sau: 



trong đó _α_ + _β_ + _γ_ = 1. Các hệsốđược tinh chỉnh trong quá trình huấn luyện và kiểm thử. 

### **2.6 Xây dựng ngữcảnh và Prompt** 

Query Context Builder chịu trách nhiệm biến kết quảtruy xuất thành một context thống nhất cho LLM. Cấu trúc đềxuất: 

- Câu hỏi gốc 

- Intent, Entity đã nhận diện 

- Các điều, khoản liên quan nhất (Top k) 

- Quan hệpháp lý được bổsung từKG 

- Metadata nguồn đểtrích dẫn 

8 

- Chỉdẫn cho LLM vềcách trảlời 

Prompt cho LLM tuân theo nguyên tắc grounded generation, tức LLM chỉđược sửdụng thông tin trong context, nếu không đủthì phải thông báo chưa đủcăn cứ, không được tự suy diễn. 

### **2.7 Sinh câu trảlời bằng LLM** 

Sửdụng Model LLM đểtổng hợp các context và đưa ra câu trảlời. Cấu trúc đềxuất: 

- Kết luận ngắn 

- Giải thích 

- Cơ sởpháp lý 

- Lưu ý: Chỉra trường hợp cần thêm thông tin, cần tư vấn từchuyên môn 

9 

