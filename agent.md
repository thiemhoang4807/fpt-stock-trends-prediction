# Nhật ký thực hiện

## Mục tiêu

Cập nhật pipeline FPT đến 30/09/2026, đối sánh Train/Test, hoàn thiện tài liệu chính thức và giữ riêng cẩm nang học tập.

## Dữ liệu

- OHLCV lấy qua vnstock từ VCI (Vietcap): 4.919 phiên, 02/01/2007–30/09/2026; thiếu 0, ngày trùng 0, volume bằng 0 ở 2 phiên, 3 hàng OHLC bất nhất được giữ và báo cáo.
- Giá theo nghìn VND/cổ phiếu, volume theo cổ phiếu. Archive giá cũ được căn cùng thang dữ liệu VCI mới bằng hệ số trung vị 0,8875; volume không đổi.
- Sáu truy vấn bổ trợ (VN-Index, USD/VND, vàng, CPI, GDP, tài chính FPT) đều lỗi lấy chính sách máy khách, không trả hàng. reports/supplemental_data_audit.json ghi lỗi; C là not_run, không suy đoán metrics.

## Pipeline và kết quả

- A: 23 đặc trưng close/volume. B: thêm bốn đặc trưng nến, tổng 27. A/B dùng cùng ngày đủ dữ liệu.
- Split theo target_date: Train 4.138 hàng, 21/03/2007–20/10/2023; Test 731 hàng, 23/10/2023–30/09/2026. Phân loại loại nhãn đứng giá: Train 3.682, Test 711.
- Phân loại tốt nhất A: HistGradientBoosting, Accuracy 52,88%, Balanced Accuracy 52,91%, F1 tăng 53,02%, ROC-AUC 52,63%.
- Phân loại tốt nhất B: Random Forest, Accuracy 54,01%, Balanced Accuracy 54,00%, F1 tăng 53,35%, ROC-AUC 55,91%. Confusion matrix hàng thật Giảm/Tăng, cột dự đoán Giảm/Tăng: [[197,165],[162,187]].
- Hồi quy tốt nhất A/B: Last-Close Baseline, MAE 1,1141 nghìn VND, RMSE 1,5359 nghìn, MAPE 1,3308%, Directional Accuracy 0%; tolerance ±0,5/±1/±2%: 26,68/50,21/78,93%.
- Dự báo as-of 30/09/2026: Random Forest B dự đoán Tăng, xác suất 57,50%; Last-Close dự đoán 63,0 nghìn VND.
- Chọn model bằng Test theo yêu cầu hiện tại; điều này có thể làm metric chọn lọc lạc quan. Mô hình triển khai được fit lại trên toàn bộ nhãn đến 30/09/2026 sau khi ghi metrics.

## Tệp và kiểm thử

- Cập nhật src/features.py, prepare.py, train.py, predict.py; thêm src/fetch_supplemental.py và test liên quan.
- Cập nhật README.md, data/README.md, docs/PROPOSAL.md, docs/REPORT.md và figures/00_pipeline_overview.png.
- Cẩm nang docs/CAM_NANG_HIEU_DU_AN.md đã viết lại cho người mới, được .gitignore loại trừ và không có trong Git index.
- Bảng điểm Validation cũ đã xóa để phản ánh giao thức Train/Test.
- Snapshot verify, EDA, prepare, train và predict chạy thành công. python -m pytest -q: 23 passed. Test Windows dùng thư mục tạm trong workspace để tránh lỗi quyền khi dọn Temp của sandbox.

## Hoàn tất trước khi push

- [x] Quét các từ khóa nguồn bị cấm trong tài liệu/code/kết quả.
- [x] Kiểm tra .gitignore, diff và trạng thái cẩm nang riêng.
- [x] Commit 60cf902 và push lên origin/main thành công.
