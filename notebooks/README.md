# Notebook thực nghiệm FPT

Mở [00_RUN_ALL](00_RUN_ALL.ipynb) và chạy từ trên xuống để tái lập thí nghiệm. Để học từng bước, mở các notebook 01–09 theo bảng bên dưới. Mỗi notebook có phần giải thích tiếng Việt và gọi hàm từ `src/`. [Cẩm nang dự án](../docs/CAM_NANG_HIEU_DU_AN.md)

## Bắt đầu

Trên máy cá nhân, cài môi trường từ thư mục gốc và mở JupyterLab.

```bash
python -m pip install -r requirements-notebooks.txt
python -m jupyter lab
```

Trên Colab, ô chuẩn bị sẽ lấy mã dự án nếu cần và cài thư viện. Các lệnh mặc định dùng bộ dữ liệu đã lưu. Notebook 00 và 06 ghi lại tệp mô hình và báo cáo. Nếu chỉ đọc kết quả, mở các liên kết trong bảng. Để dự báo hay giải thích sau khi đổi dữ liệu, chạy xong notebook 06 rồi mở notebook 07 hoặc 09.

## Chọn notebook theo phần muốn xem

| Notebook | Làm gì? | Kết quả để đối chiếu |
|---|---|---|
| [01 — Giá FPT](01_fetch_data.ipynb) | Xác minh bản giá OHLCV từ 2007 đến 30/09/2025 | [CSV giá](../data/raw/fpt/fpt_historical_price.csv) |
| [02 — Dữ liệu bổ trợ](02_fetch_supplemental.ipynb) | Căn ngày hiệu lực và kiểm tra độ phủ của dữ liệu thị trường, vĩ mô và tài chính FPT | [Kiểm toán dữ liệu](../reports/data_quality_review.json) |
| [03 — EDA](03_eda.ipynb) | Kiểm tra nến giá, xem giá, khối lượng và lợi nhuận | [Kiểm toán giá FPT](../reports/data_audit.json) |
| [04 — Đặc trưng và mục tiêu](04_features.ipynb) | Tạo 32 biến từ giá/khối lượng, tính log return và quy đổi về giá/hướng | [Công thức và ví dụ](../docs/EDA_VA_DAC_TRUNG.md) |
| [05 — Chia thời gian](05_prepare.ipynb) | Tạo tập chung 3.031 nhãn, chia 2.576 Train và 455 Test, xem 5 lượt kiểm định trong Train | [Ranh giới và số hàng](../reports/training_summary.json) |
| [06 — Huấn luyện](06_train.ipynb) | So sánh 5 phương pháp chính, ba bộ biến XGBoost và hai cửa sổ GRU | [Bảng chính](../reports/main_benchmark.csv) · [Toàn bộ điểm Test](../reports/all_test_metrics.csv) |
| [07 — Dự báo](07_predict.ipynb) | Dùng ARIMA đã học lại để dự báo sau phiên 30/09/2025 | [Dự báo đã lưu](../reports/latest_prediction.json) |
| [08 — Chuỗi thời gian](08_time_series_analysis.ipynb) | Đọc ADF, KPSS, ACF/PACF và hình phân rã STL | [Kết quả kiểm định](../reports/stationarity_tests.csv) · [Hình ACF/PACF](../figures/12_acf_pacf.png) |
| [09 — Giải thích](09_explain.ipynb) | Tráo từng biến để đo ảnh hưởng lên sai số, đọc ca lỗi và phần SHAP bổ trợ | [Mức độ quan trọng](../figures/permutation_importance.png) · [Ca lỗi](../reports/error_cases.csv) |

Sau khi lấy dữ liệu mới, kiểm tra đơn vị, đối chiếu lịch ngày/kỳ và ghi rõ thời điểm khả dụng trước khi cập nhật tệp nghiên cứu. [Hướng dẫn kiểm tra và bổ sung dữ liệu](../docs/HUONG_DAN_KIEM_TRA_VA_BO_SUNG_DU_LIEU.md)
