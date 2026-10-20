# Xuất xứ và kiểm định dữ liệu

## Chuỗi xuất xứ OHLCV FPT

```text
API lịch sử giá VCI (Vietcap)
        │  vnstock.Quote(symbol="FPT", source="VCI").history(...)
        ▼
Notebook trích xuất của DS111 UIT
        │  giữ sáu trường time, open, high, low, close, volume; xuất CSV
        ▼
Snapshot được lưu trong repo DS111 UIT
        │  4.678 phiên, 2007-01-02–2025-10-09
        ▼
src/fetch_data.py của dự án này
        ├── --download: gọi lại vnstock/VCI và chuẩn hóa OHLCV
        ├── --input: chuẩn hóa CSV do API/widget xuất thủ công
        └── --verify: kiểm tra schema, khoảng ngày và SHA-256 snapshot
```

Repo [DS111 UIT Stock Price Analysis](https://github.com/nguyenlog205/ds111-uit-stock-price-analysis) lưu notebook trích xuất tại [`notebook/data_ingestion/API_use.ipynb`](https://github.com/nguyenlog205/ds111-uit-stock-price-analysis/blob/main/notebook/data_ingestion/API_use.ipynb). Notebook import `Quote`, `Listing` và `Finance` từ `vnstock`; với giá FPT, nó gọi `Quote(symbol='FPT', source='VCI')`, sau đó `history(start='2007-01-01', end='2025-10-09')` và ghi kết quả ra CSV. Không có widget TradingView/Investing hay Selenium/Playwright trong luồng lấy giá này. `vnstock` là thư viện trung gian; `VCI` là nguồn dữ liệu được chọn trong thư viện. Tài liệu/mã hiện tại của vnstock mô tả phương thức lịch sử OHLCV và bộ chuyển đổi VCI; phiên bản API có thể đã thay đổi sau thời điểm notebook được tạo ([hướng dẫn Quote](https://github.com/vnstock-hq/vnstock-agent-guide/blob/main/docs/vnstock/advanced-usage/06-quote-price-api.md), [mã VCI Quote](https://github.com/thinh-vu/vnstock/blob/main/vnstock/explorer/vci/quote.py)).

Notebook lưu sáu trường OHLCV nguyên trạng, không nhân/chia giá và không thêm cột giá điều chỉnh. Giá trong snapshot được hiểu theo **nghìn đồng/cổ phiếu** (ví dụ close `94.2` tương ứng khoảng 94.200 đồng). Cách hiểu này được củng cố bởi báo cáo đồ án nguồn, trong đó sai số dự báo giá được ghi theo nghìn VND; notebook/CSV không gắn metadata đơn vị riêng cho cột OHLC. Báo cáo cũng ghi chung tiền tệ là VND trừ khi có chú thích, nên đơn vị này được đọc cùng thang giá và kết quả được trình bày. Snapshot không có cột hoặc tham số ghi rõ `adjusted`/`unadjusted`. Chuỗi không có bước hiệu chỉnh tại dự án DS111 và biến động ngày lớn nhất xấp xỉ giới hạn biên độ giao dịch, phù hợp với dữ liệu lịch sử đã được nhà cung cấp quy đổi theo sự kiện doanh nghiệp; tuy vậy, từ artefact đã lưu không thể xác định chắc chắn API đã điều chỉnh những loại sự kiện nào (chia/tách, cổ phiếu thưởng, quyền mua, cổ tức tiền mặt). Vì vậy, chúng tôi ghi nhận basis là **VCI trả về, có khả năng đã điều chỉnh lịch sử; chính sách chi tiết chưa được xác nhận**, không tự sửa chuỗi.

Lịch sử Git cho thấy snapshot OHLCV và notebook/API được đưa vào repo nguồn ở commit `65c7780` ngày 2025-10-16; commit `96a6524` cùng ngày sắp xếp notebook vào `notebook/data_ingestion/`; commit `bf714a1` ngày 2025-11-10 chuyển tệp sang `data/raw/fpt/`. `requirements.txt` của repo nguồn không khai báo `vnstock` dù notebook import thư viện này, nên cần cài riêng nếu muốn chạy lại notebook cũ.

## Thu thập dữ liệu lại

Môi trường dự án chính vẫn dùng snapshot đã khóa để kết quả thí nghiệm ổn định. Để gọi lại VCI, cài vnstock theo [hướng dẫn cài chính thức](https://www.vnstocks.com/docs/vnstock/v4/gioi-thieu-vnstock), sau đó chạy:

```bash
python -m pip install -U --extra-index-url https://vnstocks.com/api/simple vnstock vnai
python src/fetch_data.py --download --start 2007-01-01 --end 2025-10-09 \
  --output data/raw/fpt/fpt_historical_price.csv
```

Nếu đã tải dữ liệu bằng công cụ/widget và xuất CSV, chuyển đổi các cột ngày, OHLC và volume về schema chuẩn bằng:

```bash
python src/fetch_data.py --input path/to/fpt_export.csv \
  --output data/raw/fpt/fpt_historical_price.csv
```

Script hỗ trợ các tên cột tiếng Anh phổ biến và một số nhãn tiếng Việt; nếu tệp có cột mã, chỉ giữ `FPT`. Script sắp xếp thời gian, kiểm tra ngày trùng, giá/khối lượng thiếu hoặc không hợp lệ, rồi chỉ ghi sáu cột chuẩn. Ba dòng có quan hệ high/low bất nhất trong snapshot được giữ nguyên để không âm thầm thay đổi dữ liệu; audit báo số dòng này. Lệnh `python src/fetch_data.py --verify` kiểm tra schema, khoảng ngày, các miền giá/volume và SHA-256 của CSV sau khi chuẩn hóa LF để hash nhất quán giữa checkout CRLF trên Windows và LF trên Linux. Hash nội dung là `263eced0cb25bc0380ed0dba7dc6f8d77b409146c7b4e2b1b0fd9f0ddbf25e98`.

Hash xác nhận khả năng tái lập 100% của **các giá trị và thứ tự hàng trong snapshot đang commit** (không phân biệt LF/CRLF), không bảo đảm lần gọi API trong tương lai sẽ trả cùng dữ liệu: nhà cung cấp có thể sửa lịch sử, API hoặc chính sách điều chỉnh. `--download` tải lại toàn bộ khoảng ngày yêu cầu và thay tệp đích, không nối một phần dữ liệu vào chuỗi cũ; tệp tải mới phải được kiểm tra lại và không được coi là tương đương snapshot chỉ vì cùng ngày bắt đầu/kết thúc.

## Các dữ liệu liên quan trong repo nguồn

| Dữ liệu | Nguồn/cách lấy được repo nguồn ghi nhận | Cách xử lý trong dự án này |
|---|---|---|
| Báo cáo thu nhập FPT | Notebook `API_use.ipynb`: `vnstock.Finance(symbol='FPT', source='VCI').income_statement(period='quarter', lang='vi')` | Không dùng trong mô hình; dữ liệu quý phải gắn với ngày công bố thực tế để tránh nhìn trước. |
| USD/VND, CPI, XAU/USD | Repo nguồn ghi Investing.com; CSV có cấu trúc lịch sử/kinh tế và notebook tổng hợp dùng các tệp có sẵn | Không dùng trong mô hình hiện tại. |
| GDP Việt Nam | Repo nguồn ghi World Bank, cùng dự báo 2025 từ IMF | Không dùng; chuỗi thường niên không đồng bộ với phiên giao dịch. |
| P/E ngành ICT | Repo nguồn ghi Simply Wall St | Không dùng; chỉ có một số ngày đo lường. |
| Tin tức | `src/datasets/ingest_news.py` điều khiển Selenium trên Google News, lấy nội dung bài bằng `newspaper3k` | Không tham gia tập dữ liệu huấn luyện FPT; notebook `news_ingestion.ipynb` trong snapshot repo là tệp rỗng. |

Báo cáo đồ án nguồn ([`NHOM30_BAOCAO.pdf`](https://github.com/nguyenlog205/ds111-uit-stock-price-analysis/blob/main/NHOM30_BAOCAO.pdf)) nói chung các nguồn thị trường gồm CafeF, Vietstock và Investing; phần phương pháp xác định cụ thể rằng USD/VND, CPI, GDP, XAU/USD được tải thủ công thành CSV; market cap/P-E được chép thủ công; các trường FPT (OHLCV và tài chính) lấy qua vnstock API. README dữ liệu chi tiết ánh xạ USD/VND, CPI và XAU/USD sang Investing.com, GDP sang World Bank cùng dự báo IMF 2025, P/E ICT sang Simply Wall St. Tài liệu giữa các phiên bản không hoàn toàn nhất quán: README cũ ghi rõ GDP dùng World Bank và dự báo IMF năm 2025, trong khi README mới hơn dưới `data/raw/` bỏ trống nguồn GDP/XAU và gọi dữ liệu vàng là XAU-VND dù tên tệp/giá trị là XAU/USD. Vì vậy, nguồn của các tệp vĩ mô được dẫn theo tài liệu upstream còn lưu trong lịch sử, nhưng không xem metadata đó là đầy đủ hoặc nhất quán như nguồn VCI được chứng minh trực tiếp bằng notebook.

## Vì sao không dùng hai CSV đã xử lý sẵn

`synthetized_dataset.csv` có 1.529 ngày (2020-01-01–2025-09-30). Tỷ lệ thiếu đo trực tiếp trên bản lưu trong repo nguồn:

| Trường | Thiếu | Tỷ lệ |
|---|---:|---:|
| CPI | 1.461/1.529 | 95,55% |
| GDP | 1.524/1.529 | 99,67% |
| Market cap và P/E | 1.510/1.529 | 98,76% |
| Mỗi trường doanh thu/lợi nhuận FPT | 1.507/1.529 | 98,56% |
| Giá và volume FPT | 96/1.529 | 6,28% |

Notebook tổng hợp ghép nhiều tần suất bằng outer join theo ngày lịch, nên phần lớn ngày không có quan sát ở các chuỗi tháng/quý/năm. `predictive_modeling.csv` đã điền và chuẩn hóa dữ liệu, nhưng thời điểm fit không phù hợp để dùng lại làm đầu vào tái lập: notebook EDA gọi `pipeline.fit_transform(dataset)` trên toàn bộ bảng; `src/preprocessor.py` dùng `StandardScaler.fit_transform` cho toàn chuỗi và bù khuyết cả `bfill` lẫn `ffill`. Vì vậy thống kê ở phần cuối thời gian có thể ảnh hưởng biến đổi các ngày trước, và `bfill` có thể đưa thông tin tương lai về quá khứ. Không có mô tả lưu scaler hay quy trình fit chỉ trên train. Dự án chỉ dùng chuỗi OHLCV FPT và tự tạo lại các đặc trưng kỹ thuật từ dữ liệu tại thời điểm dự báo; scaler của mô hình hiện tại được fit trong pipeline trên phần train.

## Tệp sử dụng trong dự án

- `raw/fpt/fpt_historical_price.csv`: snapshot OHLCV gốc đã khóa bằng SHA-256.
- `processed/fpt_next_session_features.csv`: bảng đặc trưng được sinh lại bởi `python src/prepare.py`.
