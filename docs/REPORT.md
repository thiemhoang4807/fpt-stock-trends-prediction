# Báo cáo đồ án: Dự đoán xu hướng cổ phiếu FPT

## Tóm tắt

Đồ án xây dựng pipeline phân loại hướng thay đổi giá đóng cửa FPT ở phiên giao dịch kế tiếp, đồng thời so sánh một số mô hình hồi quy giá đóng cửa. Dữ liệu gồm 4.919 phiên từ 02/01/2007 đến 30/09/2026. Mô hình chỉ sử dụng OHLCV và 23 đặc trưng kỹ thuật trễ. Tập test được tách theo thời gian, từ 23/10/2023 đến 30/09/2026.

Logistic Regression được chọn trên validation nhưng đạt Balanced Accuracy 49,73% và ROC-AUC 49,41% trên test. HistGradientBoosting có Accuracy cao nhất 52,88%; Random Forest có ROC-AUC cao nhất 55,13%. Các kết quả đều yếu và không ổn định giữa metric. Với hồi quy, mô hình giữ nguyên close phiên hiện tại đạt MAE nhỏ nhất trên test là 1,114 nghìn VND; nhưng mô hình dự đoán giá không đổi có directional accuracy bằng 0%. Kết quả chưa cho thấy bằng chứng đủ mạnh để khẳng định chuỗi đặc trưng hiện tại dự báo tốt hơn baseline.

## 1. Bài toán và mục tiêu

Tại thời điểm đóng cửa phiên \(t\), hệ thống dùng lịch sử đến hết phiên đó để:

- Phân loại giá đóng cửa phiên kế tiếp tăng hay giảm so với phiên \(t\). Các phiên đóng cửa bằng nhau được loại khỏi bài toán phân loại.
- Dự đoán close của phiên kế tiếp bằng một số mô hình hồi quy bổ trợ.
- Đánh giá trên các phiên tương lai chưa dùng để huấn luyện hoặc chọn mô hình.

Mục tiêu thực nghiệm là đo chất lượng dự báo ngoài mẫu, không phải xây dựng chiến lược giao dịch hay khuyến nghị mua bán.

## 2. Dữ liệu và nguồn gốc

Pipeline dữ liệu: VCI (Vietcap) → thư viện Python <code>vnstock</code> 5.1.0 → <code>src/fetch_data.py</code> → CSV OHLCV chuẩn hóa → EDA và mô hình. API trả các trường <code>time, open, high, low, close, volume</code>; giá giữ theo thang nghìn VND/cổ phiếu của nguồn, volume là số cổ phiếu.

Ở lần chạy này quyền khách của API chỉ cung cấp tối đa 365 ngày. Archive lịch sử đã có trong dự án được giữ làm phần nền; dữ liệu VCI mới bao phủ 30/09/2025–30/09/2026. Tám phiên overlap được dùng để kiểm tra việc VCI cập nhật basis giá sau sự kiện doanh nghiệp. Trung vị tỷ số OHLC là 0,8875, độ trải tương đối dưới 0,011%. Archive trước cửa sổ mới được nhân hệ số 0,8875 trên bốn cột OHLC; volume được giữ nguyên. Các phiên trùng được thay bằng phản hồi mới. Nếu thiếu overlap hoặc tỷ số không ổn định, script dừng trước khi ghi file. Đây là phép nối và căn chỉnh archive; không phải tải lại toàn bộ 2007–2026 trong một truy vấn API. Lần chạy và checksum được lưu tại <code>reports/data_lineage.json</code>.

