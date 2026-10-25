# ĐẠI HỌC QUỐC GIA THÀNH PHỐ HỒ CHÍ MINH
## TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN

<br>

# ĐỀ XUẤT HƯỚNG NGHIÊN CỨU ĐỀ TÀI
### Đồ án môn học CS114 - Máy học

**Lĩnh vực:** Khoa học Dữ liệu & Trí tuệ Nhân tạo

## ỨNG DỤNG CÁC MÔ HÌNH HỌC MÁY ĐỂ DỰ ĐOÁN XU HƯỚNG VÀ GIÁ ĐÓNG CỬA CỔ PHIẾU FPT PHIÊN KẾ TIẾP

| STT | Họ và tên | MSSV | Vai trò |
|---:|---|---|---|
| 1 | Lê Vũ Thiêm Hoàng | 25520584 | Leader |
| 2 | Nguyễn Tấn Dũng | 25520367 | Member |
| 3 | Lưu Hoàng Minh Duy | 25520424 | Member |

<br>

**THÀNH PHỐ HỒ CHÍ MINH, NĂM 2026**

---

## Mục lục

1. Đặt vấn đề
2. Mục tiêu của đề tài
3. Phạm vi và đối tượng nghiên cứu
4. Đầu vào và đầu ra dự kiến
5. Hướng tiếp cận và công nghệ dự kiến
6. Cách đánh giá dự kiến
7. Kết quả dự kiến
8. Nội dung nhóm mong muốn được giảng viên góp ý

---

## 1. Đặt vấn đề

Giá cổ phiếu biến động theo kết quả kinh doanh, thông tin doanh nghiệp, cung cầu thị trường và các yếu tố kinh tế rộng hơn. Cổ phiếu FPT có lịch sử giao dịch dài, đồng thời có thể thu thập dữ liệu theo ngày và tạo ra một bài toán học máy có đầu vào, nhãn và cách đánh giá rõ ràng.

Đề tài đặt câu hỏi: khi chỉ biết dữ liệu đến lúc đóng cửa phiên (t), các mô hình học máy có dự báo được hướng thay đổi và mức giá đóng cửa của FPT ở phiên giao dịch kế tiếp hay không? Nhóm dự kiến so sánh Nhánh 1 dùng giá, khối lượng và chỉ báo kỹ thuật với Nhánh 2 bổ sung tỷ giá USD/VND, giá vàng, CPI, GDP, chỉ số ngành ICT và báo cáo tài chính. Dữ liệu tần suất thấp chỉ được dùng sau ngày có thể biết để hạn chế đưa thông tin tương lai vào mô hình.

Khó khăn chính là các nguồn có tần suất và phạm vi lịch sử khác nhau. Giá FPT được ghi theo phiên hằng ngày, trong khi CPI thường theo tháng, GDP và báo cáo tài chính theo quý. Nguồn dữ liệu cũng có giới hạn truy cập và có thể hiệu chỉnh lại lịch sử. Vì vậy, đề tài xem việc ghi nhận nguồn, ngày dữ liệu có hiệu lực, phạm vi quan sát và giới hạn của từng phép thử là một phần của phương pháp nghiên cứu.

Sản phẩm là hệ thống thực nghiệm học thuật hỗ trợ phân tích định lượng. Kết quả của mô hình không được xem là lời khuyên đầu tư và không thay thế quyết định của nhà đầu tư.

## 2. Mục tiêu của đề tài

**Mục tiêu chung:** Xây dựng một quy trình tái lập được để huấn luyện và đánh giá mô hình học máy dự báo hướng biến động và giá đóng cửa FPT ở phiên kế tiếp, đồng thời đo lường tác động của việc bổ sung từng nhóm đặc trưng.

**Mục tiêu cụ thể:**

1. Khảo sát dữ liệu OHLCV lịch sử FPT và dữ liệu thị trường, vĩ mô, ngành, báo cáo tài chính trong phạm vi đến ngày 30/09/2025.
2. Xây dựng quy trình kiểm tra, tiền xử lý và trích xuất đặc trưng chỉ từ thông tin có thể biết tại thời điểm dự báo; kiểm thử việc ngăn rò rỉ dữ liệu tương lai.
3. Huấn luyện và đối sánh các mô hình phân loại hướng Tăng/Giảm và hồi quy giá phiên kế tiếp bằng phép chia Train/Test theo thứ tự thời gian.
4. Thực hiện so sánh loại bỏ/bổ sung nhóm đặc trưng (Ablation Study) và phân tích các trường hợp mô hình dự báo sai.

