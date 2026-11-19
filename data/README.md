# Nguồn, biến và xử lý dữ liệu FPT

## 1. Phạm vi và dữ liệu gốc

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

Tệp `data/sources.json` ghi mã nguồn và đơn vị. [Manifest nguồn](raw/supplemental/study_2013_lineage.json) lưu hash của các tệp dùng trong lần cập nhật, độ phủ và từng truy vấn VN-Index. [Nhật ký tìm nguồn](../docs/DU_LIEU_TU_2007.md) giữ quá trình khảo sát các bản khác.

| Cột giá | Ý nghĩa | Đơn vị |
|---|---|---|
| `time` | Ngày giao dịch theo lịch Việt Nam | YYYY-MM-DD |
| `open`, `high`, `low`, `close` | Giá mở, cao nhất, thấp nhất và đóng | Nghìn VND/cổ phiếu theo thang giá Vietcap |
| `volume` | Số cổ phiếu giao dịch trong phiên | Cổ phiếu |

Bản giá điều chỉnh dùng hệ số căn chuỗi lịch sử 0,8875 cho OHLC trong đợt lưu trước. Khối lượng giữ đơn vị gốc. [Lineage OHLCV](../reports/data_lineage.json)

## 2. Cách lấy và kiểm tra từng nguồn

