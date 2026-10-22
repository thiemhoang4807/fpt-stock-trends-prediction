# Dữ liệu nghiên cứu

## Chuỗi xuất xứ

```text
VCI (Vietcap) ── vnstock ──> OHLCV FPT ──> data/raw/fpt/fpt_historical_price.csv
                                       └──> src/eda.py, src/prepare.py, src/train.py

VN-Index / tỷ giá / vàng / CPI / GDP / báo cáo FPT
        └──> src/fetch_supplemental.py
               ├──> data/raw/supplemental/*.csv (cache cục bộ)
               ├──> căn theo ngày có thể biết, không backfill
               └──> data/processed/fpt_multisource_features.csv
                         └──> bộ C nếu có đủ trường và đủ Train/Test
```

## Dữ liệu FPT đang có

Snapshot OHLCV gồm 4.919 phiên từ 02/01/2007 đến 30/09/2026. Các cột chuẩn:

| Cột | Ý nghĩa | Đơn vị |
|---|---|---|
| `time` | Ngày giao dịch | YYYY-MM-DD |
| `open` | Giá mở cửa | Nghìn VND/cổ phiếu |
| `high` | Giá cao nhất trong phiên | Nghìn VND/cổ phiếu |
| `low` | Giá thấp nhất trong phiên | Nghìn VND/cổ phiếu |
| `close` | Giá đóng cửa | Nghìn VND/cổ phiếu |
| `volume` | Khối lượng giao dịch | Cổ phiếu |

Giá lấy từ VCI (Vietcap) qua `vnstock`; nguồn VCI có thể điều chỉnh lại giá lịch sử sau sự kiện doanh nghiệp. Snapshot đang lưu cùng lineage/hash trong `reports/data_lineage.json`. Tài liệu Vnstock mô tả giá nến cổ phiếu theo nghìn đồng và ghi nhận các nguồn có thể có cách điều chỉnh lịch sử khác nhau. [Tài liệu dữ liệu thị trường](https://vnstocks.com/docs/vnstock/thi-truong-market).

Kiểm toán snapshot: không có ô thiếu hoặc ngày trùng; 2 phiên volume bằng 0; 3 dòng vi phạm quan hệ OHLC được giữ và báo cáo; lợi nhuận đóng cửa ngày có trung bình 0,0567%, độ lệch chuẩn 1,9246%, nhỏ nhất −6,9896% và lớn nhất 6,9922%. Xem số liệu đầy đủ tại `reports/data_audit.json`.

## Đặc trưng

Bộ A sử dụng 23 đặc trưng kỹ thuật từ close và volume. Bộ B bổ sung:

- `candle_range_pct = (high - low) / close`
- `candle_body_pct = (close - open) / open`
- `overnight_gap_pct = open / close(t-1) - 1`
- `close_location_in_range = (close - low) / (high - low)`

Nếu high bằng low, vị trí close trong nến được đặt bằng 0,5 vì close trùng với mức giá duy nhất trong biên độ. Tất cả đặc trưng đều chỉ dùng thông tin có thể biết tại close phiên hiện tại.

## Nguồn bổ trợ và căn chỉnh theo thời điểm

`src/fetch_supplemental.py` dùng các giao diện Vnstock sau:

| Nguồn | Dữ liệu dự kiến | Giao diện | Trễ sử dụng |
|---|---|---|---:|
| VCI/KBS | VN-Index theo ngày | `Market().index("VNINDEX").ohlcv()` | 0 ngày, dùng sau khi phiên kết thúc |
| VCB/nguồn nội địa | USD/VND theo ngày | `Macro().currency().exchange_rate()` | 1 ngày |
| Dukascopy | Vàng giao ngay XAU/USD | `Market().commodity("XAUUSD").ohlcv()` | 1 ngày |
| Nguồn vĩ mô qua Vnstock | CPI tháng | `Macro().economy().cpi()` | 10 ngày sau cuối tháng |
| Nguồn vĩ mô qua Vnstock | GDP quý | `Macro().economy().gdp()` | 45 ngày sau cuối quý |
| VCI | Báo cáo kết quả kinh doanh quý của FPT | `Fundamental().equity("FPT").income_statement()` | 45 ngày sau cuối quý |

Ngày hiệu lực là ngày kỳ báo cáo cộng số ngày trễ. Ghép dùng quan sát mới nhất có ngày hiệu lực không muộn hơn ngày giao dịch; giá trị chưa có hiệu lực vẫn để thiếu. Không dùng `backfill`. CPI tháng 09/2026 vì vậy không được dùng cho các phiên tháng 09/2026 nếu kỳ đo chỉ công bố sau ngày 30/09; GDP quý III/2026 và báo cáo quý III cũng không xuất hiện trong đặc trưng tính đến ngày 30/09/2026.

Theo tài liệu hiện hành, dữ liệu nến VN-Index, forex và hàng hóa có các chức năng cộng đồng. Báo cáo tài chính ở cấp Khách bị giới hạn tối đa 4 kỳ mỗi lần gọi; CPI, GDP và tỷ giá nội địa qua `Macro()` nằm trong nhóm mở rộng. Do đó, nhóm cần lưu phạm vi ngày thực tế và quyền truy cập; không mặc định rằng mọi nguồn có thể lấy miễn phí hoặc đầy đủ từ năm 2007. [Market](https://vnstocks.com/docs/vnstock/thi-truong-market), [Fundamental](https://vnstocks.com/docs/vnstock/co-ban-fundamental), [Macro](https://vnstocks.com/docs/vnstock/vi-mo-macro).

## Trạng thái lần thu thập hiện tại

Lệnh `python src/fetch_supplemental.py --start 2007-01-01 --end 2026-09-30` đã được thử. Sáu truy vấn hiện trả lỗi vì ứng dụng Vnstock trong môi trường chạy không lấy được chính sách máy khách từ dịch vụ; không có quan sát bổ trợ nào được lưu. Vì vậy:

- `reports/supplemental_data_audit.json` lưu trạng thái lỗi và số dòng 0 cho từng nguồn.
- Bộ C được đánh dấu `not_run` trong `reports/ablation_summary.csv`.
- Các CSV nguồn bổ trợ và bảng ghép đa nguồn được giữ cục bộ, không được thêm vào Git khi chưa có dữ liệu hợp lệ.
- Kết quả A/B chỉ phản ánh OHLCV FPT; không được diễn giải như đã kiểm định tác động của CPI, GDP, tỷ giá hay báo cáo tài chính.

Để chạy lại khi API hoạt động và tài khoản có quyền phù hợp:

```bash
python src/fetch_supplemental.py --start 2007-01-01 --end 2026-09-30
python src/train.py
```

Có thể đặt các tệp CSV đã xuất từ nguồn phù hợp vào `data/raw/supplemental/` theo các tên `vnindex_ohlcv.csv`, `usd_vnd_daily.csv`, `gold_xauusd_daily.csv`, `vietnam_cpi.csv`, `vietnam_gdp.csv`, `fpt_fundamentals_quarterly.csv`, rồi chạy:

```bash
python src/fetch_supplemental.py --from-cache
python src/train.py
```

Các tệp cache cần có cột `time`; từng cột giá trị phải dùng đúng đơn vị và có nguồn/ghi chú riêng. Với báo cáo quý, dùng chuỗi kỳ dạng `YYYY-Qn` hoặc cột ngày cuối kỳ. `--from-cache` áp độ trễ bảo thủ như bảng trên và tạo bảng ngày có thể nhập vào mô hình.
