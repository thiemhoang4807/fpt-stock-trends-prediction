# ĐỀ XUẤT Ý TƯỞNG ĐỒ ÁN MÔN HỌC CS114

**ĐẠI HỌC QUỐC GIA THÀNH PHỐ HỒ CHÍ MINH — TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN**

**Đề tài: ỨNG DỤNG HỌC MÁY DỰ ĐOÁN XU HƯỚNG VÀ GIÁ ĐÓNG CỬA CỔ PHIẾU FPT Ở PHIÊN KẾ TIẾP**

| STT | Họ và tên | MSSV |
|---|---|---|
| 1 | Lê Vũ Thiêm Hoàng | 25520584 |
| 2 | Nguyễn Tấn Dũng | 25520367 |
| 3 | Lưu Hoàng Minh Duy | 25520424 |

THÀNH PHỐ HỒ CHÍ MINH, NĂM 2026

## 1. Đặt vấn đề

Giá cổ phiếu thay đổi theo cung cầu, thông tin doanh nghiệp và điều kiện thị trường. Nhóm đặt câu hỏi: sau khi phiên giao dịch FPT hôm nay kết thúc, các mô hình có thể dự đoán hướng tăng/giảm và mức giá đóng cửa phiên kế tiếp với độ chính xác nào? Việc bổ sung dữ liệu thị trường, vĩ mô và báo cáo tài chính có cải thiện so với chỉ sử dụng giá và khối lượng hay không?

Theo góp ý của giảng viên, đề tài mở rộng từ học máy trên dữ liệu bảng sang phân tích chuỗi thời gian, mô hình thống kê và học sâu tuần tự. Nhóm chú trọng cách đánh giá theo thời gian và giải thích kết quả. Hệ thống là thực nghiệm học thuật hỗ trợ phân tích định lượng, không thay thế quyết định của nhà đầu tư.

## 2. Mục tiêu của đề tài

Mục tiêu chung là xây dựng quy trình dự báo một phiên kế tiếp có thể tái lập và đánh giá đóng góp của dữ liệu cũng như phương pháp học.

1. Kiểm toán nguồn, đơn vị, độ phủ và thời điểm có thể sử dụng của dữ liệu đến **30/09/2025**.
2. Phân tích tính dừng bằng ADF/KPSS, tương quan theo độ trễ bằng ACF/PACF và phân rã chuỗi bằng STL.
3. So sánh ba họ mô hình trên cùng các ngày, dùng kiểm định chéo thời gian trong Train để lựa chọn trước khi chấm Test.
4. Giải thích mô hình bằng SHAP và permutation importance; kiểm tra đóng góp từng nhóm đầu vào bằng nghiên cứu loại trừ (ablation study).

## 3. Phạm vi và đối tượng nghiên cứu

Đối tượng là FPT trên HOSE. Chuỗi giá gồm 4.671 phiên từ 02/01/2007 đến 30/09/2025. Mốc kết thúc được cố định để đồng bộ các nguồn đã kiểm tra. Mỗi hàng ở cuối phiên `t` dự báo phiên giao dịch quan sát được kế tiếp `t+1`, không phải mặc nhiên ngày lịch tiếp theo.

Cửa sổ so sánh chung ngắn hơn chuỗi giá vì nguồn bổ trợ bắt đầu muộn và mạng tuần tự cần đủ tối đa 60 phiên liên tiếp. Hai nhánh dùng cùng ngày, nhãn và ranh giới chia tập. Không dùng toàn bộ lịch sử cho một nhánh rồi so với nhánh khác trên một giai đoạn khác.

Dữ liệu ngành Simply Wall St đã kiểm tra chỉ có 33 mốc từ 06/02/2016 đến 24/07/2025, không có lịch sử từ 2007 và thiếu thành phần ngành theo thời điểm. Nhóm **loại ba biến ngành khỏi mô hình chính**, ghi nhận G5 là nhóm chưa thực hiện được. VN-Index được bổ sung làm biến kiểm soát thị trường chung; đây không phải chỉ số thay thế riêng cho ngành ICT. Nhóm chưa dựng rổ từ doanh nghiệp hiện còn niêm yết vì có thể tạo thiên lệch sống sót.

