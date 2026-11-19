# Notebook thực nghiệm FPT

Các notebook gọi module trong `src/`, có ô giải thích tiếng Việt và ô code riêng. Chạy từ trên xuống; 00 là luồng toàn bộ, không cần chạy thêm 01–09 nếu chỉ muốn tái lập một lần.

Nếu mới bắt đầu, đọc [cẩm nang dùng chung](../docs/CAM_NANG_HIEU_DU_AN.md), rồi mở notebook 01–05 để theo đường đi của dữ liệu. [Sổ tay nguồn dữ liệu](../data/README.md) giải thích nguồn, cách lấy, đơn vị, ngày hiệu lực và độ phủ từng biến. [EDA và đặc trưng](../docs/EDA_VA_DAC_TRUNG.md) giải thích ý nghĩa biểu đồ, công thức và ví dụ tính từng bước.

| Notebook | Nội dung |
|---|---|
| 00_RUN_ALL | Chạy dữ liệu → phân tích → ba thí nghiệm → giải thích → dự báo → tests |
| 01_fetch_data | Xác minh snapshot OHLCV; hướng dẫn tải mới khi chủ động cần |
| 02_fetch_supplemental | Nguồn bổ trợ, ý nghĩa, độ phủ, ví dụ ngày công bố và ghép lùi |
| 03_eda | Kiểm toán, cách đọc biểu đồ giá/volume/return và quyết định xử lý |
| 04_features | Công thức, mục đích của 32 biến và log return → giá/hướng |
| 05_prepare | Từ 4.671 hàng lưu đến 3.031 nhãn chung, 85/15 và 5 fold có gap |
| 06_train | Năm phương pháp, XGBoost 32/38/42 và GRU 20/60 |
| 07_predict | Một mô hình học lại sinh dự báo mới nhất |
| 08_time_series_analysis | ADF/KPSS, ACF/PACF; STL bổ trợ |
| 09_explain | Permutation, ba ca lỗi; SHAP bổ trợ |

Cài `python -m pip install -r requirements.txt` trên máy cá nhân trước. Trên Colab, ô chuẩn bị có thể clone repository và cài thư viện. Mặc định dùng snapshot offline để giữ kết quả. Notebook 06 và 00 ghi lại artefact huấn luyện nên cần chạy xong trước khi dùng 07/09. Các notebook được kiểm tra bằng kernel mới; phiên bản nộp giữ ô code sạch để thuận tiện chạy lại.

Sau khi tải một nguồn mới, dùng [hướng dẫn kiểm tra và bổ sung dữ liệu](../docs/HUONG_DAN_KIEM_TRA_VA_BO_SUNG_DU_LIEU.md). Notebook 02 có ô rà lịch ngày/kỳ bị thiếu; script `audit_data_quality.py` tạo báo cáo riêng, không sửa nguồn.
