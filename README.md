# Dự báo FPT phiên kế tiếp — CS114

Dự án dự báo **hướng Tăng/Giảm** và **lợi nhuận logarit phiên kế tiếp**, sau đó quy đổi lợi nhuận thành giá đóng cửa. Dữ liệu dừng tại **30/09/2025**. Phiên bản này bổ sung phân tích chuỗi thời gian, kiểm định chéo trong Train, ARIMA/SARIMAX, LSTM/GRU, SHAP và ablation theo nhóm dữ liệu.

## Thiết kế thực nghiệm

- **Nhánh 1:** 32 biến OHLCV, kỹ thuật và cấu trúc nến.
- **Nhánh 2:** 43 biến, thêm VN-Index, USD/VND, vàng quy đổi, CPI, GDP và 5 chỉ tiêu tài chính FPT.
- Dữ liệu ngành ICT được loại sau kiểm toán: archive có 33 mốc từ 2016, thiếu lịch sử và thành phần ngành theo thời điểm. VN-Index là biến thị trường chung, không phải chỉ số ngành thay thế. G5 được ghi rõ `excluded`.
- Hai nhánh dùng cùng 1.559 nhãn và đủ 60 phiên liên tiếp cho mọi cửa sổ học sâu. **Train 1.325 mẫu** (03/04/2019–21/10/2024); **Test 234 mẫu** (22/10/2024–30/09/2025). Phân loại Test còn 227 phiên sau khi loại nhãn đứng giá.
- **5-fold TimeSeriesSplit, gap=1** trong 85% Train. Scaler chỉ học ở phần Train của từng fold. Chọn hướng theo Balanced Accuracy CV; hồi quy theo RMSE log return CV. Sau khi khóa lựa chọn mới chấm 15% Test.

Các ngày Test đã từng được xem ở phiên bản trước. Lần này chúng không tham gia lựa chọn, nhưng chưa thể gọi đây là một giai đoạn hoàn toàn chưa từng quan sát.

## Các họ mô hình

| Họ | Mô hình |
|---|---|
| Học máy dữ liệu bảng | Majority/Last-Close Baseline, Logistic/Linear/Ridge Regression, SVC/SVR, Random Forest, XGBoost, HistGradientBoosting |
| Thống kê chuỗi thời gian | ARIMA cho Nhánh 1; SARIMAX với biến ngoại sinh cho Nhánh 2, dự báo từng phiên và cập nhật trạng thái sau khi kết quả đã biết |
| Học sâu | LSTM và GRU, cả hai bài toán, cửa sổ 10/20/30/60 phiên, mạng nhỏ chạy CPU |

Hồi quy học `next_log_return = ln(next_close/current_close)`, khôi phục `predicted_close = current_close * exp(prediction)`. Đánh giá MAE/RMSE trên log return; MAE/RMSE/MAPE, Directional Accuracy và Tolerance ±0.5%/±1%/±2% trên giá. Không tính MAPE trên log return bằng/gần 0.

## Kết quả chọn bằng Train CV

| Bài toán | Mô hình / nhánh | Điểm CV chọn mô hình | Kết quả Test |
|---|---|---|---|
| Hướng | HistGradientBoosting / Nhánh 1 | BA 55,05% | Accuracy 52,86%; BA 52,92%; F1 54,47%; AUC 0,5506 |
| Log return → giá | ARIMA / Nhánh 1 | RMSE log return 0,017192 | MAE 1,2392; RMSE 1,7537 nghìn VND; MAPE 1,2872% |

Có **30 dòng kết quả phân loại và 32 dòng hồi quy** trên Test, gồm các nhánh và cửa sổ khác nhau. Không đồng nghĩa 62 thuật toán khác nhau. XGBoost thêm đa nguồn cải thiện nhẹ hướng trên Test nhưng tăng sai số log return/giá. ADF và KPSS không đồng thuận hoàn toàn về tính dừng của log return; báo cáo giữ nguyên kết quả này.

