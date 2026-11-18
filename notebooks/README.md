# Notebook thực nghiệm FPT

Các notebook gọi module trong `src/`, có ô giải thích tiếng Việt và ô code riêng. Chạy từ trên xuống; 00 là luồng toàn bộ, không cần chạy thêm 01–09 nếu chỉ muốn tái lập một lần.

| Notebook | Nội dung |
|---|---|
| 00_RUN_ALL | Chạy dữ liệu → phân tích → ba thí nghiệm → giải thích → dự báo → tests |
| 01_fetch_data | Xác minh snapshot OHLCV; hướng dẫn tải mới khi chủ động cần |
| 02_fetch_supplemental | Chuẩn hóa nguồn đã lưu và căn thời điểm |
| 03_eda | Kiểm toán, biểu đồ giá/volume/return |
| 04_features | 32 biến và công thức log return → giá/hướng |
| 05_prepare | Cohort chung, 85/15 và 5 fold có gap |
| 06_train | Năm phương pháp; XGBoost 32/38/43; GRU 20/60 |
| 07_predict | Một mô hình học lại sinh dự báo mới nhất |
| 08_time_series_analysis | ADF/KPSS, ACF/PACF; STL bổ trợ |
| 09_explain | Permutation, ba ca lỗi; SHAP bổ trợ |

Cài `python -m pip install -r requirements.txt` trên máy cá nhân trước. Trên Colab, ô chuẩn bị có thể clone repository và cài thư viện. Mặc định dùng snapshot offline để giữ kết quả. Notebook 06 và 00 ghi lại artefact huấn luyện nên cần chạy xong trước khi dùng 07/09. Các notebook được kiểm tra bằng kernel mới; phiên bản nộp giữ ô code sạch để thuận tiện chạy lại.
