# Kiểm tra dữ liệu đang có và tìm phần còn thiếu

Tài liệu dành cho người mới vừa tải dữ liệu về. Mục tiêu là biết **đang có gì, thiếu gì, sai gì, tìm bổ sung ở đâu và khi nào mới được đưa vào mô hình**. Các số liệu kiểm tra bên dưới lấy từ snapshot hiện hành, không phải một lần tải dữ liệu mới. Nguồn/đơn vị/cách ghép từng biến nằm tại [sổ tay dữ liệu](../data/README.md); các phép tính từ giá nằm ở [EDA và đặc trưng](EDA_VA_DAC_TRUNG.md).

## 1. Vì sao vàng từ 2019, CPI từ 2018?

**Đó là phạm vi của những tệp dùng huấn luyện, không phải giới hạn được chứng minh của lịch sử dữ liệu.** Bản vàng hiện hành có 1.755 quan sát từ 01/01/2019; bản CPI có 81 lần công bố từ 27/12/2018. Đợt tìm bổ sung đã tải 249 tháng CPI từ 2005, 20 năm GDP và một phần vàng/báo cáo FPT, lưu riêng để kiểm định. Xem [kết quả thực tế và lệnh tải](DU_LIEU_TU_2007.md). Bộ đầu vào đầy đủ 43 biến vẫn chưa có lịch sử liên tục từ 2007.

