# Dữ liệu đầu vào

`raw/fpt_historical_price.csv` được sao chép từ [repo DS111 UIT](https://github.com/nguyenlog205/ds111-uit-stock-price-analysis), đường dẫn gốc `data/raw/fpt/fpt_historical_price.csv`, truy cập ngày 2026-10-20. Tệp có 4.678 phiên từ 2007-01-02 đến 2025-10-09 với các cột `time, open, high, low, close, volume`. Repo nguồn không có tệp LICENSE và README không nêu rõ nhà cung cấp cụ thể cho tệp giá lịch sử; dự án giữ nguyên dữ liệu và ghi nhận xuất xứ repo nguồn.

Các biến kỹ thuật và nhãn được tạo lại từ chuỗi `close` và `volume`. Không dùng `synthetized_dataset.csv` hoặc `predictive_modeling.csv` làm đầu vào chính vì tập tổng hợp thiếu dữ liệu lớn và tệp dự đoán có các biến đã xử lý/scaled không rõ thời điểm fit.
