# Dự báo biến động cổ phiếu FPT ở phiên kế tiếp bằng học máy và mô hình chuỗi thời gian

Đồ án môn CS114 — nhóm Lê Vũ Thiêm Hoàng (25520584), Nguyễn Tấn Dũng (25520367), Lưu Hoàng Minh Duy (25520424).

- **Cùng 3.031 phiên mục tiêu** từ 07/08/2013 đến 30/09/2025 cho các cấu hình. Mỗi mô hình dự báo log return để suy ra giá và chiều biến động của phiên kế tiếp.
- **ARIMA(0,0,0) được chọn qua Train CV** với RMSE log return 0,015860. MAE giá trên Test là 1,1106 nghìn VND, gần mức 1,1097 của Last-Close.
- **XGBoost 38 biến có độ đúng hướng 55,00%**, so với 52,95% ở 32 và 42 biến. MAE giá tăng nhẹ từ 1,1100 lên 1,1164 rồi 1,1167 nghìn VND.

## 1. Bài toán

Một mô hình dự báo `r(t+1) = ln(C(t+1)/C(t))`; giá = `C(t) × exp(r dự báo)`, hướng = dấu của dự báo. Bằng 0 là Đứng giá. Không có mô hình phân loại riêng hoặc xác suất tăng.

## 2. Dữ liệu

Tệp giá lưu 4.671 hàng từ 02/01/2007 đến 30/09/2025. Pipeline bỏ hai ngày HOSE đóng cửa 23–24/01/2018, còn 4.669 phiên. Sau 49 phiên tích lũy cho SMA50, bảng kỹ thuật có 4.620 hàng. Chuỗi chung đủ 42 biến từ 15/05/2013. Phiên đầu vào 06/08/2013 có đủ 60 phiên liên tiếp và được gán nhãn bằng ngày mục tiêu 07/08/2013. Bảng chung có 3.032 hàng gồm 3.031 nhãn và đầu vào 30/09/2025 dành cho dự báo.

| Nguồn | Phạm vi và quan sát | Cách dùng |
|---|---|---|
| FPT OHLCV, Vietcap qua vnstock | 4.671 hàng lưu, 2007–30/09/2025 | 4.669 phiên sau lọc lịch HOSE. Giá nghìn VND/cổ phiếu, khối lượng tính bằng cổ phiếu. |
| VN-Index, DNSE và CafeF | 4.668 giá đóng cửa sau bổ sung 33 phiên và sửa 16 mức giá | Tính log return và độ biến động 20 phiên. |
| USD/VND, Investing.com | 4.893 quan sát, 2007–30/09/2025 | VND trên một USD. |
| XAU/USD, bản xuất Investing.com | 4.858 giá ngày, 01/01/2007–30/09/2025 | Nhân với tỷ giá để có VND mỗi ounce vàng quốc tế. |
| CPI năm, World Bank WDI `FP.CPI.TOTL.ZG` | 20 năm 2005–2024 | Tỷ lệ lạm phát cả năm, đơn vị %. |
| GDP năm, World Bank WDI `NY.GDP.MKTP.CD` | 20 năm 2005–2024 | GDP danh nghĩa cả năm, USD hiện hành. |
| Kết quả kinh doanh FPT, Vietcap qua vnstock | 50 quý liên tục 2013Q1–2025Q2 trong phạm vi dùng | Doanh thu thuần, lợi nhuận gộp, EBIT và lợi nhuận sau thuế của cổ đông công ty mẹ. |

**32 → 38 → 42 biến.** Bộ đầu gồm 5 OHLCV, 23 chỉ báo và 4 biến nến. Bộ 38 thêm 2 biến VN-Index, USD/VND, vàng, CPI và GDP. Bộ 42 thêm 4 chỉ tiêu kết quả kinh doanh. Số cổ phiếu lưu hành được loại khỏi thiết kế vì tệp sẵn có chỉ bắt đầu khả dụng từ năm 2018.

Giá VN-Index, USD/VND và vàng được dùng sau một ngày lịch, tối đa 10 ngày từ lúc khả dụng. Báo cáo tài chính dùng theo giả định cuối quý cộng 45 ngày, giữ tối đa 150 ngày. CPI và GDP dùng theo giả định cuối năm cộng 180 ngày, giữ tối đa 550 ngày. Ví dụ số 2024 dùng từ phiên 30/06/2025 theo quy tắc này. Ghép lùi theo thời điểm khả dụng. Số CPI 3,6211 được hiểu là 3,6211%. Các ngày công bố và phiên bản số liệu lịch sử chưa xác minh đầy đủ.

