# Dữ liệu và xuất xứ

## Pipeline thu thập

    VCI (Vietcap, dữ liệu giá HOSE)
        → thư viện kết nối vnstock 5.1.0, Quote.history, source=VCI
        → src/fetch_data.py: chuẩn hóa time, open, high, low, close, volume
        → data/raw/fpt/fpt_historical_price.csv
        → kiểm toán trong src/eda.py và reports/data_audit.json

<code>vnstock</code> là công cụ kết nối Python; dữ liệu thị trường được truy xuất từ VCI. Tài liệu thư viện mô tả VCI là một trong các nguồn cho OHLCV và lưu ý chuỗi lịch sử có thể được điều chỉnh sau sự kiện quyền. Các phiên bản nguồn dữ liệu khác nhau có thể cho giá lịch sử hơi khác; xem [nguồn dữ liệu của thư viện](https://www.vnstocks.com/docs/vnstock/tham-khao/data-sources), [tài liệu API lịch sử](https://www.vnstocks.com/docs/vnstock/advanced-usage/06-quote-price-api) và [quyền truy cập hiện hành](https://www.vnstocks.com/docs/vnstock/tham-khao/cap-quyen-va-gioi-han).

Điều khoản sử dụng Vietcap bảo lưu quyền với nội dung và dữ liệu trên website, đồng thời hạn chế sao chép, phân phối hoặc xuất bản ngoài mục đích cá nhân. Trước khi phát hành công khai snapshot OHLCV hoặc dữ liệu dẫn xuất, cần kiểm tra quyền sử dụng phù hợp với [điều khoản Vietcap](https://www.vietcap.com.vn/dieu-khoan-su-dung-chinh-sach-bao-mat).

## Cách tái lập lần cập nhật này

Chạy <code>python src/fetch_data.py</code> để tải dữ liệu đến 30/09/2026. Script chuẩn hóa tên cột, ngày, số thực, volume nguyên; loại mã khác FPT nếu có; sắp xếp theo thời gian và từ chối ngày trùng hay giá trị thiếu/không hợp lệ. Lệnh <code>python src/fetch_data.py --verify</code> kiểm tra schema, thứ tự thời gian, ngày đầu/cuối, các khoảng giá và SHA-256 hiện tại.

Ở thời điểm thu thập, quyền khách của API VCI chỉ trả tối đa 365 ngày dữ liệu ngày. Vì vậy, lần chạy này giữ archive OHLCV 2007–2025 đã được quản lý trong dự án và lấy cửa sổ VCI mới từ 30/09/2025 đến 30/09/2026. Có 8 phiên trùng để đối chiếu. Tỷ số giá OHLC giữa VCI mới và archive cũ có trung vị 0,8875; độ trải tương đối của các tỷ số dưới 0,011%. Script nhân bốn cột OHLC trong phần archive trước cửa sổ API với hệ số này để cùng basis với chuỗi VCI hiện tại, thay các ngày trùng bằng dữ liệu mới và giữ nguyên volume. Nếu overlap thiếu hoặc hệ số không ổn định, script dừng và không ghi tệp mới.

Đây là bước nối archive và đồng nhất basis giá, không phải một lần tải lại toàn bộ 2007–2026 từ API. Muốn tái tạo toàn bộ chuỗi từ nguồn mà không dùng archive đã quản lý trong dự án cần một quyền dữ liệu có độ phủ đầy đủ hoặc nguồn lịch sử thay thế. Các kết quả hiện tại dựa trên tệp CSV đã lưu và có thể tái lập bằng checksum trong <code>reports/data_lineage.json</code>.

## Định dạng và đơn vị

| Cột | Ý nghĩa | Đơn vị / quy tắc |
|---|---|---|
| <code>time</code> | Ngày giao dịch | <code>YYYY-MM-DD</code>, giờ Việt Nam được rút về ngày |
| <code>open</code> | Giá mở cửa | Nghìn VND/cổ phiếu theo thang dữ liệu VCI |
| <code>high</code> | Giá cao nhất phiên | Nghìn VND/cổ phiếu |
| <code>low</code> | Giá thấp nhất phiên | Nghìn VND/cổ phiếu |
| <code>close</code> | Giá đóng cửa | Nghìn VND/cổ phiếu |
| <code>volume</code> | Khối lượng giao dịch | Số cổ phiếu |

Ví dụ giá <code>63.0</code> tương ứng khoảng 63.000 VND/cổ phiếu. Tệp không chuyển đổi giá sang đồng và không có cột <code>adjusted_close</code>; OHLC được giữ theo basis lịch sử do VCI trả về và được căn chỉnh archive như mô tả ở trên. Không diễn giải basis này như chuỗi tổng lợi nhuận có tái đầu tư cổ tức.

## Kiểm toán snapshot hiện tại

| Kiểm tra | Kết quả |
|---|---:|
| Số phiên | 4.919 |
| Khoảng ngày | 02/01/2007–30/09/2026 |
| Cột thiếu | 0 |
| Ngày trùng | 0 |
| Phiên volume bằng 0 | 2 |
| Hàng sai quan hệ OHLC | 3 |
| Giá thấp nhất / cao nhất | 1,562 / 119,36875 nghìn VND |
| Close thấp nhất / cao nhất | 1,61525 / 118,073 nghìn VND |
| Volume thấp nhất / cao nhất | 0 / 47.840.750 cổ phiếu |
| SHA-256 chuẩn hóa LF | <code>7b9f9bbefb2a50280d4761e3cfa73f995c607cf825f2d4b7013cd9204182e2cb</code> |

Ba hàng OHLC bất nhất và hai phiên volume bằng 0 được giữ nguyên để không âm thầm sửa dữ liệu nguồn; ngày bất nhất được liệt kê trong <code>reports/data_audit.json</code>. Nhãn biến động phiên kế tiếp: 2.224 tăng, 2.211 giảm, 483 không đổi. Báo cáo EDA đầy đủ nằm trong <code>reports/data_audit.json</code>.

## Vì sao mô hình dùng OHLCV

Mục tiêu là phân loại tăng/giảm ở phiên kế tiếp, nên đầu vào chỉ dùng các quan sát OHLCV đã biết tại thời điểm đóng cửa phiên hiện tại. Dự án tính lại 23 đặc trưng kỹ thuật bằng rolling/lag theo chiều quá khứ; không dùng bfill hay fit scaler trên toàn chuỗi. Các giá trị chuẩn hóa được học trong pipeline của mô hình, chỉ trên train rồi trên train cộng validation để đánh giá tập test.

Các chỉ báo vĩ mô và báo cáo tài chính có tần suất thấp, ngày công bố khác ngày kỳ báo cáo và dễ gây rò rỉ nếu ghép theo ngày hiệu lực thay vì thời điểm công bố. Chúng không nằm trong phạm vi phiên bản này.
