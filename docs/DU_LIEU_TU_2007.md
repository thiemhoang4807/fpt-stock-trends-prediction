# Tìm và kiểm tra dữ liệu bổ trợ từ năm 2007

Ngày kiểm tra: 19/11/2026. Mốc nghiên cứu vẫn là **30/09/2025**.

**Có thể tìm được dữ liệu trước 2018–2019.** Hai mốc này là giới hạn của các tệp CPI/vàng đã thu thập trước đây, không phải bằng chứng rằng các chỉ số đó chưa tồn tại. Đợt này đã tải được lịch sử CPI và GDP dài hơn, một phần lịch sử vàng, cùng báo cáo tài chính FPT cũ. Tuy nhiên, bộ 43 biến chưa đủ điều kiện để huấn luyện liên tục từ 2007.

Các bản mới nằm riêng tại [data/research/history_2007](../data/research/history_2007/). Dữ liệu huấn luyện, mô hình và điểm thực nghiệm hiện tại chưa thay đổi. [audit.json](../data/research/history_2007/audit.json) ghi số liệu kiểm tra; [download_history.json](../data/research/history_2007/download_history.json) ghi URL, thời điểm tải, lỗi và hash.

## 1. Tìm được gì, còn thiếu gì?

| Biến | Bản đang dùng | Kết quả tìm kiếm và tải thực tế | Điều kiện còn thiếu trước khi thay dữ liệu Train |
|---|---|---|---|
| Giá/khối lượng FPT | 4.671 phiên từ 02/01/2007 | Đã có lịch sử giá, không cần kéo dài phần đầu | Đối chiếu 3 hàng OHLC bất nhất và 2 hàng volume bằng 0 trong kiểm toán hiện có |
| USD/VND | 4.893 quan sát từ 01/01/2007 | Đã có từ 2007 | Giữ cùng đơn vị, cơ sở giá và thời điểm có thể biết |
| VN-Index | 4.635 phiên từ 2007 | Tải lại API DNSE: số phiên và giá đóng cửa không đổi | Vẫn thiếu 36 ngày so với lịch FPT; chưa biết tất cả là thiếu nguồn hay khác lịch giao dịch |
| CPI Việt Nam | 81 ngày công bố từ 12/2018 | **249 tháng chỉ số CPI, 01/2005–09/2025**, không thiếu tháng; tính được **237 tháng tăng cùng kỳ**, 01/2006–09/2025 | API không cung cấp lịch công bố từng tháng hoặc bản số liệu được biết tại từng thời điểm lịch sử |
| GDP Việt Nam | 15 năm, 2010–2024 | **20 năm, 2005–2024**, không thiếu năm | Có sửa đổi số liệu; cần nêu giới hạn phiên bản và quy tắc ngày sử dụng |
| Vàng XAU/USD | 1.755 ngày từ 2019 | **2.182 thanh giá ngày thuộc 7 năm rời**: 2006, 2007, 2008, 2014, 2016, 2017, 2020 | Thiếu tệp của 13 năm trong 2007–2025; nguồn mới khác cơ sở giá/giờ đóng ngày; máy chủ đã trả HTTP 429 |
| Báo cáo tài chính FPT | 52 quý, thiếu 22 quý 2007Q3–2012Q4 | Đã lưu PDF thường niên 2007 và quý II/2009, I/II/III/2010; trích các giá trị để kiểm tra | Chưa khôi phục đủ 22 quý; cần thống nhất cách ghi nhận doanh thu, số riêng quý, phiên bản và ngày công bố |
| Cổ phiếu lưu hành | 10 mốc; ngày có thể dùng sớm nhất thuộc 2018 | Xác minh được số cuối 2006 và cuối 2007 trong thuyết minh báo cáo 2007 | Hai điểm cuối năm không tạo thành lịch thay đổi vốn đầy đủ; chưa xác minh ngày công bố của bản báo cáo đang lưu |