## 3. Phạm vi và đối tượng nghiên cứu

- **Đối tượng:** Chuỗi dữ liệu giao dịch mã cổ phiếu FPT trên HOSE.
- **Thời gian nghiên cứu:** Từ phiên đầu tiên trong snapshot ngày 02/01/2007 đến phiên 30/09/2025. Mốc dừng được chọn để đồng bộ với các snapshot vĩ mô và báo cáo tài chính đã kiểm tra.
- **Đơn vị dự báo:** Một quan sát tại cuối phiên (t), dự báo phiên giao dịch FPT kế tiếp (t+1). “Phiên kế tiếp” là phiên có mặt trong dữ liệu, không phải ngày lịch kế tiếp.
- **Bài toán chính:** Phân loại close phiên (t+1) tăng hay giảm so với close phiên (t). Các phiên đứng giá được giữ trong dữ liệu gốc nhưng loại khỏi huấn luyện và chấm điểm phân loại.
- **Bài toán bổ trợ:** Hồi quy giá close phiên (t+1), với mục tiêu kiểm tra sai số giá và so sánh với baseline giữ nguyên close.
- **Hai nhánh dữ liệu:** Nhánh 1 gồm 5 trường OHLCV gốc và 27 đặc trưng kỹ thuật/nến, tổng cộng 32 biến. Nhánh 2 bổ sung 12 biến USD/VND, vàng quy đổi, CPI, GDP, vốn hóa/P-E ngành ICT và tài chính FPT, gồm lịch sử số cổ phiếu lưu hành, thành 44 biến.
- **Giới hạn:** Một mã cổ phiếu và một bước dự báo ngắn hạn không đại diện cho toàn bộ thị trường hoặc hiệu quả giao dịch dài hạn.

## 4. Đầu vào và đầu ra dự kiến

### 4.1. Đầu vào

| Nhóm | Dữ liệu | Cách dùng |
|---|---|---|
| Giao dịch FPT | `time, open, high, low, close, volume` | Tạo đặc trưng theo phiên; đơn vị giá của snapshot là nghìn VND/cổ phiếu, volume là số cổ phiếu |
| Kỹ thuật và nến | 23 chỉ báo từ close/volume, biên độ nến, thân nến, overnight gap, vị trí close | 27 đặc trưng tính từ hiện tại/quá khứ; cộng 5 trường OHLCV gốc thành 32 biến của Nhánh 1 |
| Vĩ mô | USD/VND, giá vàng quy đổi VND, CPI, GDP | Nhánh 2: ghép lùi từ ngày quan sát hoặc ngày công bố, không điền ngược |
| Ngành ICT | Vốn hóa, P/E, Absolute P/E | Có hiệu lực từ phiên sau ngày snapshot |
| Doanh nghiệp FPT | Doanh thu thuần, lợi nhuận gộp, EBIT, lợi nhuận sau thuế cổ đông công ty mẹ | EBIT tính bằng lợi nhuận trước thuế cộng chi phí lãi vay; báo cáo được dùng từ ngày hiệu lực mô phỏng |
| Cổ phiếu lưu hành | Số cổ phiếu lưu hành theo lịch sử công bố | Kiểm tra độ phủ và ngày hiệu lực trước khi đưa vào mô hình |

Các nguồn dự kiến gồm VCI/Vietcap qua vnstock cho FPT; Investing.com cho tỷ giá, vàng và CPI; World Bank cho GDP năm; Simply Wall St cho các snapshot ngành công nghệ Việt Nam. Dự án lưu nguồn, đơn vị, phạm vi và ngày có hiệu lực của từng chuỗi. Giá vàng quy đổi bằng XAU/USD nhân USD/VND, có đơn vị VND/ounce; đây không phải giá vàng miếng trong nước. GDP dùng số liệu thực tế đã công bố, không trộn với dự báo. Những chỉ tiêu thiếu lịch sử hoặc ngày công bố chưa xác minh được sẽ được nêu rõ trong báo cáo thực nghiệm.

Pipeline dưới đây mô tả phép thử hai nhánh. Hai nhánh dùng cùng những ngày có dữ liệu hợp lệ và cùng ranh giới Train/Test.

