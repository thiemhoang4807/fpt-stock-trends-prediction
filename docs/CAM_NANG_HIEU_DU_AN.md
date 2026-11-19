# Cẩm nang hiểu và thuyết trình dự án FPT

Mỗi mô hình dự báo **một số duy nhất, log return của cổ phiếu FPT ở phiên kế tiếp**. Từ số đó, nhóm suy ra giá đóng cửa và hướng tăng, giảm hoặc đứng giá. Năm phương pháp chính là Last-Close, Ridge, XGBoost, ARIMA và GRU.

Phần 0–2 giải thích đường đi từ dữ liệu gốc đến đặc trưng. Phần 3–6 giải thích cách học và chấm điểm. Phần 7–9 theo dõi một phiên thật, phân tích ca lỗi và ôn vấn đáp. Các ví dụ giả định dùng số tròn, còn kết quả thực nghiệm lấy từ `reports/`. [Sổ tay dữ liệu](../data/README.md) · [EDA và đặc trưng](EDA_VA_DAC_TRUNG.md)

## Kịch bản thuyết trình 10 phút

Mở sẵn các hình và báo cáo trước giờ trình bày. Dùng notebook 04 để minh họa phép tính trên một phiên hoặc notebook 05 để trình bày cách chia tập khi có câu hỏi.

| Người / thời gian | Bước câu chuyện | Mở tài liệu | Câu cần nói và con số cần nhớ |
|---|---|---|---|
| Hoàng, 0:00–0:50 | Bài toán | [Sơ đồ pipeline](../figures/00_pipeline_overview.png) | Sau khi phiên hôm nay đóng cửa, nhóm dự báo log return cho phiên sau. Với giá hiện tại 100 và dự báo ln(1,01), giá dự báo là 101 và hướng là Tăng. |
| Hoàng, 0:50–2:00 | Dữ liệu | [Sổ tay dữ liệu](../data/README.md) · [Notebook 02](../notebooks/02_fetch_supplemental.ipynb) | Tập chung có 3.031 nhãn từ 2013. Ba cấu hình dùng 32, 38 và 42 biến. Dữ liệu thị trường ngày dùng từ ngày lịch kế tiếp. Báo cáo quý và CPI/GDP năm dùng với độ trễ giả định 45 và 180 ngày. |
| Dũng, 2:00–3:00 | Chuỗi thời gian | [ACF/PACF](../figures/12_acf_pacf.png) | Trên log return, ADF bác bỏ nghiệm đơn vị. KPSS bác bỏ dừng mức ở ngưỡng 5%, với p ≈ 0,0338. |
| Dũng, 3:00–4:15 | Năm phương pháp | [Báo cáo](REPORT.md) | Last-Close giữ nguyên giá. Ridge cộng tín hiệu có trọng số. XGBoost ghép các cây lần lượt sửa lỗi. ARIMA dự báo từ chuỗi lợi nhuận. GRU học thông tin cần nhớ qua 20 hoặc 60 phiên. |
| Dũng, 4:15–5:15 | Đánh giá | [Notebook 05](../notebooks/05_prepare.ipynb) | Train 2.576 mẫu, Test 455 mẫu. Chọn bằng 5 lượt kiểm định trong Train, mỗi lượt chừa một hàng giữa phần học và phần chấm. |
| Duy, 5:15–8:10 | Ba thí nghiệm | [Bảng chính](../figures/main_benchmark_metrics.png) · [Thêm dữ liệu](../figures/ablation_metrics.png) · [Bộ nhớ GRU](../figures/lookback_metrics.png) | ARIMA có RMSE log return CV thấp nhất, 0,015860. XGBoost 38 biến đúng 242/440 hướng, so với 233/440 của bộ 32, nhưng MAE giá cao hơn. CV chọn GRU 60 phiên với chênh lệch RMSE nhỏ. |
| Duy, 8:10–10:00 | Giải thích và ca lỗi | [Permutation](../figures/permutation_importance.png) · [Ca lỗi](../reports/error_cases.csv) | Tỷ lệ giá so với EMA 10 phiên đứng đầu khi tráo từng biến. Ngày 03/04/2025 FPT giảm 6,97%, ARIMA dự báo tăng 0,10%. |

Có 9 cấu hình đem chấm Test gồm Last-Close, Ridge, 3 bộ biến XGBoost, ARIMA, SARIMAX và 2 cửa sổ GRU. Các bảng dùng lại một số cấu hình chung. Ngoài 9 tệp đánh giá, nhóm lưu thêm một bản ARIMA học lại để dự báo sau phiên 30/09/2025.

Nếu chỉ có 5 phút, giữ một câu cho mỗi bước, một bảng chính và một ca lỗi. Nếu có 15 phút, mở thêm notebook 04 để tính log return và notebook 05 để minh họa chia thời gian.

## 0. Học máy ở đây thật sự học điều gì?

Một hàng dữ liệu giống một phiếu bài tập. “Đầu vào” là những số đã biết khi hôm nay đóng cửa; “nhãn” là đáp án của ngày sau, chỉ biết khi ngày sau đã diễn ra. Máy xem nhiều phiếu quá khứ để tìm quy tắc, rồi dùng quy tắc đó cho một phiếu mới.

`t` là phiên hôm nay; `t+1` là phiên giao dịch kế tiếp. `C_t` là giá đóng cửa hôm nay. Dấu mũ như `r̂` nghĩa là dự báo chứ không phải số thật.

    r(t+1) = ln[C(t+1) / C(t)]

`ln` là logarithm tự nhiên. Không cần nhẩm logarithm để sử dụng mô hình: máy tính tính được. Tỷ số bằng 1 cho ln bằng 0; lớn hơn 1 cho ln dương; nhỏ hơn 1 cho ln âm. Phép `exp` đảo ngược `ln`.

Ví dụ giá hôm nay 100, mai thật sự 101:

    Tỷ số = 101/100 = 1,01
    Simple return = 1,01 − 1 = 0,01 = 1%
    Log return = ln(1,01) ≈ 0,00995033
    Đảo lại: 100 × exp(0,00995033) ≈ 101

Dự báo `r̂ = 0,00995033` đồng thời cho giá 101 và hướng Tăng. Dự báo `ln(0,99) ≈ −0,01005034` cho giá 99 và hướng Giảm. Dự báo 0 cho giá 100 và hướng Đứng giá. **Log return không phải xác suất**: 0,01 không có nghĩa “1% khả năng tăng” hoặc “99% chắc chắn”.

Phép exp luôn dương nên công thức cho giá dương khi giá hiện tại dương. Dấu của log return trùng dấu thay đổi giá. Hai đầu ra vì thế nhất quán: không xảy ra chuyện bộ phân loại đoán Tăng nhưng bộ hồi quy riêng lại đoán giá thấp hơn hôm nay.

## Phần 1. Dữ liệu và tài chính cho người mới

### 1.1. Sáu cột giao dịch FPT

Một phiên là một ngày thị trường có giao dịch. “Phiên kế tiếp” không nhất thiết là ngày lịch tiếp theo: sau thứ sáu có thể là thứ hai, và còn có ngày nghỉ lễ.

Nguồn giá là Vietcap (VCI), được lấy qua `vnstock` bằng `Quote(symbol="FPT", source="VCI").history(..., interval="1D")`. Khi chạy lại thí nghiệm, dùng `python src/fetch_data.py --verify` để đối chiếu bản giá đã lưu. Script cũng có thể chuẩn hóa CSV xuất từ nhà cung cấp. Khả năng truy vấn trực tuyến phụ thuộc phiên bản `vnstock` và kết nối của nguồn. [Hướng dẫn dữ liệu](../data/README.md)

File chuẩn là data/raw/fpt/fpt_historical_price.csv:

| Cột | Đọc bằng ngôn ngữ đời thường | Kiểu/đơn vị | Ví dụ thật 29/09/2025 |
|---|---|---|---:|
| time | Ngày của phiên giao dịch | Ngày YYYY-MM-DD | 2025-09-29 |
| open | Giá mở cửa của phiên | Nghìn VND/cổ phiếu | 86,79750 |
| high | Giá cao nhất trong phiên | Nghìn VND/cổ phiếu | 86,79750 |
| low | Giá thấp nhất trong phiên | Nghìn VND/cổ phiếu | 84,75625 |
| close | Giá đóng cửa của phiên | Nghìn VND/cổ phiếu | 84,75625 |
| volume | Số cổ phiếu được giao dịch trong phiên theo nguồn | Cổ phiếu | 10.430.900 |

Close 84,75625 tương đương 84.756,25 đồng trên thang giá lịch sử của snapshot. Volume 10.430.900 là hơn mười triệu cổ phiếu, không phải số tiền giao dịch.

Snapshot lưu 4.671 hàng giá, từ 02/01/2007 đến 30/09/2025. Kiểm toán ghi nhận:

- Không có ô thiếu và không có ngày trùng.
- Hai hàng volume bằng 0 rơi vào ngày HOSE đóng cửa 23–24/01/2018. Pipeline loại hai ngày này trước khi tính biến và nhãn.
- Có 3 dòng OHLC bất nhất: 17/08/2007, 10/06/2009, 07/12/2009. Chúng được giữ và liệt kê trong audit, không âm thầm sửa bằng suy đoán.
- 2.118 chuyển tiếp tăng, 2.074 giảm, 476 đứng giá. Tổng 4.668 sau loại hai ngày HOSE đóng cửa vì phiên cuối không có giá phiên kế tiếp trong snapshot để gán nhãn.
- Trung bình lợi nhuận ngày khoảng 0,0644%, độ lệch chuẩn khoảng 1,9193%.

“Bất nhất OHLC” chẳng hạn là high thấp hơn close hoặc low cao hơn open. Việc một dòng có số dương không bảo đảm các mối quan hệ giữa bốn giá đều đúng. Audit cho người đọc thấy điều này. Cohort thực nghiệm chung bắt đầu năm 2013 nên ba dòng lỗi cũ này không đi vào phần Train/Test hiện tại.

### 1.2. Giá lịch sử có thể đã được điều chỉnh

Các nguồn có thể điều chỉnh lại giá quá khứ khi công ty chia cổ phiếu thưởng, trả cổ tức bằng cổ phiếu hoặc có sự kiện doanh nghiệp. Ví dụ một cổ phiếu bị chia thành hai cổ phiếu không đồng nghĩa tài sản của cổ đông bỗng mất một nửa; chuỗi giá thường cần được điều chỉnh để dễ so sánh.

Dự án giữ thang giá của VCI. Archive lịch sử từng được căn cùng thang với một đoạn giá mới bằng hệ số 0,8875 trên các ngày chồng lấn; volume không nhân hệ số này. Vì vậy không nên gọi dữ liệu đang dùng là “giá khớp lệnh chưa điều chỉnh của thời điểm lịch sử”. Những số lẻ ở giá cũ có thể là hệ quả của điều chỉnh, không có nghĩa sàn đã cho khớp lệnh tại đúng mọi mức lẻ đó.

reports/data_lineage.json lưu nguồn, các bước điều chỉnh và mã băm. Mã băm là chuỗi nhận diện nội dung file: cùng nội dung tạo cùng mã, giúp kiểm tra có đang dùng đúng bản dữ liệu hay không.

Một giới hạn quan trọng: dùng các cột đúng thời điểm vẫn chưa tự động phục dựng được “bản dữ liệu mà nhà đầu tư thực sự nhìn thấy vào năm đó”. Giá và GDP có thể đã được nhà cung cấp sửa lại sau này. Tài liệu phải phân biệt chống nhìn trước bằng cách ghép ngày với việc có đủ mọi phiên bản công bố lịch sử.

### 1.3. Tại sao không còn chỉ dùng close và volume?

Phiên bản hiện tại **đã dùng open, high, low**. Ba cấp dữ liệu trong thí nghiệm thêm nguồn là:

