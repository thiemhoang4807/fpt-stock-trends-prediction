# Dự báo FPT phiên kế tiếp — CS114

Hệ thống dự báo **hướng Tăng/Giảm** và **log return phiên kế tiếp**, rồi quy đổi thành giá đóng cửa. Dữ liệu kết thúc **30/09/2025**; thực nghiệm gồm học máy dữ liệu bảng, ARIMA/SARIMAX và LSTM/GRU.

## Tóm tắt các phát hiện chính (Key Findings)

1. **Dự báo log return giúp mô hình cây làm việc trên thang biến động tương đối.** Ở Nhánh 1, MAE giá của Random Forest, XGBoost và HistGradientBoosting lần lượt là **1,2593; 1,2621; 1,3017 nghìn VND**, gần ARIMA (**1,2392**) và Ridge (**1,2455**). Giá dự báo được neo vào giá phiên hiện tại bằng công thức nhân với `exp(log return dự báo)`, thay vì buộc cây xuất trực tiếp một mức giá đã gặp trong Train.
2. **Thêm dữ liệu đa nguồn có tác động khác nhau lên hai bài toán.** Trong ablation XGBoost, G3 → G6 đưa Balanced Accuracy Test từ **54,03% lên 54,88%** (+0,85 điểm phần trăm), nhưng RMSE log return tăng từ **0,018754 lên 0,020089**. Trên CV, Balanced Accuracy cũng tăng nhẹ từ **52,57% lên 52,83%**. Đây là kết quả phù hợp với việc cần đánh giá riêng hướng và biên độ biến động khi dùng dữ liệu có tần suất thưa.
3. **Log return có bằng chứng mạnh chống nghiệm đơn vị nhưng chưa đáp ứng giả thuyết dừng mức của KPSS.** Trên lịch sử Train, ADF có **p ≈ 1,05 × 10⁻¹⁷**, còn KPSS có **p ≈ 0,0164**. Hai giả thuyết gốc đều bị bác bỏ ở mức 5%; cần phân biệt kiểm tra nghiệm đơn vị với kiểm tra tính dừng quanh một mức trung bình.

## Thiết kế và cách đọc kết quả

- Nhánh 1: **32 biến** giá, khối lượng, kỹ thuật và nến. Nhánh 2: **43 biến**, thêm VN-Index, USD/VND, vàng, CPI, GDP và 5 chỉ tiêu tài chính FPT. Biến ngành ICT đã được loại sau kiểm toán độ phủ.
- Cùng **1.559 nhãn**: Train **1.325** (03/04/2019–21/10/2024), Test **234** (22/10/2024–30/09/2025); phân loại Test có **227** phiên không đứng giá.
- Trong Train: **5 fold thời gian**, chừa 1 hàng ở ranh giới; scaler chỉ fit Train của từng lượt. Chọn hướng theo BA CV cao nhất, hồi quy theo RMSE log return CV thấp nhất, sau đó mới chấm Test.

## Bảng đối sánh chính

Mỗi nhánh giữ 9 đại diện chọn bằng CV. LSTM/GRU chỉ giữ L tốt nhất; hồi quy chọn một đại diện Linear/Ridge. CSV vẫn giữ đủ **30 dòng phân loại và 32 dòng hồi quy**. Bảng dưới rút gọn các cột; [báo cáo](docs/REPORT.md) có đủ Accuracy, Precision, Recall, F1, AUC, MAE, RMSE, MAPE, DA và dung sai. Ký hiệu **[CV chọn]** chỉ mô hình dùng trong lệnh dự báo.

### Phân loại

| Nhánh 1 | CV BA ± Std | Test BA | Nhánh 2 | CV BA ± Std | Test BA |
| --- | --- | --- | --- | --- | --- |
| Majority Baseline | 50.00% ± 0.00% | 50.00% | Majority Baseline | 50.00% ± 0.00% | 50.00% |
| Logistic Regression | 53.47% ± 2.26% | 57.21% | Logistic Regression | 51.43% ± 1.16% | 50.72% |
| SVC | 51.32% ± 3.54% | 49.08% | SVC | 51.41% ± 3.32% | 51.05% |
| Random Forest | 51.96% ± 1.75% | 52.29% | Random Forest | 52.41% ± 2.49% | 55.45% |
| XGBoost | 52.57% ± 3.64% | 54.03% | XGBoost | 52.83% ± 0.96% | 54.88% |
| HistGradientBoosting **[CV chọn]** | 55.05% ± 1.90% | 52.92% | HistGradientBoosting | 53.43% ± 2.61% | 52.19% |
| ARIMA | 50.06% ± 0.13% | 49.54% | SARIMAX | 49.88% ± 2.54% | 50.00% |
| LSTM L=30 | 52.24% ± 3.44% | 54.34% | LSTM L=20 | 50.98% ± 1.95% | 49.45% |
| GRU L=20 | 54.19% ± 2.66% | 58.24% | GRU L=20 | 52.14% ± 2.52% | 49.92% |

