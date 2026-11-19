# Dự báo biến động cổ phiếu FPT ở phiên kế tiếp bằng học máy và mô hình chuỗi thời gian

Đồ án môn CS114 của nhóm Lê Vũ Thiêm Hoàng (25520584), Nguyễn Tấn Dũng (25520367) và Lưu Hoàng Minh Duy (25520424).

## Kết quả chính

- **ARIMA(0,0,0) có RMSE log return thấp nhất qua kiểm định chéo trên Train** (0,015860). Trên Test, Last-Close vẫn có MAE giá thấp nhất (1,1097 nghìn VND/cổ phiếu), sát mức 1,1106 của ARIMA.
- **XGBoost thêm dữ liệu thị trường và vĩ mô đoán đúng thêm 9 trong 440 phiên đổi giá**, từ 52,95% lên 55,00%, trong khi MAE giá tăng từ 1,1100 lên 1,1164 nghìn VND/cổ phiếu. Thêm tiếp dữ liệu tài chính đưa tỷ lệ đúng hướng về 52,95%.
- **GRU chọn cửa sổ 60 phiên qua CV**, với sai số gần mức của cửa sổ 20 phiên và Last-Close. Kết quả trên mẫu này chưa cho thấy lợi ích rõ rệt từ bộ nhớ dài hơn.

## Bài toán

Sau khi phiên t đóng cửa, mô hình dự báo lợi nhuận logarit phiên kế tiếp, `r = ln(C(t+1)/C(t))`. Từ một dự báo r, hệ thống tính **giá đóng cửa** bằng `C(t) × exp(r)` và **hướng biến động** bằng dấu của r (dương là tăng, âm là giảm, bằng 0 là đứng giá).

## Dữ liệu

| Nguồn | Phạm vi lưu | Vai trò |
|---|---|---|
| OHLCV FPT, Vietcap qua vnstock | 4.671 hàng từ 02/01/2007 đến 30/09/2025 | Tạo 32 biến giá, khối lượng và kỹ thuật từ 4.669 phiên sau lọc lịch HOSE. |
| VN-Index, DNSE và CafeF | 4.668 mức đóng cửa sau bổ sung 33 phiên và sửa 16 mức giá | Tính log return và độ biến động thị trường 20 phiên. |
| USD/VND, XAU/USD từ Investing.com | 4.893 quan sát tỷ giá và 4.858 quan sát vàng, 2007–30/09/2025 | Dùng tỷ giá và giá vàng quốc tế quy đổi sang VND/ounce. |
| CPI và GDP năm, World Bank WDI | 20 quan sát mỗi biến, 2005–2024 | Thêm lạm phát cả năm theo % và GDP danh nghĩa theo USD. |
| Kết quả kinh doanh quý FPT, Vietcap qua vnstock | 50 quý dùng trong nghiên cứu, 2013Q1–2025Q2 | Thêm doanh thu thuần, lợi nhuận gộp, EBIT và lợi nhuận sau thuế của cổ đông công ty mẹ. |

Thí nghiệm XGBoost bổ sung lần lượt **32 → 38 → 42 biến**. Nguồn ngày dùng sau một ngày lịch. Các nguồn quý và năm dùng độ trễ giả định tương ứng 45 và 180 ngày sau cuối kỳ. Mỗi phiên chỉ ghép giá trị nguồn đã khả dụng và còn trong giới hạn độ cũ. [Nguồn và cách xử lý](data/README.md) · [EDA và công thức đặc trưng](docs/EDA_VA_DAC_TRUNG.md)

## Thiết kế thực nghiệm

Các cấu hình dùng cùng **3.031 nhãn từ 07/08/2013 đến 30/09/2025**, sau khi đủ 42 biến và 60 phiên ngữ cảnh. Chia theo ngày mục tiêu, với **2.576 mẫu Train** đến 29/11/2023 và **455 mẫu Test** từ 30/11/2023. Chọn cấu hình bằng RMSE log return trung bình qua `TimeSeriesSplit(n_splits=5, gap=1)` trên Train rồi giữ cố định tham số trong Test.

