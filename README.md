# Dự đoán xu hướng và giá đóng cửa FPT phiên kế tiếp

Đồ án môn CS114 xây dựng hai bài toán riêng: dự đoán phiên FPT kế tiếp **Tăng/Giảm** và dự đoán **giá đóng cửa** của phiên đó. Đầu vào chỉ gồm thông tin có thể sử dụng khi phiên hiện tại đã đóng cửa. Phạm vi dữ liệu kết thúc tại **30/09/2025**.

## Hai nhánh thực nghiệm

| Nhánh | Đầu vào | Số biến |
|---|---|---:|
| 1 — Price Only | 5 trường OHLCV quan sát được, 23 chỉ báo từ close/volume, 4 đặc trưng nến | 32 |
| 2 — Macro & Fundamental | Toàn bộ Nhánh 1 cộng USD/VND, vàng quy đổi VND, CPI, GDP, vốn hóa/P-E ngành công nghệ và tài chính FPT | 44 |

Hai nhánh dùng **cùng 1.682 mẫu có nhãn**, cùng ngày và cùng ranh giới Train/Test. Dù chuỗi giá có từ năm 2007, phép đối sánh bắt đầu năm 2019 vì các nguồn bổ trợ chưa có đủ trước đó. Không chấm Nhánh 1 trên toàn bộ lịch sử rồi so với Nhánh 2 trên một khoảng khác.

![Pipeline hai nhánh](figures/00_pipeline_overview.png)

## Kết quả hiện tại

Test có 253 phiên từ **25/09/2024–30/09/2025**, trong đó 244 phiên có biến động giá được dùng chấm phân loại. Bảng dưới chọn mô hình tốt nhất của mỗi nhánh theo Balanced Accuracy:

| Nhánh | Mô hình phân loại | Accuracy | Balanced Accuracy | F1 lớp Tăng | ROC-AUC |
|---|---|---:|---:|---:|---:|
| 1 | Logistic Regression | 53,69% | 54,07% | 59,50% | 55,25% |
| 2 | XGBoost | 52,87% | 53,52% | 62,30% | 54,82% |

Dữ liệu bổ trợ chưa cải thiện điểm tốt nhất của nhánh giá trong Test này. So cùng thuật toán, XGBoost tăng Balanced Accuracy từ 51,93% lên 53,52%, còn Logistic Regression giảm từ 54,07% xuống 51,72%. Kết quả phụ thuộc cả dữ liệu lẫn mô hình; chưa thể kết luận biến vĩ mô có tác dụng ổn định.

Với hồi quy, Last-Close Baseline có sai số thấp nhất ở cả hai nhánh: MAE **1,1942** và RMSE **1,7129 nghìn VND/cổ phiếu**, MAPE **1,2342%**. Tỷ lệ nằm trong ±0,5% / ±1,0% / ±2,0% lần lượt là **34,39% / 55,34% / 82,61%**. Baseline luôn dự đoán giá phiên tới bằng giá hiện tại nên Directional Accuracy bằng 0% trên các phiên thực tế có tăng/giảm.

[Biểu đồ đường từng mô hình](figures/07_regression_lines_by_branch.png), [so sánh XGBoost có phóng to 80 phiên](figures/08_branch_xgboost_comparison_zoom.png), [đối sánh bốn mô hình hồi quy](figures/11_all_regressors_branch_comparison_zoom.png), [biểu đồ điểm phân loại](figures/09_classification_metric_bars.png) và [biểu đồ sai số giá](figures/10_regression_metric_bars.png) được tạo từ dự báo Test thật.

Toàn bộ điểm của 10 cấu hình phân loại và 10 cấu hình hồi quy nằm trong `reports/classification_test_metrics.csv` và `reports/regression_test_metrics.csv`. [Báo cáo thực nghiệm](docs/REPORT.md) giải thích đầy đủ kết quả và giới hạn.

## Dữ liệu và phương pháp

Snapshot OHLCV có **4.671 phiên, 02/01/2007–30/09/2025**, gồm `time, open, high, low, close, volume`. Nguồn giá là VCI/Vietcap qua vnstock; giá theo nghìn VND/cổ phiếu, khối lượng theo cổ phiếu. Kiểm toán có 0 ô thiếu, 0 ngày trùng, 2 phiên volume bằng 0 và 3 dòng OHLC bất nhất được lưu để truy vết.

Các dữ liệu bổ trợ là snapshot xuất từ Investing.com (USD/VND, vàng, lịch CPI), World Bank (GDP năm), Simply Wall St (ngành công nghệ) và VCI/vnstock cùng công bố FPT (tài chính, cổ phiếu lưu hành). Script chuẩn hóa các CSV đã đóng gói và căn theo ngày có thể biết; lần chạy này không được mô tả như đã tải trực tuyến thành công mọi nguồn. Chi tiết trường dữ liệu, nguồn, đơn vị và cách làm mới xem [data/README.md](data/README.md).

