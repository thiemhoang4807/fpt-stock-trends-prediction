# Dự báo biến động cổ phiếu FPT ở phiên kế tiếp bằng học máy và mô hình chuỗi thời gian

Đồ án môn CS114 — nhóm Lê Vũ Thiêm Hoàng (25520584), Nguyễn Tấn Dũng (25520367), Lưu Hoàng Minh Duy (25520424).

- **Một mục tiêu, hai đầu ra:** chỉ học log return; giá và hướng đều suy ra từ cùng dự báo. Không còn mô hình phân loại riêng.
- **Lựa chọn bằng Train CV:** ARIMA có CV RMSE thấp nhất trong năm đại diện (0.017192); Test MAE giá 1.2392. Baseline đạt MAE 1.2250, nên mô hình được CV chọn chưa vượt baseline về MAE trên giai đoạn Test.
- **Thêm dữ liệu chưa tự động tốt hơn:** XGBoost 32 → 43 biến có Test RMSE log return 0.018754 → 0.020089; đúng hướng 51.98% → 48.02%. GRU chọn **GRU L=60** bằng CV.

## 1. Bài toán

Một mô hình dự báo `r(t+1) = ln(C(t+1)/C(t))`; giá = `C(t) × exp(r dự báo)`, hướng = dấu của dự báo. Bằng 0 là Đứng giá. Không có mô hình phân loại riêng hoặc xác suất tăng.

## 2. Dữ liệu

4.671 phiên OHLCV FPT, **02/01/2007–30/09/2025**. Snapshot là bản dữ liệu cố định được lưu lại để cả nhóm chạy trên cùng số liệu. Giá do VCI cung cấp qua vnstock; nguồn bổ trợ gồm DNSE, Investing.com, World Bank và công bố FPT. Mỗi nguồn có lịch sử và tần suất khác nhau:

| Nhóm dữ liệu | Khoảng quan sát trong bản lưu | Dùng để mô tả điều gì? |
|---|---|---|
| Giá và khối lượng FPT | 02/01/2007–30/09/2025, 4.671 phiên | Mức giá, đà tăng/giảm, dao động và hoạt động giao dịch |
| VN-Index | 02/01/2007–30/09/2025, 4.635 phiên | Hướng và mức biến động thị trường chung |
| USD/VND | 01/01/2007–30/09/2025, 4.893 quan sát | Giá một USD tính bằng VND |
| Vàng XAU/USD | 01/01/2019–30/09/2025, 1.755 quan sát | Giá vàng quốc tế, nhân tỷ giá để đổi sang VND/ounce |
| CPI | Ngày công bố 27/12/2018–06/09/2025, 81 quan sát | Mức tăng giá tiêu dùng so với cùng kỳ năm trước |
| GDP | 2010–2024, 15 năm | Quy mô kinh tế theo USD hiện hành, không phải tốc độ tăng trưởng |
| Báo cáo tài chính FPT | Quý I/2007–quý II/2025, 52 quý có khoảng trống | Doanh thu và ba mức lợi nhuận theo quý |
| Cổ phiếu lưu hành FPT | 10 mốc tham chiếu từ 2017 đến 07/2025 | Số cổ phiếu đang lưu hành tại các mốc công bố |

Ngày của số liệu khác ngày mô hình được phép biết số liệu. Ví dụ quý II/2025 kết thúc 30/06, nhưng bốn chỉ tiêu tài chính chỉ được dùng từ **14/08/2025** theo giả định trễ 45 ngày. Các biến ngày được dùng từ ngày lịch tiếp theo; giá trị quá cũ trở lại thiếu. Không lấy số liệu tương lai để lấp quá khứ. Đọc [hướng dẫn nguồn, cách lấy, đơn vị và độ phủ sau ghép](data/README.md) để xem quy tắc riêng từng biến.

Ba cấp đầu vào là **32 biến giá/kỹ thuật → thêm 6 biến thị trường/vĩ mô thành 38 → thêm 5 biến tài chính thành 43**. Đủ lịch sử giá từ 2007 không có nghĩa đủ mọi nguồn từ 2007. Sau yêu cầu đủ dữ liệu và cửa sổ 60 phiên liên tiếp, tập so sánh chung có 1.559 hàng gán nhãn, bắt đầu ở phiên mục tiêu 03/04/2019.

