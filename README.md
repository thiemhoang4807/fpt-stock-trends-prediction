# Dự đoán xu hướng cổ phiếu FPT

Dự án học thuật áp dụng Machine Learning để phân loại cổ phiếu FPT tăng hay giảm ở phiên giao dịch kế tiếp. Thí nghiệm phụ dự báo giá đóng cửa phiên sau để đối chiếu với baseline “giá ngày mai bằng giá hôm nay”. Dữ liệu nguồn kết thúc ngày 09-10-2025.

## Câu hỏi nghiên cứu

Với dữ liệu giá đóng cửa và khối lượng giao dịch lịch sử của FPT, các mô hình Logistic Regression, Random Forest và HistGradientBoosting có phân loại hướng biến động phiên kế tiếp tốt hơn baseline hay không?

Thời điểm dự báo là sau khi phiên giao dịch ngày `t` đóng cửa. Mô hình dùng dữ liệu quan sát đến hết ngày `t` để dự đoán lợi nhuận đóng cửa từ `t` sang phiên giao dịch kế tiếp. Nhãn phân loại là `up` nếu giá đóng cửa tăng, `down` nếu giảm; các phiên không đổi được loại khỏi thí nghiệm phân loại và vẫn được giữ trong thí nghiệm hồi quy giá.

## Kết quả thực nghiệm

Chia dữ liệu theo thời gian: train đến 2020-03-19, validation từ 2020-03-20 đến 2022-12-22, test từ 2022-12-23 đến 2025-10-09. Mô hình phân loại được chọn dựa trên Balanced Accuracy của validation; test chỉ dùng cho đánh giá cuối.

| Mô hình phân loại | Accuracy | Balanced Accuracy | F1 (tăng) | ROC-AUC |
|---|---:|---:|---:|---:|
| Majority baseline | 52.42% | 50.00% | 0.688 | 0.500 |
| Logistic Regression | 52.73% | 52.29% | 0.576 | 0.537 |
| Random Forest — chọn theo validation | 53.18% | 52.70% | 0.584 | 0.559 |
| HistGradientBoosting | 55.45% | 55.28% | 0.581 | 0.565 |

Random Forest được chọn trên validation theo quy tắc đã đặt trước. HistGradientBoosting có Balanced Accuracy test cao nhất trong lần chạy này; không dùng test để thay đổi lựa chọn mô hình. Kết quả cho thấy mức cải thiện còn khiêm tốn và cần được kiểm tra trên nhiều giai đoạn khác.

Thí nghiệm hồi quy chọn baseline giữ nguyên giá gần nhất theo validation: test RMSE **1.5010**, MAE **1.0052**, MAPE **1.10%** theo đơn vị giá của tệp nguồn. Baseline này có Directional Accuracy **0%** vì dự đoán giá không đổi; Linear Regression đạt Directional Accuracy **51.82%** nhưng MAE nhỉnh hơn một chút. Vì vậy, điểm số sai số giá thấp không đồng nghĩa với khả năng dự đoán hướng tốt.

## Cấu trúc thư mục

```text
├── data/
│   ├── raw/fpt/fpt_historical_price.csv  # OHLCV nguồn
│   ├── processed/                       # Đặc trưng sinh tự động
│   └── README.md                        # Xuất xứ và mô tả dữ liệu
├── docs/
│   ├── PROPOSAL.md                       # Đề xuất gửi giảng viên
│   └── REPORT.md                         # Báo cáo theo kết quả chạy thật
├── figures/                              # EDA và đánh giá
├── models/                               # Mô hình đã huấn luyện
├── reports/                              # Audit, metrics, dự đoán và split
├── src/
│   ├── fetch_data.py                     # Tải, chuẩn hóa và xác minh OHLCV
│   ├── features.py                       # Đọc dữ liệu và tạo đặc trưng
│   ├── eda.py                            # Kiểm tra dữ liệu và biểu đồ
│   ├── prepare.py                        # Tạo bảng đặc trưng
│   ├── train.py                          # Chia thời gian, huấn luyện, đánh giá
│   └── predict.py                        # Dự đoán phiên kế tiếp
├── tests/                                # Kiểm thử căn chỉnh nhãn và leakage
├── agent.md                              # Nhật ký tiến độ và kết quả
└── requirements.txt
```