![Sơ đồ đầu vào, xử lý và đầu ra](../figures/00_pipeline_overview.png)

### 4.2. Đầu ra

| Trường | Ý nghĩa |
|---|---|
| `Target Session` | Phiên giao dịch mục tiêu kế tiếp |
| `Predicted Direction` | Nhãn dự báo Tăng hoặc Giảm |
| `Confidence Score` | Xác suất mô hình ước tính cho lớp Tăng, có điều kiện trên hai lớp Tăng/Giảm |
| `Predicted Close Price` | Giá đóng cửa ước tính cho phiên mục tiêu, đơn vị nghìn VND/cổ phiếu |
| `Explain / Key Signals` | Tên nhóm đặc trưng được dùng và các tín hiệu đầu vào để trình bày kết quả; không diễn giải thành quan hệ nhân quả |

Ngoài dự báo mới nhất, pipeline sinh bảng metric Test, ma trận nhầm lẫn, dự báo theo từng phiên và bảng so sánh các nhóm đặc trưng.

## 5. Hướng tiếp cận và công nghệ dự kiến

Quy trình gồm các bước: thu thập/đọc snapshot → kiểm toán OHLCV → tạo đặc trưng quá khứ → căn chỉnh dữ liệu bổ trợ theo thời điểm có thể biết → chia Train/Test theo ngày mục tiêu → huấn luyện → đánh giá → lưu mô hình và dự đoán phiên kế tiếp.

Nhóm dùng Python, pandas, NumPy, matplotlib, scikit-learn, XGBoost, joblib và vnstock. OHLCV FPT lấy qua VCI/Vietcap; các CSV vĩ mô, ngành và báo cáo tài chính được chuẩn hóa bằng `src/fetch_supplemental.py`. Dự án lưu snapshot và quy tắc căn ngày để tái lập thí nghiệm.

**Nguyên tắc thực nghiệm:**

- Bắt đầu từ Majority Baseline cho phân loại và Last-Close Baseline cho hồi quy.
- So sánh mô hình tuyến tính: Logistic Regression, Linear Regression.
- So sánh mô hình cây và boosting: Random Forest, XGBoost, HistGradientBoosting.
- So sánh Nhánh 1 (giá/khối lượng/kỹ thuật) với Nhánh 2 (Nhánh 1 cộng vĩ mô, ngành, tài chính). Cả hai dùng cùng hàng dữ liệu hợp lệ và cùng Test.
- Đặt StandardScaler trong Pipeline của mô hình tuyến tính để scaler chỉ học trung bình và độ lệch chuẩn từ Train.
- Tính các đặc trưng theo hướng lùi thời gian; không dùng `backfill` để lấp khoảng trống dữ liệu bổ trợ.
- Khi thiếu lịch công bố, mô phỏng báo cáo tài chính có hiệu lực sau 45 ngày kể từ cuối quý và GDP sau 180 ngày kể từ cuối năm. Đây là giả định thực nghiệm; dữ liệu hiện hành có thể đã được điều chỉnh, nên không khẳng định đã khôi phục đầy đủ các phiên bản từng biết trong quá khứ.
- Sau khi ghi nhận kết quả Train/Test, có thể huấn luyện lại mô hình được chọn trên toàn bộ nhãn hiện có để tạo dự báo mới nhất. Metric Test vẫn là kết quả của mô hình chỉ fit trên Train.
- Quy tắc lựa chọn trong phiên bản hiện tại chọn mô hình theo Balanced Accuracy Test cho phân loại và MAE Test cho hồi quy theo yêu cầu so sánh trực tiếp. Vì Test được dùng để chọn mô hình, điểm của mô hình được chọn có thể lạc quan; đây là giới hạn cần nói rõ khi bảo vệ.

Giá nến trong snapshot có đơn vị nghìn VND/cổ phiếu. Nhóm lưu hash, phạm vi và kết quả kiểm toán để đối chiếu trong các lần chạy lại.

## 6. Cách đánh giá dự kiến

### Chia tập

Tập dữ liệu được sắp theo ngày mục tiêu: 85% mẫu đầu tiên dùng làm Train, 15% cuối dùng làm Test, không xáo trộn. Test kết thúc tại phiên 30/09/2025. Ngày bắt đầu và số mẫu của cửa sổ chung sẽ được ghi trong báo cáo sau khi kiểm tra độ phủ dữ liệu. Mọi mô hình được huấn luyện trên Train trước khi dự báo Test. Các phiên đứng giá chỉ bị loại riêng khỏi bài toán phân loại.

