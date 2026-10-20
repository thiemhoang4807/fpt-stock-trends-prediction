# Nhật ký thực hiện

## Mục tiêu hiện tại

Cập nhật dữ liệu FPT đến phiên cuối tháng 09/2026, chạy lại pipeline học máy, cập nhật tài liệu tiếng Việt, kiểm tra không còn từ khóa nguồn tham khảo bị cấm và đồng bộ thay đổi lên nhánh main.

## Phát hiện về nguồn dữ liệu

- API lịch sử OHLCV được truy cập từ VCI (Vietcap) bằng vnstock phiên bản 5.1.0, lớp Quote.history, source=VCI.
- API ở quyền khách trả tối đa 365 ngày. Lượt tải toàn giai đoạn đầu chỉ có 249 phiên; lượt đó không được giữ làm dataset.
- Snapshot đã quản lý trong dự án được khôi phục sau lượt tải bị giới hạn. Dữ liệu VCI mới có 249 phiên từ 30/09/2025 đến 30/09/2026, gồm 8 phiên overlap với snapshot.
- Tỷ số OHLC của 8 phiên overlap có trung vị 0,8875 và độ trải tương đối 0,0105%. Script nhân OHLC của archive cũ trước cửa sổ mới với 0,8875, dùng dữ liệu VCI mới cho các ngày overlap và giữ nguyên volume.
- Tệp hoàn chỉnh hiện có 4.919 hàng, từ 02/01/2007 đến 30/09/2026. SHA-256 chuẩn hóa LF: 7b9f9bbefb2a50280d4761e3cfa73f995c607cf825f2d4b7013cd9204182e2cb.
- Hạn mức API và cách căn chỉnh archive được ghi trong reports/data_lineage.json, data/README.md, README, proposal và report. Việc tái lập 2007–2026 dựa vào archive đã quản lý trong dự án; đây không phải một truy vấn VCI đơn lẻ tải lại toàn bộ lịch sử.

## Kiểm toán dữ liệu

- Thiếu giá trị: 0; ngày trùng: 0; sắp theo ngày tăng dần.
- Volume bằng 0: 2 phiên; hàng OHLC bất nhất: 3 phiên (2007-08-17, 2009-06-10, 2009-12-07), được giữ nguyên và báo cáo.
- Min/max giá: 1,562 / 119,36875 nghìn VND; min/max close: 1,61525 / 118,073 nghìn VND.
- Lợi nhuận ngày: trung bình 0,0567%, độ lệch chuẩn 1,9246%, min −6,9896%, max 6,9922%.
- Nhãn phiên kế tiếp: tăng 2.224, giảm 2.211, không đổi 483.

## Pipeline và kết quả chạy

- src/fetch_data.py: tải VCI, kiểm tra phạm vi, căn chỉnh overlap, xuất lineage và hỗ trợ verify.
- src/eda.py: tạo 4 biểu đồ EDA và reports/data_audit.json.
- src/prepare.py: tạo 4.870 hàng feature, 4.869 nhãn phiên kế tiếp, 23 đặc trưng.
- src/train.py: split train 21/03/2007–17/11/2020, validation 18/11/2020–20/10/2023, test 23/10/2023–30/09/2026. Số hàng hồi quy 3.408/730/731; phân loại 3.006/676/711.
- Bộ phân loại được chọn trên validation: Logistic Regression. Trên test: Accuracy 49,65%, Balanced Accuracy 49,73%, F1 tăng 51,36%, ROC-AUC 49,41%. HistGradientBoosting có Accuracy 52,88%; Random Forest có ROC-AUC 55,13%.
- Hồi quy được chọn: Last close baseline. Test RMSE 1,5359 nghìn VND, MAE 1,1141 nghìn VND, MAPE 1,3308%, Directional Accuracy 0%.
- src/predict.py: từ phiên 30/09/2026, Logistic Regression dự đoán tăng với xác suất 55,44%; baseline hồi quy dự đoán close 63,0 nghìn VND.

## Trạng thái công việc

- [x] Thay cách tải mặc định để lệnh python src/fetch_data.py chạy trực tiếp.
- [x] Tải và nối dữ liệu mới, bảo vệ tệp cũ nếu API/overlap không hợp lệ.
- [x] Cập nhật audit, chuẩn bị feature, huấn luyện và dự đoán.
- [x] Viết lại tài liệu dữ liệu, proposal, report và README.
- [x] Cập nhật test cho verify, nối overlap, mặc định tải và kiểm tra không leakage.
- [x] Chạy end-to-end lần cuối; 16 unit tests pass; snapshot verify pass; quét các từ khóa bị cấm trên .md, .py, .json không còn kết quả; requirements đã pin vnstock 5.1.0.
- [ ] Đẩy lên GitHub đang chờ xác nhận quyền công khai dữ liệu: điều khoản Vietcap hiện hành hạn chế sao chép, phân phối và xuất bản nội dung/dữ liệu website nếu không được cho phép.