### Hồi quy

CV dùng RMSE log return; MAE giá có đơn vị nghìn VND/cổ phiếu.

| Nhánh 1 | CV RMSE log | Test MAE | Nhánh 2 | CV RMSE log | Test MAE |
| --- | --- | --- | --- | --- | --- |
| Last-Close Baseline | 0.017250 | 1.2250 | Last-Close Baseline | 0.017250 | 1.2250 |
| Ridge Regression | 0.017612 | 1.2455 | Ridge Regression | 0.019341 | 1.4893 |
| SVR | 0.017427 | 1.3146 | SVR | 0.017348 | 1.3198 |
| Random Forest | 0.017391 | 1.2593 | Random Forest | 0.017437 | 1.2699 |
| XGBoost | 0.017750 | 1.2621 | XGBoost | 0.018068 | 1.3671 |
| HistGradientBoosting | 0.017941 | 1.3017 | HistGradientBoosting | 0.018098 | 1.4856 |
| ARIMA **[CV chọn]** | 0.017192 | 1.2392 | SARIMAX | 0.018948 | 1.3093 |
| LSTM L=60 | 0.017470 | 1.2537 | LSTM L=10 | 0.017514 | 1.3050 |
| GRU L=60 | 0.017716 | 1.2213 | GRU L=60 | 0.017273 | 1.3617 |

### Cửa sổ LSTM/GRU

CV chọn L = 20 hoặc 30 cho phân loại; hồi quy chọn L = 60 ở 3/4 tổ hợp, riêng LSTM Nhánh 2 chọn L = 10. Xem [bảng 4 độ dài và nhận xét](docs/REPORT.md#5-khảo-sát-độ-dài-cửa-sổ-trượt) hoặc [CSV đầy đủ](reports/lookback_comparison.csv).

## Chạy dự án

```bash
python -m pip install -r requirements.txt
python src/fetch_data.py --verify
python src/fetch_supplemental.py
python src/eda.py
python src/prepare.py
python src/time_series_analysis.py
python src/train.py
python src/explain.py
python src/predict.py
python -m pytest -q
```

Các lệnh dùng snapshot đã đóng gói. Tải dữ liệu mới bằng `fetch_data.py` là một chế độ riêng; xem [hướng dẫn nguồn dữ liệu](data/README.md) và `python src/fetch_data.py --help`. Dùng cùng môi trường ghi trong [environment_versions.json](reports/environment_versions.json) để đối chiếu thực nghiệm. LSTM/GRU nhỏ chạy bằng CPU.

Để chạy từng ô có giải thích tiếng Việt:

```bash
python -m pip install -r requirements-notebooks.txt
python -m jupyterlab
```

Mở [00_RUN_ALL.ipynb](notebooks/00_RUN_ALL.ipynb), hoặc học từng công đoạn qua 9 notebook riêng. Xem [hướng dẫn notebook](notebooks/README.md). Notebook gọi cùng hàm trong `src/` nên không duy trì một bản thuật toán khác.

## Cấu trúc và tài liệu

```text
data/        snapshot nguồn, dữ liệu chuẩn hóa và bảng đặc trưng
src/         thu thập, xử lý, huấn luyện, giải thích và dự báo
             benchmark_tables.py: chọn bảng gọn theo CV
tests/       kiểm thử thời gian, nguồn, cửa sổ và lựa chọn đại diện
notebooks/   00_RUN_ALL và 01–09 cho từng công đoạn
reports/     toàn bộ CV, Test, ablation, importance và kiểm toán
figures/     biểu đồ EDA, chuỗi thời gian, dự báo và giải thích
models/      mô hình đánh giá và mô hình dự báo đã refit
docs/        Proposal Markdown/LaTeX/PDF và báo cáo
agent.md     nhật ký thực hiện
```

- [Proposal](docs/PROPOSAL.md) · [PDF](docs/cs114_proposal.pdf) · [Báo cáo](docs/REPORT.md).
- [Giới hạn nghiên cứu và hướng phát triển](docs/REPORT.md#giới-hạn-nghiên-cứu--hướng-phát-triển) tập hợp phạm vi kết luận và các giả định.
- Khi đóng gói nộp bài, `git archive --format=zip --output=../cs114_submission.zip HEAD` chỉ lấy nội dung đã commit, tránh đưa nhật ký tạm và tài liệu ôn tập riêng vào ZIP.