[Sổ tay dữ liệu](data/README.md) · [EDA và công thức](docs/EDA_VA_DAC_TRUNG.md) · [Cẩm nang thuyết trình](docs/CAM_NANG_HIEU_DU_AN.md) · [Lịch sử và kiểm chứng nguồn](docs/DU_LIEU_TU_2007.md)

## 3. Đặc điểm chuỗi thời gian

ADF trên log return có p ≈ 5,63 × 10⁻¹⁷. KPSS có p ≈ 0,0338. Ở mức 5%, ADF bác bỏ nghiệm đơn vị và KPSS bác bỏ dừng mức. Hai kiểm định dùng lịch sử giá đến ngày kết thúc Train 29/11/2023. [Kiểm định và ACF/PACF](docs/REPORT.md#3-đặc-điểm-chuỗi-thời-gian)

## 4. Năm phương pháp

**Last-Close → Ridge → XGBoost → ARIMA → GRU.** Mỗi phương pháp đại diện một cách suy nghĩ: giữ nguyên, tuyến tính, cây phi tuyến, lịch sử chuỗi, bộ nhớ tuần tự. SARIMAX chỉ là đối sánh mở rộng với ARIMA trong thí nghiệm 2.

## 5. Đánh giá

**Train 2.576 mẫu (07/08/2013–29/11/2023)** và **Test 455 mẫu (30/11/2023–30/09/2025)**. Chia 85%/15% theo ngày mục tiêu. Hồi quy chấm 455 mẫu. Đúng hướng chấm 440 phiên đổi giá, dự báo đứng giá tính sai trên các phiên này. Train dùng `TimeSeriesSplit(n_splits=5, gap=1)`. Số hàng học lần lượt là 430, 859, 1.288, 1.717 và 2.146, với 429 hàng kiểm định mỗi fold. CV báo trung bình và độ lệch chuẩn mẫu. StandardScaler chỉ học từ phần Train của từng lượt fit.

## 6. Ba thí nghiệm và kết quả chính

1. So sánh năm phương pháp trên cùng ngày, mô hình ML/GRU dùng 32 biến; ARIMA chỉ dùng log return.
2. XGBoost cố định cấu hình, thêm dữ liệu **32 → 38 → 42**; đối sánh thêm ARIMA/SARIMAX.
3. GRU **L=20 so với L=60**, chọn bằng CV.

| Mô hình / cấu hình | CV RMSE log return | Test MAE giá (nghìn VND) | Test RMSE giá (nghìn VND) | Đúng hướng | Dung sai ±1% |
|---|---:|---:|---:|---:|---:|
| Last-Close Baseline | 0.015890 ± 0.002139 | 1.1097 | 1.5623 | 0.00% | 55.16% |
| Ridge Regression | 0.016166 ± 0.002189 | 1.1229 | 1.5794 | 48.41% | 54.73% |
| XGBoost | 0.016390 ± 0.002035 | 1.1100 | 1.5610 | 52.95% | 55.60% |
| ARIMA | 0.015860 ± 0.002130 | 1.1106 | 1.5636 | 52.27% | 55.16% |
| GRU L=60 | 0.016054 ± 0.002182 | 1.1114 | 1.5618 | 49.77% | 55.16% |

CV hiển thị trung bình ± độ lệch chuẩn qua 5 fold. Bảng chi tiết: [main](reports/main_benchmark.csv), [ablation](reports/ablation.csv), [ARIMA/SARIMAX](reports/statistical_extension.csv), [GRU](reports/lookback.csv). Có **9 cấu hình Test duy nhất, 10 artefact mô hình** gồm bản học lại.

![Giá thực tế và dự báo](figures/main_benchmark_prices.png)

## 7. Giải thích và phân tích lỗi

Permutation Importance là phần chính; SHAP là phụ lục. [Báo cáo](docs/REPORT.md) trình bày 3 ca sai số lớn nhất với biến động FPT/VN-Index cùng phiên, tách quan sát khỏi giả thuyết nguyên nhân. Các giới hạn và hướng phát triển được tập hợp tại [cuối báo cáo](docs/REPORT.md#giới-hạn-nghiên-cứu--hướng-phát-triển).

### Cài đặt và chạy

```bash
python -m pip install -r requirements.txt
python src/fetch_data.py --verify
python src/fetch_supplemental.py --from-cache
python src/audit_data_quality.py
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
              audit_data_quality, fetch_historical_candidates,
              time_series_analysis, plots, explain, predict
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
