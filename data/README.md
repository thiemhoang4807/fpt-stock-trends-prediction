# Sổ tay nguồn và xử lý dữ liệu FPT đến 30/09/2025

## 1. Nguồn và phạm vi

Dự án dùng snapshot (bản chụp dữ liệu đã cố định) để tái lập thí nghiệm. Giai đoạn của chuỗi giá là 02/01/2007–30/09/2025. Giai đoạn so sánh các thí nghiệm ngắn hơn vì các bản nguồn bổ trợ chưa thu thập đủ lịch sử từ năm 2007. Ngày đầu của snapshot không phải ngày đầu nhà cung cấp có dữ liệu. Vàng từ 2019, CPI cuối 2018 và GDP từ 2010 là giới hạn bản lưu hiện có, không phải bằng chứng không có số liệu sớm hơn.

Đọc [hướng dẫn kiểm tra và bổ sung dữ liệu](../docs/HUONG_DAN_KIEM_TRA_VA_BO_SUNG_DU_LIEU.md), [EDA và công thức](../docs/EDA_VA_DAC_TRUNG.md) và [cẩm nang dùng chung](../docs/CAM_NANG_HIEU_DU_AN.md).

| Dữ liệu | Nguồn tài chính | Cách lấy và tệp nguồn | Phạm vi snapshot sau cắt |
|---|---|---|---|
| OHLCV FPT | VCI/Vietcap qua vnstock | Quote.history; data/raw/fpt/fpt_historical_price.csv | 4.671 phiên, 02/01/2007–30/09/2025 |
| USD/VND | Investing.com | Xuất CSV lịch sử; supplemental/usd_vnd_source.csv | 4.893 quan sát, 01/01/2007–30/09/2025 |
| Vàng XAU/USD | Investing.com | Xuất CSV lịch sử; supplemental/gold_xauusd_source.csv | 1.755 quan sát, 01/01/2019–30/09/2025 |
| CPI Việt Nam | Investing.com, lịch công bố số liệu GSO | Chép/xuất bảng lịch kinh tế; supplemental/vietnam_cpi_source.csv | 81 lần công bố, 27/12/2018–06/09/2025 |
| GDP Việt Nam | World Bank, NY.GDP.MKTP.CD | Xuất CSV GDP danh nghĩa USD theo năm; supplemental/vietnam_gdp_source.csv | 15 năm, 2010–2024; loại dự báo năm 2025 |
| VN-Index | DNSE API chỉ số | supplemental/vnindex_source.csv; tải tự động bằng --download-market | 4.635 phiên, 02/01/2007–30/09/2025; đơn vị điểm |
| Báo cáo tài chính FPT | VCI qua vnstock | Báo cáo kết quả kinh doanh quý; supplemental/fpt_income_statement_source.csv | 52 kỳ từ 2007-Q1 đến 2025-Q2; thiếu giai đoạn 2007-Q3–2012-Q4 |
| Số cổ phiếu lưu hành | Công bố và báo cáo thường niên FPT | Trích chỉ tiêu và ngày có thể biết; supplemental/fpt_shares_outstanding.csv | 10 mốc, báo cáo cuối 2017 đến tăng vốn tháng 7/2025 |

Các tệp dưới supplemental/ đều nằm trong data/raw/. Các lần thu thập trước lưu CSV nguồn và trích công bố cổ phiếu từ FPT, sau đó chuẩn hóa. Đợt cập nhật tài liệu này chỉ kiểm tra, không tải lại hoặc thay các giá trị nguồn. Các bản xuất vĩ mô/tài chính được tái dùng để giữ khả năng tái lập; riêng VN-Index đã được tải trực tiếp từ API DNSE trong đợt nâng cấp. Hash và thông tin truy xuất nằm trong `data/raw/supplemental/vnindex_lineage.json`.

Nguồn trực tiếp và mô tả công cụ:

