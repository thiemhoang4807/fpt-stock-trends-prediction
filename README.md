# Dự đoán xu hướng và giá đóng cửa FPT phiên kế tiếp

Dự án xây dựng pipeline học máy để dự báo (1) close phiên FPT kế tiếp tăng hay giảm so với phiên hiện tại và (2) mức close phiên kế tiếp. Đây là hai đầu ra khác nhau; kết quả dùng cho đồ án học thuật, không phải khuyến nghị đầu tư.

## Dữ liệu

Snapshot giá có 4.919 phiên từ 02/01/2007 đến 30/09/2026, gồm `time, open, high, low, close, volume`. Nguồn OHLCV là VCI (Vietcap) qua `vnstock`; giá theo nghìn VND/cổ phiếu, volume theo cổ phiếu. Kiểm toán ghi nhận 0 giá trị thiếu, 0 ngày trùng, 2 phiên volume bằng 0 và 3 dòng OHLC bất nhất được giữ để truy vết. Xem [data/README.md](data/README.md), `reports/data_audit.json` và `reports/data_lineage.json`.

Thử nghiệm đặc trưng:

- **A — Core Technical:** 23 biến tính từ close và volume.
- **B — Full OHLCV:** A cộng bốn biến nến (biên độ, thân nến, khoảng trống giá mở cửa, vị trí close).
- **C — Multi-source:** B cộng VN-Index, USD/VND, vàng, CPI, GDP và báo cáo quý FPT sau khi căn đúng ngày có thể biết.