[Đọc báo cáo đầy đủ](docs/REPORT.md) để xem CV Mean ± Std, Test, ablation, lookback, SHAP, permutation, biểu đồ và giới hạn. Các kết quả chưa chứng minh hiệu quả đầu tư.

## Dữ liệu

FPT có 4.671 phiên từ 02/01/2007 đến 30/09/2025, nguồn VCI/vnstock; giá nghìn VND/cổ phiếu, volume là số cổ phiếu. Lịch sử có điều chỉnh thang giá, chi tiết trong lineage. VN-Index tải trực tiếp DNSE có 4.635 phiên, đơn vị điểm. Tỷ giá/vàng/CPI, GDP và tài chính tái sử dụng bản xuất tài chính gốc đã lưu để tái lập.

Dữ liệu chỉ ghép lùi sau ngày có thể biết; quý giả định trễ 45 ngày, GDP năm 180 ngày khi thiếu lịch thực. Đây chưa phải kho đầy đủ mọi phiên bản công bố trong quá khứ. [Nguồn, đơn vị và cách lấy](data/README.md).

## Chạy bằng Notebook

```bash
python -m pip install -r requirements-notebooks.txt
python -m jupyterlab
```

Mở [00_RUN_ALL.ipynb](notebooks/00_RUN_ALL.ipynb), chọn kernel và chạy từ đầu. Hoặc [mở trên Colab](https://colab.research.google.com/github/thiemhoang4807/fpt-stock-trends-prediction/blob/main/notebooks/00_RUN_ALL.ipynb). Mặc định dùng snapshot đã đóng gói, không cần gọi lại API. [Hướng dẫn 10 notebook](notebooks/README.md).

## Chạy bằng Python

```bash
python -m pip install -r requirements.txt
python src/fetch_data.py --verify
python src/fetch_supplemental.py --from-cache
python src/eda.py
python src/prepare.py
python src/time_series_analysis.py
python src/train.py
python src/explain.py
python src/predict.py
python -m pytest -q
```

Làm mới riêng chỉ số: `python src/fetch_supplemental.py --download-market --from-cache`. Khi đổi dữ liệu cần chạy lại các bước sau. Cấu hình hiện tại chạy CPU; lưới CV tốn thời gian hơn một lần chia Train/Test.

## Cấu trúc chính

```text
src/
  fetch_data.py, fetch_supplemental.py   # Thu thập, chuẩn hóa, kiểm định nguồn
  features.py, prepare.py               # Đặc trưng, nhãn, nhóm G1–G6, cửa sổ
  eda.py, time_series_analysis.py       # EDA, ADF/KPSS, ACF/PACF, STL
  sequence_models.py                   # ARIMA/SARIMAX và LSTM/GRU
  train.py, explain.py, predict.py      # CV/Test, giải thích, dự báo
notebooks/                             # 00 tổng hợp và 01–09 theo bước
reports/                               # CV, Test, lookback, ablation, kiểm toán
figures/                               # Đồ thị dữ liệu, dự báo, giải thích
models/evaluation/                     # Mô hình chỉ học Train để chấm Test
models/best_*.joblib                    # Bản học lại toàn bộ nhãn để minh họa
```

46 kiểm thử đạt. Cả 10 notebook đã chạy bằng kernel mới trong bản sao cách ly, hai bảng metrics khớp pipeline Python trong dung sai 1e-10, dự báo JSON khớp và dữ liệu gốc không đổi. Nhánh clone/cài riêng Colab và tải API tùy chọn chưa được xác minh bằng lần chạy local này. Phiên bản thư viện thực thi: [environment_versions.json](reports/environment_versions.json).

[Proposal](docs/PROPOSAL.md) · [Proposal PDF](docs/cs114_proposal.pdf) · [Báo cáo](docs/REPORT.md). Cẩm nang riêng `docs/CAM_NANG_HIEU_DU_AN.md` được Git bỏ qua.