- **Giá FPT** được lưu từ `Quote.history` của VCI qua vnstock. `python src/fetch_data.py --verify` kiểm tra cấu trúc OHLCV, số hàng và mã SHA-256 của snapshot với hồ sơ nguồn. Pipeline tái lập bằng CSV lưu sẵn.
- **USD/VND** dùng giá đóng cửa của CSV lịch sử. Giá `26,421` là 26.421 VND/USD. Ngày trong tệp là ngày/tháng/năm. [Lịch sử USD/VND](https://vn.investing.com/currencies/usd-vnd-historical-data)
- **Vàng** dùng toàn bộ chuỗi giá đóng cửa đã kiểm tra và cắt về 30/09/2025 của bản xuất do thành viên cung cấp. Ví dụ `3,858.51` là 3.858,51 USD/ounce. Giá vàng ghi trong mô hình là tích **hai số đã ghép đúng thời điểm** của XAU/USD và USD/VND. [Lịch sử XAU/USD](https://vn.investing.com/currencies/xau-usd-historical-data)
- **CPI/GDP** giữ giá trị gốc trong WDI, giới hạn đến hết 2024. Các trường ngày công bố thực còn trống. Quan sát CPI 2024 là 3,6210927%, GDP khoảng 476,325 tỷ USD. [CPI Việt Nam](https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG?locations=VN) · [GDP Việt Nam](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=VN)
- **Tài chính FPT** dùng số riêng quý hợp nhất đơn vị VND. `EBIT = lợi nhuận trước thuế + |chi phí lãi vay|`. Bản lưu có thêm hai quý năm 2007 ngoài chuỗi 50 quý. Ngày kết thúc quý được suy từ Năm/Kỳ. [Công bố FPT](https://fpt.com/en/ir/information-disclosures)

Đối chiếu lịch từ năm 2013 cho thấy DNSE thiếu 33 phiên có giao dịch FPT. Dùng giá đóng cửa CafeF cho các phiên thiếu và 16 mức khác nhau trong các khoảng đối chiếu năm 2020. Báo cáo phiên của các công ty chứng khoán xác nhận các mức CafeF được kiểm tra chéo, như 869,91 điểm ngày 15/07/2020 và 903,98 điểm ngày 29/09/2020. Sau hiệu chỉnh, các phiên FPT trong phạm vi từ 2013 đều có giá đóng cửa VN-Index. Hai ngày HOSE đóng cửa được loại khỏi lịch phiên trước khi tính nhãn. [Lịch sử CafeF](https://cafef.vn/du-lieu/lich-su-giao-dich-vnindex-1.chn) · [Bản tin Funan](https://funan.com.vn/en/diem-tin-giao-dich-15072020.409463) · [Xác nhận lịch HOSE](https://baochinhphu.vn/hose-giao-dich-tro-lai-sau-hai-ngay-dong-cua-102233882.htm)

## 3. Biến bổ trợ và thời điểm sử dụng

**32 → 38 → 42 biến.** Bộ đầu gồm 5 OHLCV, 23 chỉ báo và 4 biến nến. Bộ 38 thêm 2 biến VN-Index, USD/VND, vàng, CPI và GDP. Bộ 42 thêm 4 chỉ tiêu kết quả kinh doanh. Số cổ phiếu lưu hành được loại khỏi thiết kế vì tệp sẵn có chỉ bắt đầu khả dụng từ năm 2018.

| Biến bổ trợ | Ý nghĩa/đơn vị | Mục đích thử nghiệm |
|---|---|---|
| `vnindex_return_1d` | Logarithm tỷ số hai mức đóng cửa VN-Index liên tiếp trong nguồn; không có đơn vị | Mô tả hướng chuyển động thị trường gần nhất trong lịch đã đối chiếu |
| `vnindex_volatility_20d` | Độ lệch chuẩn 20 log return thị trường, chia phương sai cho 20 | Mô tả giai đoạn thị trường bình lặng hay biến động mạnh |
| `usd_vnd_rate` | VND để mua một USD; tỷ giá tăng nghĩa là cần nhiều VND hơn | Thử thông tin bối cảnh tỷ giá, có thể liên quan thu nhập/chi phí ngoại tệ |
| `gold_vnd_per_ounce` | XAU/USD nhân USD/VND đã căn thời điểm; VND/ounce vàng quốc tế | Thử thông tin từ một thị trường tài sản khác |
| `cpi_annual_inflation_pct` | Lạm phát CPI cả năm, đơn vị % | Bối cảnh lạm phát trong năm gần nhất đủ điều kiện sử dụng |
| `gdp_usd` | GDP cả năm theo USD hiện hành | Mô tả quy mô kinh tế dài hạn; không thay cho tốc độ tăng GDP thực |
| `fpt_net_revenue_vnd` | Doanh thu sau các khoản giảm trừ, VND/quý | Mô tả quy mô hoạt động kinh doanh |
| `fpt_gross_profit_vnd` | Doanh thu thuần trừ giá vốn, VND/quý | Mô tả phần còn lại sau chi phí trực tiếp, chưa trừ mọi chi phí |
| `fpt_ebit_vnd` | Lợi nhuận trước thuế + trị tuyệt đối chi phí lãi vay, VND/quý | Xấp xỉ lợi nhuận trước lãi vay và thuế theo quy tắc của dự án |
| `fpt_parent_net_profit_vnd` | Lợi nhuận sau thuế thuộc cổ đông công ty mẹ, VND/quý | Phân biệt lợi ích thuộc cổ đông FPT với phần của cổ đông không kiểm soát |

Giá VN-Index, USD/VND và vàng được dùng sau một ngày lịch, tối đa 10 ngày từ lúc khả dụng. Báo cáo tài chính dùng theo giả định cuối quý cộng 45 ngày, giữ tối đa 150 ngày. CPI và GDP dùng theo giả định cuối năm cộng 180 ngày, giữ tối đa 550 ngày. Ví dụ số 2024 dùng từ phiên 30/06/2025 theo quy tắc này. Ghép lùi theo thời điểm khả dụng. Số CPI 3,6211 được hiểu là 3,6211%. Các ngày công bố và phiên bản số liệu lịch sử chưa xác minh đầy đủ.

Các đặc trưng kỹ thuật được giải thích bằng công thức và ví dụ riêng. [EDA và đặc trưng](../docs/EDA_VA_DAC_TRUNG.md)

## 4. Kiểm tra độ phủ và tái lập

- Tập chung có 60 phiên đầu vào đủ 42 biến cho mỗi dự báo. Từ 15/05/2013 đến cutoff, các phiên trong bảng bổ trợ đủ biến, và pipeline báo lỗi nếu xuất hiện khoảng trống.
- Bản giá có ba bất nhất OHLC trước 2010. Chúng nằm ngoài tập chung. Một mốc VN-Index còn lệch trước 2013 và 22 quý thiếu trước 2013 được ghi trong kiểm toán.
- Tất cả mô hình được chấm trên cùng các ngày mục tiêu. Hướng dự báo được suy từ dấu của log return. [Báo cáo thực nghiệm](../docs/REPORT.md)

```bash
python src/fetch_data.py --verify
python src/fetch_supplemental.py --from-cache
python src/audit_data_quality.py
python src/prepare.py
```

`--from-cache` đọc các tệp đầu vào đã chuẩn hóa bên dưới, tạo `data/processed/fpt_multisource_features.csv` và lưu danh sách tệp cùng mã SHA-256 trong hồ sơ ghép. [Kiểm toán nguồn](../reports/supplemental_data_audit.json)

| Nhóm | Tệp đầu vào trong `data/raw/supplemental/` |
|---|---|
| VN-Index | `vnindex_source.csv`, `vnindex_close_corrections.csv` |
| Tỷ giá và vàng | `usd_vnd_daily.csv`, `gold_xauusd_study.csv` |
| Vĩ mô năm | `vietnam_cpi_annual.csv`, `vietnam_gdp_annual.csv` |
| Kết quả kinh doanh | `fpt_fundamentals_quarterly.csv` |

`prepare_macro_refresh.py` kiểm tra tệp xuất vàng và gói CSV WDI CPI. `python src/fetch_supplemental.py --download-market` tải một bản VN-Index ứng viên vào `tmp/market_candidate/` để đối chiếu trước khi cập nhật dữ liệu nghiên cứu. [Hướng dẫn kiểm tra bản mới](../docs/HUONG_DAN_KIEM_TRA_VA_BO_SUNG_DU_LIEU.md)

Các bản WDI có giá trị CPI và GDP cho đủ 20 năm. Ngày công bố thực để trống ở cả 20 hàng của mỗi bảng. Báo cáo kiểm toán đếm ô trống và giá trị vô hạn bằng hai chỉ tiêu riêng. [Kiểm toán độ phủ](../reports/data_quality_review.json)
