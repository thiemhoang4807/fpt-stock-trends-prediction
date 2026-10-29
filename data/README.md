# Dữ liệu nghiên cứu FPT đến 30/09/2025

## 1. Nguồn và phạm vi

Dự án dùng snapshot (bản chụp dữ liệu đã cố định) để tái lập thí nghiệm. Giai đoạn của chuỗi giá là 02/01/2007–30/09/2025. Giai đoạn so sánh hai nhánh ngắn hơn vì các nguồn bổ trợ không cùng bắt đầu năm 2007.

| Dữ liệu | Nguồn tài chính | Cách lấy và tệp nguồn | Phạm vi snapshot sau cắt |
|---|---|---|---|
| OHLCV FPT | VCI/Vietcap qua vnstock | Quote.history; data/raw/fpt/fpt_historical_price.csv | 4.671 phiên, 02/01/2007–30/09/2025 |
| USD/VND | Investing.com | Xuất CSV lịch sử; supplemental/usd_vnd_source.csv | 4.893 quan sát, 01/01/2007–30/09/2025 |
| Vàng XAU/USD | Investing.com | Xuất CSV lịch sử; supplemental/gold_xauusd_source.csv | 1.755 quan sát, 01/01/2019–30/09/2025 |
| CPI Việt Nam | Investing.com, lịch công bố số liệu GSO | Chép/xuất bảng lịch kinh tế; supplemental/vietnam_cpi_source.csv | 81 lần công bố, 27/12/2018–06/09/2025 |
| GDP Việt Nam | World Bank, NY.GDP.MKTP.CD | Xuất CSV GDP danh nghĩa USD theo năm; supplemental/vietnam_gdp_source.csv | 15 năm, 2010–2024; loại dự báo năm 2025 |
| Ngành công nghệ Việt Nam (chỉ kiểm toán, loại khỏi mô hình) | Simply Wall St | Bảng lịch sử 10Y/Data; supplemental/ict_industry_source.csv | 33 snapshot, 06/02/2016–24/07/2025 |
| VN-Index | DNSE API chỉ số | supplemental/vnindex_source.csv; tải tự động bằng --download-market | 4.635 phiên, 02/01/2007–30/09/2025; đơn vị điểm |
| Báo cáo tài chính FPT | VCI qua vnstock | Báo cáo kết quả kinh doanh quý; supplemental/fpt_income_statement_source.csv | 52 kỳ từ 2007-Q1 đến 2025-Q2; thiếu giai đoạn 2007-Q3–2012-Q4 |
| Số cổ phiếu lưu hành | Công bố và báo cáo thường niên FPT | Trích chỉ tiêu và ngày có thể biết; supplemental/fpt_shares_outstanding.csv | 10 mốc, báo cáo cuối 2017 đến tăng vốn tháng 7/2025 |

Các tệp dưới supplemental/ đều nằm trong data/raw/. Lần cập nhật này sử dụng các CSV lưu trữ có sẵn và trích bổ sung công bố cổ phiếu từ FPT, sau đó chạy lại chuẩn hóa. Các bản xuất vĩ mô/tài chính được tái dùng để giữ khả năng tái lập; riêng VN-Index đã được tải trực tiếp từ API DNSE trong đợt nâng cấp. Hash và thông tin truy xuất nằm trong `data/raw/supplemental/vnindex_lineage.json`.

Nguồn trực tiếp và mô tả công cụ:

- [Dữ liệu thị trường Vnstock](https://vnstocks.com/docs/vnstock/thi-truong-market).
- [USD/VND lịch sử](https://vn.investing.com/currencies/usd-vnd-historical-data), [XAU/USD lịch sử](https://vn.investing.com/currencies/xau-usd-historical-data), [lịch CPI Việt Nam](https://vn.investing.com/economic-calendar/vietnamese-cpi-1851).
- [GDP danh nghĩa Việt Nam của World Bank](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=VN).
- [Ngành công nghệ Việt Nam trên Simply Wall St](https://simplywall.st/markets/vn/tech).
- [Công bố thông tin FPT](https://fpt.com/en/ir/information-disclosures). URL của từng báo cáo cổ phiếu nằm ngay trong fpt_shares_outstanding.csv.

## 2. Luồng dữ liệu

```text
VCI / các tệp xuất Investing / World Bank / DNSE / công bố FPT
    |
    +-- snapshot OHLCV -> fetch_data.py --verify -> eda.py
    |
    +-- snapshot bổ trợ -> fetch_supplemental.py --from-cache
                          | chuẩn ngày, đơn vị, cutoff, ngày hiệu lực, hạn dùng
                          v
                    fpt_multisource_features.csv
                          |
OHLCV -> features.py -> prepare.py -> cohort chung đủ 43 biến
                                      | Nhánh 1: 32 biến OHLCV/kỹ thuật
                                      | Nhánh 2: 43 biến gồm 11 biến bổ trợ
                                      v
                                Train 85% (CV 5 fold) / Test 15%
```

Không nội suy tuyến tính giữa hai kỳ báo cáo: phép nội suy đó cần giá trị của kỳ tương lai. Không mở rộng giá FPT sang ngày nghỉ rồi tạo giá/volume giả. Tập ngày gốc là các phiên FPT thực sự có trong snapshot.

## 3. Schema OHLCV và đơn vị

| Cột | Ý nghĩa | Đơn vị |
|---|---|---|
| time | Ngày giao dịch | YYYY-MM-DD |
| open | Giá mở cửa | nghìn VND/cổ phiếu |
| high | Giá cao nhất phiên | nghìn VND/cổ phiếu |
| low | Giá thấp nhất phiên | nghìn VND/cổ phiếu |
| close | Giá đóng cửa | nghìn VND/cổ phiếu |
| volume | Khối lượng giao dịch | cổ phiếu |

Ví dụ close = 82.54 tương ứng 82.540 đồng/cổ phiếu theo thang của snapshot. Không tự nhân/chia 1.000 thêm lần nữa trong huấn luyện. Chuỗi giá lưu thang lịch sử do VCI cung cấp; phiên bản trước của archive đã căn OHLC bằng hệ số 0,8875 khi nối các cửa sổ giá. Việc cắt về 2025 giữ thang đó, không khẳng định đây là giá niêm yết chưa điều chỉnh hay là bản giá từng thấy chính xác tại thời điểm 2025. Volume không bị nhân hệ số. Chi tiết và SHA-256 nằm trong reports/data_lineage.json.

## 4. Chuẩn hóa nguồn bổ trợ

src/fetch_supplemental.py đọc các tệp *_source.csv và lịch cổ phiếu lưu hành, tạo các tệp chuẩn có cột time và các cột số tương ứng, rồi ghép vào phiên FPT.

| Trường đầu vào mô hình | Đơn vị/định nghĩa |
|---|---|
| vnindex_return_1d | Lợi nhuận logarit một phiên của VN-Index, dùng trễ một ngày lịch |
| vnindex_volatility_20d | Độ lệch chuẩn 20 lợi nhuận logarit của VN-Index, ddof=0, dùng trễ một ngày lịch |
| usd_vnd_rate | VND cho 1 USD; lấy cột “Lần cuối”, bỏ dấu phẩy phân cách hàng nghìn |
| gold_vnd_per_ounce | XAU/USD × USD/VND đã căn ngày; VND cho 1 troy ounce vàng quốc tế, không phải giá SJC |
| cpi_yoy_pct | Tỷ lệ CPI cùng kỳ theo %, ví dụ 3.24 là 3,24%, không phải mức chỉ số CPI = 103,24 |
| gdp_usd | GDP danh nghĩa cả năm theo USD, không phải tăng trưởng GDP hay GDP quý |
| fpt_net_revenue_vnd | Doanh thu thuần riêng kỳ quý, VND |
| fpt_gross_profit_vnd | Lợi nhuận gộp quý, VND |
| fpt_ebit_vnd | EBIT tính theo quy ước lợi nhuận trước thuế + trị tuyệt đối chi phí lãi vay; VND |
| fpt_parent_net_profit_vnd | Lợi nhuận sau thuế thuộc cổ đông công ty mẹ, VND |
| fpt_shares_outstanding | Số cổ phiếu lưu hành gần nhất biết từ các báo cáo/sự kiện đã thu thập, cổ phiếu |

EBIT không đồng nhất với “Lãi/Lỗ từ hoạt động kinh doanh”. Ví dụ 2025-Q2: 3.141.032.584.460 + 216.761.295.705 = 3.357.793.880.165 VND. Đây là EBIT theo công thức của dự án, không phải một cột EBIT độc lập đã được kiểm toán.

Ba trường ngành được giữ trong dữ liệu chuẩn hóa để kiểm toán nhưng không thuộc danh sách đầu vào. Archive chỉ có 33 mốc từ 2016, không phủ 2007; thiếu thành phần/khối lượng ngành theo thời điểm. VN-Index phản ánh thị trường chung, không được coi là chỉ số ngành ICT. Không tạo rổ giả từ các doanh nghiệp hiện còn niêm yết. Chi tiết quyết định ở `reports/sector_coverage_audit.json`.

Ngày USD/VND và vàng được đọc bằng dd/MM/yyyy; CPI dùng MM/dd/yyyy của tệp xuất; ngành dùng dd-MM-yyyy. Vì vậy “09/06/2025” trong CPI là 06/09/2025. Không suy đoán một quy tắc ngày chung cho mọi nguồn.

## 5. Ngày hiệu lực và giới hạn dữ liệu cũ

| Nguồn | Ngày dùng trong mô phỏng | Hạn giữ sau ngày có hiệu lực |
|---|---|---:|
| VN-Index, USD/VND, XAU/USD | Ngày quan sát + 1 ngày lịch | 10 ngày |
| CPI | Ngày công bố ghi trong lịch nguồn + 1 ngày | 65 ngày |
| GDP năm | Cuối năm + 180 ngày, giả định bảo thủ | 550 ngày |
| Ngành (chỉ lưu kiểm toán) | Ngày snapshot + 1 ngày | 180 ngày |
| Báo cáo quý FPT | Cuối quý + 45 ngày, giả định thực nghiệm | 150 ngày |
| Cổ phiếu lưu hành | Ngày công bố/ngày tham chiếu trong CSV + 1 ngày | 550 ngày |

Ghép backward as-of lấy quan sát mới nhất có hiệu lực không muộn hơn phiên đang xử lý. Giá trị chưa công bố giữ thiếu. Sau hạn dùng, giá trị cũng trở lại thiếu thay vì giữ một báo cáo cũ qua nhiều năm. Vì snapshot tài chính có khoảng trống 2007–2013, không dùng báo cáo 2007-Q2 để lấp cả khoảng này.

Ví dụ: 2025-Q2 kết thúc 30/06/2025; giả định 45 ngày cho ngày có hiệu lực 14/08/2025. Báo cáo 2025-Q3 chưa được dùng tại 30/09/2025. CPI công bố 06/10/2025 bị cắt khỏi tệp nguồn. GDP cả năm 2025 bị loại. Cổ phiếu lưu hành 1.703.507.121 từ công bố tăng vốn tháng 7 được dùng từ các phiên sau mốc công bố 01/08/2025, không gán ngược cho năm 2019.

Bảng cổ phiếu là lịch sử các điểm gần nhất đã thu thập, không phải sổ thay đổi cổ phiếu đầy đủ từng ngày. Riêng báo cáo cuối 2017 dùng mốc tham chiếu bảo thủ 30/06/2018 khi chưa xác minh được ngày công bố chính xác.

Quy tắc độ trễ ngăn dùng báo cáo trước ngày hiệu lực giả định, nhưng không phục hồi phiên bản báo cáo/GDP từng được công bố trong quá khứ. Dữ liệu điều chỉnh lại và thành phần ngành hiện hành vẫn có thể gây thiên lệch. Vì thế đây là mô phỏng căn thời điểm công bố có nêu giả định, chưa phải kho dữ liệu lịch sử theo từng phiên bản hoàn chỉnh.

## 6. Kết quả kiểm toán và cohort so sánh

OHLCV có 0 ô thiếu, 0 ngày trùng, 2 phiên volume bằng 0, 3 hàng quan hệ OHLC bất nhất (17/08/2007, 10/06/2009, 07/12/2009). Các hàng này được giữ và đánh dấu, không âm thầm sửa. Chúng nằm trước cohort so sánh chung 2019–2025.

Vàng có 2.988 phiên FPT trước khi đủ dữ liệu; CPI có 2.987; GDP có 1.110; ngành có 2.262; tài chính có 1.407 phiên thiếu sau áp dụng hạn dùng; cổ phiếu lưu hành có 2.859. Những ô thiếu đầu chuỗi không được backfill. Bảng ghép vẫn lưu chúng để kiểm toán.

Sau bước tạo chỉ báo, cần thêm 60 phiên giao dịch liên tiếp đủ 43 biến để mọi cửa sổ LSTM/GRU dùng cùng các ngày. Còn 1.560 hàng, trong đó 1.559 hàng có nhãn và một hàng cuối dành cho dự báo. Chỉ số phiên gốc được giữ khi một chỉ báo không xác định để không nén lỗ hổng thành các phiên liền nhau.

| Tập | Ngày mục tiêu | Hồi quy | Phân loại |
|---|---|---:|---:|
| Train 85% | 03/04/2019–21/10/2024 | 1.325 | Bỏ riêng nhãn đứng giá khi fit |
| Test 15% | 22/10/2024–30/09/2025 | 234 | 227 |

Phân loại bỏ nhãn đứng giá sau khi xác định ranh giới chung. Trên Train, 5-fold TimeSeriesSplit có gap=1 dùng để chọn tham số/mô hình; mọi scaler chỉ fit ở phần Train của từng fold. Không sử dụng Test để chọn. Mục tiêu hồi quy là log return, sau dự báo mới quy đổi về giá. Các bảng kiểm toán chi tiết: `reports/data_audit.json`, `supplemental_data_audit.json`, `split_metadata.json`.

## 7. Tái lập và cập nhật

Chạy hoàn toàn từ các snapshot được đóng gói:

```bash
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

Để chuẩn hóa và đồng thời cắt các tệp xuất về mốc nghiên cứu, chạy thêm --trim-inputs. Lệnh này loại quan sát sau cutoff và dòng GDP dự báo cùng năm:

```bash
python src/fetch_supplemental.py --from-cache --trim-inputs --end 2025-09-30
```

Để lấy lại OHLCV trực tuyến khi vnstock/VCI truy cập được:

```bash
python src/fetch_data.py --download --start 2007-01-01 --end 2025-09-30
```

Tải lại có thể tạo một phiên bản giá điều chỉnh khác, nên phải kiểm tra lineage và chạy lại các bước sau thay vì ghép metric cũ với dữ liệu mới.

Quy trình làm mới dữ liệu thủ công tại nguồn:

1. Investing: mở lịch sử USD/VND hoặc XAU/USD, chọn khoảng ngày và xuất CSV; giữ các cột tiếng Việt như tệp *_source.csv. Lịch CPI cần giữ “Ngày Phát Hành” và “Thực tế”; không lấy dự báo thay số thực tế.
2. World Bank: xuất GDP NY.GDP.MKTP.CD của Việt Nam, chuẩn hóa Year/GDP_in_USD; chỉ giữ năm trước năm cutoff.
3. Simply Wall St: mở mục định giá ngành công nghệ, chọn lịch sử 10Y và bảng Data; lưu Date, Market Cap, PE, Absolute PE. Không gọi đây là dữ liệu ngành theo ngày nếu nguồn chỉ có snapshot.
4. Báo cáo FPT: có thể xuất báo cáo kết quả kinh doanh quý qua giao diện Finance/income_statement của phiên bản vnstock hỗ trợ hoặc API tài chính tương ứng của bản đã cài. Giữ nhãn nguồn trong fpt_income_statement_source.csv; không đoán cách ánh xạ khi schema API thay đổi. Lịch sử cổ phiếu lưu hành được ghi từ công bố FPT và lưu URL bên cạnh giá trị.
5. Chạy lại fetch_supplemental.py, xem audit ngày/đơn vị/missing, rồi prepare/train. Script chuẩn hóa không tự vượt đăng nhập, giới hạn API hoặc tải lại website; phần xuất CSV có thể cần thao tác của người thu thập.

Trong lần cắt này, 7 hàng tỷ giá, 31 hàng vàng, 1 hàng CPI, 1 snapshot ngành và 1 dòng GDP dự báo ngoài phạm vi đã bị loại khỏi các tệp nguồn. Những hàng đó có thể tải lại tại nguồn nếu mở rộng một nghiên cứu khác; không còn đi vào mô hình của nghiên cứu này.

Tải mới riêng chỉ số thị trường (sau đó pipeline sẽ chuẩn hóa snapshot):

```bash
python src/fetch_supplemental.py --download-market --from-cache --end 2025-09-30
```

API: `https://api.dnse.com.vn/chart-api/v2/ohlcs/index`, `symbol=VNINDEX`, `resolution=1D`. Bộ kiểm định yêu cầu các mảng giá/khối lượng/thời gian cùng độ dài, không trùng ngày, giá hữu hạn và dương. Giữ giá VN-Index theo **điểm**, không áp phép đổi giá cổ phiếu sang nghìn VND. Nguồn có 4.635 quan sát trong khi FPT có 4.671; ghép theo ngày có hiệu lực và hạn 10 ngày, không giả định hai lịch hoàn toàn giống nhau.