### Bảng chấm điểm hướng Tăng/Giảm

- Accuracy: tỷ lệ dự đoán đúng trên tổng số phiên.
- Balanced Accuracy: trung bình khả năng nhận đúng của lớp Giảm và lớp Tăng, giảm thiên lệch do chênh lệch số mẫu.
- Precision, Recall và F1-score: mô tả chất lượng nhận diện lớp Tăng.
- ROC-AUC: đo khả năng xếp hạng phiên Tăng cao hơn phiên Giảm trên các ngưỡng xác suất.
- Ma trận nhầm lẫn: cho biết số lần dự đoán Giảm/Tăng đúng và sai.

### Bảng chấm điểm giá đóng cửa

- MAE và RMSE đo độ lớn sai số giá; MAPE đo sai số tương đối theo phần trăm.
- Directional Accuracy đo số phiên mô hình dự đoán đúng chiều tăng/giảm khi giá thực tế có thay đổi.
- Tolerance Accuracy đo tỷ lệ giá dự đoán nằm trong ±0,5%, ±1,0% và ±2,0% so với giá thực tế.

HOSE công bố biên độ dao động thông thường ±7% so với giá tham chiếu cho cổ phiếu; có các trường hợp ngoại lệ theo quy định. Đây là bối cảnh về biên độ thị trường, không phải ngưỡng đảm bảo dự báo ±7% là “đủ tốt”. Sai số 0,5%/1%/2% được báo riêng để người đọc thấy mức gần nhau của dự đoán và giá thực tế. [Tài liệu biên độ giá HOSE](https://staticfile.hsx.vn/Uploads/UploadDocuments/2372201/4.Bien%20do%20dao%20dong%20gia.pdf).

## 7. Kết quả dự kiến

1. Pipeline thu thập/chuẩn hóa/kiểm toán OHLCV và dữ liệu bổ trợ theo ngày hiệu lực.
2. Bộ mô hình phân loại và hồi quy, kèm lệnh tạo dự báo phiên kế tiếp.
3. Báo cáo thực nghiệm Train/Test gồm so sánh hai nhánh, Tolerance Accuracy, confusion matrix, biểu đồ Actual Close so với Predicted Close của từng mô hình, biểu đồ hai nhánh có cửa sổ phóng to 60–90 phiên và biểu đồ cột các độ đo.
4. Phân tích ưu, nhược điểm, ảnh hưởng của dữ liệu bổ trợ, các lỗi điển hình và giới hạn.

Nhóm dự kiến báo cáo cả trường hợp dữ liệu bổ trợ làm kết quả tăng, không đổi hoặc giảm, đồng thời giải thích giới hạn của cửa sổ đánh giá. Chất lượng đồ án được thể hiện ở quy trình đúng, kết quả tái lập được và phân tích có căn cứ.

### Tiến độ thực hiện trong 10 tuần

| Thời gian | Công việc |
|---|---|
| Tuần 1–2 | Kiểm toán OHLCV và chuẩn hóa nguồn bổ trợ |
| Tuần 3–4 | Tạo đặc trưng, căn ngày có thể biết và kiểm thử chống rò rỉ |
| Tuần 5–6 | Huấn luyện, đối sánh mô hình hai nhánh |
| Tuần 7–8 | Phân tích lỗi, hoàn thiện biểu đồ và báo cáo |
| Tuần 9–10 | Chuẩn bị slide, luyện thuyết trình và hoàn thiện nộp bài |

## 8. Nội dung nhóm mong muốn được giảng viên góp ý

1. Đề tài nên giữ phạm vi phân tích sâu một mã FPT hay mở rộng sang một số mã cùng ngành ICT?
2. Với dự báo theo ngày, mức độ cần thiết của dữ liệu vĩ mô và báo cáo tài chính theo quý là bao nhiêu nếu ngày công bố chưa luôn được cung cấp đầy đủ?
3. Đồ án nên tập trung so sánh các mô hình học máy trên dữ liệu bảng hay cần mở rộng sang Deep Learning như LSTM/Transformer?
4. Cần ưu tiên tiêu chí đánh giá và mức kết quả tối thiểu nào để phù hợp với yêu cầu của học phần, nhất là khi thị trường có nhiễu và Test gần mức ngẫu nhiên?