### Đọc hiểu dữ liệu và công thức từ đâu?

1. [Cẩm nang hiểu dự án](docs/CAM_NANG_HIEU_DU_AN.md): dành cho cả nhóm, có ví dụ tính từng bước và kịch bản thuyết trình.
2. [Nguồn và từ điển dữ liệu](data/README.md): mỗi biến lấy ở đâu, lấy thế nào, đơn vị, ý nghĩa, khoảng thời gian và cách xử lý thiếu.
3. [EDA và đặc trưng](docs/EDA_VA_DAC_TRUNG.md): đọc biểu đồ, kiểm tra dữ liệu, giải thích đủ 32 biến giá/kỹ thuật, công thức và lý do sử dụng.
4. [Báo cáo thực nghiệm](docs/REPORT.md): thiết kế đánh giá và kết quả thật của ba thí nghiệm.
5. [Kiểm tra và bổ sung dữ liệu](docs/HUONG_DAN_KIEM_TRA_VA_BO_SUNG_DU_LIEU.md): danh sách thiếu/lỗi đã thấy, nguồn để tìm lịch sử sớm hơn và 9 bước kiểm tra file mới.

**Chất lượng dữ liệu còn cần hoàn thiện:** mốc vàng 2019/CPI 2018 là giới hạn bản đã thu thập. Rà soát bổ sung ghi nhận 36 ngày có trong FPT nhưng thiếu ở nguồn VN-Index; 17 đoạn tính return nguồn đi qua các ngày bị khuyết. Báo cáo quý thiếu 22 quý; các ngày công bố quý/GDP có phần giả định. Xem [audit chi tiết](reports/data_quality_review.json). Các bảng điểm dưới đây vẫn thuộc snapshot hiện hành, chưa phải kết quả trên nguồn đã bổ sung/sửa.

Ví dụ mục đích của công thức: `close/SMA20 − 1` diễn tả giá hôm nay cao hơn trung bình 20 phiên bao nhiêu phần trăm; `log(1 + volume)` giảm chênh lệch thang đo của khối lượng; `ln(close ngày sau/close hôm nay)` là mục tiêu mô hình cần dự báo. **Đặc trưng mô tả đầu vào, mục tiêu là đáp án cần học**; không đưa cột đáp án vào đầu vào.

## 3. Đặc điểm chuỗi thời gian