| Cấp dữ liệu | Đầu vào | Số biến |
|---|---|---:|
| Giá và kỹ thuật | 23 chỉ báo từ close/volume + 4 đặc trưng nến + 5 số OHLCV hiện tại | 32 |
| Thêm thị trường/vĩ mô | 32 biến giá/kỹ thuật + 2 chỉ báo VN-Index, USD/VND, vàng, CPI, GDP | 38 |
| Thêm tài chính FPT | Toàn bộ 32 biến giá/kỹ thuật + 10 biến thị trường/vĩ mô/tài chính | 42 |

Năm cột giá hiện tại được đặt tên current_open, current_high, current_low, current_close, current_volume. Chúng là dữ liệu phiên t, đã biết khi phiên t đóng cửa. Bốn đặc trưng nến giúp mô hình đọc hình dạng của phiên: dao động rộng hay hẹp, đóng cửa cao hay thấp so với mở cửa, có nhảy giá khi mở cửa không, đóng cửa nằm gần đỉnh hay đáy.

Việc chỉ bắt đầu từ close/volume có ưu điểm dễ giải thích, nhưng đó không còn là toàn bộ đầu vào của bản hiện tại. Không nên thuyết trình rằng dự án “bỏ open/high/low”.

### 1.4. Thị trường, vĩ mô, tài chính doanh nghiệp và kỹ thuật khác nhau ra sao?

Hãy hình dung bốn nhóm thông tin:

- Thị trường chung là những gì đang xảy ra trên sàn nói chung, được mô tả ở đây bằng VN-Index.
- Vĩ mô là điều kiện của cả nền kinh tế: giá cả, quy mô sản xuất, tỷ giá.
- Vi mô/cơ bản doanh nghiệp là hoạt động kinh doanh và cấu trúc vốn của riêng FPT.
- Kỹ thuật là những gì rút ra trực tiếp từ đường giá và khối lượng giao dịch.

| Biến | Ý nghĩa đơn giản | Đừng nhầm với |
|---|---|---|
| USD/VND | Cần bao nhiêu VND để đổi 1 USD | Lợi nhuận của FPT |
| CPI | Chỉ số giá của một giỏ hàng hóa/dịch vụ tiêu dùng | Mức giá cổ phiếu |
| CPI YoY | Giá tiêu dùng tăng bao nhiêu phần trăm so với cùng kỳ năm trước | CPI gốc hoặc mức tăng tháng này so với tháng trước |
| GDP danh nghĩa bằng USD | Tổng giá trị sản phẩm/dịch vụ của nền kinh tế tính theo giá hiện hành, quy đổi USD | Tốc độ tăng GDP thực theo phần trăm |
| Vàng quy đổi VND | Giá vàng quốc tế USD/ounce nhân tỷ giá VND/USD | Giá vàng miếng SJC hoặc giá một lượng vàng trong nước |
| VN-Index | Chỉ số phản ánh biến động chung của nhóm cổ phiếu trong chỉ số trên HOSE, có đơn vị điểm | Giá của một cổ phiếu hoặc số tiền VND |
| Doanh thu thuần | Tiền bán hàng/dịch vụ sau các khoản giảm trừ doanh thu | Tiền lãi ròng |
| Lợi nhuận gộp | Doanh thu thuần trừ chi phí trực tiếp tạo sản phẩm/dịch vụ | Lợi nhuận cuối cùng sau mọi chi phí |
| EBIT | Lợi nhuận trước chi phí lãi vay và thuế | Lợi nhuận sau thuế hoặc mặc nhiên bằng dòng “lợi nhuận hoạt động” |
| LNST cổ đông công ty mẹ | Phần lãi sau thuế thuộc về cổ đông của công ty mẹ | Toàn bộ lãi hợp nhất gồm cả phần cổ đông không kiểm soát |
| Cổ phiếu lưu hành | Số cổ phiếu thuộc cổ đông, loại cổ phiếu quỹ theo định nghĩa nguồn | Volume giao dịch trong một ngày |

Ví dụ doanh thu thuần 100 đồng, giá vốn 60 đồng thì lợi nhuận gộp là 40 đồng. Nếu tiếp tục chi 20 đồng cho bán hàng/quản lý, 3 đồng lãi vay và 4 đồng thuế thì tiền lãi cuối cùng khác rất nhiều 40 đồng ban đầu. Mỗi dòng báo cáo trả lời một câu hỏi khác nhau.

Trong code hiện tại, EBIT được tính theo định nghĩa:

    EBIT = Lợi nhuận trước thuế + trị tuyệt đối chi phí lãi vay

Nguồn lưu chi phí lãi vay dưới dạng số âm, nên cần lấy trị tuyệt đối trước khi cộng. Với quý II/2025:

    3.141.032.584.460 + 216.761.295.705
    = 3.357.793.880.165 VND

Đó là fpt_ebit_vnd. Không lấy nguyên lợi nhuận hoạt động rồi gắn nhãn EBIT.

### 1.5. Dữ liệu bổ trợ từ đâu?

| Nguồn | Phạm vi và quan sát | Cách dùng |
|---|---|---|
| FPT OHLCV, Vietcap qua vnstock | 4.671 hàng lưu, 2007–30/09/2025 | 4.669 phiên sau lọc lịch HOSE. Giá nghìn VND/cổ phiếu, khối lượng tính bằng cổ phiếu. |
| VN-Index, DNSE và CafeF | 4.668 giá đóng cửa sau bổ sung 33 phiên và sửa 16 mức giá | Tính log return và độ biến động 20 phiên. |
| USD/VND, Investing.com | 4.893 quan sát, 2007–30/09/2025 | VND trên một USD. |
| XAU/USD, bản xuất Investing.com | 4.858 giá ngày, 01/01/2007–30/09/2025 | Nhân với tỷ giá để có VND mỗi ounce vàng quốc tế. |
| CPI năm, World Bank WDI `FP.CPI.TOTL.ZG` | 20 năm 2005–2024 | Tỷ lệ lạm phát cả năm, đơn vị %. |
| GDP năm, World Bank WDI `NY.GDP.MKTP.CD` | 20 năm 2005–2024 | GDP danh nghĩa cả năm, USD hiện hành. |
| Kết quả kinh doanh FPT, Vietcap qua vnstock | 50 quý liên tục 2013Q1–2025Q2 trong phạm vi dùng | Doanh thu thuần, lợi nhuận gộp, EBIT và lợi nhuận sau thuế của cổ đông công ty mẹ. |

Số cổ phiếu lưu hành trong tệp hiện có chỉ bắt đầu khả dụng từ năm 2018, muộn hơn mốc bắt đầu nghiên cứu. Bốn chỉ tiêu kết quả kinh doanh có chuỗi đủ dài để đưa vào bộ 42 biến.

### 1.6. Máy được biết thông tin lúc nào?

Giá VN-Index, USD/VND và vàng được dùng sau một ngày lịch, tối đa 10 ngày từ lúc khả dụng. Báo cáo tài chính dùng theo giả định cuối quý cộng 45 ngày, giữ tối đa 150 ngày. CPI và GDP dùng theo giả định cuối năm cộng 180 ngày, giữ tối đa 550 ngày. Ví dụ số 2024 dùng từ phiên 30/06/2025 theo quy tắc này. Ghép lùi theo thời điểm khả dụng. Số CPI 3,6211 được hiểu là 3,6211%. Các ngày công bố và phiên bản số liệu lịch sử chưa xác minh đầy đủ.

Ví dụ quý II/2025 kết thúc 30/06. Máy vẫn dùng báo cáo quý trước vào 13/08 nếu còn hạn. Từ 14/08 mới được chuyển sang số quý II theo giả định. Một số báo cáo được giữ trên nhiều hàng theo ngày, nhưng vẫn chỉ có một con số của quý đó. Các biến năm cũng hoạt động như vậy.

### 1.7. Từng cột dùng làm gì?

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

Ví dụ nếu XAU/USD là 3.833,93 USD/ounce và USD/VND là 26.421 VND/USD thì giá quy đổi là 3.833,93 × 26.421 = 101.296.264,53 VND/ounce. Hai cột đều phải có hiệu lực ở phiên dự báo. Nếu doanh thu thuần là 100 và giá vốn là 70 thì lợi nhuận gộp là 30. Nếu lợi nhuận trước thuế là 20 và lãi vay là 2 thì EBIT theo định nghĩa dự án là 22.

### 1.8. Độ phủ và mốc 2013

Tệp giá lưu 4.671 hàng từ 02/01/2007 đến 30/09/2025. Pipeline bỏ hai ngày HOSE đóng cửa 23–24/01/2018, còn 4.669 phiên. Sau 49 phiên tích lũy cho SMA50, bảng kỹ thuật có 4.620 hàng. Chuỗi chung đủ 42 biến từ 15/05/2013. Phiên đầu vào 06/08/2013 có đủ 60 phiên liên tiếp và được gán nhãn bằng ngày mục tiêu 07/08/2013. Bảng chung có 3.032 hàng gồm 3.031 nhãn và đầu vào 30/09/2025 dành cho dự báo.

