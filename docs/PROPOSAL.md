# ĐỀ XUẤT ĐỒ ÁN CUỐI KỲ MACHINE LEARNING

## Tên đề tài

**Phân loại xu hướng tăng/giảm của cổ phiếu FPT ở phiên kế tiếp bằng các mô hình Machine Learning trên dữ liệu giá và khối lượng giao dịch**

## 1. Đặt vấn đề

Giá cổ phiếu thay đổi theo nhiều yếu tố và chứa nhiễu đáng kể. Việc dự đoán trực tiếp một mức giá cụ thể dễ tạo cảm giác chính xác nhưng chưa trả lời được câu hỏi thực tế của thí nghiệm: các thông tin đã quan sát có giúp nhận biết phiên tiếp theo tăng hay giảm hay không? Đề tài chuyển vấn đề thành một bài toán phân loại nhị phân có nhãn rõ ràng, đầu vào xác định và có thể đánh giá trên một giai đoạn tương lai chưa dùng trong huấn luyện.

FPT được chọn vì có lịch sử giao dịch dài và repo nguồn cung cấp dữ liệu giá, khối lượng theo ngày. Đề tài vừa áp dụng các kỹ thuật học có giám sát đã học—tạo đặc trưng, huấn luyện, xác thực theo thời gian, đo hiệu quả—vừa tạo cơ hội phân tích các giới hạn của dự đoán tài chính.

## 2. Mục tiêu và câu hỏi nghiên cứu

Mục tiêu chính là đánh giá liệu dữ liệu lịch sử giá đóng cửa và khối lượng FPT có khả năng phân loại hướng biến động của phiên kế tiếp tốt hơn baseline hay không. Câu hỏi nghiên cứu:

> **Các mô hình Logistic Regression, Random Forest và HistGradientBoosting có phân loại xu hướng tăng/giảm phiên kế tiếp của cổ phiếu FPT tốt hơn mô hình baseline trên dữ liệu kiểm tra theo thời gian hay không?**

Các mục tiêu cụ thể:

1. Kiểm tra chất lượng dữ liệu OHLCV, mô tả lịch sử giá, khối lượng và phân phối lợi nhuận.
2. Tạo các đặc trưng kỹ thuật chỉ từ dữ liệu đã biết đến cuối phiên dự báo.
3. So sánh baseline với các mô hình phân loại tuyến tính và phi tuyến trên cùng các giai đoạn thời gian.
4. Phân tích sai số bằng Balanced Accuracy, F1, ROC-AUC, confusion matrix và các chỉ số liên quan.
5. Thực hiện thêm thí nghiệm hồi quy giá đóng cửa phiên kế tiếp để minh họa vì sao sai số giá và dự đoán hướng là hai mục tiêu khác nhau.

## 3. Phạm vi dữ liệu và xuất xứ

