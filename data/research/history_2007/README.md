# Dữ liệu nghiên cứu mở rộng từ 2007

Đây là **bản ứng viên**, chưa được pipeline huấn luyện sử dụng. Xem [báo cáo nguồn, kiểm định và hướng sử dụng](../../../docs/DU_LIEU_TU_2007.md).

| Tệp | Nội dung |
|---|---|
| `cpi_monthly_index.csv` | 249 tháng CPI, 2005-01–2025-09; mức chỉ số gốc và CPI cùng kỳ |
| `cpi_monthly_yoy.csv` | 237 tháng có đủ lịch sử để tính tỷ lệ tăng cùng kỳ |
| `gdp_annual.csv` | GDP USD hiện hành, 20 năm 2005–2024 |
| `gold_daily_partial.csv` | 2.182 thanh giá BID từ 7 năm rời; chưa phải chuỗi đủ 2007–2025 |
| `cpi_overlap_diagnostic.csv` | Đối chiếu CPI bằng tháng tham chiếu suy đoán; không dùng để xác nhận lịch công bố |
| `gdp_overlap.csv`, `gold_overlap.csv` | Đối chiếu số liệu nguồn mới và bản đang dùng |
| `fpt_financial_evidence.csv` | Số đọc từ 5 PDF, giữ định nghĩa theo bảng gốc, chưa thống nhất để ghép Train |
| `fpt_shares_evidence.csv` | Hai mốc cổ phiếu cuối năm, phân biệt phổ thông/ưu đãi/quỹ |
| `raw/` | Phản hồi API, tệp vàng nén và PDF nguồn |
| `download_history.json` | Các lần tải, URL, ngày tải, mã lỗi và SHA-256 nếu thành công |
| `audit.json` | Độ phủ, đối chiếu, hash và các điều kiện chưa đạt |

`publication_date` trống nghĩa là **chưa xác minh ngày công bố**, không được thay bằng ngày kết thúc kỳ để đưa vào mô hình. API được tải năm 2026 có thể chứa các lần điều chỉnh số liệu quá khứ. Các giá trị tham chiếu đều được cắt trước hoặc tại 30/09/2025.

Từ thư mục gốc: `python src/fetch_historical_candidates.py` dựng lại các CSV API/vàng và `audit.json` ngoại tuyến. Tệp đối chiếu PDF là kết quả đọc và kiểm tra thủ công trên đúng trang đã ghi. Các điểm thực nghiệm chính thức vẫn thuộc bộ dữ liệu hiện tại trong `data/raw` và `data/processed`.
