# Dự đoán xu hướng cổ phiếu FPT

Dự án nghiên cứu khả năng dự báo hướng biến động giá đóng cửa FPT ở phiên giao dịch kế tiếp bằng các đặc trưng kỹ thuật tính từ OHLCV quá khứ. Bài toán hồi quy giá đóng cửa được dùng như phần đánh giá bổ trợ. Đây là đồ án học tập, không phải công cụ tư vấn đầu tư.

## Dữ liệu

Tập dữ liệu hiện tại có 4.919 phiên, từ 02/01/2007 đến 30/09/2026, gồm <code>time, open, high, low, close, volume</code>. Nguồn thị trường là VCI (Vietcap), truy cập bằng thư viện Python <code>vnstock</code> phiên bản 5.1.0. Giá trong tệp giữ nguyên thang VCI và được biểu diễn bằng nghìn đồng/cổ phiếu; volume là số cổ phiếu.

API ở quyền khách hiện giới hạn lịch sử nến ngày ở 365 ngày. Vì vậy, lệnh thu thập giữ archive lịch sử đã được quản lý trong dự án, tải cửa sổ mới từ VCI, kiểm tra phần ngày trùng và căn chỉnh OHLC cũ về cùng basis giá. Lần tái lập này dùng 8 phiên trùng để tính hệ số 0,8875; độ phân tán giữa các tỷ lệ OHLC dưới 0,011%. Volume không bị nhân hệ số. Chi tiết được lưu trong <code>reports/data_lineage.json</code>. Giới hạn và điều chỉnh lịch sử của VCI được mô tả trong [tài liệu Vnstock về quyền truy cập](https://www.vnstocks.com/docs/vnstock/tham-khao/cap-quyen-va-gioi-han) và [nguồn dữ liệu thị trường](https://www.vnstocks.com/docs/vnstock/tham-khao/data-sources).

Kiểm toán dữ liệu ghi nhận: không có ô thiếu hoặc ngày trùng; 2 phiên volume bằng 0; 3 phiên có quan hệ OHLC không nhất quán được giữ nguyên và đánh dấu. Lợi nhuận ngày có trung bình 0,0567%, độ lệch chuẩn 1,9246%, nhỏ nhất −6,9896%, lớn nhất 6,9922%. Nhãn phiên kế tiếp gồm 2.224 tăng, 2.211 giảm và 483 không đổi.

## Kết quả kiểm tra trên tập test

Tập test theo thời gian bao phủ 23/10/2023–30/09/2026. Bộ phân loại được chọn bằng validation là Logistic Regression. Các metric dưới đây đều tính trên test; F1 là F1 của lớp tăng.

| Bộ phân loại | Accuracy | Balanced Accuracy | F1 tăng | ROC-AUC |
|---|---:|---:|---:|---:|
| Majority baseline | 49,09% | 50,00% | 65,85% | 50,00% |
| Logistic Regression | 49,65% | 49,73% | 51,36% | 49,41% |
| Random Forest | 51,62% | 51,60% | 50,57% | 55,13% |
| HistGradientBoosting | 52,88% | 52,91% | 53,02% | 52,63% |

Mô hình phân loại được chọn không vượt baseline một cách thuyết phục trên test; kết quả hiện tại không cho thấy khả năng dự báo hướng ổn định. Với hồi quy, baseline giữ giá đóng cửa bằng phiên hiện tại đạt MAE 1,114 nghìn đồng, RMSE 1,536 nghìn đồng, MAPE 1,331%; do dự đoán không đổi nên directional accuracy bằng 0%. Bảng đầy đủ nằm tại <code>reports/classification_test_metrics.csv</code> và <code>reports/regression_test_metrics.csv</code>.

## Chạy dự án

Tạo môi trường Python, cài thư viện và chạy lần lượt:

    python -m pip install -r requirements.txt
    python src/fetch_data.py
    python src/fetch_data.py --verify
    python src/eda.py
    python src/prepare.py
    python src/train.py
    python src/predict.py
    python -m pytest -q

Để tải khoảng ngày khác, dùng <code>python src/fetch_data.py --download --start YYYY-MM-DD --end YYYY-MM-DD</code>. Nếu API chỉ trả cửa sổ gần đây, script cần archive cũ có sẵn và phần ngày trùng đủ để xác nhận basis. Nếu bắt đầu từ archive mới hoặc thiếu overlap, script dừng mà không thay dữ liệu hiện hữu. Có thể chuẩn hóa CSV đã xuất bằng <code>python src/fetch_data.py --input FILE.csv --output normalized.csv</code>.

## Pipeline

    VCI → vnstock → src/fetch_data.py → data/raw/fpt/fpt_historical_price.csv
       → src/eda.py → reports/data_audit.json và figures/
       → src/prepare.py → data/processed/fpt_next_session_features.csv
       → src/train.py → models/, reports/, figures/
       → src/predict.py → reports/latest_prediction.json

Các đặc trưng gồm 23 biến trễ và chỉ báo kỹ thuật. Tập train, validation, test được tách theo thời gian. Scaler nằm bên trong pipeline học máy và chỉ fit trên train trước khi mô hình cuối được fit trên train cộng validation.

## Cấu trúc chính

- <code>src/fetch_data.py</code>: tải, chuẩn hóa, nối archive và kiểm định OHLCV.
- <code>src/eda.py</code>: kiểm toán dữ liệu và tạo biểu đồ khám phá.
- <code>src/features.py</code>, <code>src/prepare.py</code>: tạo đặc trưng quá khứ và nhãn phiên kế tiếp.
- <code>src/train.py</code>: huấn luyện, chọn mô hình bằng validation và đánh giá test.
- <code>src/predict.py</code>: dự đoán phiên kế tiếp sau phiên cuối dữ liệu.
- <code>data/raw/</code>, <code>data/processed/</code>: dữ liệu nguồn và bảng đặc trưng.
- <code>models/</code>: bộ phân loại và hồi quy được chọn.
- <code>reports/</code>: audit, nguồn gốc dữ liệu, ranh giới split, metric, dự đoán.
- <code>figures/</code>: biểu đồ EDA, confusion matrix và dự đoán giá.
- <code>tests/</code>: kiểm thử chuẩn hóa, căn chỉnh nguồn, đặc trưng và tách tập thời gian.

## Hình minh họa

![Giá đóng cửa FPT](figures/01_fpt_close.png)

![Phân phối lợi nhuận ngày](figures/03_daily_return_distribution.png)

![Confusion matrix trên test](figures/05_test_confusion_matrix.png)
