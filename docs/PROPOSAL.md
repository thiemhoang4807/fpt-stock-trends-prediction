# Đề xuất đồ án: Dự đoán hướng biến động cổ phiếu FPT bằng Machine Learning

## 1. Đặt vấn đề

Giá cổ phiếu chịu ảnh hưởng đồng thời từ thông tin doanh nghiệp, thị trường, tâm lý nhà đầu tư và các cú sốc khó lường. Một mô hình có thể khớp tốt dữ liệu quá khứ nhưng vẫn không dự báo được phiên kế tiếp. Vì vậy, đồ án tập trung vào bài toán Machine Learning có thể định nghĩa và đánh giá rõ ràng: dùng thông tin đã biết đến cuối phiên hiện tại để phân loại giá đóng cửa FPT ở phiên kế tiếp tăng hay giảm.

## 2. Câu hỏi và mục tiêu nghiên cứu

**Câu hỏi chính:** Các đặc trưng kỹ thuật tính từ OHLCV quá khứ có giúp dự đoán hướng đóng cửa phiên kế tiếp của FPT tốt hơn baseline đơn giản trên các giai đoạn tương lai hay không?

Mục tiêu:

1. Xây dựng pipeline thu thập, chuẩn hóa và kiểm toán dữ liệu OHLCV FPT.
2. Tính đặc trưng chỉ từ dữ liệu có sẵn tại thời điểm dự báo, kiểm tra nguy cơ rò rỉ.
3. Huấn luyện và so sánh baseline, mô hình tuyến tính và mô hình cây theo thứ tự thời gian.
4. Đánh giá độc lập trên giai đoạn test mới nhất và phân tích metric, nhầm lẫn, giới hạn.
5. Cung cấp mã, dữ liệu đã dùng, cấu hình và báo cáo để có thể chạy lại thí nghiệm.

## 3. Phạm vi dữ liệu

Tập dữ liệu hiện dùng có 4.919 phiên từ 02/01/2007 đến 30/09/2026, gồm <code>time, open, high, low, close, volume</code>. Nguồn giá là VCI (Vietcap), được truy cập qua thư viện Python <code>vnstock</code> 5.1.0 và chuẩn hóa bằng <code>src/fetch_data.py</code>. Giá được giữ theo thang nghìn VND/cổ phiếu của nguồn; volume là số cổ phiếu.