- [Dữ liệu thị trường Vnstock](https://vnstocks.com/docs/vnstock/thi-truong-market).
- [USD/VND lịch sử](https://vn.investing.com/currencies/usd-vnd-historical-data), [XAU/USD lịch sử](https://vn.investing.com/currencies/xau-usd-historical-data), [lịch CPI Việt Nam](https://vn.investing.com/economic-calendar/vietnamese-cpi-1851).
- [GDP danh nghĩa Việt Nam của World Bank](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=VN).
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
                                      | Cấp 1: 32 biến OHLCV/kỹ thuật
                                      | Cấp 2: 38 biến; cấp 3: 43 biến gồm 11 biến bổ trợ
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


Ngày USD/VND và vàng được đọc bằng dd/MM/yyyy; CPI dùng MM/dd/yyyy của tệp xuất. Không dùng một định dạng ngày chung cho mọi nguồn. Vì vậy “09/06/2025” trong CPI là 06/09/2025. Không suy đoán một quy tắc ngày chung cho mọi nguồn.

## 5. Ngày hiệu lực và giới hạn dữ liệu cũ

| Nguồn | Ngày dùng trong mô phỏng | Hạn giữ sau ngày có hiệu lực |
|---|---|---:|
| VN-Index, USD/VND, XAU/USD | Ngày quan sát + 1 ngày lịch | 10 ngày |
| CPI | Ngày công bố ghi trong lịch nguồn + 1 ngày | 65 ngày |
| GDP năm | Cuối năm + 180 ngày, giả định bảo thủ | 550 ngày |
| Báo cáo quý FPT | Cuối quý + 45 ngày, giả định thực nghiệm | 150 ngày |
| Cổ phiếu lưu hành | Ngày công bố/ngày tham chiếu trong CSV + 1 ngày | 550 ngày |

Ghép backward as-of lấy quan sát mới nhất có hiệu lực không muộn hơn phiên đang xử lý. Giá trị chưa công bố giữ thiếu. Sau hạn dùng, giá trị cũng trở lại thiếu thay vì giữ một báo cáo cũ qua nhiều năm. Vì snapshot tài chính có khoảng trống 2007–2013, không dùng báo cáo 2007-Q2 để lấp cả khoảng này.

Ví dụ: 2025-Q2 kết thúc 30/06/2025; giả định 45 ngày cho ngày có hiệu lực 14/08/2025. Báo cáo 2025-Q3 chưa được dùng tại 30/09/2025. CPI công bố 06/10/2025 bị cắt khỏi tệp nguồn. GDP cả năm 2025 bị loại. Cổ phiếu lưu hành 1.703.507.121 từ công bố tăng vốn tháng 7 được dùng từ các phiên sau mốc công bố 01/08/2025, không gán ngược cho năm 2019.

Bảng cổ phiếu là lịch sử các điểm gần nhất đã thu thập, không phải sổ thay đổi cổ phiếu đầy đủ từng ngày. Riêng báo cáo cuối 2017 dùng mốc tham chiếu bảo thủ 30/06/2018 khi chưa xác minh được ngày công bố chính xác.

Quy tắc độ trễ ngăn dùng báo cáo trước ngày hiệu lực giả định, nhưng không phục hồi phiên bản báo cáo/GDP từng được công bố trong quá khứ. Giá và báo cáo tài chính điều chỉnh lại vẫn có thể gây thiên lệch. Vì thế đây là mô phỏng căn thời điểm công bố có nêu giả định, chưa phải kho dữ liệu lịch sử theo từng phiên bản hoàn chỉnh.

## 6. Kết quả kiểm toán và cohort so sánh

OHLCV có 0 ô thiếu, 0 ngày trùng, 2 phiên volume bằng 0, 3 hàng quan hệ OHLC bất nhất (17/08/2007, 10/06/2009, 07/12/2009). Các hàng này được giữ và đánh dấu, không âm thầm sửa. Chúng nằm trước cohort so sánh chung 2019–2025.

Số ô thiếu sau ghép lên 4.671 phiên FPT: vàng 2.988, CPI 2.987, GDP 1.110, mỗi chỉ tiêu quý 1.407, cổ phiếu lưu hành 2.859. Không chỉ thiếu đầu chuỗi: tài chính có 1.322 phiên thiếu nội bộ từ 14/01/2008 đến 14/05/2013. Các ô này không được backfill. Bảng ghép vẫn lưu chúng để kiểm toán.

Sau bước tạo chỉ báo, cần thêm 60 phiên giao dịch liên tiếp đủ 43 biến để mọi cửa sổ GRU dùng cùng các ngày. Còn 1.560 hàng, trong đó 1.559 hàng có nhãn và một hàng cuối dành cho dự báo. Chỉ số phiên gốc được giữ khi một chỉ báo không xác định để không nén lỗ hổng thành các phiên liền nhau.

| Tập | Ngày mục tiêu | Mẫu học/chấm log return | Phiên dùng chấm đúng hướng |
|---|---|---:|---:|
| Train 85% | 03/04/2019–21/10/2024 | 1.325 | Không dùng để công bố điểm Test |
| Test 15% | 22/10/2024–30/09/2025 | 234 | 227 phiên đổi giá |

Một mục tiêu log return sinh cả giá và hướng, không có mô hình phân loại riêng. Hướng có dấu −1/0/+1; dự báo 0 tính sai trên phiên thực tế đổi giá. Năm phương pháp chính và ba thí nghiệm dùng cùng ngày; 5-fold TimeSeriesSplit, gap=1, chỉ nằm trong Train. XGBoost giữ cùng tham số ở cấp 32/38/43 biến. Chọn mô hình bằng CV RMSE log return. Ranh giới và kế hoạch tại `reports/training_summary.json`, `reports/experiment_plan.json`.

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
3. Báo cáo FPT: có thể xuất báo cáo kết quả kinh doanh quý qua giao diện Finance/income_statement của phiên bản vnstock hỗ trợ hoặc API tài chính tương ứng của bản đã cài. Giữ nhãn nguồn trong fpt_income_statement_source.csv; không đoán cách ánh xạ khi schema API thay đổi. Lịch sử cổ phiếu lưu hành được ghi từ công bố FPT và lưu URL bên cạnh giá trị.
4. Chạy lại fetch_supplemental.py, xem audit ngày/đơn vị/missing, rồi prepare/train. Script chuẩn hóa không tự vượt đăng nhập, giới hạn API hoặc tải lại website; phần xuất CSV có thể cần thao tác của người thu thập.

Trong lần cắt này, 7 hàng tỷ giá, 31 hàng vàng, 1 hàng CPI và 1 dòng GDP dự báo ngoài phạm vi đã bị loại khỏi các tệp nguồn. Những hàng đó có thể tải lại tại nguồn nếu mở rộng một nghiên cứu khác; không còn đi vào mô hình của nghiên cứu này.

Tải mới riêng chỉ số thị trường (sau đó pipeline sẽ chuẩn hóa snapshot):

```bash
python src/fetch_supplemental.py --download-market --from-cache --end 2025-09-30
```

API: `https://api.dnse.com.vn/chart-api/v2/ohlcs/index`, `symbol=VNINDEX`, `resolution=1D`. Bộ kiểm định yêu cầu các mảng giá/khối lượng/thời gian cùng độ dài, không trùng ngày, giá hữu hạn và dương. Giữ giá VN-Index theo **điểm**, không áp phép đổi giá cổ phiếu sang nghìn VND. Nguồn có 4.635 quan sát trong khi FPT có 4.671; ghép theo ngày có hiệu lực và hạn 10 ngày, không giả định hai lịch hoàn toàn giống nhau.

## 8. Ý nghĩa, mục đích của các biến và ngày đầu dùng được

Năm cột OHLCV số được giữ dưới tên `current_open/high/low/close/volume`. Giá mở cửa so với close hôm trước cho biết khoảng nhảy mở cửa; high/low mô tả biên độ; close mô tả trạng thái cuối phiên và dùng để tính lợi nhuận; volume mô tả mức hoạt động giao dịch. `time` là khóa ngày, không phải một trong 32 đầu vào số. Thêm 23 chỉ báo và 4 biến nến tạo đủ 32 biến; công thức và lý do sử dụng từng biến nằm ở [EDA và đặc trưng](../docs/EDA_VA_DAC_TRUNG.md).

| Biến bổ trợ | Câu hỏi muốn thử nghiệm bằng biến này | Phiên FPT đầu có giá trị | Tổng thiếu / thiếu nội bộ |
|---|---|---|---:|
| `vnindex_return_1d` | Thị trường chung gần đây tăng hay giảm? | 04/01/2007 | 7 / 5 |
| `vnindex_volatility_20d` | Thị trường đang yên hay dao động mạnh? | 31/01/2007 | 26 / 5 |
| `usd_vnd_rate` | Điều kiện tỷ giá có liên quan biến động FPT không? | 02/01/2007 | 0 / 0 |
| `gold_vnd_per_ounce` | Một thị trường tài sản khác có thêm thông tin không? | 02/01/2019 | 2.988 / 0 |
| `cpi_yoy_pct` | Môi trường lạm phát có thêm thông tin không? | 28/12/2018 | 2.987 / 0 |
| `gdp_usd` | Quy mô kinh tế dài hạn có hữu ích cho dự báo ngày không? | 29/06/2011 | 1.110 / 0 |
| `fpt_net_revenue_vnd` | Quy mô bán hàng/dịch vụ sau giảm trừ là bao nhiêu? | 15/05/2007 | 1.407 / 1.322 |
| `fpt_gross_profit_vnd` | Sau trừ giá vốn còn bao nhiêu lợi nhuận? | 15/05/2007 | 1.407 / 1.322 |
| `fpt_ebit_vnd` | Kết quả trước lãi vay và thuế theo quy tắc của dự án ra sao? | 15/05/2007 | 1.407 / 1.322 |
| `fpt_parent_net_profit_vnd` | Phần lãi sau thuế thuộc cổ đông công ty mẹ là bao nhiêu? | 15/05/2007 | 1.407 / 1.322 |
| `fpt_shares_outstanding` | Quy mô vốn/cổ phiếu đã thay đổi thế nào? | 02/07/2018 | 2.859 / 0 |

Tất cả các biến còn giá trị hợp lệ ở phiên cuối 30/09/2025, nhưng không có nghĩa đều có quan sát nguồn mới ngày đó. Ngày 30/09 vẫn dùng báo cáo quý II, GDP năm 2024 và CPI công bố 06/09. Những câu hỏi trong bảng là giả thuyết để kiểm tra; không cài trước quy tắc như “CPI tăng thì giá FPT giảm”.

Doanh thu là giá trị được ghi nhận theo kế toán, không mặc định là tiền mặt đã thu. Lợi nhuận gộp = doanh thu thuần − giá vốn, chưa trừ mọi chi phí. Lợi nhuận sau thuế hợp nhất còn bao gồm phần của cổ đông không kiểm soát; cột mô hình chỉ lấy phần thuộc cổ đông công ty mẹ. Cổ phiếu lưu hành là số cổ phiếu tại mốc quan sát, khác volume giao dịch một ngày. Hiện code dùng mức giá trị quý/năm, chưa biến chúng thành tăng trưởng quý, biên lợi nhuận hoặc EPS.

## 9. Chi tiết thao tác chuẩn hóa nguồn

### 9.1. Bản xuất tỷ giá/vàng và CPI

Investing.com cho phép xem theo ngày/tuần/tháng; phải chọn **ngày** cho tỷ giá/vàng. Tệp hiện tại có `Ngày` theo ngày/tháng/năm và `Lần cuối` dùng dấu phẩy phân cách nghìn: `3,833.93` thành `3833.93`. Nếu giao diện xuất tên cột tiếng Anh hoặc dấu thập phân khác, cần ánh xạ trước; không chỉ đổi tên tệp rồi chạy parser.

CPI dùng `Ngày Phát Hành` và `Thực tế`. Giữ bản xuất gốc để đối chiếu cột dự báo/trước đó, nhưng không dùng dự báo làm đáp án. Chuỗi `3.24%` thành số `3.24`; không chia 100 trong cột `cpi_yoy_pct`. CPI hiện chưa có trường riêng cho **tháng số liệu**; phải bổ sung khi đối chiếu tính đầy đủ. Một tháng không có lần công bố chưa chứng minh mất một tháng số liệu, vì lịch công bố có thể chuyển sang đầu tháng sau.

Bộ chuẩn hóa tự bỏ hàng không đọc được ngày hoặc mọi cột số đều thiếu, sắp thời gian và giữ dòng cuối khi trùng ngày. Đây là lý do phải kiểm tra bản nguồn **trước chuẩn hóa**, không chỉ bảng sau khi đã bỏ hàng. Lưu số hàng trước/sau và giải trình bản ghi bị loại; không dùng quy tắc giữ dòng cuối để giải quyết hai số mâu thuẫn chưa xác minh.

### 9.2. GDP và báo cáo quý

CSV tải từ World Bank có thể có siêu dữ liệu và các năm trải thành nhiều cột; cần chuyển về `Year,GDP_in_USD`, một hàng một năm. Không tự gán tên đó cho một chuỗi “GDP growth” hoặc GDP giá cố định. Trang nguồn hiện có lịch sử trước 2010; muốn mở rộng dự án phải lấy thêm các năm cũ và ghi lại phiên bản tải, không chỉ kéo dài số 2010 về quá khứ.

Đối với báo cáo FPT, chọn báo cáo hợp nhất theo quý, kiểm tra VND/triệu VND/tỷ VND và số riêng quý/lũy kế. Các cột parser thực sự đọc:

| Cột bản xuất | Kết quả chuẩn hóa |
|---|---|
| `Năm`, `Kỳ` | `time` là ngày cuối quý |
| `Doanh thu thuần` | `fpt_net_revenue_vnd` |
| `Lãi gộp` | `fpt_gross_profit_vnd` |
| `LN trước thuế`, `Chi phí tiền lãi vay` | `fpt_ebit_vnd` theo công thức đã mô tả |
| `Lợi nhuận sau thuế của Cổ đông công ty mẹ (đồng)` | `fpt_parent_net_profit_vnd` |

Schema API/phiên bản thư viện có thể khác. Dự án pin vnstock 5.1.0; tài liệu website có thể đã hướng dẫn phiên bản mới hơn. Script `--from-cache` chỉ đọc các bản xuất, không tự đăng nhập và lấy lại toàn bộ báo cáo.

### 9.3. Cổ phiếu lưu hành

Tệp có `time, fpt_shares_outstanding, period_end, availability_basis, source_url`. `period_end` là mốc số liệu nói đến; `time` là mốc công bố/tham chiếu dùng để ghép. `availability_basis` ghi căn cứ hoặc giả định, `source_url` cho phép kiểm chứng. Cần đọc công bố phát hành/mua cổ phiếu quỹ để bổ sung sự kiện giữa hai báo cáo năm; không lấy số đang lưu hành hiện tại để điền mọi ngày cũ.

### 9.4. Ví dụ ghép nguồn khác tần suất

| Phiên đầu vào FPT | Số được phép dùng theo quy tắc hiện tại |
|---|---|
| 27/06/2025 | Chưa dùng GDP 2024 vì 31/12/2024 + 180 ngày = 29/06/2025 |
| 30/06/2025 | Phiên đầu sau ngày hiệu lực GDP 2024; dùng 476.388.230.307,18 USD |
| 13/08/2025 | Chưa dùng báo cáo quý II vì ngày hiệu lực là 14/08 |
| 14/08/2025 | Bắt đầu dùng doanh thu quý II 16.624.713.040.067 VND |
| 30/09/2025 | USD/VND 26.421 và XAU/USD 3.833,93 của ngày 29/09; vàng quy đổi 101.296.264,53 VND/ounce |

Tuổi dữ liệu tính từ ngày hiệu lực, bằng ngày lịch. Giá trị được dùng ở đúng giới hạn tuổi và trở lại thiếu khi vượt ngưỡng. Quy tắc tuổi là lựa chọn kỹ thuật, không phải luật rằng dữ liệu kinh tế “hết giá trị” đúng ngày đó. Không chia doanh thu quý cho 90 để tạo doanh thu ngày; không nối đường thẳng giữa hai quý vì sẽ dùng số tương lai.

## 10. Kiểm toán bổ sung: còn vấn đề nào?

Chạy `python src/audit_data_quality.py` để tạo [data_quality_review.json](../reports/data_quality_review.json). Lệnh này chỉ đọc nguồn và bảng ghép, ghi báo cáo riêng; không sửa dữ liệu hoặc mô hình.

- Tám bảng nguồn chuẩn dùng cho mô hình đều đọc được ngày, không trùng ngày và không có ô trống tại các hàng đã lưu. Điều này không phát hiện được mất cả hàng nếu chỉ nhìn `isna()`.
- FPT có 3 bất nhất OHLC và 2 phiên volume bằng 0 (23–24/01/2018). Cần kiểm chứng nguồn/lịch giao dịch trước khi quyết định sửa; không tự gán volume bằng 0 là lỗi.
- VN-Index không có dòng tại **36 ngày có trong FPT**; có **17 đoạn** mà return giữa hai quan sát nguồn trải qua nhiều ngày FPT. `vnindex_return_1d` ở các đoạn đó không còn đúng nghĩa một phiên. Ghép giữ giá trị cũ làm nhiều lỗ không hiện thành ô thiếu; 5 phiên 01–05/02/2021 vẫn thiếu sau giới hạn tuổi. Phải sửa nguồn rồi tính lại return, không điền giá lặp để ép return bằng 0.
- Báo cáo quý thiếu 22 quý. Ba đẳng thức số học về doanh thu, lợi nhuận gộp và phân bổ lợi nhuận sau thuế khớp ở cả 52 hàng đang có; chưa đối chiếu từng hàng với PDF gốc.
- Vàng/CPI chưa thu thập lịch sử sớm, GDP trước 2010 chưa có trong bản lưu. Cổ phiếu lưu hành chỉ có 10 mốc; lịch ngày công bố và số liệu hồi tố chưa được xác minh đầy đủ.

Vì thế báo cáo hiện tại là thực nghiệm trên snapshot với các giới hạn đã biết. Kế hoạch tìm nguồn và quy trình nghiệm thu nằm trong [hướng dẫn bổ sung](../docs/HUONG_DAN_KIEM_TRA_VA_BO_SUNG_DU_LIEU.md). Khi thay dữ liệu phải chạy lại đặc trưng, đánh giá và cập nhật metric; không dùng bảng điểm hiện có để mô tả một dataset đã sửa.