Đối chiếu lịch từ năm 2013 cho thấy DNSE thiếu 33 phiên có giao dịch FPT. Dùng giá đóng cửa CafeF cho các phiên thiếu và 16 mức khác nhau trong các khoảng đối chiếu năm 2020. Báo cáo phiên của các công ty chứng khoán xác nhận các mức CafeF được kiểm tra chéo, như 869,91 điểm ngày 15/07/2020 và 903,98 điểm ngày 29/09/2020. Sau hiệu chỉnh, các phiên FPT trong phạm vi từ 2013 đều có giá đóng cửa VN-Index. Hai ngày HOSE đóng cửa được loại khỏi lịch phiên trước khi tính nhãn. [Lịch sử CafeF](https://cafef.vn/du-lieu/lich-su-giao-dich-vnindex-1.chn) · [Bản tin Funan](https://funan.com.vn/en/diem-tin-giao-dich-15072020.409463) · [Xác nhận lịch HOSE](https://baochinhphu.vn/hose-giao-dich-tro-lai-sau-hai-ngay-dong-cua-102233882.htm)

Ngày 30/09/2025 là hàng đầu vào dự báo cuối. Hàng này dùng CPI 2024 là 3,6211%, GDP 2024 khoảng 476,325 tỷ USD và báo cáo FPT quý II/2025. Giá vàng đóng cửa được dùng là 3.833,93 USD/ounce của 29/09. Có thể đối chiếu trực tiếp bằng bảng `data/processed/fpt_multisource_features.csv` và dữ liệu nguồn.

Nếu muốn tìm hiểu tệp gốc, độ trễ và từng bước kiểm tra lỗi, đọc [sổ tay dữ liệu](../data/README.md) và [lịch sử tìm nguồn](DU_LIEU_TU_2007.md).

## Phần 2. Từ giá và volume tạo ra 32 đặc trưng

### 2.1. Ký hiệu trước khi đọc công thức

P(t) là close phiên hiện tại t; P(t−1) là close phiên trước. V(t) là volume. N là số phiên trong một cửa sổ. Dấu chia “/”, cộng “+”, trừ “−”, nhân “×” có ý nghĩa thông thường.

Return 0,02 là tỷ lệ tương ứng mức tăng 2%. Nhân tỷ lệ với 100 để viết theo phần trăm. Riêng cột `cpi_annual_inflation_pct` đã lưu theo đơn vị %, ví dụ 3,6211 tương ứng lạm phát 3,6211%.

Đặc trưng là con số mô hình được nhìn. Nhãn/target là đáp án đúng mô hình cần học. Có đáp án trong bảng để chấm không có nghĩa được đưa đáp án đó vào đầu vào.

### 2.2. Đủ 23 cột kỹ thuật và công thức

| STT | Cột trong code | Công thức/ý nghĩa |
|---:|---|---|
| 1 | return_1d | P(t)/P(t−1) − 1: thay đổi từ phiên trước |
| 2 | return_2d | P(t)/P(t−2) − 1: thay đổi sau 2 phiên |
| 3 | return_5d | P(t)/P(t−5) − 1 |
| 4 | return_10d | P(t)/P(t−10) − 1 |
| 5 | return_20d | P(t)/P(t−20) − 1 |
| 6 | sma_5_ratio | P(t)/SMA5(t) − 1 |
| 7 | sma_10_ratio | P(t)/SMA10(t) − 1 |
| 8 | sma_20_ratio | P(t)/SMA20(t) − 1 |
| 9 | sma_50_ratio | P(t)/SMA50(t) − 1 |
| 10 | ema_5_ratio | P(t)/EMA5(t) − 1 |
| 11 | ema_10_ratio | P(t)/EMA10(t) − 1 |
| 12 | ema_20_ratio | P(t)/EMA20(t) − 1 |
| 13 | ema_50_ratio | P(t)/EMA50(t) − 1 |
| 14 | rsi_14 | RSI14/100; mức tăng gần đây so với mức giảm gần đây |
| 15 | macd_ratio | (EMA12 − EMA26)/P(t) |
| 16 | macd_signal_ratio | EMA9 của đường MACD, sau đó chia P(t) |
| 17 | macd_histogram_ratio | (MACD − đường Signal)/P(t) |
| 18 | bollinger_percent_b_20 | (P(t) − dải dưới)/(dải trên − dải dưới) |
| 19 | bollinger_width_20 | (dải trên − dải dưới)/SMA20 |
| 20 | volatility_5d | Độ lệch chuẩn của 5 return một phiên gần nhất |
| 21 | volatility_20d | Độ lệch chuẩn của 20 return một phiên gần nhất |
| 22 | log_volume_change_1d | log(1+V(t)) − log(1+V(t−1)) |
| 23 | log_volume_zscore_20d | [log(1+V(t)) − trung bình log-volume 20 phiên]/độ lệch chuẩn log-volume 20 phiên |

“Lag return” trong bảng này là thay đổi giữa hiện tại và N phiên trước, không phải nhãn return của tương lai và cũng không nhất thiết là cột return hôm trước được dịch nguyên sang hôm nay.

SMA là trung bình cộng giá trong N phiên gần nhất, gồm phiên t. Ratio dương nghĩa giá hiện tại ở trên mức trung bình, âm nghĩa ở dưới. Ví dụ ratio −0,02 là thấp hơn mức trung bình khoảng 2%.

EMA là trung bình có trọng số ưu tiên giá mới. Nó vẫn chỉ dùng quá khứ và hiện tại. Với chu kỳ N, tỷ trọng cho giá mới là 2/(N+1); phần còn lại cho trung bình cũ. Đây là ý nghĩa của alpha, không phải tham số bí ẩn.

RSI so sánh độ lớn các lần tăng và giảm gần đây. RSI cao nghĩa phần tăng đang mạnh hơn trong lịch sử gần; RSI thấp nghĩa phần giảm đang mạnh hơn. “Quá mua” thường được gọi khi RSI trên 70 và “quá bán” khi dưới 30. Hai mốc này là quy ước mô tả, không bảo đảm phiên kế tiếp đảo chiều. Trong dữ liệu mô hình, 70 được lưu thành 0,70 và 30 thành 0,30.

MACD lấy một đường EMA ngắn trừ một đường EMA dài. Đường Signal là trung bình EMA tiếp theo của chính đường MACD. Histogram là chênh giữa MACD và Signal; dương khi MACD nằm trên Signal. Chia cả ba cho close làm chúng bớt lệ thuộc vào việc cổ phiếu đang có giá 10 hay 100.

Bollinger tạo một “hành lang” quanh SMA20:

    Dải trên = SMA20 + 2 × độ lệch chuẩn của 20 giá close
    Dải dưới = SMA20 − 2 × độ lệch chuẩn của 20 giá close

%B cho biết giá nằm ở đâu trong hành lang. 0 là tại dải dưới, 0,5 ở giữa, 1 tại dải trên. Nó có thể nhỏ hơn 0 hoặc lớn hơn 1 nếu giá ra ngoài dải. Bandwidth đo hành lang rộng bao nhiêu so với trung bình, không đo trực tiếp xác suất giá tăng.

Volatility là độ phân tán của return. Chuỗi giá tăng đều mỗi ngày có thể có volatility nhỏ, dù xu hướng tăng rõ. Chuỗi lúc tăng mạnh lúc giảm mạnh có volatility lớn. Volatility không mang sẵn dấu Tăng/Giảm của ngày sau.

Logarithm, viết log, nén những con số rất lớn lại. Tăng volume từ một triệu lên hai triệu và từ hai triệu lên bốn triệu cùng là nhân đôi; log giúp biểu diễn hai bước này gần nhau về độ lớn. Dùng log(1+V) thay vì log(V) để volume 0 không gây lỗi.

Z-score trả lời “giá trị hiện tại cách mức bình thường bao nhiêu độ lệch chuẩn?”. Nếu trung bình là 100, độ lệch chuẩn 5, giá trị 110 thì z-score = (110−100)/5 = 2. Trong code thực tế áp trên log-volume, không phải trực tiếp 110 cổ phiếu của ví dụ này.

### 2.3. Bốn biến nến và năm biến gốc

| Biến | Công thức | Hiểu bằng hình ảnh |
|---|---|---|
| candle_range_pct | (high−low)/close | Trong ngày giá quét qua khoảng rộng hay hẹp |
| candle_body_pct | (close−open)/open | Từ mở cửa tới đóng cửa tăng hay giảm bao nhiêu |
| overnight_gap_pct | open(t)/close(t−1)−1 | Mở cửa hôm nay đã khác close hôm qua bao nhiêu |
| close_location_in_range | (close−low)/(high−low) | Close nằm gần đáy 0 hay gần đỉnh 1 |
| current_open | open(t) | Giá mở cửa hiện tại |
| current_high | high(t) | Giá cao nhất hiện tại |
| current_low | low(t) | Giá thấp nhất hiện tại |
| current_close | close(t) | Giá đóng cửa hiện tại |
| current_volume | volume(t) | Khối lượng hiện tại |

Nếu high = low, không thể chia cho 0 trong biến vị trí close. Code gán vị trí 0,5, nghĩa trung tính: cả phiên chỉ có một mức giá nên không có “gần đáy” hay “gần đỉnh” khác nhau.

Cấp giá/kỹ thuật có 23 + 4 + 5 = 32 cột. Cấp thị trường/vĩ mô có 32 + 6 = 38 cột; cấp đầy đủ có 38 + 4 = 42 cột. current_close là giá đã biết; next_close chỉ dùng chấm, không thuộc đầu vào X.

### 2.4. Tự làm tính với năm ngày giả định

Các con số dưới đây là ví dụ học toán, không phải dữ liệu FPT. Năm điểm không đủ tính đầy đủ RSI14, EMA26 hay SMA50 thật. Vì thế ví dụ dùng cửa sổ ngắn để nhìn được phép tính; code mô hình vẫn dùng đúng các cửa sổ đã ghi trong tên cột.

| Ngày giả định | Close | Volume | Chênh close với hôm trước |
|---:|---:|---:|---:|
| 1 | 10 | 100 | Chưa có |
| 2 | 12 | 120 | +2 |
| 3 | 11 | 90 | −1 |
| 4 | 14 | 150 | +3 |
| 5 | 13 | 130 | −1 |

#### Return: phần tăng/giảm chia cho giá ban đầu

Ngày 2:

    (12−10)/10 = 2/10 = 0,20 = 20%

Ngày 3:

    (11−12)/12 = −1/12 ≈ −0,08333 = −8,333%

Ngày 4:

    (14−11)/11 = 3/11 ≈ 0,27273 = 27,273%

Ngày 5:

    (13−14)/14 = −1/14 ≈ −0,07143 = −7,143%

Return 2 phiên ở ngày 5 là 13/11−1 = 2/11 ≈ 18,182%. Không lấy return ngày 4 cộng return ngày 5 để mặc nhiên được return gộp; tỷ lệ tăng/giảm theo các mẫu số khác nhau cần được ghép đúng.

#### SMA3: cộng ba giá rồi chia ba

Ngày 3:

    (10+12+11)/3 = 33/3 = 11

Ngày 4 bỏ ngày 1 ra, thêm ngày 4:

    (12+11+14)/3 = 37/3 ≈ 12,3333

Ngày 5:

    (11+14+13)/3 = 38/3 ≈ 12,6667

Ratio ở ngày 5 là 13/12,6667−1 ≈ 0,02632, tức close cao hơn SMA3 khoảng 2,632%.

#### EMA3: nửa giá mới, nửa trung bình cũ

Chu kỳ N=3 nên tỷ trọng mới = 2/(3+1)=0,5. Bắt đầu EMA đầu tiên bằng 10:

    Ngày 1: EMA = 10
    Ngày 2: 0,5×12 + 0,5×10 = 6+5 = 11
    Ngày 3: 0,5×11 + 0,5×11 = 11
    Ngày 4: 0,5×14 + 0,5×11 = 7+5,5 = 12,5
    Ngày 5: 0,5×13 + 0,5×12,5 = 6,5+6,25 = 12,75

Tại ngày 5, EMA3 ratio = 13/12,75−1 ≈ 1,961%. EMA và SMA khác nhau vì EMA ưu tiên giá mới hơn.

Code dùng adjust=False, nghĩa là tính đệ quy như các phép tính trên. min_periods=N nghĩa là dù nội bộ đã có phép tính từ đầu, chỉ xuất kết quả sau khi đủ N quan sát.

#### RSI rút gọn 2 thay đổi: so phần tăng với phần giảm

Ta dùng chu kỳ 2 để học phép tính. Dãy thay đổi là +2, −1, +3, −1. Tách mỗi thay đổi thành hai cột:

| Chuyển tiếp | Phần tăng | Phần giảm, lấy độ lớn dương |
|---|---:|---:|
| 10 → 12 | 2 | 0 |
| 12 → 11 | 0 | 1 |
| 11 → 14 | 3 | 0 |
| 14 → 13 | 0 | 1 |

Giống cách đệ quy code dùng với chu kỳ rút gọn, khởi đầu từ thay đổi đầu tiên: tăng bình quân = 2, giảm bình quân = 0. Chu kỳ 2 cho tỷ trọng mới 1/2:

    Sau thay đổi −1:
    Tăng bình quân = 0,5×0 + 0,5×2 = 1
    Giảm bình quân = 0,5×1 + 0,5×0 = 0,5
    RS = 1/0,5 = 2
    RSI = 100 − 100/(1+2)
        = 100 − 33,3333 = 66,6667

Sau thay đổi +3:

    Tăng bình quân = 0,5×3 + 0,5×1 = 2
    Giảm bình quân = 0,5×0 + 0,5×0,5 = 0,25
    RS = 2/0,25 = 8
    RSI = 100 − 100/9 ≈ 88,8889

Sau thay đổi −1:

    Tăng bình quân = 0,5×0 + 0,5×2 = 1
    Giảm bình quân = 0,5×1 + 0,5×0,25 = 0,625
    RS = 1/0,625 = 1,6
    RSI = 100 − 100/2,6 ≈ 61,5385

Code thật dùng chu kỳ 14. Mỗi bước giữ 13/14 phần mức bình quân cũ và thêm 1/14 phần biến động mới. “Wilder smoothing” chính là quy tắc giữ phần cũ nhiều hơn này; không cần học thuộc tên để hiểu phép cộng và chia. Với `ewm(adjust=False)`, code khởi tạo từ biến động đầu tiên như ví dụ; `min_periods=14` chỉ trì hoãn hiển thị tới khi có đủ 14 thay đổi, không có nghĩa khởi tạo bằng trung bình cộng của 14 thay đổi đầu. Vì vậy kết quả đầu chuỗi có thể khác phần mềm dùng cách khởi tạo khác. Kết quả chia 100 trước khi đưa vào mô hình. Nếu chỉ có tăng và không có giảm, code xử lý riêng để RSI bằng 100; nếu không tăng cũng không giảm thì dùng 50.

#### MACD rút gọn: trừ hai EMA

Ví dụ dùng EMA nhanh 2, EMA chậm 3. Với EMA2, tỷ trọng mới là 2/(2+1)=2/3. EMA3 là dãy vừa tính.

    EMA2 ngày 2 = (2/3)×12 + (1/3)×10 ≈ 11,3333
    EMA2 ngày 3 = (2/3)×11 + (1/3)×11,3333 ≈ 11,1111
    EMA2 ngày 4 = (2/3)×14 + (1/3)×11,1111 ≈ 13,0370
    EMA2 ngày 5 = (2/3)×13 + (1/3)×13,0370 ≈ 13,0123

Trừ EMA nhanh cho EMA chậm:

| Ngày | EMA2 | EMA3 | MACD rút gọn |
|---:|---:|---:|---:|
| 1 | 10,0000 | 10,0000 | 0,0000 |
| 2 | 11,3333 | 11,0000 | 0,3333 |
| 3 | 11,1111 | 11,0000 | 0,1111 |
| 4 | 13,0370 | 12,5000 | 0,5370 |
| 5 | 13,0123 | 12,7500 | 0,2623 |

Đường Signal rút gọn dùng EMA2 của dãy MACD:

    Signal ngày 1 = 0
    Ngày 2: (2/3)×0,3333 + (1/3)×0 ≈ 0,2222
    Ngày 3: (2/3)×0,1111 + (1/3)×0,2222 ≈ 0,1481
    Ngày 4: (2/3)×0,5370 + (1/3)×0,1481 ≈ 0,4074
    Ngày 5: (2/3)×0,2623 + (1/3)×0,4074 ≈ 0,3107

Histogram ngày 5 = 0,2623−0,3107 ≈ −0,0484. Bản thật thay 2/3/2 của ví dụ bằng 12/26/9, có kiểm tra đủ lịch sử, rồi chia MACD, Signal, Histogram cho close.

#### Bollinger Bands: dựng hành lang quanh trung bình

Dùng ba giá ngày 1–3 là 10,12,11 để tính nhẩm:

    Trung bình = (10+12+11)/3 = 11
    Sai lệch với trung bình: −1, +1, 0
    Bình phương sai lệch: 1, 1, 0
    Trung bình bình phương = (1+1+0)/3 = 2/3
    Độ lệch chuẩn = căn(2/3) ≈ 0,8165

Căn bậc hai ở đây là phép đảo của bình phương. Số 0,8165 khi bình phương trở lại xấp xỉ 0,6667.

    Dải trên = 11 + 2×0,8165 = 12,6330
    Dải dưới = 11 − 2×0,8165 = 9,3670
    %B ngày 3 = (11−9,3670)/(12,6330−9,3670)
               = 1,6330/3,2660 = 0,5
    Bandwidth = 3,2660/11 ≈ 0,2969 = 29,69%

Trong code, ddof=0 nghĩa là ở bước trung bình bình phương, chia cho đúng số điểm N: ví dụ này chia 3. Một cách thống kê khác chia N−1 để ước lượng từ mẫu; code đã chọn rõ cách chia N. Bản mô hình dùng 20 close, không dùng ba close.

#### Volatility: giá dao động có đều không?

Dùng ba return đầu: 0,20; −0,083333; 0,272727.

    Trung bình return
    = (0,20−0,083333+0,272727)/3 ≈ 0,129798

Lấy từng return trừ trung bình rồi bình phương:

    (0,20−0,129798)^2 ≈ 0,004928
    (−0,083333−0,129798)^2 ≈ 0,045425
    (0,272727−0,129798)^2 ≈ 0,020429

Sau đó:

    Trung bình bình phương
    = (0,004928+0,045425+0,020429)/3 ≈ 0,023594
    Căn(0,023594) ≈ 0,153603 = 15,3603%

Đây là độ dao động của ví dụ có biến động rất lớn, không phải dự báo ngày mai tăng 15,36%. Bản thật dùng cửa sổ 5 và 20 return.

#### Log-volume: không cần tính tay logarithm để hiểu vai trò

Từ volume 100 lên 120:

    log(1+120)−log(1+100)
    = log(121)−log(101)
    ≈ 0,1807

Máy tính thực hiện log. Điều cần hiểu là giá trị dương khi volume tăng, âm khi volume giảm, và số cực lớn bị nén bớt. Để tạo z-score, máy tính lấy trung bình và độ lệch chuẩn của 20 log-volume gần nhất rồi tính khoảng cách chuẩn hóa như ví dụ 110,100,5 ở trên.

### 2.5. Vì sao mất 49 hàng đầu?

SMA50 cần 50 phiên mới có kết quả. Ở phiên 1 chỉ có một giá, không thể có trung bình 50 giá thật. 49 hàng đầu vì vậy chưa đủ đầu vào và bị bỏ khỏi bảng đặc trưng hoàn chỉnh.

Đoạn cần tích lũy lịch sử này gọi là warm-up, tức thời gian “khởi động” của chỉ báo. Không lấy 49 giá tương lai điền ngược để giữ đủ hàng.

Sau bước này, bảng kỹ thuật có 4.620 hàng. Phần 1.8 giải thích vì sao khi ghép dữ liệu bổ trợ và yêu cầu lịch sử liên tiếp, tập so sánh chung thu hẹp còn 3.032 hàng.

### 2.6. Tại sao dùng những công thức đó, thay vì đưa nguyên cả bảng giá?

Một hàng OHLCV chỉ mô tả một phiên. Nó chưa nói trực tiếp phiên đó khác mức thường gặp trong tháng ra sao. Tạo đặc trưng là **viết lại lịch sử thành các câu hỏi bằng con số**, để mô hình không phải tự tìm lại mọi phép tính từ đầu.

| Nhóm công thức | Vấn đề muốn biểu diễn | Vì sao tính như vậy? | Khi đọc cần nhớ |
|---|---|---|---|
| Return 1/2/5/10/20 phiên | Giá vừa đi theo hướng nào, trong bao lâu? | Chia giá hiện tại cho giá k phiên trước để đo thay đổi tương đối; từ 10 lên 11 và từ 100 lên 110 đều là 10% | Return 5 phiên là một thay đổi tích lũy 5 phiên, không phải trung bình 5 return |
| Close/SMA − 1 | Hôm nay cao/thấp bao nhiêu so với mức trung bình gần đây? | Trung bình giảm ảnh hưởng của một phiên; tỷ lệ đặt các giai đoạn giá khác nhau vào thang gần nhau | Chu kỳ 5 phản ứng nhanh, 50 chậm; “trên trung bình” chưa quyết định ngày mai |
| Close/EMA − 1 | Giá mới đang lệch khỏi một mức nền ưu tiên thông tin gần đây thế nào? | EMA cho giá mới trọng số lớn hơn nhưng vẫn giữ thông tin cũ | Nhanh hơn không đồng nghĩa chính xác hơn; chọn nhiều chu kỳ để thử các khoảng nhìn |
| RSI | Những lần tăng đang mạnh hơn hay những lần giảm đang mạnh hơn? | Tách phần tăng/phần giảm, làm trung bình có trọng số rồi đưa về thang 0–100 | Không đo xác suất tăng; dự án chia 100 để lưu 0–1 |
| MACD/Signal/Histogram | Xu hướng ngắn đang tách xa hay quay lại xu hướng dài? | EMA12 − EMA26 đo chênh; EMA9 của chênh tạo mức nền; histogram đo chênh so với nền này | Chia cho close làm giảm lệ thuộc mức giá tuyệt đối; ba cột liên quan nhau nên không phải ba nguồn thông tin độc lập |
| Bollinger %B | Giá nằm thấp/cao trong hành lang dao động gần đây? | Dùng trung bình ± 2 độ lệch chuẩn, rồi đo vị trí tương đối trong hành lang | Dải là cách mô tả, không phải khoảng chắc chắn 95% cho giá ngày mai |
| Bollinger width | Giai đoạn vừa qua đang co hẹp hay mở rộng mức dao động giá? | Độ rộng dải chia cho SMA giúp so các giai đoạn giá 10 và 100 | Độ rộng tăng chưa cho biết hướng tăng hay giảm |
| Volatility 5/20 | Lợi nhuận các phiên đang đều hay thất thường? | Độ lệch chuẩn đo mức lệch khỏi trung bình, không bị các dấu dương/âm triệt tiêu như khi chỉ lấy trung bình | Volatility của FPT dùng simple return; của VN-Index dùng log return theo code hiện tại |
| Log-volume change | Mức giao dịch hôm nay tăng/giảm tương đối ra sao? | Hiệu hai log gần với log của tỷ số, nén khoảng chênh khối lượng rất lớn | `+1` giúp nhận volume bằng 0; không biến khối lượng thành tiền |
| Log-volume z-score | Hôm nay có giao dịch bất thường so với 20 phiên gần nhất không? | Trừ mức nền rồi chia độ lệch chuẩn, quy đổi thành số “bước dao động thường gặp” | Đây là chuẩn hóa cuốn chiếu từng ngày, khác `StandardScaler` học trên Train |
| Biên độ nến | Phiên hiện tại dao động rộng đến đâu? | `(high−low)/close` biến khoảng giá thành tỷ lệ | Giá giảm mạnh và tăng mạnh đều có thể tạo biên độ lớn |
| Thân nến | Từ lúc mở đến đóng cửa, giá tăng/giảm bao nhiêu? | `(close−open)/open` chỉ đo đoạn trong phiên | Khác return đóng cửa–đóng cửa vì chưa gồm nhảy giá khi mở cửa |
| Overnight gap | Giá vừa mở phiên có chênh khỏi đóng cửa phiên trước không? | `open/previous_close−1` tách riêng biến động giữa hai phiên | “Overnight” có thể kéo dài cuối tuần/ngày lễ, không luôn là đúng một đêm |
| Vị trí close | Phiên đóng gần đầu trên hay đầu dưới khoảng giá? | `(close−low)/(high−low)` dùng toàn khoảng ngày làm thước | Khi high=low, không có khoảng để đo; code dùng 0,5 |
| Năm số OHLCV hiện tại | Mức giá, khối lượng và hình dạng hiện tại là bao nhiêu? | Giữ dữ liệu gốc bên cạnh các tỷ lệ để mô hình có cả mức và thay đổi | Nhiều số cùng phản ánh close nên có tương quan; thêm cột không tự thêm thông tin độc lập |

Ví dụ `close=102`, SMA5=100 cho ratio `102/100−1=0,02`. Mô hình nhìn thấy “cao hơn nền 2%”, thay vì phải phân biệt 102 nghìn và 100 nghìn một cách tuyệt đối. Nhưng nếu đưa thêm USD/VND=26.421, doanh thu hơn 16 nghìn tỷ và RSI=0,6 vào một mô hình tuyến tính, các thang số rất khác nhau; lúc đó cần chuẩn hóa phù hợp ở bước mô hình, được giải thích tại phần 4.3.

Tại sao giữ cả SMA, EMA và MACD dù chúng liên quan? Đó là một tập ứng viên nhỏ, dễ giải thích cho ba góc nhìn mức nền, phản ứng nhanh và chênh xu hướng. Sau đó dùng đối sánh và permutation để kiểm tra mô hình phụ thuộc chúng ra sao. Không tuyên bố mỗi công thức là một tín hiệu tài chính độc lập đã được chứng minh có khả năng sinh lợi.

### 2.7. EDA: xem gì trong từng hình và kiểm tra để làm gì?

EDA viết đầy đủ là *Exploratory Data Analysis*, nghĩa là xem xét dữ liệu trước khi kết luận về mô hình. Nó giống kiểm tra nguyên liệu và dụng cụ trước khi nấu: dữ liệu sai đơn vị hay sai ngày có thể tạo điểm số đẹp nhưng không có ý nghĩa.

**Bước 1 — Kiểm tra bảng có thể dùng được.** `load_price_data` đổi ngày, đổi số, kiểm tra ô thiếu, trùng ngày, giá không dương, khối lượng âm và số vô hạn. Những lỗi này khiến chương trình báo lỗi thay vì đoán số thay thế. Một bản giá bị trùng ngày làm `shift(1)` không còn nghĩa “phiên trước”; một close bằng 0 làm tỷ số và log mất ý nghĩa. Dữ liệu hiện tại có 0 ô thiếu và 0 ngày trùng trong 6 cột gốc.

**Bước 2 — Kiểm tra quan hệ giữa các số.** Giá trong một phiên hợp lý cần `low ≤ min(open, close)`, `high ≥ max(open, close)` và `low ≤ high`. Audit tìm 3 phiên vi phạm ở 2007–2009. Code ghi lại, giữ snapshot để đối chiếu, không âm thầm đổi high thành close. Có 2 phiên volume=0 nhưng 0 là một số quan sát, không phải ô trống. Hai loại kiểm tra này khác nhau: đúng kiểu số chưa đủ để đúng logic thị trường.

**Bước 3 — Đọc đường giá.** Mở [01_fpt_close.png](../figures/01_fpt_close.png). Trục ngang là ngày, trục đứng là close nghìn VND/cổ phiếu. Giá thấp nhất 1,61525 và cao nhất 118,073 trên chuỗi close cho thấy thang giá thay đổi lớn. Hình giúp nhận ra xu thế dài hạn, đoạn biến động mạnh và mức giá giữa các giai đoạn. Nhìn đường giá đi lên không đủ để kết luận phiên ngày mai sẽ tăng.

**Bước 4 — Đọc khối lượng.** Sau khi lọc hai ngày HOSE đóng cửa, khối lượng từ 1.820 tới 23.514.300 cổ phiếu. Trục `symlog` nén vùng số lớn để thấy các mức thấp hơn. Thang này chỉ chỉnh cách hiển thị, còn `ln(1+volume)` được tính trên số gốc để tạo hai đặc trưng. [Biểu đồ khối lượng](../figures/02_fpt_volume.png)

**Bước 5 — Đọc phân phối lợi nhuận.** Mở [03_daily_return_distribution.png](../figures/03_daily_return_distribution.png). Mỗi cột đếm số phiên có simple return nằm trong một khoảng. Đường tại 0 ngăn tăng và giảm. Toàn snapshot có trung bình khoảng 0,0644%/phiên, độ lệch chuẩn mẫu khoảng 1,9193%; lợi nhuận nhỏ nhất −6,9896%, lớn nhất 6,9922%. Phân vị 1% khoảng −4,9473% và 99% khoảng 4,9716%: một phần nhỏ phiên có biên độ rất khác phần giữa. “Phân vị 1%” nghĩa khoảng 1% quan sát ở mức đó hoặc thấp hơn, không phải xác suất được bảo đảm cho tương lai.

**Bước 6 — Đọc số phiên theo hướng.** Mở [04_next_session_class_balance.png](../figures/04_next_session_class_balance.png). Có 2.118 chuyển tiếp Tăng, 2.074 Giảm và 476 Đứng giá. Tổng là 4.668 chuyển tiếp, ít hơn 4.669 phiên vì hàng cuối chưa có phiên sau trong snapshot. Biểu đồ vẫn hữu ích dù hiện tại không huấn luyện bộ phân loại: nó giúp hiểu cách chấm hướng suy ra từ log return và lý do không cộng phiên đứng giá vào mẫu số Directional Accuracy.

**Bước 7 — Kiểm tra nguồn bổ trợ trước khi ghép.** CPI và GDP mỗi nguồn có 20 kỳ năm. So ngày khả dụng và hạn tuổi với lịch FPT. Đủ số năm trong tệp vẫn cần kiểm tra đủ biến trên từng phiên.

EDA toàn bộ snapshot nhằm mô tả chất lượng dữ liệu; kiểm định chuỗi thời gian phục vụ phân tích chính dùng lịch sử đến cuối Train như phần 3. Không nhìn toàn bộ đường Test rồi đổi chỉ báo/siêu tham số để làm đẹp kết quả. Tệp kiểm toán có thể mở trực tiếp tại [data_audit.json](../reports/data_audit.json); cách đọc công thức và đối chiếu từng hình có thêm trong [EDA và đặc trưng](EDA_VA_DAC_TRUNG.md).

### 2.8. Dữ liệu bất thường, dữ liệu thiếu và chuẩn hóa được xử lý khác nhau

**Bất thường không đồng nghĩa sai.** Một phiên giảm rất mạnh có thể là sự kiện thị trường thật. Pipeline hiện tại không tự xóa các phiên lợi nhuận lớn, không kéo mọi giá trị về một ngưỡng phần trăm và không ép phân phối thành hình chuông. Xóa các ngày khó dự báo sẽ làm bài toán dễ giả tạo. Ba bất nhất OHLC được ghi rõ để người đọc phân biệt với biến động giá thật; chúng nằm trước cửa sổ so sánh chung hiện tại.

**Thiếu lịch sử tính toán và thiếu quan sát nguồn được phát hiện riêng.** SMA50 cần đủ 50 giá. Độ lệch chuẩn bằng 0 có thể làm z-score không xác định. Trong nguồn thị trường, một phiên không có bản ghi cần được đối chiếu trước khi tính return.

Bảng giữ `session_index` của từng phiên sau khi kiểm tra lịch HOSE. Cửa sổ 60 phiên phải có đủ 42 biến và chỉ số đầu–cuối cách đúng 59 phiên.

Ba cấp dữ liệu dùng cùng 3.031 nhãn. Nhờ vậy, khi thêm cột trong thí nghiệm XGBoost, giai đoạn chấm giữ nguyên.

**Đổi cách biểu diễn khác với học tham số chuẩn hóa.** Tính return hay tỷ lệ SMA chỉ dùng cửa sổ đã quan sát đến phiên t, có thể làm trước chia tập. `StandardScaler` cần học trung bình và độ lệch chuẩn, vì vậy chỉ fit phần Train tương ứng. Cùng cột doanh thu, số “2 độ lệch chuẩn” phải được hiểu theo mốc chuẩn của Train, không theo mốc tính cả những năm chưa đến. Chi tiết phép tính `z=(x−trung bình Train)/độ lệch chuẩn Train` nằm ở phần 4.3.

**Ngữ cảnh thống kê có một xử lý riêng:** ARIMA/SARIMAX giữ các phiên lịch sử trung gian để chuỗi không bị nén đứt đoạn. Các ô ngoại sinh còn thiếu trong ngữ cảnh SARIMAX được điền median học từ Train, rồi chuẩn hóa theo Train; không lấy trung vị từ Test. “Median” là số ở giữa khi sắp các quan sát theo độ lớn. Cách điền này không khiến một báo cáo chưa công bố bỗng xuất hiện; đó chỉ là giá trị thay thế kỹ thuật để mô hình xử lý ngữ cảnh thiếu và phải được phân biệt với các ngày đủ đầu vào trong tập so sánh.

---


## Phần 3. Hiểu chuỗi thời gian mà không học thuộc thuật ngữ

### 3.1. Tính dừng: quy luật có giữ tương đối ổn định không?

Hình dung đo nhiệt độ ở một phòng giữ điều hòa 25°C. Có lúc 24,8, có lúc 25,3, nhưng mức trung tâm không đi mãi lên. Dãy này gợi hình ảnh một chuỗi ổn định quanh một mức. Ngược lại, đo chiều cao của một đứa trẻ qua nhiều năm có xu hướng tăng: trung bình giai đoạn đầu khác giai đoạn cuối.

“Dừng yếu” thường đòi trung bình và phương sai ổn định theo thời gian, còn mức liên hệ giữa hai điểm phụ thuộc khoảng cách giữa chúng. Đây là tính chất thống kê, không có nghĩa mọi giá trị bằng nhau. “Dừng chặt” là yêu cầu mạnh hơn đối với toàn bộ phân phối; KPSS trong dự án không chứng minh tính chất đó.

Giá cổ phiếu có thể từ vùng 10 sang vùng 100; việc học trực tiếp mức giá dễ bị ảnh hưởng bởi thay đổi thang. Tăng 1 đồng từ 10 lên 11 là 10%, còn từ 100 lên 101 chỉ là 1%. Log return diễn tả tỷ lệ nên phân biệt được hai trường hợp.

### 3.2. ADF và KPSS: đọc hai câu hỏi, không học mẹo “p nhỏ là tốt”

`p-value` cho biết: nếu giả thuyết gốc đúng và các điều kiện kiểm định phù hợp, kết quả cực đoan như đang thấy có hiếm không? p nhỏ làm ta nghi ngờ giả thuyết gốc. p không phải xác suất giả thuyết đúng và cũng không phải độ chính xác mô hình.

| Kiểm định | Tên đầy đủ | Giả thuyết gốc | Nếu p < 0,05 |
|---|---|---|---|
| ADF | Augmented Dickey–Fuller | Chuỗi có nghiệm đơn vị, một dạng không dừng | Bác bỏ giả thuyết nghiệm đơn vị |
| KPSS | Kwiatkowski–Phillips–Schmidt–Shin | Chuỗi dừng mức quanh hằng số trong cấu hình hiện tại | Bác bỏ giả thuyết dừng mức |

“Nghiệm đơn vị” có thể hiểu sơ bộ là một cú thay đổi không nhanh chóng bị kéo về mức trung tâm, như đi bộ ngẫu nhiên. Không cần giải phương trình đa thức để đọc kết quả đồ án.

| Chuỗi, lịch sử đến 29/11/2023 | ADF p | KPSS p | Điều được phép nói |
|---|---:|---:|---|
| Close | 0,9991 | < 0,01 | ADF chưa bác bỏ nghiệm đơn vị, KPSS bác bỏ dừng mức |
| Log return | khoảng 5,63 × 10⁻¹⁷ | 0,0338 | ADF bác bỏ nghiệm đơn vị, nhưng KPSS vẫn bác bỏ dừng mức |

Hai kết quả của log return không phải máy bị lỗi: các giả thuyết khác nhau và các kiểm định nhạy với đặc điểm khác nhau. Thay đổi chế độ hoặc cấu trúc còn lại có thể cần phân tích thêm. Không suy ra “log return đã dừng hoàn toàn”; cũng không suy ra KPSS đã chứng minh cụm biến động. Muốn nghiên cứu cụm biến động cần xem chuỗi bình phương return và kiểm định phù hợp riêng.

Có 4.214 mức giá và 4.213 log return trong lịch sử này, nhiều hơn 2.576 hàng Train học máy vì kiểm định dùng giá trước ngày kết thúc Train, còn cohort ML cần đủ các nguồn bổ trợ. Tài liệu chính thức: [ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html), [KPSS](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html).

### 3.3. ACF và PACF nhìn như thế nào?

ACF là *Autocorrelation Function*, tự tương quan. Cột độ trễ 1 hỏi hôm nay có đi cùng hôm qua không; độ trễ 5 hỏi hôm nay có đi cùng năm phiên trước không. Tương quan gần +1 gợi liên hệ cùng chiều, gần −1 gợi liên hệ ngược chiều, gần 0 gợi liên hệ tuyến tính yếu.

PACF là *Partial Autocorrelation Function*, tự tương quan riêng phần. Khi nhìn độ trễ 2, nó tách liên hệ trực tiếp với hai phiên trước khỏi phần có thể giải thích qua phiên liền trước. Ví dụ A liên quan B, B liên quan C: ACF có thể thấy A liên quan C, còn PACF hỏi liên hệ ấy còn bao nhiêu sau khi tính đến B.

Trong `figures/12_acf_pacf.png`, mỗi hàng là một chuỗi, mỗi cột là ACF/PACF. Vùng tô là dải tham chiếu 95% cho từng độ trễ. Vài cột vượt dải chưa đủ khẳng định chắc chắn có tín hiệu dự báo hữu ích, đặc biệt khi xem nhiều cột. Không chọn mô hình chỉ bằng cách đếm các cột đẹp.

### 3.4. Vì sao log return giúp thiết kế gọn hơn?

Mô hình cây chia đầu vào thành nhóm và dự báo từ giá trị đã học trong các nhóm. Nếu học trực tiếp giá ở vùng thấp rồi phải đoán mức chưa từng thấy, khả năng ngoại suy thường bị hạn chế. Với log return, cây dự báo mức biến động tương đối; giá hôm nay được nhân trở lại ở bước cuối.

    Quy tắc dự báo tăng khoảng 1%:
    Hôm nay giá 10:  dự báo 10 × 1,01 = 10,1
    Hôm nay giá 100: dự báo 100 × 1,01 = 101

Đổi mục tiêu không khiến thông tin chưa biết tự xuất hiện. Thí nghiệm hiện tại không chạy đối chứng mới với mục tiêu giá trực tiếp, nên không đo riêng được “bao nhiêu cải thiện do đổi mục tiêu”.

STL là *Seasonal and Trend decomposition using Loess*: tách chuỗi thành xu thế, thành phần chu kỳ và phần dư. Bản này dùng chu kỳ quy ước 5 phiên trên log(close), đặt ở phụ lục `13_time_series_decomposition.png`; không đưa các thành phần vào đầu vào và không nói đã chứng minh mùa vụ tuần.

## Phần 4. Học, chọn và kiểm tra theo đúng dòng thời gian

### 4.1. Vì sao không trộn ngẫu nhiên các ngày?

Làm bài thi năm 2020 nhưng đã luyện từ dữ liệu năm 2024 có thể cho điểm đẹp mà không phản ánh điều làm được khi thật sự ở năm 2020. Chia theo thời gian giúp câu hỏi gần thực tế hơn: học quá khứ, dự báo phần đến sau.

Train là phần học; Test là phần chấm sau khi lựa chọn đã cố định. Không có Validation rời ở cấp ngoài, nhưng vẫn có các đoạn kiểm định bên trong Train để chọn cấu hình. “Không có Validation rời” không đồng nghĩa “không có kiểm định”.

**Train 2.576 mẫu (07/08/2013–29/11/2023)** và **Test 455 mẫu (30/11/2023–30/09/2025)**. Chia 85%/15% theo ngày mục tiêu. Hồi quy chấm 455 mẫu. Đúng hướng chấm 440 phiên đổi giá, dự báo đứng giá tính sai trên các phiên này.

Trong Train dùng `TimeSeriesSplit(n_splits=5, gap=1)`. Năm fold lần lượt có 430, 859, 1.288, 1.717 và 2.146 hàng học, mỗi fold có 429 hàng kiểm định. Chừa một hàng giúp tách nhãn gần ranh giới theo thời gian.

Chọn siêu tham số và L bằng **RMSE log return CV nhỏ nhất**, khóa lựa chọn trong `experiment_plan.json`, rồi fit toàn bộ Train và chấm Test. StandardScaler chỉ học từ Train của mỗi fold; GRU dùng các phiên ngữ cảnh quá khứ trong cửa sổ Train. Sau khi lưu kết quả đánh giá, mô hình chính được CV chọn học lại toàn bộ giai đoạn có nhãn (cohort ML có 3.031 hàng; thống kê còn giữ các phiên ngữ cảnh liên tục) để tạo dự báo mới nhất. Artefact học lại không dùng để chấm lại Test.

### 4.2. Một fold là gì? Gap 1 giúp gì?

Một *fold* là một lượt học/chấm nhỏ trong Train. CV viết tắt *Cross-Validation*, kiểm định chéo. Với chuỗi thời gian, mỗi lượt học một đoạn quá khứ rồi chấm đoạn kế tiếp. TimeSeriesSplit tạo các chỉ số hàng theo quy tắc đó.

Ví dụ giả định:

    Lượt 1: học hàng 1–4; chừa hàng 5; chấm 6–7
    Lượt 2: học hàng 1–6; chừa hàng 7; chấm 8–9
    Lượt 3: học hàng 1–8; chừa hàng 9; chấm 10–11

Đây chỉ là hình dung, không phải số hàng thật. Gap 1 chừa một hàng giữa phần học và phần chấm của mỗi fold, tạo khoảng đệm cho nhãn một bước tới. GRU vẫn được phép nhìn các phiên ngữ cảnh quá khứ đã biết; gap không buộc nó phải quên lịch sử quan sát hợp lệ.

### 4.3. StandardScaler nằm trong Pipeline nghĩa là gì?

Volume hàng triệu, RSI khoảng 0–1, tỷ giá hàng chục nghìn: các cột có thang khác nhau. StandardScaler đổi mỗi giá trị bằng:

    z = (giá trị − trung bình Train) / độ lệch chuẩn Train

Ví dụ Train có 10, 12, 14:

    Trung bình = (10+12+14)/3 = 12
    Sai lệch = −2, 0, 2; bình phương = 4, 0, 4
    Độ lệch chuẩn = căn[(4+0+4)/3] ≈ 1,633
    Giá trị 14 thành (14−12)/1,633 ≈ 1,225

Test có 20 thì vẫn dùng trung bình 12 và độ lệch chuẩn 1,633: `(20−12)/1,633 ≈ 4,899`. Không tính lại trung bình gồm Test, vì quá khứ sẽ học được thông tin phân phối tương lai.

Pipeline là dây chuyền ghép các bước: với Ridge là **chuẩn hóa → hồi quy**. Khi gọi `fit` trên Train, scaler lẫn Ridge chỉ học Train đó. Khi gọi `predict` trên Test, scaler áp công thức đã học. XGBoost không cần scaler cho ngưỡng cây; GRU và ngoại sinh SARIMAX có scaler riêng nhưng vẫn chỉ fit phía Train.

`fit` là học tham số; `predict` là áp mô hình xuất dự báo; `transform` chỉ chuyển đổi bằng quy tắc có sẵn; `fit_transform` vừa học quy tắc vừa chuyển đổi, chỉ dùng ở phía Train tương ứng.

### 4.4. Tại sao có mô hình học toàn bộ dữ liệu sau khi chấm?

Mô hình trong `models/evaluation/` chỉ học Train để chấm Test. `models/best_regressor.joblib` là bản phương pháp được CV chọn, học lại mọi nhãn biết đến 30/09/2025 để dự báo phiên kế tiếp. Không lấy bản học lại quay về chấm Test và gọi là ngoài mẫu. `predict.py` dùng bản học lại; `explain.py` đọc bản đánh giá Train-only.

## Phần 5. Năm phương pháp chính và một đối sánh mở rộng

### 5.1. Last-Close Baseline: luôn trả lời “giữ nguyên”

Baseline là mốc đơn giản để biết mô hình phức tạp có thật sự tốt hơn một quy tắc dễ hay không.

    r̂ = 0
    Giá dự báo = C(t) × exp(0) = C(t)

Không có hệ số cần học. Hôm nay 100, dự báo 100; mai thật sự 100,3 thì sai số chỉ 0,3. Nhưng trên phiên thực tế tăng/giảm, dự báo đứng giá luôn sai hướng. Đây là khác nhau giữa gần mức giá và đúng dấu biến động.

### 5.2. Ridge: cộng tín hiệu, kiểm soát độ lớn trọng số

Ridge là hồi quy tuyến tính có phạt bình phương trọng số, còn gọi phạt L2:

    r̂ = b + w1×x1 + w2×x2 + ...

Ví dụ giả định x1=1, x2=−0,5 sau chuẩn hóa; w1=0,002, w2=−0,001, b=0,0002:

    r̂ = 0,0002 + 0,002×1 + (−0,001)×(−0,5)
       = 0,0002 + 0,002 + 0,0005 = 0,0027

Máy tìm trọng số để sai số nhỏ, đồng thời chịu phạt khi trọng số lớn. Alpha điều khiển mức phạt, không phải độ chính xác. Nó hạn chế bám nhiễu khi nhiều chỉ báo tương quan. Repo thử alpha 10 và 100; CV chọn **100**. Đây không phải ARIMA bậc 100.

### 5.3. XGBoost: nhiều cây nhỏ lần lượt sửa sai

Cây quyết định giống chuỗi câu hỏi: return 5 phiên có vượt ngưỡng không? Giá dưới SMA không? Đi đến một ô cuối chứa dự báo số. Boosting ghép nhiều cây; cây sau sửa phần mà tổ hợp trước chưa tốt.

Ví dụ minh họa:

    Dự báo đầu = 0
    Cây sau đề xuất sửa +0,0100
    Learning rate 0,04 chỉ nhận 4% phần sửa
    Dự báo mới = 0 + 0,04×0,0100 = 0,0004

Repo dùng 120 cây, learning rate 0,04; thử độ sâu 2/3, CV chọn **2**. Độ sâu là số tầng câu hỏi, không phải số phiên nhớ. Cây đọc một hàng chứa chỉ báo tóm tắt quá khứ, không đọc tuần tự 60 hàng như GRU.

Ở thí nghiệm thêm dữ liệu, giữ cấu hình đã chọn trên 32 biến cho cả 38/42 biến. Chỉ thay thông tin đầu vào, không đồng thời tinh chỉnh tham số từng bộ để lấy điểm đẹp.

### 5.4. ARIMA: lịch sử lợi nhuận của chính cổ phiếu

ARIMA là *AutoRegressive Integrated Moving Average*. Bộ `(p,d,q)` gồm:

- p: số độ trễ chuỗi trong phần tự hồi quy.
- d: số lần lấy sai phân của chuỗi đang mô hình hóa.
- q: số độ trễ sai số dự báo trong phần trung bình trượt; khác đường chỉ báo SMA.

Dự án đã chuyển giá thành log return, chỉ thử d=0 và bậc (0,0,0)/(1,0,0), có hằng số. ARIMA không dùng cả 32 cột dù nằm trong thí nghiệm giá/kỹ thuật.

CV chọn **ARIMA(0,0,0)**. Với bậc này, dự báo log return là một hằng số dương học từ Train, xấp xỉ 0,001002 cho mọi hàng Test. Giá dự báo thay đổi theo `close × exp(log return dự báo)`. Mô hình luôn dự báo tăng trên Test và đúng ở 230/440 phiên đổi giá.

Ở cấu hình thử **ARIMA(1,0,0)**, phần tự hồi quy dùng log return đã quan sát gần nhất. Ví dụ trung bình bằng 0,1%, hệ số trễ bằng 0,2 và log return mới nhất là 1,1%, thì dự báo minh họa bằng `0,1% + 0,2 × (1,1% − 0,1%) = 0,3%`. Cấu hình được chọn ở lần chạy này là bậc 0.

### 5.5. GRU: đọc một đoạn lịch sử, học nên giữ gì

GRU là *Gated Recurrent Unit*, mạng thần kinh có bộ nhớ và cổng điều khiển thông tin. Hình dung đọc nhật ký 60 phiên: sau mỗi phiên cập nhật một bản tóm tắt, chọn giữ bao nhiêu thông tin cũ và nhận bao nhiêu mới.

Ví dụ chỉ để hiểu cách trộn: bộ nhớ cũ 0,4, ứng viên mới 0,8; giữ 75% cũ, nhận 25% mới:

    Bộ nhớ mới = 0,75×0,4 + 0,25×0,8 = 0,3+0,2 = 0,5

Trong GRU thật, cổng là các số được học; còn có cổng reset tác động lên ứng viên. Ví dụ này không phải toàn bộ công thức mạng mà minh họa nhớ có chọn lọc.

L=20 cho đầu vào một mẫu là 20 phiên × 32 đặc trưng. L=60 là 60×32. Không lấy 60 hàng đã lọc đứt quãng rồi gọi 60 phiên liên tiếp: code giữ chỉ số phiên gốc `session_index` để kiểm tra.

Một lớp GRU 16 nút ẩn, 12 epoch. Epoch là một lượt qua mẫu học; batch 64 là nhóm tối đa 64 mẫu trước một lần cập nhật trọng số. Learning rate 0,001 là độ lớn bước cập nhật; Adam là thuật toán điều chỉnh bước. Seed 42 cố định khởi tạo để tái lập. Nhãn nhân 100 khi tối ưu, chia lại 100 khi xuất, không đổi thang báo cáo.

60 phiên chứa nhiều ngữ cảnh hơn nhưng có thể thêm nhiễu hoặc khó học; không mặc định tốt hơn. Ta kiểm tra 20/60 thay vì khẳng định trước.

### 5.6. SARIMAX: thêm điều kiện bên ngoài vào mô hình chuỗi

SARIMAX là *Seasonal AutoRegressive Integrated Moving Average with eXogenous regressors*. Exogenous ở đây là đầu vào ngoài chuỗi return FPT: VN-Index, tỷ giá, vàng, CPI, GDP, tài chính. Không hàm ý chúng đã được chứng minh ngoại sinh theo nghĩa nhân quả kinh tế lượng.

    r̂ = phần từ chuỗi FPT
         + trọng số × tỷ giá đã chuẩn hóa
         + trọng số × thị trường đã chuẩn hóa + ...

Bản này không dùng mùa vụ, thử cùng hai bậc với ARIMA. CV chọn **SARIMAX(0,0,0)** với 10 biến bổ trợ và hằng số. Trong cấu hình chọn, phần tự hồi quy bị bỏ; dự báo chủ yếu từ hằng số và ngoại sinh. Không gọi là mô hình mùa vụ phức tạp chỉ vì tên thư viện có chữ S.

Nếu thiếu ngoại sinh trong ngữ cảnh thống kê, pipeline dùng trung vị và tham số chuẩn hóa học từ Train. Trong cửa sổ đánh giá hiện tại, cả 10 biến bổ trợ đều có đủ giá trị. Mô hình thêm một cột toàn số 1 để học hệ số chặn.

SARIMAX chỉ thuộc mở rộng thí nghiệm 2. Cùng ngày Test không có nghĩa số quan sát fit nội bộ giống hệt: thống kê giữ lịch liên tục trong khoảng Train; mô hình bảng học cohort hợp lệ. Manifest lưu khác biệt này.

## Phần 6. Đọc bảng điểm bằng phép tính đơn giản

### 6.1. Sáu cột: tên phương pháp và năm độ đo

Gọi sai số giá phiên i là `e_i = giá dự báo − giá thực tế`:

- **MAE** = trung bình `|e_i|`; **RMSE** = căn bậc hai của trung bình `e_i²`, phạt mạnh lỗi lớn. Cả hai có đơn vị nghìn VND/cổ phiếu.
- **CV RMSE log return** dùng cùng công thức trên lợi nhuận logarit, không có đơn vị giá. Không đọc 0,017 thành 0,017 nghìn VND.
- **Đúng hướng** = số dự báo có dấu đúng / số phiên thực tế đổi giá × 100. Dấu 0 không trùng dấu +1 hoặc −1.
- **Dung sai ±1%** = tỷ lệ phiên có `|e_i| / giá thực tế ≤ 0,01`. MAE/MAPE và dung sai dùng cả phiên đứng giá.

CSV giữ thêm Test MAE/RMSE log return, MAPE giá, dung sai ±0,5% và ±2%. Không dùng MAPE trên log return vì các giá trị gần 0 làm mẫu số không ổn định. Bảng chính có một cột tên và năm cột độ đo.


### 6.2. Nhẩm MAE, RMSE và dung sai trước khi đọc số thật

Giả sử hôm nay giá 62, ngày mai thật sự 63 và dự báo 63,2 (nghìn đồng):

    Thật: 63 − 62 = +1 → Tăng.
    Dự báo: 63,2 − 62 = +1,2 → Tăng → đúng hướng.
    Sai số giá: 63,2 − 63 = +0,2 nghìn đồng = 200 đồng.
    Sai số tương đối: 0,2/63 × 100 = 0,31746%.
    0,31746% ≤ 0,5%, ≤ 1%, ≤ 2% → đạt cả ba ngưỡng.

Nếu dự báo 70, vẫn đúng hướng nhưng sai 7/63 × 100 = 11,11%, không đạt dung sai nào. Nếu dự báo đúng bằng 62, hướng là Đứng giá, bị chấm sai hướng vì thực tế tăng; sai số giá 1/63 × 100 = 1,5873%, vẫn đạt ngưỡng ±2%. Hai cách chấm trả lời hai câu hỏi khác nhau.

Với ba sai số tuyệt đối 1, 2, 3:

    MAE = (1+2+3)/3 = 2.
    Bình phương sai số: 1, 4, 9.
    Trung bình bình phương = (1+4+9)/3 = 14/3 = 4,6667.
    RMSE = căn(4,6667) ≈ 2,1602.

RMSE lớn hơn vì lỗi 3 bị phạt mạnh. Nếu bốn phiên có sai số tương đối 0,4%, 0,8%, 1,5%, 3%: dung sai ±0,5% đạt 1/4 = 25%; ±1% đạt 2/4 = 50%; ±2% đạt 3/4 = 75%. Dung sai càng rộng, tỷ lệ đạt không thể giảm.

### 6.3. Kết quả thật: thí nghiệm 1

| Mô hình / cấu hình | CV RMSE log return | Test MAE giá (nghìn VND) | Test RMSE giá (nghìn VND) | Đúng hướng | Dung sai ±1% |
|---|---:|---:|---:|---:|---:|
| Last-Close Baseline | 0.015890 ± 0.002139 | 1.1097 | 1.5623 | 0.00% | 55.16% |
| Ridge Regression | 0.016166 ± 0.002189 | 1.1229 | 1.5794 | 48.41% | 54.73% |
| XGBoost | 0.016390 ± 0.002035 | 1.1100 | 1.5610 | 52.95% | 55.60% |
| ARIMA | 0.015860 ± 0.002130 | 1.1106 | 1.5636 | 52.27% | 55.16% |
| GRU L=60 | 0.016054 ± 0.002182 | 1.1114 | 1.5618 | 49.77% | 55.16% |

ARIMA(0,0,0) có CV RMSE 0,015860, nhỏ hơn nhẹ mức 0,015890 của Last-Close. Cấu hình này dự báo một mức log return cố định học từ Train. ARIMA có MAE Test 1,1106 nghìn VND và đúng hướng 52,27%. Last-Close có MAE 1,1097 nghìn VND và luôn trả đứng giá. XGBoost 32 biến có RMSE giá 1,5610 nghìn VND, thấp nhất trong bảng năm phương pháp.

GRU L=60 có MAE 1,1114, so với 1,1097 nghìn VND của Last-Close. Độ chênh dưới 2 đồng/cổ phiếu theo thang giá lưu. Một lần chạy với một seed chỉ cho biết kết quả của thiết lập này.

### 6.4. Kết quả thật: thí nghiệm 2 thêm dữ liệu

| Mô hình / cấu hình | CV RMSE log return | Test MAE giá (nghìn VND) | Test RMSE giá (nghìn VND) | Đúng hướng | Dung sai ±1% |
|---|---:|---:|---:|---:|---:|
| price_32 | 0.016390 ± 0.002035 | 1.1100 | 1.5610 | 52.95% | 55.60% |
| macro_38 | 0.016409 ± 0.001915 | 1.1164 | 1.5707 | 55.00% | 54.95% |
| financial_42 | 0.016473 ± 0.001815 | 1.1167 | 1.5730 | 52.95% | 54.95% |

Cùng cấu hình XGBoost trên cùng các phiên, thêm khối thị trường/vĩ mô nâng độ đúng hướng từ 52,95% lên 55,00%, đồng thời MAE giá tăng từ 1,1100 lên 1,1164 nghìn VND. Thêm bốn chỉ tiêu FPT cho MAE 1,1167 và độ đúng hướng 52,95%. Mỗi độ đo trả lời một câu hỏi khác nhau. Chênh lệch này mô tả mẫu Test hiện tại.

Bộ 38 biến đoán đúng thêm 9 trên 440 phiên có đổi giá, đồng thời tăng sai số khi dự báo mức giá. Bộ 42 biến quay về 233 phiên đúng hướng. Tần suất cập nhật thấp và độ trễ của số liệu quý là những giả thuyết để giải thích kết quả này.

Đối sánh mở rộng:

| Mô hình / cấu hình | CV RMSE log return | Test MAE giá (nghìn VND) | Test RMSE giá (nghìn VND) | Đúng hướng | Dung sai ±1% |
|---|---:|---:|---:|---:|---:|
| ARIMA | 0.015860 ± 0.002130 | 1.1106 | 1.5636 | 52.27% | 55.16% |
| SARIMAX | 0.016629 ± 0.000984 | 1.2753 | 1.7415 | 52.27% | 47.69% |

SARIMAX và ARIMA cùng đạt 52,27% đúng hướng. SARIMAX có sai số giá lớn hơn, với MAE 1,2753 so với 1,1106 nghìn VND/cổ phiếu.

### 6.5. Kết quả thật: thí nghiệm 3, nhớ 20 hay 60 phiên?

| Mô hình / cấu hình | CV RMSE log return | Test MAE giá (nghìn VND) | Test RMSE giá (nghìn VND) | Đúng hướng | Dung sai ±1% |
|---|---:|---:|---:|---:|---:|
| GRU L=20 | 0.016068 ± 0.002157 | 1.1131 | 1.5624 | 49.09% | 56.26% |
| GRU L=60 | 0.016054 ± 0.002182 | 1.1114 | 1.5618 | 49.77% | 55.16% |

CV chọn L=60 vì 0,016054 < 0,016068. Trong Test, L=60 có MAE 1,1114 và L=20 có MAE 1,1131 nghìn VND. L=20 đạt nhiều phiên trong dung sai ±1% hơn.

## Phần 7. Theo một dòng dữ liệu thật qua từng file

Phiên đầu vào **2025-09-29**, phiên mục tiêu **2025-09-30**. Đây là dự báo Test của ARIMA, không dùng mô hình học lại để dựng ví dụ đánh giá.

| Cột raw | Giá trị |
|---|---:|
| open | 86.79750 |
| high | 86.79750 |
| low | 84.75625 |
| close | 84.75625 |
| volume | 10,430,900 |

1. `fetch_data.py` kiểm tra schema/ngày/số/hash; `--verify` không sửa giá.
2. `eda.py` dùng hàng này trong thống kê và hình; không dạy mô hình.
3. `features.py` tạo `return_1d = -0.02051282`, `sma_5_ratio = -0.02251791`, `rsi_14 = 0.35085516` cùng các cột khác từ quá khứ đến phiên t. RSI lưu thang 0–1, nhân 100 để đọc thang quen thuộc.
4. `prepare.py` ghép nguồn có hiệu lực, giữ chỉ số phiên và cửa sổ hợp lệ. Hàng thuộc Test vì ngày mục tiêu sau 29/11/2023.
5. Nhãn sau khi có kết quả thật: `ln(82.54000/84.75625) = -0.026496466`. Không đưa nhãn vào đầu vào.
6. `train.py` dự báo log return `0.001002175`, suy ra giá `84.75625 × exp(0.001002175) ≈ 84.84123`. Dự báo mang dấu dương (Tăng), thực tế mang dấu âm (Giảm). Sai số tuyệt đối là `84.84123 − 82.54 ≈ 2.30123` nghìn VND/cổ phiếu.
7. `predict.py` dùng bản ARIMA học lại trên tất cả nhãn. Tại 30/09/2025, log return dự báo khoảng 0,000955963. Close 82,54 nhân exp của số đó cho 82,61894 nghìn VND, tăng khoảng 0,09564%.

### 7.1. Bản đồ hàm chính

| Module / hàm | Đầu vào và xử lý | Đầu ra |
|---|---|---|
| fetch_data: normalize_ohlcv, audit_ohlcv, verify_snapshot | Giá nguồn → schema; kiểm tra thứ tự, số, hash | OHLCV và kiểm định |
| fetch_supplemental: release_aware_asof, run_from_cache | Đọc bộ dữ liệu nghiên cứu đã chuẩn hóa, lấy số có hiệu lực gần nhất và kiểm tra tuổi dữ liệu | Bảng bổ trợ và kiểm toán |
| features: load_price_data, _rsi, build_feature_table | Cutoff trước nhãn; tính chỉ báo từ quá khứ | Đặc trưng, nhãn và hàng cuối chưa có nhãn |
| prepare: merge_supplemental, build_experiment_table, feature_groups | Ghép cột khai báo, lọc cửa sổ, định nghĩa 32/38/42 | Cohort và ngữ cảnh |
| train: _chronological_splits, cv_splits | Chia ngày mục tiêu và 5 fold có gap | Chỉ số hàng, ranh giới |
| train: make_estimator, fit_candidate, _search | Tạo thuật toán; fit fold và tính điểm | Dự báo log return, artefact, CV |
| train: select_main_ids, run_training | Chọn bằng CV trước Test; ghi 3 thí nghiệm; học lại | CSV, mô hình, kế hoạch |
| sequence_models: _windows, fit_predict_sequence | Lấy L phiên liền nhau, scaler Train, học GRU | Trọng số/scaler và dự báo |
| sequence_models: fit_predict_statistical, _statistical_roll | Fit thống kê; dự báo trước cập nhật trạng thái | Dự báo từng bước, hội tụ |
| metrics: restore_price, direction_from_return, evaluate_returns | Log return → giá/dấu; chấm đúng mẫu số | Các độ đo |
| plots: draw_experiments | Bảng điểm và dự báo → đồ thị | figures/ |
| time_series_analysis: stationarity, run_analysis | Giá/return → kiểm định, ACF/PACF, STL | CSV/JSON và hình |
| explain: explain, error_cases | XGBoost Train-only; tráo cột, SHAP; 3 lỗi lớn | Importance, hình, ca lỗi |
| predict: predict_latest | Bản học lại và hàng mới nhất | latest_prediction.json |

### 7.2. Tests bảo vệ điều gì?

Kiểm thử kiểm tra dữ liệu/đơn vị, cutoff trước nhãn; sửa tương lai không làm đổi đặc trưng quá khứ; báo cáo chưa công bố không điền về trước; scaler Train; cửa sổ không nhảy phiên; ARIMA dự báo trước nhận kết quả; dấu 0; phép đổi giá; tính lại metric từ từng dự báo khớp CSV; XGBoost cùng cấu hình; đúng 9 artefact đánh giá.

Chạy `python -m pytest -q` để kiểm tra các quy tắc trên. Mở notebook bằng kernel mới rồi chạy các ô từ đầu để kiểm tra tính tái lập của luồng thực nghiệm. [Kết quả kiểm chứng bản nghiên cứu 2013](../reports/study_2013_validation.json)

## Phần 8. Giải thích mô hình và ba ca lỗi thật

### 8.1. Permutation Importance: tráo thông tin để thử mức phụ thuộc

Giả sử RMSE gốc 0,018754. Giữ mô hình, tráo giá trị cột SMA5 ratio giữa các phiên, giữ các cột và đáp án khác. Nếu RMSE thành 0,018957:

    Mức tăng lỗi = 0,018957 − 0,018754 = 0,000203.

Tráo `ema_10_ratio` làm RMSE log return tăng trung bình khoảng 0,00009500 qua 10 lần. Hai biến kế tiếp là `macd_ratio` và `return_5d`.

Giá trị âm nghĩa tráo làm lỗi giảm. Có thể cột gây nhiễu, mô hình dùng chưa đúng hoặc ngẫu nhiên mẫu; không tự xóa cột sau xem Test. Hai cột tương quan có thể thay thế nhau, làm tráo một cột ít tác động. Tráo cũng có thể tạo tổ hợp phi thực tế theo thời gian. Đây là công cụ giải thích có giới hạn.

### 8.2. SHAP là phần bổ trợ

Dự báo nền 0,001, đóng góp +0,002 và −0,0015 → tổng 0,0015. SHAP chia chênh lệch dự báo so với nền theo một quy tắc phân bổ. Khác permutation: SHAP chia đầu ra, permutation đo lỗi tăng.

Mỗi chấm là một hàng; vị trí ngang là đóng góp log return, phải đẩy dự báo lên, trái kéo xuống. Màu là giá trị đặc trưng cao/thấp, không phải nhãn. Nền gồm 100 hàng Train; giải thích 150 hàng Test. Thuyết trình chính chỉ cần permutation, SHAP để trả lời thêm.

### 8.3. Ba ca sai số lớn nhất của ARIMA

| Ngày mục tiêu | Giá hôm trước | Giá thực tế | Giá dự báo | Sai số tuyệt đối | FPT thực tế | VN-Index cùng phiên |
|---|---:|---:|---:|---:|---:|---:|
| 2025-04-03 | 93.3561 | 86.8508 | 93.4497 | 6.5990 | -6.97% | -6.68% |
| 2025-04-16 | 88.7678 | 82.5641 | 88.8568 | 6.2926 | -6.99% | -1.42% |
| 2025-02-03 | 117.3808 | 111.3369 | 117.4984 | 6.1616 | -5.15% | -0.95% |

Cả ba phiên FPT giảm mạnh trong khi ARIMA(0,0,0) dự báo tăng khoảng 0,10%. Ngày 03/04/2025, FPT và VN-Index cùng giảm trên 6%. Ngày 16/04, FPT giảm 6,99% và VN-Index giảm 1,42%. Sau kỳ nghỉ, đầu vào 24/01 dự báo phiên 03/02. Các số VN-Index cùng phiên chỉ mô tả bối cảnh sau khi chấm.

## Phần 9. Mười câu vấn đáp

**1. Dự án dự báo giá hay hướng?** Chỉ học log return. Giá bằng close hiện tại nhân exp dự báo; hướng là dấu. Hai đầu ra nhất quán và được chấm theo hai góc nhìn.

**2. Vì sao chỉ năm phương pháp?** Chúng đại diện giữ nguyên, tuyến tính, cây phi tuyến, phụ thuộc chuỗi và bộ nhớ học sâu. Nhóm so sánh sâu theo cùng quy trình thay vì tăng số thuật toán gần nhau.

**3. Baseline MAE thấp sao đúng hướng 0%?** Nó trả đứng giá. Giá hôm nay thường gần giá ngày mai, nhưng trên phiên thực tế tăng/giảm thì đứng giá không đúng dấu.

**4. Vì sao không thêm LSTM/Transformer?** GRU đã đại diện học sâu tuần tự, phù hợp dữ liệu/tài nguyên. Nhóm kiểm tra có kiểm soát bộ nhớ 20/60; thêm mạng chỉ hữu ích khi có câu hỏi riêng và đủ thời gian phân tích.

**5. Thêm vĩ mô và báo cáo quý giúp gì?** Bộ 38 biến tăng độ đúng hướng nhưng MAE giá nhích lên. Thêm bốn chỉ tiêu quý quay về mức đúng hướng của bộ 32 biến. So cùng phiên và cấu hình XGBoost trước khi kết luận.

**6. Chống leakage thế nào?** Đặc trưng chỉ đến t; nguồn bổ trợ sau hiệu lực; scaler Train từng fold; chia thời gian có gap; cửa sổ giữ phiên gốc. Nguồn điều chỉnh và ngày công bố giả định vẫn là giới hạn phải nêu.

**7. ADF p nhỏ chứng minh mô hình tốt chưa?** Chưa. ADF bác bỏ nghiệm đơn vị nhưng KPSS vẫn bác bỏ dừng mức. Hiệu quả dự báo phải được đo riêng, không suy từ một kiểm định.

**8. Vì sao chọn ARIMA?** ARIMA có RMSE log return thấp nhất trong Train CV. Nhóm áp dụng quy tắc đã đặt trước khi đọc Test. Nếu chấm bằng MAE giá trên Test, Last-Close nhỉnh hơn rất ít.

**9. Đúng hướng 55% có đáng kể không?** XGBoost 38 biến đúng 242/440 phiên đổi giá. Quy tắc luôn dự báo tăng đúng 230/440 phiên vì tập này có 230 phiên tăng. Mức hơn 12 phiên mô tả đợt Test này, còn độ ổn định cần kiểm tra trên các giai đoạn khác.

**10. SHAP/permutation có xác định nguyên nhân kinh tế?** Không. Chúng giải thích hành vi mô hình: một bên phân bổ đầu ra, một bên đo lỗi tăng khi tráo thông tin. Cần thiết kế khác để nói nhân quả.

## Phần 10. Từ điển nhanh và cách học

| Từ | Nghĩa đơn giản |
|---|---|
| Snapshot | Bản dữ liệu cố định để dùng lại |
| Feature / target | Số máy nhìn / đáp án cần học |
| Train / Test | Phần học / phần kiểm tra sau chọn |
| CV / fold | Nhiều lượt học quá khứ rồi chấm đoạn sau / một lượt |
| Gap | Hàng chừa giữa học và kiểm định |
| Hyperparameter | Cài đặt chọn trước fit, như độ sâu cây |
| Fit / predict | Học quy tắc / dùng quy tắc dự báo |
| Scaler / Pipeline | Bộ đổi thang số / chuỗi bước gắn với mô hình |
| Cohort | Tập ngày đủ điều kiện giữ chung |
| Lookback / sliding window | Số phiên nhìn lại / đoạn lịch sử trượt theo ngày |
| Epoch / batch / seed | Một lượt học / nhóm mẫu mỗi lần cập nhật / số cố định ngẫu nhiên |
| Regularization | Phạt độ phức tạp để bớt bám nhiễu |
| Exog / state update | Biến ngoài chuỗi FPT / cập nhật bộ nhớ sau quan sát |
| Artefact | Tệp mô hình, scaler hoặc kết quả lưu lại |
| Point-in-Time / vintage | Thông tin biết tại thời điểm dự báo / phiên bản số liệu đã công bố |
| Look-ahead / leakage | Vô tình cho máy nhìn tương lai |
| Ablation | Giữ cách học, thay nhóm dữ liệu để đo đóng góp |
| MAE / RMSE / MAPE | Sai số tuyệt đối trung bình / bình phương rồi căn / sai số phần trăm trung bình |
| Tolerance | Ngưỡng lệch giá được chấm đạt |
| ACF / PACF | Liên hệ với trễ / liên hệ sau kiểm soát trễ trung gian |
| Residual | Phần chưa được mô hình hoặc phân rã giải thích |
| Permutation / SHAP | Tráo cột đo mức phụ thuộc / chia đóng góp vào dự báo |

Học nhanh: đọc phần 0 → 4 → 5 → 6 trước, rồi phần dữ liệu/chỉ báo để hiểu từng cột. Mở notebook 00 để chạy toàn bộ, hoặc 01–09 để học từng bước; chạy từ trên xuống. Khi đổi dữ liệu phải chạy lại đặc trưng, CV, Test và giải thích. Không dùng số cũ cho phiên bản mới.

Giới hạn nghiên cứu và hướng kiểm chứng tiếp tập hợp ở cuối `docs/REPORT.md`. Không học thuộc một con số như quy luật của thị trường.