**Không thể chỉ thêm CPI/vàng rồi khẳng định toàn bộ dữ liệu đã chạy được từ 2007.** Báo cáo quý và lịch cổ phiếu lưu hành vẫn giới hạn bộ 43 biến. Bộ giá 32 biến có lịch sử dài hơn, nhưng các thí nghiệm đang dùng cùng cửa sổ dữ liệu để so sánh công bằng.

## 2. CPI: lấy ở đâu, đổi sang biến đang dùng như thế nào?

Nguồn mới là **World Bank Global Economic Monitor (GEM)**, mã `CPTOTNSXN`, quốc gia `VNM`, nguồn API số 15. Metadata của World Bank ghi đây là chỉ số giá tiêu dùng chưa điều chỉnh mùa vụ, tính toán dựa trên dữ liệu Datastream. Đây là nguồn khác với tệp lịch công bố Investing.com đang dùng.

- [API CPI tháng 2005–09/2025](https://api.worldbank.org/v2/country/VNM/indicator/CPTOTNSXN?source=15&date=2005M01:2025M09&format=json&per_page=1000).
- [Định nghĩa chỉ tiêu của World Bank](https://api.worldbank.org/v2/indicator/CPTOTNSXN?source=15&format=json).
- [Chỉ số CPI đã chuẩn hóa](../data/research/history_2007/cpi_monthly_index.csv).
- [CPI tăng cùng kỳ đã tính](../data/research/history_2007/cpi_monthly_yoy.csv).

API trả về **mức chỉ số giá**, không phải tỷ lệ lạm phát %. Để tạo `cpi_yoy_pct`:

\[
\mathrm{CPIYoY}_m = 100\left(\frac{I_m}{I_{m-12}}-1\right).
\]

Ví dụ chỉ số cùng tháng năm trước bằng 100, tháng này bằng 103 thì `(103 / 100 - 1) × 100 = 3%`. Cần đủ 12 tháng trước đó, nên tải từ 2005 thay vì chỉ tải từ 2007. Script kiểm tra lịch tháng liên tục trước khi dịch 12 hàng; nếu thiếu một tháng, 12 hàng có thể không còn là 12 tháng và phép tính sẽ sai.

Đối chiếu 81 quan sát cũ: độ lệch tuyệt đối lớn nhất là **0,039790 điểm phần trăm**. Tuy nhiên, tệp cũ chỉ lưu ngày công bố, chưa lưu tháng tham chiếu. Bảng đối chiếu đang suy đoán: ngày công bố từ 1–15 thuộc tháng trước, các ngày còn lại thuộc tháng hiện tại. Quy tắc này chỉ phục vụ khảo sát, chưa phải bằng chứng xác minh toàn bộ lịch công bố. Chi tiết tại [cpi_overlap_diagnostic.csv](../data/research/history_2007/cpi_overlap_diagnostic.csv).

Không thay `publication_date` bằng `period_end`: CPI tháng 09/2025 có trong API hôm nay không có nghĩa nó đã được biết khi FPT đóng cửa ngày 30/09/2025. Các ô `publication_date` còn trống được giữ đúng nghĩa **chưa xác minh**, không phải thiếu giá trị CPI. Có thể nghiên cứu giả định trễ sau cuối tháng, nhưng phải công bố giả định và kiểm tra độ nhạy; không gọi đó là ngày công bố thực tế.

Metadata bản tải này ghi `lastupdated = 2026-09-08`. Đây là ngày cập nhật của nguồn API, không phải ngày công bố của từng quan sát. Chỉ dùng các tháng tham chiếu đến cutoff vẫn chưa loại được rủi ro dữ liệu quá khứ đã bị sửa đổi trong bản tải mới.

## 3. GDP: có trước 2010, nhưng cần đúng loại chỉ tiêu

Nguồn là **World Bank World Development Indicators**, mã `NY.GDP.MKTP.CD`: GDP danh nghĩa theo **USD hiện hành**, tần suất **năm**.

- [API GDP 2005–2024](https://api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.CD?date=2005:2024&format=json&per_page=100).
- [Dữ liệu đã chuẩn hóa](../data/research/history_2007/gdp_annual.csv).

Ví dụ GDP năm 2007 trong bản tải bằng khoảng **77,414 tỷ USD**. Không diễn giải nó thành tốc độ tăng trưởng GDP, GDP theo quý hoặc giá trị đã loại lạm phát. Tải cả năm 2005–2006 cung cấp dữ liệu trước mốc nghiên cứu, nếu chọn giả định sử dụng số năm trước sau một độ trễ nhất định.

So với 15 năm đang dùng, sai lệch tương đối lớn nhất khoảng **0,013363%**; số năm 2023–2024 đã thay đổi nhẹ. Bản API có mốc cập nhật `2026-11-11`. Khi nghiệm thu cần chọn một phiên bản nhất quán và lưu nguồn, không ghép tùy tiện các phiên bản để làm các số trùng nhau. Xem [gdp_overlap.csv](../data/research/history_2007/gdp_overlap.csv).

## 4. Vàng: có dữ liệu 2007, hiện chưa tải đủ chuỗi liên tục

Nguồn thử nghiệm là **Dukascopy XAU/USD**, thanh giá ngày **BID** theo UTC, đơn vị USD/ounce. Đây không phải giá vàng miếng SJC và không phải chuỗi giá vàng tương lai. Nó cũng không mặc nhiên trùng với giá đóng cửa Investing.com trong bộ hiện tại.

- [Công cụ lịch sử chính thức của Dukascopy](https://www.dukascopy.com/api/data/get/historical-data-export).
- [Tệp giá năm 2007 đã tải](https://datafeed.dukascopy.com/datafeed/XAUUSD/2007/BID_candles_day_1.bi5).
- [CSV các năm đã giải mã](../data/research/history_2007/gold_daily_partial.csv).

Tệp nhị phân nén LZMA chứa 24 byte cho mỗi thanh: thời gian, mở cửa, đóng cửa, thấp nhất, cao nhất, chỉ số hoạt động của nguồn. Giá nguyên chia cho 1.000; hệ số được đối chiếu với [metadata của bộ đọc định dạng tương ứng](https://raw.githubusercontent.com/Leo4815162342/dukascopy-node/v1.43.0/src/utils/instrument-meta-data/generated/instrument-meta-data.json). Chỉ số hoạt động không được hiểu là khối lượng cổ phiếu hoặc số ounce vàng vật chất giao dịch.

Riêng 2007 có 365 hàng lịch; bỏ 52 hàng có toàn bộ OHLC bằng nhau và hoạt động bằng 0, còn **313 thanh**. Một số thanh Chủ nhật là có thật trong lịch UTC của nguồn, không được tự xóa chỉ vì trùng cuối tuần. Ngày của thanh là lúc mở ngày UTC; giá đóng của ngày đó chỉ hoàn tất ở đầu ngày UTC kế tiếp, tương đương 07:00 giờ Việt Nam. CSV lưu rõ `bar_complete_at_utc`.

Trên **260 ngày trùng năm 2020**, mức lệch giá tuyệt đối tương đối trung bình là **0,132181%**, lớn nhất **1,331965%**. Sai khác này có thể liên quan đến BID so với giá nguồn khác và cách chốt ngày; đối chiếu hiện tại chưa tách được từng nguyên nhân. Không ép hai chuỗi khớp bằng một hệ số rồi nối đuôi. Xem [gold_overlap.csv](../data/research/history_2007/gold_overlap.csv).

Các năm còn thiếu tệp: **2009–2013, 2015, 2018–2019, 2021–2025**. Các lần tải gặp timeout, ngắt kết nối và sau đó HTTP **429 — Too Many Requests**. Đây là hạn chế tải trong lần kiểm tra, không chứng minh nhà cung cấp không có lịch sử đó. Script mới dừng gọi một máy chủ ngay khi gặp 429 và giữ các năm đã tải. Có thể thử lại sau hoặc xuất CSV qua công cụ chính thức; không điền bằng nội suy để che các khoảng trống năm.

Để quy đổi vàng sang VND/ounce về sau: `gold_usd_per_ounce × usd_vnd_rate`. Cần ghép cả hai theo thông tin đã có tại lúc dự báo, kiểm tra thời gian cập nhật và độ cũ của từng nguồn; không nhân với một tỷ giá của tương lai.

## 5. Báo cáo FPT: tìm thấy tài liệu cũ, cần thống nhất cách đọc

Đã tải **5 PDF do FPT lập**, lưu trên kho tài liệu tài chính công khai của CafeF. Bản nguồn, URL và hash được giữ để có thể kiểm tra lại:

| Tài liệu | Trang PDF đã đối chiếu trực quan (đếm từ 1) | Dữ liệu trích |
|---|---:|---|
| [Thường niên 2007](../data/research/history_2007/raw/fpt_2007_annual.pdf) | 44 và 65 | Kết quả cả năm; cổ phiếu tại cuối 2006 và 2007 |
| [Quý II/2009](../data/research/history_2007/raw/fpt_2009q2.pdf) | 5 | Số riêng quý, lũy kế và cột so sánh |
| [Quý I/2010](../data/research/history_2007/raw/fpt_2010q1.pdf) | 4 | Doanh thu, lợi nhuận gộp, lãi vay, lợi nhuận trước thuế và lợi nhuận cổ đông công ty mẹ |
| [Quý II/2010](../data/research/history_2007/raw/fpt_2010q2.pdf) | 4 | Các chỉ tiêu riêng quý II |
| [Quý III/2010](../data/research/history_2007/raw/fpt_2010q3.pdf) | 2 | Các chỉ tiêu riêng quý III |

Các số đã đọc nằm tại [fpt_financial_evidence.csv](../data/research/history_2007/fpt_financial_evidence.csv), không phải bảng đầu vào được tự động ghép vào Train. Có ba vấn đề đáng chú ý:

1. **Khác cách trình bày doanh thu.** Báo cáo quý II/2009 ghi dòng doanh thu 8.799.390.127.379 VND; một dòng khác ghi doanh thu bán cho bên thứ ba 4.051.314.434.591 VND. Không được chọn tùy dòng rồi gắn chung tên `fpt_net_revenue_vnd`. Cần đọc thuyết minh và thống nhất định nghĩa qua các thời kỳ.
2. **Số so sánh có thể đổi giữa các bản báo cáo.** Cùng quý II/2009, dòng doanh thu trong báo cáo quý II/2009 là 8.799.390.127.379 VND, nhưng cột năm trước ở báo cáo quý II/2010 là 9.271.528.221.342 VND. Chưa xác minh được toàn bộ nguyên nhân chênh lệch; không dùng số trong bản 2010 để giả định nhà đầu tư đã biết nó năm 2009.
3. **Ngày lập khác ngày công bố.** Ví dụ báo cáo quý II/2009 ghi lập ngày 24/07/2009. CSV lưu `report_prepared_date`, còn `publication_date` để trống nếu chưa có bằng chứng ngày phát hành. Không biến ngày ký hoặc tên tệp thành ngày công bố đã xác minh.

EBIT trong các quý có đủ trường được tính bằng lợi nhuận trước thuế cộng chi phí lãi vay. Ví dụ quý II/2009: `395.272.053.315 + 15.652.650.645 = 410.924.703.960 VND`. Với năm 2007, bảng trích này chưa đối chiếu chi phí lãi vay nên để EBIT trống. Hai phép đối chiếu doanh thu trừ giá vốn trừ lợi nhuận gộp lệch 1 VND ngay trong bảng nguồn; giữ nguyên và ghi nhận, không âm thầm sửa số.

Về cổ phiếu, cuối 2007 có **91.899.459 cổ phiếu phổ thông lưu hành**, **435.520 cổ phiếu ưu đãi lưu hành**, tổng **92.334.979 cổ phiếu lưu hành**. Số đã phát hành **92.352.579** còn gồm **17.600 cổ phiếu quỹ**. Bốn khái niệm này khác nhau. Bảng [fpt_shares_evidence.csv](../data/research/history_2007/fpt_shares_evidence.csv) giữ riêng từng loại. Số tại cuối 2006 được báo cáo lại trong tài liệu năm 2007, chưa đủ bằng chứng để gán khả dụng ngay ngày đầu 2007.

## 6. Cách chạy và các tệp được sinh ra

Từ thư mục gốc dự án, với môi trường `requirements.txt` hiện tại:

```bash
# Dựng lại CSV và báo cáo kiểm tra từ các phản hồi đã lưu; không cần mạng.
python src/fetch_historical_candidates.py

# Tải phản hồi CPI/GDP còn thiếu. Tệp đã có được giữ nguyên.
python src/fetch_historical_candidates.py --download

# Sau khi nguồn vàng hoạt động lại, thử tải riêng những năm chưa có.
python src/fetch_historical_candidates.py --download --gold-years 2009 2010 2011 2012 2013 2015 2018 2019 2021 2022 2023 2024 2025

python -m pytest -q
```

Lệnh tải giữ cache, không tự thay bằng phiên bản API mới nhất. Muốn khảo sát một phiên bản mới cần lưu ở bản sao nghiên cứu riêng và ghi lại ngày tải. CSV trích báo cáo PDF được đối chiếu thủ công; script không giả vờ tự đọc đúng mọi mẫu báo cáo. Không cần cài thêm thư viện PDF để chạy lệnh dựng CSV CPI/GDP/vàng.

Phản hồi API và tệp nhị phân nằm trong `raw/`; CSV nghiên cứu, các bảng đối chiếu và `audit.json` nằm ở cấp trên. Không có lệnh nào trong script mới ghi vào `data/raw/fpt`, `data/raw/supplemental`, `data/processed`, `models/` hay bảng điểm trong `reports/`.

## 7. Nên mở rộng thí nghiệm thế nào?

**Không cần mọi biến đều bắt đầu đúng 01/01/2007.** Cần xác định thông tin nào có thể biết ở mỗi ngày và câu hỏi thí nghiệm nào đang được trả lời.

1. Giữ kết quả hiện tại làm mốc trên dữ liệu đã kiểm tra. Đợt tìm nguồn này chưa phát sinh điểm huấn luyện mới.
2. Hoàn thiện phần dễ kiểm tra trước: lịch tháng CPI và năm GDP đã đủ; bổ sung ngày công bố hoặc khai báo rõ giả định độ trễ và giới hạn số liệu điều chỉnh. Với vàng, tải đủ các năm còn thiếu và kiểm tra lại toàn chuỗi cùng một nguồn.
3. Tài chính cần tiếp tục tìm **22 quý 2007Q3–2012Q4** của snapshot đang dùng và lịch thay đổi cổ phiếu trước 2018. Các PDF mới tìm là đầu mối để khôi phục một phần, chưa phải xác nhận đã lấp hết khoảng trống.
4. Nếu lịch tài chính không đủ, có thể thiết kế một thí nghiệm dài chỉ dùng giá cùng các biến vĩ mô đã đủ, và một thí nghiệm ngắn thêm báo cáo tài chính. Trong mỗi phép so sánh phải dùng cùng tập ngày, cùng Test và cùng quy tắc chọn mô hình bằng CV. Không so hai điểm rồi quy hết khác biệt cho biến tài chính khi thời kỳ Test đã khác.
5. Khi thay dữ liệu thật, chạy lại kiểm toán → ghép theo thời điểm có thể biết → tạo đặc trưng → CV trên Train → Test → dự báo/giải thích. Lưu phiên bản dữ liệu và kết quả mới; không gắn điểm hiện tại vào bộ dữ liệu kéo dài đến 2007.

Đích của việc mở rộng là tăng độ phủ và kiểm tra tính ổn định qua các giai đoạn thị trường. Không chọn nguồn, khoảng thời gian hay cách sửa số để làm đẹp điểm Test.
