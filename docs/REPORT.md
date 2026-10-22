# Báo cáo thực nghiệm: Dự đoán hướng và giá đóng cửa FPT phiên kế tiếp

## Tóm tắt

Dự án dự báo hai đại lượng khác nhau từ dữ liệu có đến cuối phiên (t): (1) giá đóng cửa phiên kế tiếp tăng hay giảm so với close phiên (t), và (2) giá close phiên kế tiếp. Snapshot gồm 4.919 phiên từ 02/01/2007 đến 30/09/2026. Sau khi bỏ 49 phiên chưa đủ lịch sử cho đặc trưng kỹ thuật, có 4.869 nhãn hồi quy.

Dữ liệu được chia theo thời gian, 85% đầu làm Train và 15% cuối làm Test. Train kết thúc ở target session 20/10/2023; Test kéo dài từ 23/10/2023 đến 30/09/2026. Bộ A gồm 23 chỉ báo kỹ thuật; bộ B bổ sung bốn đặc trưng nến. Trên Test, Random Forest với bộ B có Balanced Accuracy 54,00%, so với 52,91% của HistGradientBoosting với bộ A. Last-Close Baseline có MAE 1,114 nghìn VND/cổ phiếu và Directional Accuracy 0%.

Bộ C chưa được chạy vì các yêu cầu đến Vnstock đều thất bại khi lấy chính sách truy cập từ dịch vụ. Không có dữ liệu vĩ mô hoặc báo cáo tài chính nào được đưa vào kết quả. Vì thế, mọi kết luận định lượng trong báo cáo này chỉ áp dụng cho A và B.

## 1. Bài toán

Tại cuối phiên (t), đầu vào chứa dữ liệu đến hết phiên đó. Nhãn phân loại là:

[
direction_{t+1} =
\begin{cases}
1 & close_{t+1} > close_t \\
0 & close_{t+1} < close_t
\end{cases}
]

Các phiên có close không đổi được giữ trong dữ liệu thô nhưng loại khỏi bài toán phân loại. Bài toán hồi quy dự đoán trực tiếp (close_{t+1}), gồm cả phiên không đổi.

Hai bài toán được chấm riêng. Accuracy phân loại không đo sai số giá; MAE hồi quy không đo đúng chiều tăng/giảm.

## 2. Dữ liệu và kiểm toán