Lần chạy hiện tại thực hiện A và B trên cùng các phiên Train/Test. Việc tải các nguồn bổ trợ qua Vnstock đã được thử nhưng truy vấn đều không lấy được chính sách máy khách; bộ C hiện được ghi rõ là `not_run`, không có kết quả giả định. Tài liệu Vnstock cho biết Market có các tuyến dữ liệu VN-Index, forex và hàng hóa; Fundamental có giới hạn số kỳ theo quyền; Macro cho GDP/CPI/tỷ giá nội địa yêu cầu quyền mở rộng. [Market](https://vnstocks.com/docs/vnstock/thi-truong-market), [Fundamental](https://vnstocks.com/docs/vnstock/co-ban-fundamental), [Macro](https://vnstocks.com/docs/vnstock/vi-mo-macro).

## Thiết lập

Dữ liệu có đặc trưng đầy đủ được chia theo thứ tự ngày mục tiêu: 85% đầu làm Train và 15% cuối làm Test. Train kết thúc ngày 20/10/2023; Test từ 23/10/2023 đến 30/09/2026. Classification bỏ nhãn đứng giá; regression giữ tất cả phiên. `StandardScaler` nằm trong Pipeline và chỉ được fit trên Train khi tính metric Test.

Các bảng metric Test được dùng để chọn mô hình theo yêu cầu so sánh hiện tại. Do đó, kết quả của mô hình được chọn có thể lạc quan hơn một đánh giá độc lập; báo cáo giữ nguyên giới hạn này. Sau khi đã ghi metric, mô hình được chọn được fit lại trên toàn bộ nhãn có sẵn để tạo dự báo phiên mới nhất.

## Kết quả hiện tại

Bảng dưới ghi mô hình tốt nhất trong mỗi bộ đặc trưng theo quy tắc lựa chọn đã định.

| Bộ | Mô hình phân loại | Accuracy | Balanced Accuracy | F1 (Tăng) | ROC-AUC |
|---|---|---:|---:|---:|---:|
| A | HistGradientBoosting | 52,88% | 52,91% | 53,02% | 52,63% |
| B | Random Forest | 54,01% | 54,00% | 53,35% | 55,91% |

Bộ B tăng Balanced Accuracy 1,09 điểm phần trăm so với kết quả tốt nhất của A. Hiệu quả vẫn ở gần mức ngẫu nhiên, nên chưa thể kết luận mô hình dự báo hướng ổn định.

Last-Close Baseline là mô hình hồi quy được chọn: MAE 1,114 nghìn VND, RMSE 1,536 nghìn VND, MAPE 1,331%, Directional Accuracy 0%. Tolerance Accuracy lần lượt là 26,68% trong ±0,5%, 50,21% trong ±1% và 78,93% trong ±2% giá thực tế. Mô hình giữ nguyên close nên sai số giá thấp nhưng không thể đoán chiều tăng/giảm.

Dự báo cuối snapshot (30/09/2026): Random Forest bộ B dự báo **Tăng** với xác suất 57,50%; Last-Close Baseline dự báo close 63,0 nghìn VND. Đây là output minh họa, không phải tư vấn mua/bán. Bảng đầy đủ nằm tại `reports/classification_test_metrics.csv`, `reports/regression_test_metrics.csv`, `reports/ablation_summary.csv`.

## Chạy dự án

```bash
python -m pip install -r requirements.txt
python src/fetch_data.py --verify
python src/eda.py
python src/prepare.py
python src/train.py
python src/predict.py
python -m pytest -q
```

Để tải các nguồn bổ trợ và tạo dữ liệu C (cần API truy cập được và quyền phù hợp):

```bash
python src/fetch_supplemental.py --start 2007-01-01 --end 2026-09-30
python src/train.py
```

Nếu API không truy cập được, có thể đặt các CSV đã xuất vào `data/raw/supplemental/` theo tên và cấu trúc trong [data/README.md](data/README.md), rồi chạy:

```bash
python src/fetch_supplemental.py --from-cache
python src/train.py
```

Tập bổ trợ được căn theo thời điểm hiệu lực: CPI +10 ngày, GDP và báo cáo quý +45 ngày, chuỗi FX/vàng +1 ngày, VN-Index dùng sau khi phiên đóng cửa. Không có `backfill`.

## Cách hiểu metric giá

Tolerance Accuracy tính tỷ lệ dự đoán mà sai số tương đối so với close thật không quá 0,5%, 1% hoặc 2%. Ở giá close 63.000 đồng, các ngưỡng tương đương ±315, ±630 và ±1.260 đồng. HOSE có biên độ thông thường ±7% so với tham chiếu, nhưng đây là giới hạn giao dịch và không phải tiêu chuẩn chất lượng của dự đoán. [Tài liệu HOSE](https://staticfile.hsx.vn/Uploads/UploadDocuments/2372201/4.Bien%20do%20dao%20dong%20gia.pdf).

## Cấu trúc chính

```text
src/
  fetch_data.py             Tải/chuẩn hóa/kiểm tra OHLCV FPT
  fetch_supplemental.py      Tải cache và căn thời điểm dữ liệu bổ trợ
  eda.py                    Kiểm toán OHLCV và tạo biểu đồ
  features.py                Tạo đặc trưng A/B và nhãn phiên kế tiếp
  prepare.py                Xuất bảng đặc trưng
  train.py                  Huấn luyện A/B/C, chấm Test, lưu mô hình
  predict.py                Tạo dự báo phiên kế tiếp
data/
  raw/fpt/                   Snapshot OHLCV FPT
  raw/supplemental/           Cache nguồn bổ trợ (cục bộ)
  processed/                  Bảng đặc trưng
docs/
  PROPOSAL.md                 Đề xuất theo cấu trúc UIT
  REPORT.md                   Báo cáo kết quả thực nghiệm
  CAM_NANG_HIEU_DU_AN.md       Cẩm nang học tập cá nhân, bị Git bỏ qua
reports/                      Audit, metrics, dự báo và ranh giới split
figures/                      Biểu đồ EDA, pipeline và đánh giá
models/                       Mô hình được chọn để dự báo mới nhất
tests/                        Kiểm thử đặc trưng, split, căn chỉnh và metric
```