## 4. Đầu vào và đầu ra dự kiến

### 4.1. Đầu vào

| Nhánh | Các nhóm dữ liệu | Số biến |
|---|---|---:|
| Nhánh 1 — Giá và khối lượng | 5 trường OHLCV hiện tại, 23 chỉ báo kỹ thuật, 4 đặc trưng nến | 32 |
| Nhánh 2 — Đa nguồn | Toàn bộ Nhánh 1; lợi nhuận và biến động VN-Index; USD/VND, vàng quy đổi VND, CPI, GDP; 5 chỉ tiêu tài chính FPT | 43 |

Năm chỉ tiêu tài chính gồm doanh thu thuần, lợi nhuận gộp, EBIT, lợi nhuận sau thuế cổ đông công ty mẹ và số cổ phiếu lưu hành. Nguồn gồm VCI/vnstock, công bố FPT, DNSE, Investing.com và World Bank. Vàng quy đổi là giá quốc tế USD/ounce nhân tỷ giá VND/USD, không phải giá vàng miếng trong nước.

Dữ liệu tần suất thấp chỉ ghép từ ngày có thể biết, không điền ngược. Khi thiếu lịch công bố thực tế, báo cáo quý giả định trễ 45 ngày sau cuối quý, GDP năm trễ 180 ngày sau cuối năm. Giả định này giúp kiểm soát thời điểm sử dụng nhưng chưa khôi phục được đầy đủ các phiên bản dữ liệu lịch sử. Bộ chuẩn hóa chỉ học từ phần Train tương ứng.

### 4.2. Đầu ra và biến mục tiêu

Phân loại dùng nhãn `1` khi giá phiên sau tăng, `0` khi giảm; phiên đứng giá bị loại khỏi chấm phân loại. Hồi quy giữ cả phiên đứng giá và học lợi nhuận logarit:

$$r_{t+1}=\ln(C_{t+1}/C_t),\qquad \widehat C_{t+1}=C_t\exp(\widehat r_{t+1}).$$

| Trường | Ý nghĩa |
|---|---|
| Target session | Phiên giao dịch quan sát được kế tiếp |
| Predicted direction | Tăng hoặc Giảm |
| Direction score / probability | Điểm dự báo; chỉ gọi là xác suất nếu mô hình hỗ trợ |
| Predicted log return | Lợi nhuận logarit dự báo phiên kế tiếp |
| Predicted close price | Giá đóng cửa suy ra, nghìn VND/cổ phiếu |
| Model / feature set | Mô hình và nhánh dữ liệu tạo dự báo |

Điểm biên SVC hoặc lợi nhuận dự báo ARIMA không được gọi là xác suất. Hai bài toán có thể chọn hai mô hình khác nhau.

![Sơ đồ đầu vào, xử lý và đầu ra](../figures/00_pipeline_overview.png)

## 5. Hướng tiếp cận và công nghệ dự kiến

Nhóm dùng Python, pandas, NumPy, scikit-learn, XGBoost, statsmodels, PyTorch, SHAP và Jupyter Notebook.

- **Thống kê chuỗi thời gian:** ARIMA cho nhánh giá; SARIMAX cho nhánh đa nguồn với các biến ngoại sinh đã căn thời điểm. Khởi đầu bằng bậc `(0,0,0)` và `(1,0,0)` trên log return, chưa dùng mùa vụ. Dự báo từng phiên; chỉ cập nhật trạng thái bằng kết quả đã quan sát và giữ nguyên tham số trong phần đánh giá.
- **Học máy và boosting:** Majority/Last-Close Baseline, Logistic/Linear/Ridge Regression, SVC/SVR, Random Forest, XGBoost và HistGradientBoosting. Lưới nhỏ được đặt trước và lựa chọn bằng CV.
- **Học sâu tuần tự:** LSTM và GRU cho cả hai bài toán, một lớp 16 nút ẩn, thử `L ∈ {10, 20, 30, 60}` phiên. Cấu hình đầu tiên dùng 12 lượt học cố định trên CPU, không dừng theo kết quả Test. Cửa sổ phải giữ đúng phiên liên tiếp.