Nguồn snapshot giá là VCI (Vietcap), truy cập qua thư viện Python `vnstock`. File chuẩn có các cột `time, open, high, low, close, volume`; giá theo nghìn VND/cổ phiếu, khối lượng theo cổ phiếu. Vnstock mô tả giá cổ phiếu theo nghìn đồng và lưu ý các nguồn có thể có cách điều chỉnh lịch sử khác nhau sau sự kiện doanh nghiệp. [Tài liệu Vnstock về dữ liệu thị trường](https://vnstocks.com/docs/vnstock/thi-truong-market).

| Chỉ tiêu | Kết quả |
|---|---:|
| Số phiên OHLCV | 4.919 |
| Ngày đầu – ngày cuối | 02/01/2007 – 30/09/2026 |
| Thiếu dữ liệu | 0 ô |
| Ngày trùng | 0 |
| Volume bằng 0 | 2 phiên |
| Dòng có quan hệ OHLC bất nhất | 3 |
| Min/max close | 1,61525 – 118,073 nghìn VND |
| Lợi nhuận ngày trung bình | 0,0567% |
| Độ lệch chuẩn lợi nhuận ngày | 1,9246% |
| Lợi nhuận ngày nhỏ nhất – lớn nhất | −6,9896% – 6,9922% |

Ba dòng OHLC bất nhất vào 17/08/2007, 10/06/2009 và 07/12/2009 được giữ lại trong snapshot và đánh dấu trong audit; chúng không bị âm thầm sửa. Lợi nhuận phiên kế tiếp trong toàn bộ snapshot có 2.224 phiên tăng, 2.211 giảm và 483 không đổi.

![Giá đóng cửa FPT](../figures/01_fpt_close.png)

![Khối lượng giao dịch](../figures/02_fpt_volume.png)

![Phân phối lợi nhuận](../figures/03_daily_return_distribution.png)

## 3. Đặc trưng và tránh rò rỉ

Bộ A gồm 23 đặc trưng chỉ tính từ close và volume: lợi nhuận trễ 1/2/5/10/20 phiên, tỷ lệ close so với SMA/EMA, RSI, MACD, Bollinger %B/độ rộng, biến động và thay đổi volume.

Bộ B bổ sung bốn biến từ nến phiên (t):

1. Biên độ ((high-low)/close).
2. Thân nến ((close-open)/open).
3. Khoảng trống mở cửa (open_t/close_{t-1}-1).
4. Vị trí close trong biên độ ((close-low)/(high-low)). Khi biên độ bằng 0, giá close là mức giá duy nhất của phiên và biến này được gán 0,5.

Target dùng `close.shift(-1)`, nhưng `next_close` và `direction` không nằm trong đầu vào. Đặc trưng tại phiên (t) chỉ dùng giá/volume đã biết tại hoặc trước phiên đó. Một kiểm thử thay đổi giá tương lai xác nhận các đặc trưng ở phiên trước không đổi.

Dữ liệu bổ trợ, khi lấy được, được căn theo ngày có thể biết bằng phép ghép lùi (lấy quan sát gần nhất có hiệu lực không muộn hơn ngày giao dịch). Không điền ngược giá trị thiếu. Script dự kiến trễ 1 ngày cho tỷ giá/vàng, 10 ngày cho CPI và 45 ngày cho GDP/báo cáo quý. Ngày cuối kỳ của báo cáo không đồng nghĩa với ngày thông tin được công bố.

## 4. Thiết lập Train/Test

Split được áp dụng theo target session, không xáo trộn:

| Tập | Khoảng ngày target | Hồi quy | Phân loại |
|---|---|---:|---:|
| Train, 85% đầu | 21/03/2007–20/10/2023 | 4.138 | 3.682 |
| Test, 15% cuối | 23/10/2023–30/09/2026 | 731 | 711 |

Phân loại bỏ các nhãn đứng giá, nên số hàng phân loại thấp hơn hồi quy. A và B có cùng tập ngày và cùng ranh giới. `StandardScaler` nằm trong Pipeline của Logistic Regression và Linear Regression; scaler chỉ được fit trên Train trong phép đánh giá Test.

Các mô hình phân loại: Majority Baseline, Logistic Regression, Random Forest và HistGradientBoosting. Các mô hình hồi quy: Last-Close Baseline, Linear Regression, Random Forest Regressor và HistGradientBoosting Regressor. Tất cả mô hình học máy được fit trên Train, sau đó dự đoán Test.

Theo yêu cầu so sánh trực tiếp, mô hình phân loại được đánh dấu chọn theo Balanced Accuracy Test, tie-break bằng F1 lớp tăng; mô hình hồi quy chọn theo MAE Test, tie-break bằng RMSE. Vì tập Test tham gia vào bước chọn mô hình, kết quả của mô hình được chọn có thể lạc quan và không còn là ước lượng độc lập hoàn toàn. Sau khi lưu metric, mô hình A/B được chọn được fit lại trên toàn bộ nhãn có sẵn để tạo dự báo mới nhất. Việc fit lại này không thay đổi metric Test đã báo cáo.

## 5. Kết quả phân loại Tăng/Giảm

F1, Precision và Recall dưới đây tính cho lớp Tăng.

| Bộ | Mô hình | Accuracy | Balanced Accuracy | Precision (Tăng) | Recall (Tăng) | F1 (Tăng) | ROC-AUC |
|---|---|---:|---:|---:|---:|---:|---:|
| A | Majority Baseline | 49,09% | 50,00% | 49,09% | 100,00% | 65,85% | 50,00% |
| A | Logistic Regression | 49,65% | 49,73% | 48,84% | 54,15% | 51,36% | 49,41% |
| A | Random Forest | 51,62% | 51,60% | 50,72% | 50,43% | 50,57% | 55,13% |
| A | HistGradientBoosting | 52,88% | 52,91% | 51,92% | 54,15% | 53,02% | 52,63% |
| B | Majority Baseline | 49,09% | 50,00% | 49,09% | 100,00% | 65,85% | 50,00% |
| B | Logistic Regression | 50,35% | 50,46% | 49,49% | 56,16% | 52,62% | 50,49% |
| B | Random Forest | 54,01% | 54,00% | 53,13% | 53,58% | 53,35% | 55,91% |
| B | HistGradientBoosting | 51,76% | 51,78% | 50,83% | 52,72% | 51,76% | 52,07% |

Trong phép so sánh này, bộ B cải thiện Balanced Accuracy tốt nhất từ 52,91% lên 54,00%, tức tăng khoảng 1,09 điểm phần trăm. Random Forest bộ B cũng có Accuracy cao nhất 54,01% và ROC-AUC 55,91%. Đây là cải thiện vừa phải; kết quả vẫn gần mức ngẫu nhiên, chưa chứng minh được khả năng dự báo ổn định.

Confusion matrix của Random Forest bộ B; hàng là nhãn thật, cột là dự đoán:

| | Dự đoán Giảm | Dự đoán Tăng |
|---|---:|---:|
| Thực tế Giảm | 197 | 165 |
| Thực tế Tăng | 162 | 187 |

![Confusion matrix trên Test](../figures/05_test_confusion_matrix.png)

## 6. Kết quả hồi quy giá

Giá được đo theo nghìn VND/cổ phiếu. Tolerance Accuracy là tỷ lệ phiên có sai số tương đối so với giá thực tế không quá ngưỡng.

| Bộ | Mô hình | RMSE | MAE | MAPE | Directional Accuracy | Trong ±0,5% | Trong ±1% | Trong ±2% |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | Last-Close Baseline | 1,5359 | **1,1141** | 1,3308% | 0,00% | 26,68% | 50,21% | 78,93% |
| A | Linear Regression | 1,5372 | 1,1183 | 1,3370% | 48,66% | 28,45% | 49,93% | 78,52% |
| A | Random Forest Regressor | 27,7087 | 22,6920 | 24,0408% | 52,74% | 2,33% | 4,38% | 8,07% |
| A | HistGradientBoosting Regressor | 27,5928 | 22,5710 | 23,9094% | 51,90% | 0,55% | 1,50% | 5,20% |
| B | Last-Close Baseline | 1,5359 | **1,1141** | 1,3308% | 0,00% | 26,68% | 50,21% | 78,93% |
| B | Linear Regression | 1,5352 | 1,1150 | 1,3181% | 48,66% | 28,45% | 49,93% | 78,66% |
| B | Random Forest Regressor | 27,7086 | 22,6920 | 24,0408% | 52,74% | 2,33% | 4,38% | 8,07% |
| B | HistGradientBoosting Regressor | 27,3896 | 22,3036 | 23,5809% | 52,18% | 1,64% | 3,28% | 6,43% |

Last-Close Baseline có MAE thấp nhất, nhưng vì nó luôn dự đoán giá ngày mai bằng giá hôm nay nên Directional Accuracy bằng 0%. Nó dự báo mức giá sát trong một ngày thường nhưng không đoán chiều. Hai mô hình cây có thể nhận ra một phần chiều biến động nhưng sai số mức giá lớn, cho thấy mô hình hiện tại dự báo trực tiếp giá tuyệt đối chưa xử lý tốt xu hướng dài hạn.

±0,5%, ±1% và ±2% là dung sai tương đối của đồ án, không phải biên độ sàn. Ở mức giá 63.000 đồng, các mức này tương đương lần lượt ±315, ±630 và ±1.260 đồng. HOSE công bố biên độ dao động thông thường của cổ phiếu ±7% so với giá tham chiếu, với ngoại lệ theo trường hợp; biên độ giao dịch là bối cảnh thị trường, không phải tiêu chuẩn chất lượng mô hình. [Tài liệu biên độ giá HOSE](https://staticfile.hsx.vn/Uploads/UploadDocuments/2372201/4.Bien%20do%20dao%20dong%20gia.pdf).

![Giá thực tế và dự đoán](../figures/06_actual_vs_predicted_close.png)

## 7. Thử nghiệm bổ trợ C

C dự kiến kết hợp đặc trưng B với VN-Index, USD/VND, giá vàng, CPI, GDP và dữ liệu tài chính FPT. Script `src/fetch_supplemental.py` đã được chạy cho giai đoạn 2007–30/09/2026. Sáu truy vấn đều trả lỗi truy cập chính sách máy khách của Vnstock; dữ liệu nhận được bằng không. Vì vậy, bộ C có trạng thái `not_run`, không có Accuracy/MAE và không được dùng để chọn mô hình.

Đây là giới hạn môi trường thu thập chứ không phải kết quả cho thấy biến vĩ mô không hữu ích. Tài liệu Vnstock hiện mô tả dữ liệu nến VN-Index, forex và hàng hóa trong các tuyến cộng đồng; báo cáo tài chính cấp Khách có thể bị giới hạn bốn kỳ, còn GDP/CPI/tỷ giá qua `Macro()` thuộc bản mở rộng. [Market](https://vnstocks.com/docs/vnstock/thi-truong-market), [Fundamental](https://vnstocks.com/docs/vnstock/co-ban-fundamental), [Macro](https://vnstocks.com/docs/vnstock/vi-mo-macro). Khi có kết nối và quyền phù hợp, chạy script thu thập, kiểm tra ngày công bố và chạy lại `python src/train.py`; bảng ablation sẽ tự ghi coverage riêng của C.

## 8. Dự báo mới nhất

Với dữ liệu đến 30/09/2026, mô hình phân loại được chọn là Random Forest bộ B. Dự báo chiều phiên kế tiếp là Tăng với xác suất 57,50% trên hai lớp Tăng/Giảm. Mô hình hồi quy được chọn là Last-Close Baseline, dự báo close 63,0 nghìn VND, bằng close phiên 30/09/2026.

Hai kết quả trên đến từ hai bài toán riêng. Đây là minh họa đầu ra học thuật, không phải khuyến nghị đầu tư.

## 9. Kết luận và giới hạn

Trên cùng giai đoạn Test, các đặc trưng nến B giúp mô hình Random Forest tăng Balanced Accuracy khoảng 1,09 điểm phần trăm so với mô hình tốt nhất của A. Mức cải thiện chưa đủ để khẳng định dự báo hướng đáng tin cậy. Với giá, Last-Close Baseline có sai số nhỏ hơn rõ rệt so với các mô hình cây, nhưng không dự báo được chiều.

Giới hạn quan trọng gồm Test được dùng để chọn mô hình, bộ C chưa chạy được, một cổ phiếu duy nhất, giả định độ trễ báo cáo theo số ngày thay vì lịch công bố chính xác, và nguồn giá có thể điều chỉnh lại lịch sử. Hướng tiếp theo là khôi phục truy cập API hoặc nạp cache nguồn đã kiểm chứng, ghi nhận ngày công bố thật của báo cáo, đánh giá walk-forward nhiều cửa sổ và thử hồi quy lợi nhuận thay vì mức giá tuyệt đối.

## Tái lập kết quả

```bash
python src/eda.py
python src/prepare.py
python src/train.py
python src/predict.py
python -m pytest -q
```

Để thử thu thập dữ liệu bổ trợ:

```bash
python src/fetch_supplemental.py --start 2007-01-01 --end 2026-09-30
python src/train.py
```

Bảng kết quả đầy đủ nằm tại `reports/classification_test_metrics.csv`, `reports/regression_test_metrics.csv`, `reports/ablation_summary.csv`; ranh giới ngày và quy tắc lựa chọn mô hình nằm tại `reports/split_metadata.json`.