ADF bác bỏ nghiệm đơn vị của log return (p ≈ 1,05 × 10⁻¹⁷), nhưng KPSS vẫn bác bỏ dừng mức (p ≈ 0,0164). Kết quả hỗ trợ dùng biến động tương đối, không bảo đảm dự báo tốt. [Bảng kiểm định và ACF/PACF](docs/REPORT.md#3-đặc-điểm-chuỗi-thời-gian); STL ở phụ lục.

## 4. Năm phương pháp

**Last-Close → Ridge → XGBoost → ARIMA → GRU.** Mỗi phương pháp đại diện một cách suy nghĩ: giữ nguyên, tuyến tính, cây phi tuyến, lịch sử chuỗi, bộ nhớ tuần tự. SARIMAX chỉ là đối sánh mở rộng với ARIMA trong thí nghiệm 2.

## 5. Đánh giá

Train 1.325 / Test 234 mẫu; Test từ 22/10/2024 đến 30/09/2025. Train dùng CV 5 fold, `gap=1`; chọn theo RMSE log return. Độ chính xác hướng chấm 227 phiên đổi giá, dự báo 0 tính sai. Bộ chuẩn hóa chỉ học Train; artefact đánh giá tách khỏi bản học lại để dự báo.

## 6. Ba thí nghiệm và kết quả chính

1. So sánh năm phương pháp trên cùng ngày, mô hình ML/GRU dùng 32 biến; ARIMA chỉ dùng log return.
2. XGBoost cố định cấu hình, thêm dữ liệu **32 → 38 → 43**; đối sánh thêm ARIMA/SARIMAX.
3. GRU **L=20 so với L=60**, chọn bằng CV.

| Mô hình / cấu hình | CV RMSE log return | Test MAE giá (nghìn VND) | Test RMSE giá (nghìn VND) | Đúng hướng (%) | Dung sai ±1% (%) |
|---|---:|---:|---:|---:|---:|
| Last-Close Baseline | 0.017250 ± 0.003429 | 1.2250 | 1.7398 | 0.00% | 54.70% |
| Ridge Regression | 0.017612 ± 0.003467 | 1.2455 | 1.7534 | 52.42% | 52.99% |
| XGBoost | 0.017750 ± 0.002956 | 1.2621 | 1.7774 | 51.98% | 52.56% |
| ARIMA | 0.017192 ± 0.003481 | 1.2392 | 1.7537 | 48.90% | 54.27% |
| GRU L=60 | 0.017716 ± 0.003444 | 1.2213 | 1.7384 | 54.19% | 54.27% |

CV hiển thị trung bình ± độ lệch chuẩn qua 5 fold. Bảng chi tiết: [main](reports/main_benchmark.csv), [ablation](reports/ablation.csv), [ARIMA/SARIMAX](reports/statistical_extension.csv), [GRU](reports/lookback.csv). Có **9 cấu hình Test duy nhất, 10 artefact mô hình** gồm bản học lại.

![Giá thực tế và dự báo](figures/main_benchmark_prices.png)

## 7. Giải thích và phân tích lỗi

Permutation Importance là phần chính; SHAP là phụ lục. [Báo cáo](docs/REPORT.md) trình bày 3 ca sai số lớn nhất với biến động FPT/VN-Index cùng phiên, tách quan sát khỏi giả thuyết nguyên nhân. Các giới hạn và hướng phát triển được tập hợp tại [cuối báo cáo](docs/REPORT.md#giới-hạn-nghiên-cứu--hướng-phát-triển).

### Cài đặt và chạy

```bash
python -m pip install -r requirements.txt
python src/fetch_data.py --verify
python src/audit_data_quality.py
python src/fetch_supplemental.py --from-cache
python src/eda.py
python src/prepare.py
python src/time_series_analysis.py
python src/train.py
python src/explain.py
python src/predict.py
python -m pytest -q
```

Lệnh mặc định tái lập snapshot, không cần tải lại nguồn. Môi trường thực nghiệm: Python 3.14, CPU, seed 42; phiên bản thư viện tại [environment_versions.json](reports/environment_versions.json). Tải mới giá bằng `python src/fetch_data.py --download --start 2007-01-01 --end 2025-09-30` có thể đổi phiên bản giá điều chỉnh; khi đó phải kiểm toán và chạy lại.

Chạy theo ô tại [00_RUN_ALL.ipynb](notebooks/00_RUN_ALL.ipynb), hoặc từng notebook 01–09 theo [hướng dẫn](notebooks/README.md). Notebook gọi hàm trong `src/` để chỉ có một nơi định nghĩa thuật toán. Huấn luyện CV chạy trên CPU và lâu hơn các bước đọc dữ liệu.

```text
src/          thu thập, đặc trưng, chuẩn bị, metrics, train, sequence_models,
              audit_data_quality, time_series_analysis, plots, explain, predict
notebooks/    00 chạy toàn bộ; 01–09 giải thích và chạy từng bước
data/         raw snapshot và processed do pipeline tạo
reports/      CV, 3 thí nghiệm, dự báo từng phiên, kiểm toán, ca lỗi
models/       evaluation/ (9 bản Train-only), best_regressor.joblib
figures/      EDA, ACF/PACF, 3 thí nghiệm, permutation; phụ lục SHAP/STL
docs/         REPORT.md, CAM_NANG_HIEU_DU_AN.md, EDA_VA_DAC_TRUNG.md,
              HUONG_DAN_KIEM_TRA_VA_BO_SUNG_DU_LIEU.md,
              PROPOSAL.md, cs114_proposal.tex/.pdf
tests/        kiểm định dữ liệu, thời gian, cửa sổ, đầu ra và artefact
```

[Cẩm nang dùng chung](docs/CAM_NANG_HIEU_DU_AN.md) · [Proposal Markdown đã nộp](docs/PROPOSAL.md) · [Proposal PDF đã nộp](docs/cs114_proposal.pdf). Proposal được giữ theo bản đã nộp; thiết kế thực nghiệm hiện hành nằm trong báo cáo và cẩm nang.