## Cài đặt và chạy

Khuyến nghị Python 3.10 trở lên. Trong thư mục gốc repo:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src/fetch_data.py --verify
python src/eda.py
python src/prepare.py
python src/train.py
python src/predict.py
python -m pytest -q
```

`train.py` tự tạo lại đặc trưng trước khi huấn luyện. Lệnh `prepare.py` có thể chạy riêng để xem và lưu bảng đặc trưng tại `data/processed/fpt_next_session_features.csv`. `predict.py` sử dụng các artifact trong `models/` và dòng mới nhất trong CSV; ví dụ dự đoán hiện tại được ghi tại `reports/latest_prediction.json`.

Để tải dữ liệu qua API VCI như notebook nguồn, cài thêm `vnstock` bằng `python -m pip install -U --extra-index-url https://vnstocks.com/api/simple vnstock vnai`, rồi chạy `python src/fetch_data.py --download --start 2007-01-01 --end YYYY-MM-DD --output data/raw/fpt/fpt_historical_price.csv`. Nếu dùng CSV xuất từ API/widget, chuẩn hóa bằng `python src/fetch_data.py --input export.csv --output data/raw/fpt/fpt_historical_price.csv`. Mỗi lệnh tải/chuẩn hóa ghi đè tệp đích đã chỉ định; chạy lại `--verify` trước khi dùng snapshot để tái tạo kết quả.

Các biểu đồ được lưu dưới `figures/`; kết quả số nằm ở `reports/`. Pipeline không xáo trộn thứ tự thời gian, không dùng `bfill`, và đặt `StandardScaler` bên trong pipeline để chỉ fit trên dữ liệu huấn luyện.

## Đặc trưng và mô hình

23 đặc trưng phân loại được tạo từ lợi nhuận trễ 1/2/5/10/20 phiên, SMA/EMA 5/10/20/50, RSI-14, MACD, Bollinger Bands 20 phiên, biến động 5/20 phiên và thay đổi/độ lệch chuẩn hóa của log-volume. Bài toán hồi quy thêm giá đóng cửa hiện tại làm đầu vào. Tất cả đều chỉ dùng giá trị biết được vào cuối phiên `t`.

Mô hình phân loại gồm Majority baseline, Logistic Regression, Random Forest và HistGradientBoosting. Mô hình hồi quy gồm Last close baseline, Linear Regression, Random Forest và HistGradientBoosting. Deep learning không được dùng vì dữ liệu chỉ có một mã cổ phiếu và khoảng 4.600 quan sát hữu dụng; mô hình chuỗi sâu sẽ tăng độ phức tạp và nguy cơ overfit mà chưa có căn cứ về lợi ích.

## Dữ liệu

Dữ liệu OHLCV có nguồn API được notebook của [repo DS111 UIT](https://github.com/nguyenlog205/ds111-uit-stock-price-analysis/blob/main/notebook/data_ingestion/API_use.ipynb) ghi rõ: thư viện `vnstock`, lớp `Quote`, nguồn `VCI` (Vietcap). Snapshot có 4.678 phiên từ 2007-01-02 đến 2025-10-09. `src/fetch_data.py --verify` kiểm tra hash snapshot; tải lại từ API có thể khác do nhà cung cấp cập nhật chuỗi lịch sử. Đơn vị giá được diễn giải là nghìn đồng theo thang giá VCI nhưng metadata không xác nhận rõ; trạng thái adjusted/unadjusted cũng không được lưu, nên báo cáo ghi nhận giới hạn này. Xem [data/README.md](data/README.md) để biết kết quả kiểm toán toàn bộ luồng dữ liệu và hướng dẫn tái tải.

## Kiểm thử

`python -m pytest -q` kiểm tra căn chỉnh nhãn với phiên kế tiếp, xác nhận các đặc trưng quá khứ không đổi khi sửa dữ liệu tương lai, và xác nhận thứ tự thời gian của các tập. Kết quả thực nghiệm đầy đủ, ma trận nhầm lẫn và giới hạn của dữ liệu được trình bày trong [báo cáo](docs/REPORT.md).