Danh mục của cơ quan thống kê có [công bố CPI tháng 12/2007](https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2019/12/chi-so-gia-tieu-dung-chi-so-gia-vang-va-chi-so-gia-do-la-my-thang-12-nam-2007/) và [niên giám 2007](https://www.nso.gov.vn/wp-content/uploads/2026/01/niengiam2007_watermark.pdf). Đây là đầu mối đối chiếu với chuỗi tháng World Bank vừa tải và tìm lịch công bố gốc. Đường dẫn được đăng lại nhiều năm sau không phải ngày công bố gốc để đưa vào mô hình.

Với vàng, [World Gold Council](https://www.gold.org/goldhub/data/gold-prices) mô tả chuỗi giá bình quân tháng/quý/năm từ 1978, đồng thời thông báo hạn chế dữ liệu LBMA lịch sử từ tháng 3/2025. Điều này xác nhận lịch sử sớm hơn tồn tại, **không xác nhận đã lấy được chuỗi giá đóng cửa hàng ngày từ 2007** tương thích với XAU/USD đang dùng. Không lấy trung bình tháng rồi gọi nó là giá ngày.

Muốn quay toàn bộ mẫu về 2007 còn phải giải quyết báo cáo tài chính thiếu 22 quý, GDP trước 2010 và cổ phiếu lưu hành trước các mốc đã có. Bổ sung riêng vàng/CPI chưa đủ để cả 43 biến có lịch sử từ 2007.

## 2. Kiểm tra thực tế đã thấy gì?

Chạy từ thư mục gốc:

```bash
python src/fetch_data.py --verify
python src/audit_data_quality.py
```

Lệnh thứ nhất kiểm tra bản giá theo schema/phạm vi/dấu kiểm tra; lệnh thứ hai chỉ đọc dữ liệu hiện có và ghi [báo cáo chất lượng](../reports/data_quality_review.json). Hai lệnh không lấp thiếu hoặc huấn luyện lại. “Dấu kiểm tra đúng” nghĩa là file chưa đổi so với snapshot đã định, không có nghĩa mọi số trong snapshot đều đúng với thị trường.

| Nhóm | Phát hiện | Việc cần làm |
|---|---|---|
| FPT OHLCV | 4.671 dòng, không thiếu ô/trùng ngày; 3 hàng không thỏa quan hệ OHLC | Đối chiếu bản giá khác cùng cơ sở điều chỉnh tại 17/08/2007, 10/06/2009, 07/12/2009 |
| FPT volume | Bằng 0 ở 23–24/01/2018 | Kiểm tra thông báo/lịch giao dịch; chưa tự kết luận là lỗi |
| VN-Index | 36 ngày có trong FPT nhưng không có trong bản nguồn; 17 đoạn return nguồn đi qua ngày FPT bị khuyết | Ưu tiên tải/đối chiếu lại đúng các đoạn, tính return sau khi lịch ngày được kiểm tra |
| Vàng/CPI | Chưa có phần trước 2019/cuối 2018 trong bản lưu | Thu thập lịch sử sớm hơn nếu muốn mở rộng mẫu; không backfill bằng số đầu tiên |
| GDP | Chỉ có 2010–2024 dù nguồn có lịch sử cũ hơn | Lấy thêm các năm cũ cùng chỉ tiêu, kiểm tra phiên bản và ngày hiệu lực |
| Báo cáo quý | Thiếu quý III/2007–quý IV/2012, tổng 22 quý | Tìm báo cáo hợp nhất từ công bố FPT; kiểm tra số quý so với lũy kế |
| Cổ phiếu lưu hành | 10 mốc, không phải lịch đầy đủ mọi sự kiện | Bổ sung công bố phát hành/cổ phiếu quỹ và ngày công bố |
| CPI/ngày công bố | Có ngày phát hành nhưng thiếu trường riêng tháng số liệu | Bổ sung tháng tham chiếu và chứng cứ, tránh dịch nhầm số liệu một tháng |
| Phiên bản lịch sử | Quý +45 ngày, GDP +180 ngày là giả định; số liệu có thể được hồi tố | Tìm lịch công bố thật và giữ phiên bản nguồn; ghi giả định nếu chưa xác minh |

Ba đẳng thức tài chính đã khớp ở cả 52 quý có dữ liệu: doanh thu sau giảm trừ; doanh thu thuần trừ giá vốn; lợi nhuận sau thuế bằng phần công ty mẹ cộng phần không kiểm soát. Đây là kiểm tra nội bộ, chưa phải xác minh toàn bộ báo cáo gốc.

### Ví dụ lỗi rõ ràng và điều chưa thể kết luận

Ngày 17/08/2007, bảng có `low=8.298125` nhưng `close=7.242`, tức close thấp hơn low. Một nến theo cùng cơ sở giá phải chứa close trong khoảng thấp–cao; hàng này cần kiểm chứng. Không tự nâng close lên low, vì như vậy sẽ tạo một giá không có chứng cứ và thay cả lợi nhuận/nhãn các phiên liên quan.

Volume bằng 0 khác ô trống: nó có thể phản ánh ngày không giao dịch, sự cố thị trường, hoặc lỗi cung cấp. Cần nguồn chứng minh mới chọn cách xử lý. Cuối tuần/ngày nghỉ không có hàng cũng không tự động là “mất dữ liệu”. Báo cáo audit so hai lịch nguồn là để khoanh vùng cần kiểm tra, không thay cho lịch giao dịch chính thức.

### Vấn đề bị che bởi phép điền xuống

Bản VN-Index thiếu 36 ngày so lịch FPT, nhưng bảng cuối chỉ có 5 ô thiếu nội bộ ở 01–05/02/2021 vì các khoảng ngắn hơn được giữ giá trị đã biết. Ví dụ đoạn 20/01/2021 → 05/02/2021 có nhiều phiên FPT ở giữa mà nguồn chỉ số không lưu. `ln(I_05/02 / I_20/01)` là mức đổi giữa hai quan sát đó, không phải lợi nhuận đúng một phiên 05/02. Tên cột `vnindex_return_1d` không tự bảo đảm ý nghĩa một phiên nếu lịch nguồn bị đứt.

Vì vậy, trước khi thêm hàng nghìn ngày lịch sử mới, nên kiểm tra các đoạn thiếu ngay trong giai đoạn đang đánh giá. Kết quả XGBoost 32 → 38 → 43 hiện chỉ mô tả hiệu quả trên snapshot này, chưa tách được ảnh hưởng của chất lượng nguồn khỏi ảnh hưởng của nhóm biến.

## 3. Tìm dữ liệu bổ sung theo thứ tự nào?

### Ưu tiên 1: sửa các điểm có khả năng ảnh hưởng thiết kế hiện tại

1. Đối chiếu VN-Index tại 36 ngày trong `calendar_comparison.fpt_dates_absent_from_vnindex` của JSON audit. Lấy bản DNSE mới vào thư mục khác hoặc tìm nguồn chỉ số đáng tin cậy; so toàn đoạn trước/sau chỗ thiếu. Không thay bằng VN30 hoặc giá ETF.
2. Kiểm tra CPI đúng chỉ tiêu **cả nước, cùng kỳ năm trước**, có tháng tham chiếu và ngày phát hành. Đối chiếu các mốc chuyển lịch công bố, không suy từ tháng phát hành.
3. Kiểm chứng ngày công bố báo cáo quý và những sự kiện cổ phiếu lưu hành trong cửa sổ 2019–2025. Đây là bước cải thiện tính đúng thời điểm, kể cả khi không kéo dài số hàng.
4. Đối chiếu ba bất nhất OHLC và hai ngày volume bằng 0 để hoàn thiện audit; các ngày này nằm trước mẫu chung nhưng vẫn thuộc dữ liệu công bố của dự án.

### Ưu tiên 2: mở rộng lịch sử vàng

Trước hết thử cùng [nguồn XAU/USD hiện hành](https://vn.investing.com/currencies/xau-usd-historical-data): chọn hàng ngày, yêu cầu 01/01/2007–31/12/2019; lấy từng năm nếu bảng giới hạn số hàng. Năm 2019 là phần giao với bản hiện có để kiểm tra hai lần xuất có khớp không. Sau khi tải, mở đầu/cuối tệp để xác nhận phạm vi **thực nhận**; ngày nhập trên giao diện không chứng minh file đã chứa đủ ngày.

Cần ghi: giá giao ngay XAU/USD, USD/ounce troy, giá đóng/lần cuối, tần suất ngày, múi giờ hoặc cách chốt phiên nếu nguồn có nêu. Không thay ngầm bằng hợp đồng tương lai vàng, giá ETF vàng, giá SJC hoặc giá bình quân tháng. Nếu chỉ có nguồn khác, so phần giao nhau và nêu rõ đổi định nghĩa; tốt hơn là dựng lại toàn chuỗi theo một nguồn nhất quán rồi chạy thí nghiệm mới.

World Gold Council có thể dùng để tham chiếu giá bình quân dài hạn; khả năng tải chuỗi ngày lịch sử phụ thuộc quyền truy cập và định nghĩa cụ thể. Không nên trả tiền mua nguồn chỉ để tăng số hàng khi nhóm chưa xử lý các lỗi trong mẫu hiện có.

### Ưu tiên 3: mở rộng CPI

Tìm ở [cơ sở dữ liệu thống kê Việt Nam](https://www.gso.gov.vn/en/statistical-data/), các thông cáo CPI tháng và niên giám của cơ quan thống kê. [IMF CPI](https://data.imf.org/Datasets/CPI) là nguồn đối chiếu/xuất dữ liệu theo quốc gia và cấu phần. Chọn Việt Nam, toàn quốc, toàn bộ giỏ hàng, tần suất tháng; kiểm tra siêu dữ liệu về đơn vị, năm gốc và phạm vi thực có. Đợt này mới xác minh đầu mối nguồn, chưa nghiệm thu một bản tải IMF đầy đủ từ 2007.

Ba kiểu số rất dễ nhầm:

| Kiểu số | Ví dụ | Có đưa thẳng vào `cpi_yoy_pct` không? |
|---|---|---|
| Tăng cùng kỳ năm trước (%) | 3,24% | Có, sau khi xác minh phạm vi và ngày công bố |
| Chỉ số so cùng kỳ năm trước = 100 | 103,24 | Đổi thành 103,24 − 100 = 3,24% |
| Mức CPI năm gốc = 100 | 108,7 | Không; cần mức cùng tháng năm trước, cùng chuỗi gốc |
| Chỉ số so tháng trước = 100 | 100,3 | Không; 0,3% là tăng tháng, chưa phải tăng năm |

Nếu có mức CPI cùng cơ sở năm gốc:

$$CPI\_YoY_m=100\left(\frac{CPI_m}{CPI_{m-12}}-1\right).$$

Ví dụ CPI tháng này 110, cùng tháng năm trước 105: `(110/105 − 1) × 100 ≈ 4,7619%`. Muốn tính đủ năm 2007 phải lấy thêm các tháng năm 2006. Nếu có chuỗi chỉ số so tháng trước, phải nhân liên hoàn đủ 12 tỷ số rồi trừ 1; cộng 12 phần trăm chỉ là xấp xỉ. Không nối mức CPI khác năm gốc mà không kiểm tra liên kết/điều chỉnh cơ sở.

Lưu cả tháng số liệu và ngày công bố. Không dùng ngày tải website năm 2026 thay ngày phát hành gốc năm 2007. Nếu không xác minh được lịch công bố cũ, cần ghi quy tắc giả định và giới hạn; không tuyên bố “hoàn toàn đúng dữ liệu từng biết trong quá khứ”.

### Các nguồn còn lại

- **GDP:** dùng cùng [chỉ tiêu World Bank NY.GDP.MKTP.CD cho Việt Nam](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=VN), lấy thêm các năm cũ và phần giao nhau; phân biệt USD hiện hành với USD giá cố định/tăng trưởng %. Nguồn hiện hiển thị lịch sử từ 1985, dài hơn bản dự án.
- **Báo cáo quý:** tìm [công bố thông tin FPT](https://fpt.com/en/ir/information-disclosures). Ưu tiên báo cáo hợp nhất và số riêng quý. Nếu chỉ có lũy kế: riêng quý II = sáu tháng − quý I; quý III = chín tháng − sáu tháng; quý IV = cả năm − chín tháng, nhưng chỉ khi các báo cáo cùng phạm vi kế toán/phiên bản. Ghi phép chuyển đổi và ngày đủ cả hai số để tính.
- **Cổ phiếu lưu hành:** lấy báo cáo năm và các lần tăng vốn/phát hành/mua cổ phiếu quỹ; giữ số liệu, mốc sự kiện, ngày công bố và URL. Không chia vốn hóa cho giá điều chỉnh để suy ra một lịch cổ phiếu không được kiểm chứng.

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

Nên ưu tiên **một cửa sổ thực nghiệm có dữ liệu nhất quán** trước khi cố kéo mọi nguồn về 2007. Chuỗi giá dài vẫn hữu ích cho mô tả EDA, nhưng phần đa nguồn có thể đặt phạm vi 2019–2025 sau khi kiểm chứng các khoảng thiếu. Nếu mở rộng về 2007 là mục tiêu nghiên cứu mới, cần thu thập đồng bộ nhiều nguồn; số hàng tăng chưa bảo đảm dự báo tốt hơn vì thị trường và doanh nghiệp đã thay đổi qua nhiều giai đoạn.

Trong đợt tài liệu này, không thay các giá trị nguồn, không sửa mô hình theo kết quả Test và không thay metric đã lưu. Audit mới giúp nhóm biết cần khắc phục gì trước lần thực nghiệm tiếp theo. Hướng ưu tiên là sửa/kiểm chứng lịch VN-Index và ngày công bố, rồi mới bổ sung lịch sử vàng/CPI cùng các báo cáo còn thiếu.