ADF và KPSS có giả thuyết gốc khác nhau nên cần đọc đồng thời, không coi một p-value là chứng minh chắc chắn tính dừng. ACF/PACF giúp mô tả liên hệ với quá khứ. Phân rã STL dùng chu kỳ quy ước 5 phiên để khảo sát, không mặc định có mùa vụ tuần và không đưa thành phần phân rã vào đầu vào dự báo.

## 6. Cách đánh giá dự kiến

Giữ **85% mẫu đầu làm Train, 15% cuối làm Test**, kết thúc 30/09/2025. Trong Train, dùng `TimeSeriesSplit(n_splits=5, gap=1)` với cửa sổ mở rộng. Mỗi fold học quá khứ rồi chấm đoạn kế tiếp; báo cáo trung bình ± độ lệch chuẩn mẫu qua 5 fold. Các fold bằng số hàng nhưng có thể không bằng số ngày lịch do khoảng trống nguồn.

Chọn mô hình phân loại bằng **Balanced Accuracy CV**, hồi quy bằng **RMSE log return CV**. Sau đó fit toàn bộ Train và chấm Test. Mô hình đánh giá được lưu riêng; bản dự báo minh họa có thể học lại toàn bộ nhãn sau khi cố định kết quả. Các ngày Test đã từng được xem trong phiên bản cũ, vì vậy nhóm chỉ khẳng định không dùng Test để lựa chọn trong lần nâng cấp này, chưa thể gọi đó là một giai đoạn ngoài mẫu hoàn toàn chưa từng quan sát.

| Bài toán | Độ đo |
|---|---|
| Hướng | Accuracy, Balanced Accuracy, Precision, Recall, F1-score, ROC-AUC, confusion matrix |
| Log return | MAE, RMSE |
| Giá khôi phục | MAE, RMSE, MAPE, Directional Accuracy; Tolerance Accuracy ±0.5%, ±1.0%, ±2.0% |

Không dùng MAPE trên log return vì các giá trị bằng/gần 0 làm sai số phần trăm không phù hợp. Nhóm vẽ giá thực tế và dự báo của các họ mô hình trên toàn Test và phóng to 80 phiên, cùng biểu đồ so sánh nhánh và độ dài cửa sổ.

Ablation giữ XGBoost, cùng các ngày và cùng CV: G1 giá/khối lượng và lợi nhuận trễ; G2 thêm chỉ báo kỹ thuật; G3 thêm OHLC/nến; G4 thêm thị trường/vĩ mô; G5 ghi loại vì nguồn ngành chưa phù hợp; G6 thêm tài chính doanh nghiệp. G5 không phải một thí nghiệm độc lập có dữ liệu giả lập.

SHAP và permutation importance phân tích mô hình cây chọn bằng CV; background SHAP chỉ lấy Train. Không điều chỉnh mô hình sau khi xem giải thích Test. Các biến tương quan có thể chia sẻ độ quan trọng; các kết quả mô tả hành vi dự báo, không chứng minh tác động nhân quả.

## 7. Kết quả dự kiến

1. Pipeline dữ liệu, bảng đặc trưng, kiểm toán và notebook có hướng dẫn từng bước.
2. Mô hình của ba họ cùng công cụ dự báo hướng, log return và giá phiên kế tiếp.
3. Bảng CV/Test, đối sánh độ dài cửa sổ, ablation, SHAP và permutation importance.
4. Báo cáo ưu/nhược điểm, trường hợp thất bại và giới hạn dữ liệu; đề xuất kiểm thử trên giai đoạn mới, lịch công bố thực tế và nhiều seed.

Nhóm báo cáo cả trường hợp mô hình phức tạp không vượt baseline. Kết quả đã chạy được trình bày riêng tại [REPORT.md](REPORT.md); bản PDF tương ứng là [cs114_proposal.pdf](cs114_proposal.pdf).
