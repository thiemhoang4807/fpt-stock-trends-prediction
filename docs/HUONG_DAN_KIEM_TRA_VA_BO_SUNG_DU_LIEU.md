# Kiểm tra dữ liệu đang có và tìm phần còn thiếu

Tài liệu dành cho người mới vừa tải dữ liệu về. Mục tiêu là biết **đang có gì, thiếu gì, sai gì, tìm bổ sung ở đâu và khi nào mới được đưa vào mô hình**. Các số liệu kiểm tra bên dưới lấy từ snapshot hiện hành, không phải một lần tải dữ liệu mới. Nguồn/đơn vị/cách ghép từng biến nằm tại [sổ tay dữ liệu](../data/README.md); các phép tính từ giá nằm ở [EDA và đặc trưng](EDA_VA_DAC_TRUNG.md).

## 1. Dữ liệu của thiết kế hiện hành

Bản vàng do thành viên nhóm cung cấp có 4.858 phiên giá ngày kể từ 2007. CPI và GDP năm đều đủ 2005–2024. Có 50 báo cáo quý liên tiếp từ quý I/2013 đến quý II/2025. Sau căn thời điểm và tích lũy 60 phiên, tập chính có 3.031 nhãn với ngày mục tiêu đầu tiên 07/08/2013. [Nguồn và từ điển dữ liệu](../data/README.md)

## 2. Kiểm tra độ phủ sau khi chuẩn hóa

```bash
python src/fetch_data.py --verify
python src/fetch_supplemental.py --from-cache
python src/audit_data_quality.py
```

Kiểm toán phân biệt ô trống, ngày quan sát bị mất và ngày sàn đóng cửa. Với VN-Index, 33 phiên còn thiếu được bổ sung bằng giá đóng cửa CafeF và 16 phiên được hiệu chỉnh sau đối chiếu. Hai ngày HOSE đóng cửa 23–24/01/2018 được bỏ khỏi lịch FPT đã dùng. Ba dòng OHLC bất nhất, 22 quý chưa có dữ liệu và một ngày lệch VN-Index còn lại đều ở trước phạm vi mô hình. [Chi tiết kiểm toán](../reports/data_quality_review.json)

## 3. Nguồn có thể đối chiếu tiếp

Ưu tiên lịch công bố gốc của các báo cáo hợp nhất FPT và bản số liệu CPI/GDP biết được tại từng thời điểm. Khi cần thử CPI tháng, hãy so các tháng trùng với thống kê chính thức và dùng một định nghĩa cho cả chuỗi. [Công bố FPT](https://fpt.com/en/ir/information-disclosures) · [Lịch sử tìm nguồn](DU_LIEU_TU_2007.md)

## 4. Nhận một file mới: kiểm tra theo 9 bước

1. **Giữ nguyên bản xuất.** Lưu ở thư mục riêng như `tmp/data_candidates/`, chưa ghi đè snapshot đang dùng. Ghi URL, thời điểm tải, mã chuỗi, đơn vị, múi giờ, tần suất và bộ lọc. `tmp/` bị Git bỏ qua; bản đã nghiệm thu mới đưa vào dữ liệu chính thức.
2. **Kiểm tra loại file.** CSV phải là bảng đọc được, không phải trang HTML báo lỗi tải về dưới đuôi `.csv`.
3. **Kiểm tra schema và kiểu.** Ngày phải đọc bằng định dạng chỉ rõ; số phải xử lý dấu thập phân/phân cách nghìn đúng nguồn. So số hàng trước/sau chuyển kiểu; liệt kê hàng không đọc được, không âm thầm bỏ.
4. **Kiểm tra ngày và kỳ.** Ngày đầu/cuối, ngày trùng, thứ tự, thời gian sau cutoff, thiếu cả hàng giữa chuỗi. Với báo cáo quý, so danh sách quý dự kiến với danh sách đang có; với ngày, đối chiếu lịch nguồn và lịch sàn phù hợp.
5. **Kiểm tra đơn vị và ý nghĩa.** Nghìn VND khác VND; GDP mức khác GDP tăng trưởng; CPI cả nước khác một tỉnh; cổ phiếu lưu hành khác volume; báo cáo hợp nhất khác riêng lẻ.
6. **Kiểm tra quan hệ nội bộ.** Giá dương, volume không âm, `low ≤ open/close ≤ high`; các đẳng thức kế toán; xem đột biến và các đoạn lặp bất thường. Đột biến là điểm cần kiểm chứng, không tự động là số phải xóa.
7. **So phần giao với bản cũ.** So đúng ngày và đúng chỉ tiêu. Liệt kê số khớp, số khác, sai lệch tuyệt đối/tương đối. Nếu giá lịch sử khác đồng loạt theo tỷ lệ, tìm sự kiện/cơ sở điều chỉnh; không tự nhân hệ số chỉ để ép hai file khớp.
8. **Kiểm tra thời điểm biết.** Tách kỳ báo cáo khỏi ngày công bố; giữ số liệu mới chỉ sau hiệu lực. Không kéo số đầu về trước ngày có dữ liệu, không dùng số đã sửa về sau mà bỏ qua ghi chú phiên bản.
9. **Nghiệm thu và chạy lại.** Sau khi giải thích được xung đột, thay bản nguồn, cập nhật nguồn/lineage, chạy lại audit → đặc trưng → huấn luyện/đánh giá → dự báo → tests. Lưu bảng điểm mới cùng phiên bản dữ liệu mới.

Một bản ghi nguồn nên có các trường sau trong bảng ghi chép thu thập (đây là schema nên lưu thêm, không phải khẳng định mọi parser hiện đã nhận các cột này):

| Trường | Ý nghĩa |
|---|---|
| `series_id` | Chuỗi/chỉ tiêu chính xác |
| `reference_period` | Ngày/tháng/quý/năm số liệu nói tới |
| `release_date` | Ngày công bố thật nếu có |
| `available_date` | Ngày cho phép dùng trong mô hình, kèm quy tắc |
| `value`, `unit` | Giá trị và đơn vị |
| `source_url`, `retrieved_at` | Nguồn và lúc lấy |
| `availability_basis`, `revision_note` | Căn cứ ngày hiệu lực và ghi chú sửa số liệu |

## 5. Phạm vi phù hợp cho đồ án hiện tại

Khi có dữ liệu nguồn mới, kiểm tra theo danh sách trên và đóng băng một bản để cả nhóm có thể chạy lại cùng Train/Test.

Nếu muốn mở rộng về trước 2013, ưu tiên xác minh các quý FPT còn thiếu và mốc công bố của từng nguồn. Trên tập đang dùng, phiên FPT nào cũng đã có giá đóng cửa VN-Index tương ứng. Việc có lịch công bố gốc và bản số liệu theo từng lần phát hành sẽ giúp thay các quy tắc trễ giả định. [Hồ sơ nguồn hiện hành](../data/raw/supplemental/study_2013_lineage.json)