API ở quyền khách giới hạn lịch sử OHLCV ngày ở 365 ngày. Để tái lập tập nghiên cứu hiện có, script giữ archive lịch sử đã được quản lý trong dự án, lấy cửa sổ mới, rồi kiểm tra và căn chỉnh bốn cột OHLC theo tỷ lệ VCI trả về trên overlap. Lần cập nhật này dùng 8 phiên trùng, hệ số trung vị 0,8875 và độ trải tương đối dưới 0,011%; volume không được điều chỉnh. Nếu không có archive hoặc overlap không đủ tin cậy, script dừng mà không ghi dữ liệu. Hạn mức và basis giá được ghi trong <code>reports/data_lineage.json</code>; tài liệu chính thức: [quyền truy cập](https://www.vnstocks.com/docs/vnstock/tham-khao/cap-quyen-va-gioi-han), [nguồn dữ liệu](https://www.vnstocks.com/docs/vnstock/tham-khao/data-sources).

Phạm vi phiên bản đầu chỉ gồm OHLCV của FPT. Không ghép CPI, GDP, báo cáo tài chính hay tin tức vì chúng có tần suất và thời điểm công bố khác với ngày kỳ báo cáo; ghép sai thời điểm có thể đưa thông tin tương lai vào đặc trưng.

## 4. Định nghĩa nhãn và đặc trưng

Với phiên \(t\), lợi nhuận mục tiêu là \(r_{t+1}=close_{t+1}/close_t-1\). Nhãn tăng bằng 1 khi \(r_{t+1}>0\), giảm bằng 0 khi \(r_{t+1}<0\); phiên không đổi được báo cáo riêng và loại khỏi phân loại. Bài toán hồi quy dự đoán <code>close(t+1)</code> để bổ trợ cho đánh giá giá.

Hai mươi ba đặc trưng gồm lợi nhuận trễ 1–20 phiên, tỷ lệ giá với SMA/EMA 5–50 phiên, RSI, MACD và thành phần, Bollinger Bands, biến động 5/20 phiên, thay đổi log-volume và z-score log-volume. Mọi cửa sổ chỉ nhìn về quá khứ. Close phiên kế tiếp chỉ được dùng làm nhãn, không nằm trong đầu vào.

## 5. Phương pháp và mô hình

- **Baseline phân loại:** MajorityClassifier dự đoán lớp thường gặp nhất trong train.
- **Mô hình tuyến tính:** Logistic Regression với StandardScaler trong pipeline và cân bằng lớp.
- **Mô hình cây:** Random Forest và HistGradientBoosting.
- **Hồi quy bổ trợ:** giữ close hiện tại làm persistence baseline, Linear Regression, Random Forest Regressor và HistGradientBoosting Regressor.

Chia train/validation/test theo thứ tự target date, xấp xỉ 70/15/15. Chọn mô hình phân loại bằng Balanced Accuracy validation, tie-break bằng F1 lớp tăng. Chọn mô hình hồi quy bằng MAE validation. Scaler được fit trên train khi đo validation; mô hình cuối fit trên train cộng validation trước khi đánh giá test.

## 6. Đánh giá

Phân loại dùng Accuracy, Balanced Accuracy, Precision/Recall/F1 lớp tăng, ROC-AUC và confusion matrix. Hồi quy dùng RMSE, MAE, MAPE và Directional Accuracy. So sánh baseline là yêu cầu quan trọng: nếu mô hình phức tạp không cải thiện kết quả ngoài mẫu, kết luận đó vẫn là kết quả nghiên cứu hợp lệ.

Thử nghiệm hiện tại trên test 23/10/2023–30/09/2026 chọn Logistic Regression theo validation, nhưng mô hình đạt Balanced Accuracy 49,73% và ROC-AUC 49,41%. HistGradientBoosting đạt Accuracy 52,88%, còn Random Forest đạt ROC-AUC 55,13%. Baseline hồi quy giữ close đạt MAE 1,114 nghìn VND nhưng không dự báo được chiều biến động. Kết quả sơ bộ cho thấy phải trình bày giới hạn dự báo thay vì giả định trước rằng Machine Learning sẽ thắng baseline.

## 7. Kế hoạch 10 tuần cho nhóm 3 người

| Tuần | Công việc | Sản phẩm |
|---|---|---|
| 1 | Chốt câu hỏi, phạm vi và tiêu chí đánh giá | Proposal và sơ đồ pipeline |
| 2 | Kiểm tra nguồn, schema, đơn vị và lưu snapshot | Data dictionary, checksum |
| 3 | EDA và kiểm toán chất lượng | Audit JSON, biểu đồ |
| 4 | Tạo nhãn và đặc trưng trễ | Bảng đặc trưng, kiểm tra leakage |
| 5 | Cài baseline và Logistic Regression | Kết quả validation đầu tiên |
| 6 | Huấn luyện Random Forest và HistGradientBoosting | Bảng so sánh |
| 7 | Thử nghiệm hồi quy bổ trợ, rà soát split | Metrics và confusion matrix |
| 8 | Phân tích sai số, kiểm tra độ ổn định | Phần thảo luận |
| 9 | Hoàn thiện báo cáo và slide | Bản nháp để phản biện nội bộ |
| 10 | Tái chạy toàn bộ, sửa báo cáo, tập thuyết trình | Bản nộp và demo |

Phân công gợi ý: thành viên 1 phụ trách dữ liệu/EDA; thành viên 2 phụ trách đặc trưng, mô hình và kiểm thử; thành viên 3 phụ trách thiết kế thí nghiệm, phân tích metric, báo cáo và slide. Cả nhóm cùng rà soát tính đúng của nhãn, leakage và kết luận.

## 8. Sản phẩm và giới hạn

Sản phẩm gồm pipeline Python, snapshot OHLCV đã kiểm toán, các bảng metric, mô hình được chọn, biểu đồ và báo cáo. Dữ liệu thị trường có thể được nguồn cập nhật lại; quyền khách không cấp lịch sử đầy đủ để dựng lại toàn bộ chuỗi từ đầu. Hệ số căn chỉnh archive dựa trên overlap và được lưu để kiểm tra. Một cổ phiếu và OHLCV kỹ thuật không đại diện toàn bộ thông tin thị trường; kết quả không thể dùng như khuyến nghị đầu tư.