Tài liệu Vnstock hiện hành mô tả hạn mức theo quyền và ghi nhận nguồn dữ liệu lịch sử có thể khác nhau ở cách điều chỉnh sau sự kiện quyền: [quyền truy cập](https://www.vnstocks.com/docs/vnstock/tham-khao/cap-quyen-va-gioi-han), [nguồn thị trường](https://www.vnstocks.com/docs/vnstock/tham-khao/data-sources). Do đó, metric chỉ tái lập trên snapshot đã lưu và basis được ghi trong báo cáo nguồn gốc.

## 3. Kiểm toán và khám phá dữ liệu

| Chỉ tiêu | Kết quả |
|---|---:|
| Số phiên | 4.919 |
| Từ ngày – đến ngày | 02/01/2007–30/09/2026 |
| Thiếu giá trị theo cột | 0 |
| Ngày trùng | 0 |
| Sắp xếp thời gian | Tăng dần |
| Phiên volume bằng 0 | 2 |
| Hàng vi phạm quan hệ OHLC | 3 |
| Giá thấp nhất – cao nhất | 1,562–119,36875 nghìn VND |
| Close thấp nhất – cao nhất | 1,61525–118,073 nghìn VND |
| Volume thấp nhất – cao nhất | 0–47.840.750 cổ phiếu |

Ba ngày vi phạm OHLC là 17/08/2007, 10/06/2009 và 07/12/2009. Chúng được giữ lại để bảo toàn dữ liệu đã lưu, đồng thời được nêu rõ trong audit. Lợi nhuận đóng cửa ngày trên ngày có trung bình 0,0567%, độ lệch chuẩn 1,9246%, nhỏ nhất −6,9896%, lớn nhất 6,9922%. Với nhãn phiên kế tiếp, có 2.224 phiên tăng, 2.211 phiên giảm và 483 phiên không đổi.

![Giá đóng cửa FPT](../figures/01_fpt_close.png)

![Khối lượng giao dịch FPT](../figures/02_fpt_volume.png)

![Phân phối lợi nhuận ngày](../figures/03_daily_return_distribution.png)

![Cân bằng nhãn phiên kế tiếp](../figures/04_next_session_class_balance.png)

## 4. Tiền xử lý và đặc trưng

Ngày được chuẩn hóa thành <code>YYYY-MM-DD</code>; OHLC chuyển về kiểu số dương và volume về số nguyên không âm. Dữ liệu được sắp xếp tăng dần, không điền giá trị thiếu. Tính nhất quán OHLC được kiểm tra nhưng các hàng lịch sử bất nhất không bị âm thầm sửa.

Hai mươi ba đặc trưng chỉ dựa trên dữ liệu đến thời điểm dự báo:

- Lợi nhuận trễ 1, 2, 5, 10, 20 phiên.
- Tỷ lệ close so với SMA và EMA 5, 10, 20, 50 phiên.
- RSI 14 phiên; MACD, đường tín hiệu MACD và histogram theo close.
- Bollinger %B và độ rộng dải 20 phiên.
- Độ biến động 5 và 20 phiên.
- Thay đổi log-volume và z-score log-volume 20 phiên.

Close phiên kế tiếp và nhãn được tạo bằng dịch chuyển một phiên chỉ để làm target, không nằm trong 23 cột đầu vào. Bốn mươi chín hàng đầu không đủ warm-up cho rolling features nên bị loại; dòng cuối chưa có target phiên sau vẫn được giữ để dự đoán mới nhất. Kiểm thử thay đổi phần dữ liệu tương lai xác nhận các đặc trưng ở thời điểm trước đó không đổi.

## 5. Thiết lập thực nghiệm

Các mẫu được chia theo thứ tự ngày của target, tỷ lệ xấp xỉ 70% train, 15% validation, 15% test. Không shuffle.

| Tập | Ngày target | Hồi quy | Phân loại |
|---|---|---:|---:|
| Train | 21/03/2007–17/11/2020 | 3.408 | 3.006 |
| Validation | 18/11/2020–20/10/2023 | 730 | 676 |
| Test | 23/10/2023–30/09/2026 | 731 | 711 |

Phân loại dùng Majority baseline, Logistic Regression, Random Forest và HistGradientBoosting. Logistic Regression dùng StandardScaler trong pipeline, <code>C=1</code>, cân bằng lớp, tối đa 3.000 vòng lặp. Random Forest dùng 350 cây, độ sâu tối đa 8 và tối thiểu 20 mẫu ở lá. HistGradientBoosting dùng learning rate 0,05, tối đa 160 vòng lặp và 15 lá tối đa. Regression so sánh Last close baseline, Linear Regression, Random Forest và HistGradientBoosting với các thiết lập cây tương ứng.

Scaler chỉ được fit trên train khi đo validation. Sau khi chọn mô hình trên validation, mô hình cuối được fit lại trên train cộng validation rồi đánh giá một lần trên test. Bộ phân loại chọn theo Balanced Accuracy validation, tie-break bằng F1 lớp tăng. Bộ hồi quy chọn theo MAE validation, có bao gồm baseline giữ close phiên hiện tại.

## 6. Kết quả phân loại

F1 dưới đây tính cho lớp tăng. Kết quả làm tròn đến hai chữ số phần trăm.

| Mô hình | Accuracy | Balanced Accuracy | F1 tăng | ROC-AUC | Chọn bằng validation |
|---|---:|---:|---:|---:|---|
| Majority baseline | 49,09% | 50,00% | 65,85% | 50,00% | Không |
| Logistic Regression | 49,65% | 49,73% | 51,36% | 49,41% | Có |
| Random Forest | 51,62% | 51,60% | 50,57% | 55,13% | Không |
| HistGradientBoosting | 52,88% | 52,91% | 53,02% | 52,63% | Không |

Confusion matrix của Logistic Regression trên test, theo hàng là nhãn thật và cột là dự đoán:

| | Dự đoán giảm | Dự đoán tăng |
|---|---:|---:|
| Thực tế giảm | 164 | 198 |
| Thực tế tăng | 160 | 189 |

![Confusion matrix Logistic Regression](../figures/05_test_confusion_matrix.png)

Logistic Regression được chọn vì kết quả validation tốt nhất theo quy tắc đã định trước, nhưng trên test các metric của nó nằm sát mức ngẫu nhiên. HistGradientBoosting có Accuracy và Balanced Accuracy cao nhất; Random Forest có ROC-AUC cao nhất. Không nên chọn lại mô hình theo test sau khi đã xem kết quả, vì như vậy biến test thành dữ liệu chọn mô hình.

## 7. Kết quả hồi quy

Sai số giá tính theo nghìn VND/cổ phiếu. Directional Accuracy chỉ tính trên các phiên mà close thực tế có thay đổi.

| Mô hình | RMSE | MAE | MAPE | Directional Accuracy |
|---|---:|---:|---:|---:|
| Last close baseline | 1,5359 | 1,1141 | 1,3308% | 0,00% |
| Linear Regression | 1,5372 | 1,1183 | 1,3370% | 48,66% |
| HistGradientBoosting | 27,5928 | 22,5710 | 23,9094% | 51,90% |
| Random Forest | 27,7087 | 22,6920 | 24,0408% | 52,74% |

Baseline giữ nguyên close có MAE thấp nhất trên validation và test. Đây là mốc mạnh cho bài toán dự đoán giá phiên kế tiếp, nhưng nó luôn dự đoán không đổi nên Directional Accuracy bằng 0%. Hai mô hình cây có sai số lớn hơn rõ rệt trên giai đoạn test; điều này cho thấy các mô hình phi tuyến hiện tại chưa khái quát tốt mức giá ngoài mẫu.

![Giá thực tế và dự đoán trên test](../figures/06_actual_vs_predicted_close.png)

## 8. Dự đoán sau phiên cuối dữ liệu

Từ phiên 30/09/2026, bộ phân loại Logistic Regression dự đoán hướng tăng với xác suất 55,44% có điều kiện trên hai lớp tăng/giảm. Mô hình hồi quy được chọn là Last close baseline, dự đoán close kế tiếp bằng 63,0 nghìn VND, tức thay đổi 0%. Đây là hai đầu ra từ hai bài toán khác nhau; chúng không tạo thành khuyến nghị giao dịch. Kết quả được lưu trong <code>reports/latest_prediction.json</code>.

## 9. Kết luận, giới hạn và hướng phát triển

Pipeline xử lý chuỗi OHLCV dài, tạo đặc trưng không nhìn trước, chia tập theo thời gian, lưu metric và mô hình, đồng thời kiểm tra trực tiếp khả năng dự báo ngoài mẫu. Kết quả cho thấy các đặc trưng kỹ thuật đơn biến chưa tạo ra phân loại hướng đáng tin cậy trên giai đoạn test gần nhất. Baseline giữ close là mốc hợp lý cho hồi quy giá một phiên, nhưng không dùng được như dự báo hướng.

Giới hạn chính gồm việc nguồn khách chỉ trả cửa sổ 365 ngày; archive cũ phải được căn chỉnh theo hệ số suy ra từ overlap; VCI có thể sửa lại lịch sử; một nguồn mã đơn lẻ không nắm thông tin thị trường chung hay tin tức; không có tìm kiếm siêu tham số rộng. Các bước tiếp theo nên cố định phiên bản snapshot và basis điều chỉnh, thêm dữ liệu thị trường ngoài mẫu OHLCV chỉ khi có timestamp công bố phù hợp, đánh giá walk-forward nhiều cửa sổ và tính thêm chi phí giao dịch trước khi thử chiến lược.