Đầu vào chính là snapshot `data/raw/fpt/fpt_historical_price.csv` trong repo [DS111 UIT Stock Price Analysis](https://github.com/nguyenlog205/ds111-uit-stock-price-analysis), gồm sáu trường `time, open, high, low, close, volume`, 4.678 phiên từ 2007-01-02 đến 2025-10-09. Kiểm tra trực tiếp notebook [`API_use.ipynb`](https://github.com/nguyenlog205/ds111-uit-stock-price-analysis/blob/main/notebook/data_ingestion/API_use.ipynb) xác định cách trích xuất: `vnstock.Quote(symbol='FPT', source='VCI').history(start='2007-01-01', end='2025-10-09')`, sau đó lưu DataFrame thành CSV. Do đó nguồn được chọn là VCI/Vietcap thông qua thư viện Python `vnstock`, không phải dữ liệu lấy từ widget TradingView hay công cụ Selenium. Tệp có 4.678 hàng, không có giá trị thiếu hoặc ngày lặp; có hai phiên volume bằng 0 và ba hàng có bất nhất high/low được giữ nguyên.

Giá trị được ghi ở thang xấp xỉ nghìn đồng/cổ phiếu (ví dụ `94.2` tương ứng khoảng 94.200 đồng); báo cáo đồ án nguồn cũng ghi sai số dự báo giá theo nghìn VND, dù CSV không lưu metadata đơn vị. Notebook không có cờ hoặc mô tả cho biết VCI trả chuỗi adjusted/unadjusted; snapshot chỉ chứa OHLCV. Dự án vì thế giữ nguyên thang giá từ nhà cung cấp, không tự điều chỉnh. `python src/fetch_data.py --verify` xác nhận SHA-256 nội dung LF-normalized `263eced0cb25bc0380ed0dba7dc6f8d77b409146c7b4e2b1b0fd9f0ddbf25e98`, cấu trúc và khoảng ngày. Chuẩn hóa LF làm hash nhất quán giữa Windows và Linux; API có thể sửa lịch sử nên lần tải sau không được giả định giống snapshot.

Các tệp liên quan trong repo nguồn được ghi xuất xứ riêng: báo cáo thu nhập FPT dùng `vnstock.Finance`/VCI; USD/VND, CPI và XAU/USD được ghi là Investing.com; GDP từ World Bank với dự báo 2025 từ IMF; P/E ngành ICT từ Simply Wall St. Báo cáo nguồn xác nhận macro được tải thủ công thành CSV, market cap/P-E chép thủ công, còn OHLCV và tài chính FPT lấy bằng API vnstock. Tài liệu upstream cũ/mới có chỗ thiếu hoặc không nhất quán về nguồn GDP/XAU; chi tiết được ghi trong [data/README.md](../data/README.md). Repo còn có script dùng Selenium điều khiển Google News và `newspaper3k` để bóc nội dung, nhưng script này không tạo đặc trưng trong CSV huấn luyện của đồ án. Dự án chỉ dùng OHLCV FPT.

Không sử dụng `synthetized_dataset.csv`/`predictive_modeling.csv` làm đầu vào. Tập tổng hợp 1.529 ngày thiếu CPI 95,55%, GDP 99,67%, market cap/P-E 98,76%, các biến báo cáo FPT 98,56%, giá/volume 6,28%. Notebook tiền xử lý tạo `predictive_modeling.csv` gọi `fit_transform` trên cả bảng và dùng `bfill`; `src/preprocessor.py` cũng fit `StandardScaler` trên toàn chuỗi. Thời điểm fit không được lưu thành metadata riêng, nên có nguy cơ đưa phân phối tương lai vào giai đoạn trước. Dự án tự tính đặc trưng chỉ từ dữ liệu quá khứ và fit scaler trong pipeline trên tập train.

Để tải lại qua VCI (cần cài `vnstock` theo hướng dẫn chính thức):

```bash
python src/fetch_data.py --download --start 2007-01-01 --end 2025-10-09 --output data/raw/fpt/fpt_historical_price.csv
```

Có thể chuẩn hóa tệp xuất sẵn bằng `python src/fetch_data.py --input export.csv --output data/raw/fpt/fpt_historical_price.csv`; lệnh kiểm định snapshot là `python src/fetch_data.py --verify`. Chi tiết audit và giới hạn đơn vị/điều chỉnh được nêu trong [data/README.md](../data/README.md).

## 4. Định nghĩa bài toán

Thời điểm dự báo là sau khi phiên `t` đóng cửa. Từ các quan sát đến hết phiên `t`, mô hình dự đoán phiên giao dịch kế tiếp:

\[
r_{t+1}=\frac{Close_{t+1}}{Close_t}-1
\]

Nhãn phân loại chính là `up` nếu \(r_{t+1}>0\), `down` nếu \(r_{t+1}<0\). Trường hợp giá đóng cửa không đổi được xem là trung tính và loại khỏi bài toán nhị phân; trong nguồn có 479 trường hợp như vậy. Quy tắc này tránh gộp các phiên không đổi vào lớp giảm. Tập hồi quy giá phụ vẫn giữ các trường hợp giá không đổi.

## 5. Phương pháp

### 5.1. Tiền xử lý và tạo đặc trưng

Dữ liệu được chuyển cột thời gian sang kiểu ngày, sắp xếp tăng dần và kiểm tra tính duy nhất. Không nội suy hoặc điền ngược dữ liệu. Các NaN đầu chuỗi phát sinh tự nhiên do cửa sổ chỉ báo được loại bỏ; dòng cuối không có nhãn phiên kế tiếp chỉ dùng được để tạo dự đoán mới, không dùng trong đánh giá.

23 đặc trưng phân loại gồm:

- Lợi nhuận trễ 1, 2, 5, 10 và 20 phiên.
- Tỷ lệ giá đóng cửa so với SMA/EMA ở cửa sổ 5, 10, 20 và 50 phiên.
- RSI-14; MACD, đường tín hiệu và histogram được chia theo giá đóng cửa.
- Phần trăm vị trí và độ rộng Bollinger Bands 20 phiên.
- Độ lệch chuẩn lợi nhuận 5 và 20 phiên.
- Thay đổi một phiên và z-score 20 phiên của log-volume.

Các chỉ báo đều tính từ hiện tại và quá khứ, không sử dụng giá phiên kế tiếp. Bài toán hồi quy bổ sung giá đóng cửa hiện tại làm đặc trưng để dự báo giá ở thang đo nguồn.

### 5.2. Mô hình

| Vai trò | Mô hình | Thiết lập chính |
|---|---|---|
| Baseline phân loại | Majority classifier | Dự đoán lớp phổ biến trong train |
| Tuyến tính | Logistic Regression | `C=1`, cân bằng lớp, tối đa 3.000 vòng; StandardScaler trong pipeline |
| Cây tổ hợp | Random Forest | 350 cây, `max_depth=8`, `min_samples_leaf=20`, `balanced_subsample` |
| Boosting | HistGradientBoosting | `learning_rate=0.05`, `max_iter=160`, tối đa 15 lá, L2=1, tắt early stopping nội bộ |

Trong hồi quy giá, so sánh thêm baseline giữ nguyên giá đóng cửa hiện tại, Linear Regression, Random Forest Regressor và HistGradientBoosting Regressor. Không dùng LSTM/GRU vì dữ liệu một mã cổ phiếu có kích thước vừa phải; ưu tiên các mô hình dễ giải thích và chạy được trên Colab miễn phí.

### 5.3. Chia tập và chống rò rỉ

Chia theo ngày mục tiêu của nhãn, giữ nguyên thứ tự thời gian: khoảng 70% train, 15% validation, 15% test. Kết quả chạy trên tệp hiện tại tạo ra các khoảng:

- Train: nhãn đến 2020-03-19.
- Validation: 2020-03-20 đến 2022-12-22.
- Test: 2022-12-23 đến 2025-10-09.

Mô hình và mọi biến đổi được fit trên train để tính validation. Sau khi chọn mô hình theo validation, pipeline được fit lại trên train+validation rồi đánh giá một lần trên test. StandardScaler nằm bên trong pipeline Logistic/Linear Regression, nên không fit trước trên toàn bộ chuỗi.

## 6. Đánh giá

Với phân loại, dùng Accuracy, Balanced Accuracy, Precision, Recall, F1 cho lớp tăng, ROC-AUC và confusion matrix. Balanced Accuracy được báo cáo cùng Accuracy để tránh kết luận phụ thuộc vào chênh lệch tỷ lệ lớp. Tiêu chí chọn classifier là Balanced Accuracy validation cao nhất; nếu hòa, dùng F1 lớp tăng để phân định.

Với hồi quy, báo cáo RMSE, MAE, MAPE và Directional Accuracy. Directional Accuracy so dấu biến động dự đoán với biến động thực tế, chỉ tính trên các phiên có giá thực tế thay đổi. Tiêu chí chọn hồi quy là MAE validation thấp nhất, kể cả baseline giữ nguyên giá.

## 7. Kết quả dự kiến và ý nghĩa

Đề tài dự kiến tạo pipeline chạy lại được, báo cáo so sánh mô hình và phân tích những trường hợp dự đoán sai. Không giả định mô hình sẽ đạt độ chính xác cao: kết quả gần baseline cũng có giá trị vì thể hiện độ khó của bài toán và hạn chế của chỉ báo kỹ thuật đơn biến. Không xem kết quả phân loại là bằng chứng về lợi nhuận đầu tư.

## 8. Kế hoạch 10 tuần

| Tuần | Công việc | Sản phẩm |
|---|---|---|
| 1 | Chốt câu hỏi, nhãn và phạm vi | Đề cương và định nghĩa dự báo |
| 2 | Thu thập, kiểm tra dữ liệu | CSV nguồn và kiểm kê dữ liệu |
| 3 | EDA, trực quan hóa | Biểu đồ giá, volume, lợi nhuận |
| 4 | Tạo đặc trưng, kiểm tra nhãn | Bảng đặc trưng và kiểm thử căn chỉnh |
| 5 | Majority baseline, Logistic Regression | Kết quả ban đầu |
| 6 | Random Forest, HistGradientBoosting | Bảng validation |
| 7 | Chốt cấu hình, đánh giá test | Metrics, confusion matrix, dự báo giá phụ |
| 8 | Phân tích lỗi và giới hạn | Phần thảo luận |
| 9 | Viết báo cáo và slide | Bản thảo hoàn chỉnh |
| 10 | Kiểm tra tái lập, luyện thuyết trình | Repo và bản trình bày cuối |

## 9. Phân công đề xuất cho nhóm ba người

- Thành viên 1: dữ liệu, kiểm kê, EDA và trực quan hóa.
- Thành viên 2: tạo đặc trưng, baseline và Logistic Regression.
- Thành viên 3: Random Forest/Boosting, đánh giá và lưu artifact.
- Cả nhóm: rà soát rò rỉ dữ liệu, thống nhất cách diễn giải, viết báo cáo và chuẩn bị thuyết trình.

## 10. Giới hạn

Thí nghiệm ban đầu chỉ dùng một cổ phiếu, không có VN-Index, nhóm ngành hay tin tức. Nguồn dữ liệu có thể được nhà cung cấp hiệu chỉnh lại theo sự kiện doanh nghiệp; metadata snapshot không xác nhận chính sách adjusted/unadjusted. Đơn vị nghìn đồng là diễn giải theo thang giá của tệp, không phải metadata được lưu. Nguồn kết thúc ngày 2025-10-09 nên chưa phản ánh các phiên sau ngày đó. Đây là các giới hạn cần giữ khi diễn giải kết quả.