1. So sánh **Last-Close, Ridge, XGBoost, ARIMA và GRU**. Ridge, XGBoost và GRU dùng 32 biến, ARIMA dùng lịch sử log return.
2. Giữ cấu hình XGBoost để đo tác động khi tăng từ **32 lên 38 và 42 biến**. Thử thêm SARIMAX với 10 biến bên ngoài làm đối sánh thống kê với ARIMA.
3. So sánh **GRU cửa sổ 20 và 60 phiên** trên cùng mốc dự báo. Kiến trúc và lịch huấn luyện được giữ cố định.

## Bảng đối sánh chính

MAE và RMSE giá tính bằng nghìn VND/cổ phiếu trên 455 phiên. Tỷ lệ đúng hướng chỉ chấm 440 phiên thực tế đổi giá. Dung sai ±1% là tỷ lệ dự báo cách giá thực tế tối đa 1%.

| Mô hình | CV RMSE log return ↓ | Test MAE giá ↓ | Test RMSE giá ↓ | Đúng hướng ↑ | Dung sai ±1% ↑ |
|---|---:|---:|---:|---:|---:|
| Last-Close | 0,015890 ± 0,002139 | **1,1097** | 1,5623 | 0,00% | 55,16% |
| Ridge | 0,016166 ± 0,002189 | 1,1229 | 1,5794 | 48,41% | 54,73% |
| XGBoost (32 biến) | 0,016390 ± 0,002035 | 1,1100 | **1,5610** | **52,95%** | **55,60%** |
| ARIMA(0,0,0) | **0,015860 ± 0,002130** | 1,1106 | 1,5636 | 52,27% | 55,16% |
| GRU (60 phiên) | 0,016054 ± 0,002182 | 1,1114 | 1,5618 | 49,77% | 55,16% |

CV báo trung bình ± độ lệch chuẩn mẫu qua 5 fold. Last-Close luôn dự báo đứng giá nên đúng hướng 0,00% trên các phiên đổi giá. ARIMA(0,0,0) dự báo log return dương cố định nên 52,27% chính là tỷ lệ phiên tăng trong tập chấm hướng.

![Giá đóng cửa thực tế và dự báo trên Test, cùng phần phóng to 80 phiên cuối](figures/main_benchmark_prices.png)

[Báo cáo thực nghiệm, kiểm định chuỗi thời gian và phân tích lỗi](docs/REPORT.md) · [Đủ 9 cấu hình Test](reports/all_test_metrics.csv) · [XGBoost 32/38/42 biến](reports/ablation.csv) · [ARIMA/SARIMAX](reports/statistical_extension.csv) · [Các cửa sổ GRU](reports/lookback.csv)

## Tái lập kết quả

Chạy từ thư mục gốc của dự án với Python 3.14. Pipeline dùng các tệp dữ liệu lưu sẵn. [Phiên bản môi trường thực nghiệm](reports/environment_versions.json)

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

- Chạy theo ô bằng [00_RUN_ALL.ipynb](notebooks/00_RUN_ALL.ipynb) hoặc [các notebook theo từng bước](notebooks/README.md). Notebook gọi cùng mã trong `src/`.
- Dựng lại biểu đồ đối sánh từ kết quả đã lưu bằng `python src/plots.py`.
- Xem đầu ra dự báo tại [latest_prediction.json](reports/latest_prediction.json). Tệp dùng mô hình học lại sau đánh giá để minh họa dự báo sau phiên 30/09/2025.

| Thư mục | Nội dung |
|---|---|
| [src/](src/), [tests/](tests/) | Pipeline và bộ kiểm thử |
| [data/](data/), [notebooks/](notebooks/) | Dữ liệu đầu vào, bảng đặc trưng và hướng dẫn chạy |
| [reports/](reports/), [figures/](figures/) | Kiểm toán dữ liệu, điểm CV/Test, dự báo từng phiên và hình minh họa |
| [models/](models/) | 9 cấu hình học trên Train để chấm Test và 1 bản học lại để dự báo |
| [docs/](docs/) | Báo cáo, cẩm nang và đề xuất đã nộp |

[Cẩm nang học chung](docs/CAM_NANG_HIEU_DU_AN.md) · [Bản đề xuất đã nộp](docs/cs114_proposal.pdf)