Dữ liệu quý được dùng sau cuối quý 45 ngày và GDP năm sau cuối năm 180 ngày theo giả định thực nghiệm. Dữ liệu ngày, CPI và snapshot ngành có độ trễ một ngày. Chỉ ghép lùi, không `backfill` hay nội suy qua quan sát tương lai; nguồn quá cũ bị đặt lại thành thiếu. Các giả định này chưa tái tạo được toàn bộ phiên bản báo cáo từng công bố trong quá khứ.

Train gồm 1.429 mẫu đầu, Test gồm 253 mẫu cuối theo ngày mục tiêu. Phân loại loại phiên đứng giá sau khi ấn định ranh giới chung. `StandardScaler` nằm trong `Pipeline` của Logistic/Linear Regression và chỉ fit trên Train. Không có tập Validation rời; siêu tham số được đặt trước, không dùng Test để điều chỉnh hoặc dừng sớm.

Theo thiết kế hiện tại, mô hình triển khai được chọn sau khi đối chiếu bảng Test rồi fit lại trên toàn bộ nhãn của cohort chung đến cutoff. Vì Test có tham gia chọn mô hình, điểm của mô hình được chọn mang tính thăm dò và có thể lạc quan. Các bảng Test vẫn là dự báo của mô hình chỉ học Train.

## Chạy dự án

Python 3.11 trở lên được khuyến nghị; cài các thư viện đã khai báo rồi chạy từ thư mục gốc:

```bash
python -m pip install -r requirements.txt
python src/fetch_data.py --verify
python src/fetch_supplemental.py --from-cache
python src/eda.py
python src/prepare.py
python src/train.py
python src/predict.py
python -m pytest -q
```

Chuỗi lệnh trên dùng snapshot cố định và không cần truy cập website khi tái chạy phần bổ trợ. Tải lại OHLCV qua vnstock/VCI là bước tùy chọn khi dịch vụ và quyền tài khoản cho phép:

```bash
python src/fetch_data.py --download --start 2007-01-01 --end 2025-09-30
```

Sau khi thay dữ liệu nguồn phải chạy lại kiểm toán, chuẩn hóa, huấn luyện và dự báo. Giá lịch sử có thể được nhà cung cấp điều chỉnh; không ghép điểm cũ với một snapshot giá mới.

## Dự báo sau phiên cuối snapshot

Với thông tin đến 30/09/2025, Logistic Regression Nhánh 1 dự báo **Tăng**, xác suất lớp Tăng **52,79%** trên hai lớp Tăng/Giảm. Last-Close Baseline dự báo **82,54 nghìn VND/cổ phiếu**, bằng close hiện tại trong thang lịch sử của snapshot. Hai đầu ra có thể khác nhau về chiều vì chúng do hai mô hình, hai mục tiêu riêng tạo ra.

Đây là minh họa học thuật; các điểm Test và xác suất chưa chứng minh hiệu quả đầu tư. Xem `reports/latest_prediction.json`.

## Cấu trúc thư mục

```text
src/
  fetch_data.py          Tải/chuẩn hóa/kiểm định OHLCV FPT
  fetch_supplemental.py  Chuẩn hóa snapshot bổ trợ, cutoff và ghép theo ngày hiệu lực
  eda.py                 Kiểm toán dữ liệu, biểu đồ EDA và sơ đồ pipeline
  features.py            32 biến giá/kỹ thuật và nhãn phiên kế tiếp
  prepare.py             Bảng đặc trưng giá và cohort chung hai nhánh
  train.py               5 mô hình mỗi bài toán, mỗi nhánh; metrics và biểu đồ
  predict.py             Dự báo từ đúng phiên mới nhất đã có đủ đầu vào
data/
  raw/fpt/               Snapshot OHLCV
  raw/supplemental/      Tệp xuất nguồn và các bảng chuẩn hóa
  processed/             Bảng đặc trưng và cohort hai nhánh
reports/                 Kiểm toán, metrics, dự báo từng mô hình, siêu tham số
figures/                 Sơ đồ, EDA, confusion matrix, line chart và bar chart
models/                  Mô hình đã chọn, fit lại để minh họa dự báo
tests/                   Kiểm thử chuẩn hóa, thời gian, dữ liệu rò rỉ và metrics
docs/
  PROPOSAL.md            Đề xuất đồ án CS114
  cs114_proposal.tex     Nguồn LaTeX
  cs114_proposal.pdf     Proposal đã biên dịch
  REPORT.md              Báo cáo thực nghiệm
```

Cẩm nang học tập riêng `docs/CAM_NANG_HIEU_DU_AN.md` được `.gitignore` loại trừ và không thuộc nội dung xuất bản.

Để biên dịch lại proposal khi đã cài XeLaTeX, Times New Roman và các gói LaTeX cần thiết, chạy hai lượt trong thư mục `docs`:

```bash
cd docs
xelatex -interaction=nonstopmode -halt-on-error cs114_proposal.tex
xelatex -interaction=nonstopmode -halt-on-error cs114_proposal.tex
```

## Tài liệu

- [Đề xuất Markdown](docs/PROPOSAL.md) · [Proposal PDF](docs/cs114_proposal.pdf) · [Nguồn LaTeX](docs/cs114_proposal.tex).
- [Báo cáo thực nghiệm](docs/REPORT.md) · [Nguồn và cách xử lý dữ liệu](data/README.md).
