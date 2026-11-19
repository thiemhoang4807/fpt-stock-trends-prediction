# Nhật ký thực hiện CS114

## Mục tiêu và trạng thái hiện tại

Thiết kế hiện hành: cutoff 30/09/2025; một mục tiêu next_log_return suy ra giá và hướng; năm phương pháp chính và ba thí nghiệm, CV 5 fold trong Train 85%, Test 15%. Nhật ký các thiết kế cũ bên dưới được giữ như lịch sử, không phải luồng chạy hiện tại.

**Quy ước từ người dùng ngày 19/11/2026:** Từ các đợt cập nhật sau, không chỉnh docs/PROPOSAL.md, docs/cs114_proposal.tex hoặc docs/cs114_proposal.pdf vì đã nộp giảng viên; chỉ chỉnh các file khác. Bản Proposal của đợt rút gọn này đã hoàn tất trước chỉ dẫn mới và được giữ nguyên.

## Checklist theo giai đoạn

### Rà soát trước khi đóng gói — 20/11/2026

- [x] Kiểm tra trạng thái Git, phạm vi thí nghiệm từ 2013 và ba tệp Proposal đã nộp. Đối chiếu cách chia, lựa chọn bằng CV và nguồn các bảng kết quả.
- [x] Rà soát đầu vào tái lập, kiểm định snapshot và sửa thống kê kiểm toán dữ liệu. Luồng ngoại tuyến đọc 7 CSV đầu vào đã chuẩn hóa. Lệnh tải VN-Index lưu ứng viên riêng. Thống kê ô trống CPI/GDP tách khỏi số vô hạn. Xác minh giá FPT đối chiếu SHA-256 và số dòng trong hồ sơ nguồn.
- [x] Làm gọn bảng, biểu đồ, báo cáo, cẩm nang và hướng dẫn notebook. Bảng chính giữ 5 phương pháp, hai bảng riêng trình bày mức dữ liệu và cửa sổ GRU. Sáu hình đối sánh dựng lại từ CSV. Cẩm nang công khai có kịch bản thuyết trình 10 phút. Kiểm tra 161 liên kết cục bộ.
- [x] Kiểm thử, đối chiếu kết quả, kiểm tra liên kết và dọn tệp nháp trong `tmp/`.
- [x] Chuẩn bị bản công bố trên `main`. Phần công bố gồm mã, kiểm thử, hình, tài liệu và hai báo cáo kiểm toán cập nhật.

Kiểm thử Python đạt 72/72. Chạy lại pipeline trong bản sao cho 16 bảng CSV khớp ở dung sai tương đối `1e-10` và tuyệt đối `1e-12`. Bảy JSON khớp nội dung, gồm dự báo sau phiên 30/09/2025. Kiểm tra Git xác nhận dữ liệu thí nghiệm, bảng điểm, các mô hình và ba tệp Proposal vẫn cùng nội dung với bản trước.

Chạy 10/10 notebook trên kernel mới trong bản sao và kiểm tra lại 16 CSV cùng dự báo. Các ô mã công bố khớp bản trước. Đã dọn 258 tệp tạm và cache, tổng cộng 32,02 MiB, sau khi xác minh đường dẫn nằm trong dự án và giá trị nguồn được bảo toàn.

### Tái huấn luyện theo cửa sổ 2013 và 42 biến — 19/11/2026

- [x] Chốt phạm vi 32 → 38 → 42 biến theo yêu cầu. Đối chiếu nguồn cho các ngày thiếu VN-Index, xác minh hai ngày HOSE đóng cửa 23–24/01/2018.
- [x] Đóng băng dữ liệu XAU/USD 4.858 ngày, CPI/GDP WDI 20 năm và 49 hàng sửa lịch sử VN-Index (33 bổ sung, 16 sửa giá đóng cửa). Lưu URL, lượng trùng và hash nguồn. CPI/GDP giả định cuối năm +180 ngày, tài chính quý +45 ngày. Không thiếu đầu vào trên tập chung sau hiệu chỉnh. Giữ bản giá gốc và lọc hai ngày HOSE đóng cửa khi chuẩn bị dữ liệu.
- [x] Chạy EDA, ghép, chuẩn bị, ADF/KPSS, CV/Test, giải thích và dự báo. Có 3.031 nhãn từ 07/08/2013, Train 2.576 đến 29/11/2023, Test 455 đến 30/09/2025. XGBoost 32/38/42 đúng hướng 52,95/55,00/52,95%, MAE giá 1,1100/1,1164/1,1167. ARIMA(0,0,0) được chọn bằng CV RMSE 0,015860. Cập nhật tài liệu và kiểm chứng 67 tests đạt. Giữ ba tệp Proposal đã nộp.
- [x] Chạy 10/10 notebook trong bản sao bằng kernel mới. 13 bảng báo cáo và 3 bảng đặc trưng khớp trong dung sai 1e-10/1e-12. JSON dự báo giống hệt. Không có dữ liệu thiếu trong tập chung hay ô ngoại sinh SARIMAX cần điền. Lưu kiểm định tại reports/study_2013_validation.json.
- [x] Commit thực nghiệm `d2bf730` đã được push lên `main` và đối chiếu SHA từ remote. Hồ sơ nguồn, cẩm nang, bảng kết quả, mô hình và notebook nằm trong cùng phiên bản.

### Xác định mốc bắt đầu thí nghiệm — 19/11/2026

- [x] Đối chiếu 38, 42 và 43 biến với vàng mới, CPI/GDP năm giả định trễ 180 ngày, yêu cầu 60 phiên liên tiếp và chia thời gian 85%/15%. Bản 43 biến cũ tái lập đúng 1.559 nhãn, 1.325 Train và 234 Test.
- [x] So mốc 2012–2014. Bộ 42 biến có hàng đầu vào đầy đủ 15/05/2013, mục tiêu đầu tiên 07/08/2013 và 2.969 nhãn (2.523/446). Lùi mốc danh nghĩa về 2012 không thêm nhãn. Lấy từ 2014 có 2.864 nhãn. Bộ 43 dùng các mốc cổ phiếu đang lưu bắt đầu dự báo 25/09/2018, có 1.688 nhãn.
- [x] Ghi các phương án trong tài liệu và lưu phạm vi kiểm tra tại data/local/macro_2007/start_window_audit.json. Khuyến nghị 2013 cho 42 biến nếu được duyệt phạm vi. Cần xác minh quy tắc khả dụng CPI/GDP và năm phiên thiếu chỉ báo VN-Index trước lần chạy mới.

### Kiểm tra nguồn báo cáo FPT bằng vnstock — 19/11/2026

- [x] Xác nhận môi trường dự án đã cài `vnstock 5.1.0`; notebook tham khảo dùng `Finance` với FPT và VCI. Xóa bản clone tạm sau khi đọc.
- [x] Gọi kết quả kinh doanh quý bằng `vnstock 5.1.0` với VCI, KBS, MAS. Tất cả báo bản cũ đã ngừng từ 11/11/2026. Cài `vnstock 6.0.1` và `vnstock-oapi 0.1.2` trong thư mục thử nghiệm. Gọi `Fundamental().equity("FPT")`: VCI báo tuyến báo cáo không hỗ trợ, FHSC báo thiếu `FHSC_API_KEY` cho cả kết quả kinh doanh và bảng cân đối. `Reference().company("FPT").capital_history(source="fhsc")` báo chưa hỗ trợ ở thế hệ 6.
- [x] So tệp tham khảo với snapshot hiện hành: cùng 52 dòng, 29 cột và trùng giá trị từng dòng. Chỉ có 2007Q1–Q2 và 2013Q1–2025Q2. Chưa bổ sung được 22 quý 2007Q3–2012Q4. Đã xóa các bản clone tạm.
- [ ] Chờ dữ liệu kết quả kinh doanh đã xuất hoặc khóa FHSC được người dùng cấu hình trên máy. Cần kiểm tra độ phủ và đối chiếu báo cáo gốc khi có kết quả. Lịch cổ phiếu lưu hành cần nguồn công bố riêng. Chưa thay snapshot hay chạy lại thí nghiệm.

### Chuẩn hóa XAU/USD và CPI năm — 19/11/2026

- [x] Nhận bản xuất XAU/USD từ người dùng. Tệp có 5.000 hàng theo thứ tự giảm dần từ 01/01/2007 đến 16/04/2026, ngày không trùng.
- [x] Tải gói CSV WDI chính thức sau khi API JSON hết thời gian chờ. Hàng VNM/FP.CPI.TOTL.ZG có đủ 20 giá trị 2005–2024. Có số cả năm 2025 trong nguồn nhưng nằm sau cutoff. WDI ghi ngày cập nhật 11/11/2026.
- [x] Chuẩn hóa vàng đến 30/09/2025. Giữ 4.858 hàng, cắt 142 hàng sau cutoff. Giá OHLC hợp lệ và mỗi ngày có tối đa một hàng. Trong 1.742 ngày trùng có 1.570 giá đóng khác snapshot đang dùng, lệch tối đa 7,80 USD/ounce. Bản mới thiếu 13 ngày có trong bản cũ. Kiểm tra ghép chỉ dùng vàng đã có từ ngày trước và tối đa 10 ngày tuổi cho kết quả 4.671/4.671 phiên FPT có giá đủ điều kiện.
- [x] Lưu các bảng vàng, CPI năm, GDP năm và báo cáo kiểm định dưới data/local/macro_2007. Cập nhật tài liệu nguồn và thêm lệnh prepare_macro_refresh.py để xử lý lại tệp xuất. Toàn bộ 66 kiểm thử đạt.
- [ ] Chờ xác nhận quy tắc khả dụng CPI/GDP và cách xử lý phạm vi bộ 43 biến. Dữ liệu phụ trợ tài chính còn thiếu 22 quý, lịch số cổ phiếu lưu hành từ trước 2018 chưa đủ và lịch VN-Index còn 36 phiên lệch với FPT. Chưa ghép dữ liệu mới vào huấn luyện. Bản Proposal, dữ liệu chính và kết quả thực nghiệm giữ nguyên.

### Xác minh ba nguồn vĩ mô người dùng chỉ định — 19/11/2026

- [x] Mở lại lịch CPI Việt Nam và bảng lịch sử XAU/USD trên Investing.com. Lịch CPI mở rộng được đến 29/05/2024 trong phiên kiểm tra, sau đó nút Hiển thị thêm chưa trả thêm hàng. Bộ lọc vàng nhận 01/01/2007–30/09/2025, nhưng bảng vẫn hiển thị tháng gần nhất và nút Tải xuống mở hộp đăng ký/đăng nhập.
- [x] Đối chiếu chỉ tiêu GDP danh nghĩa theo USD hiện hành của World Bank. Bản phản hồi API đã lưu có đủ 20 năm 2005–2024, đúng quốc gia và mã chỉ tiêu, khớp SHA-256. Ngày công bố từng năm chưa xác minh.
- [ ] Chờ tệp CPI theo ngày công bố và XAU/USD ngày do người dùng cung cấp. Bộ 43 biến cũng cần xác minh các quý tài chính còn thiếu, lịch cổ phiếu lưu hành và các phiên lệch lịch VN-Index so với FPT trước khi mở rộng về 2007.
- [ ] Kiểm định độ phủ và tính khả dụng theo thời gian, rồi xử lý lại dữ liệu và chạy toàn bộ pipeline theo phạm vi đã xác nhận.

Người dùng yêu cầu dừng ngay khâu thu thập nếu gặp dữ liệu không tải được hoặc cần xác minh. Lần kiểm tra này chưa ghi đè đầu vào hay chạy lại huấn luyện.

### Tìm và kiểm chứng lịch sử từ 2007 — 19/11/2026

- [x] Kiểm tra trạng thái main sạch và đọc cấu trúc dữ liệu đang dùng.
- [x] Tìm nguồn trực tiếp cho vàng, CPI, GDP, báo cáo quý và cổ phiếu lưu hành từ 2007; kiểm tra thêm lịch VN-Index.
- [x] Tải bản ứng viên riêng, ghi URL, thời gian, đơn vị, phạm vi và dấu kiểm tra; không ghi đè snapshot khi chưa kiểm chứng.
- [x] So phần giao nhau, số kỳ thiếu, ngày công bố và khả năng nối dữ liệu; quyết định từng nguồn trên chất lượng dữ liệu, không dựa vào điểm Test.
- [x] Lưu các bản ứng viên đã tải cùng quy trình tái lập và báo cáo rõ điều kiện còn thiếu. Chưa thay bộ huấn luyện khi chưa đạt tiêu chuẩn.
- [x] Cập nhật tài liệu/cẩm nang, kiểm thử và đồng bộ GitHub; giữ nguyên Proposal đã nộp.

Phát hiện đầu: World Bank có kho lạm phát tháng và dữ liệu GDP lịch sử; website FPT có công bố báo cáo quý IV/2007 ngày 24/01/2008. Cần tải nội dung để xác nhận trường số, độ phủ và ngày có thể biết; chưa coi kết quả tìm kiếm là dataset hoàn chỉnh.

Đã tải: World Bank GEM 249 tháng chỉ số CPI (01/2005–09/2025, không thiếu kỳ), WDI 20 năm GDP (2005–2024). CPI tính cùng kỳ so với 81 mốc hiện có lệch tối đa 0,03979 điểm phần trăm khi suy đoán kỳ tham chiếu từ lịch phát hành; đây là đối chiếu khảo sát, chưa xác minh lịch công bố lịch sử. Giá vàng tải thành công 7 năm rời (2006/2007/2008/2014/2016/2017/2020); các năm khác gặp timeout và sau đó HTTP 429 nên dừng tải nguồn này. Đã tải báo cáo thường niên 2007, báo cáo quý II/2009 và I/II/III/2010 của FPT; nhìn bảng gốc xác nhận cổ phiếu phổ thông khác tổng cổ phiếu gồm ưu đãi. Các nguồn hiện lưu riêng để kiểm định, chưa thay dữ liệu huấn luyện.

Đã lưu 17 tệp phản hồi/PDF gốc (~5,08 MB) và các CSV ứng viên vào data/research/history_2007. Script fetch_historical_candidates.py chạy ngoại tuyến, kiểm tra tháng liên tục trước khi tính CPI cùng kỳ, giải mã vàng đúng đơn vị và dừng tải một máy chủ khi gặp HTTP 429. 62 tests đạt. Vàng sau bỏ hàng lịch rỗng còn 2.182 thanh; 260 ngày trùng lệch tương đối tuyệt đối trung bình 0,132181%, tối đa 1,331965%. GDP trùng 15 năm, lệch tối đa 0,013363%. VN-Index tải lại vẫn 4.635 phiên, 36 ngày không khớp lịch FPT và giá không đổi. Đã xem trực quan 6 trang PDF; giữ riêng số cổ phiếu phổ thông/ưu đãi/quỹ và số liệu doanh thu chưa đồng nhất. Chưa đủ điều kiện thay bộ 43 biến nên không huấn luyện lại. Đã cập nhật hướng dẫn tìm nguồn, README, sổ tay dữ liệu, REPORT và cẩm nang công khai; Proposal giữ nguyên.

Kiểm tra cuối đợt mở rộng: 63/63 tests đạt, CLI dựng ứng viên ngoại tuyến thành công, snapshot FPT verify đạt 4.671 hàng và hash giữ nguyên. 60 tệp được bảo vệ không đổi; 10 notebook hợp lệ; liên kết mới không hỏng; không có định danh tham khảo bị cấm trong các tệp sửa. Chứng cứ tại reports/history_extension_validation.json. Cẩm nang vẫn được Git theo dõi và sẽ công bố cùng tài liệu nguồn mới. Đang đóng gói và push main; không chỉnh Proposal.

Hoàn tất đợt tìm và kiểm chứng: commit 96a725f đã push thành công lên origin/main. Đã dọn thư mục tìm kiếm tạm/cache sau khi lưu bằng chứng. 17 tệp nguồn được cấu hình giữ nguyên byte qua Git và đã đối chiếu SHA-256 giữa file local và blob Git. Cẩm nang công khai có trong commit. Giới hạn còn lại được nêu trong docs/DU_LIEU_TU_2007.md và audit.json; không tuyên bố bộ 43 biến đã đầy đủ từ 2007. Nhật ký xác nhận này được đồng bộ bằng commit tiếp theo.

### Cập nhật hướng dẫn dữ liệu và chia sẻ cẩm nang — 19/11/2026

Yêu cầu mới: giải thích nguồn, cách lấy, đơn vị, ý nghĩa, mục đích, độ phủ và xử lý từng biến đang sử dụng; mở rộng EDA và lý do dùng các công thức. Người dùng cho phép công bố cẩm nang lên GitHub từ đợt này, thay cho quy ước giữ riêng trước đây. Không chỉnh ba tệp Proposal đã nộp. Phần hỏi đáp riêng trong cuộc trò chuyện không bổ sung vào tài liệu.

- [x] Đọc trạng thái Git, tài liệu, mã thu thập và các báo cáo kiểm toán hiện có; lưu dấu kiểm tra dữ liệu, kết quả, mô hình, biểu đồ và Proposal trước khi chỉnh tài liệu.
- [x] Đối chiếu nguồn và độ phủ thực tế, viết hướng dẫn dữ liệu theo từng trường.
- [x] Bổ sung hướng dẫn EDA, công thức đặc trưng và các ô giải thích trong notebook.
- [x] Cập nhật cẩm nang dùng chung, README và báo cáo; bỏ quy tắc Git bỏ qua cẩm nang.
- [x] Kiểm thử, kiểm tra liên kết và tính nhất quán số liệu; xác nhận dữ liệu/mô hình/kết quả/Proposal không đổi.
- [x] Commit và push tài liệu chính thức lên main, xác minh cẩm nang có trong bản công bố.

Phát hiện ban đầu: có 4.671 phiên OHLCV, nhưng nguồn vàng bắt đầu 2019, CPI cuối 2018 và báo cáo quý có khoảng trống. Cần phân biệt kỳ số liệu, ngày hiệu lực theo quy tắc, và độ phủ sau khi ghép lên lịch giao dịch. Tập so sánh chung có 1.559 nhãn, các mô hình dùng 32/38/43 biến.

Tiến độ bổ sung: hoàn thành data/README.md, tài liệu EDA/công thức, cẩm nang dùng chung và các ô giải thích notebook 01–05/08. Sửa ba tên trường nguồn bị lỗi mã hóa trong data/sources.json. Lượt kiểm tra đầu: 47 tests pass; fetch_data --verify xác nhận 4.671 hàng và hash giá không đổi.

Theo câu hỏi tiếp theo về thiếu dữ liệu, thêm src/audit_data_quality.py và reports/data_quality_review.json để rà soát chỉ đọc. Phát hiện 36 ngày có trong FPT nhưng không có trong nguồn VN-Index, 17 đoạn return nguồn có thể trải qua nhiều phiên; sau ghép giữ giá trị cũ còn 5 ô thiếu nội bộ. Thiếu 22 quý tài chính (2007Q3–2012Q4); ba đẳng thức kế toán khớp ở cả 52 hàng hiện có. Giá có 3 bất nhất OHLC và 2 phiên volume bằng 0 cần đối chiếu. Các số liệu nguồn không được tự sửa. Viết hướng dẫn tìm thêm dữ liệu và 9 bước kiểm tra file mới; phân biệt giới hạn bản thu thập với giới hạn nhà cung cấp. Các trang công khai xác nhận có đầu mối CPI 2007, vàng bình quân trước 2007, GDP trước 2010; chưa nghiệm thu chuỗi vàng ngày/CPI đầy đủ từ 2007. Kiểm tra cuối: 47 tests pass (9,07 giây), 10 notebook hợp lệ và mọi ô code phân tích cú pháp được; không chạy lại huấn luyện. Liên kết nội bộ hợp lệ, không có từ khóa tham khảo bị cấm trong các file được rà. Đối chiếu 71 hash xác nhận dữ liệu/mô hình/kết quả/biểu đồ/Proposal cũ không đổi; cẩm nang không còn bị Git bỏ qua. Chứng cứ tại reports/documentation_validation.json. Đã commit và push thay đổi chính lên origin/main: 3444f46. Cẩm nang đã được Git theo dõi và công bố theo yêu cầu mới; ba tệp Proposal không có thay đổi. Dọn tệp kiểm tra tạm sau khi lưu chứng cứ xác minh vào reports/documentation_validation.json.

### 1. Dữ liệu và kiểm toán

- [x] Kiểm tra Git và bảo toàn thay đổi của dự án; đang làm trên main.
- [x] Kiểm tra quy trình thu thập CSV, API, báo cáo/slide, notebook và lịch sử thay đổi trong bản kiểm toán tạm ngoài workspace.
- [x] Xóa bản kiểm toán tạm sau khi hoàn tất. Không đưa tên, tác giả hay mã nguồn tham khảo vào dự án.
- [x] Cắt OHLCV về 02/01/2007–30/09/2025: 4.671 hàng; verify schema, ngày và hash thành công.
- [x] Chuẩn hóa USD/VND, vàng, CPI, GDP, ngành và tài chính từ snapshot nguồn tài chính; mô tả trung thực quy trình xuất CSV bán tự động.
- [x] Cắt cả tệp xuất nguồn: loại 7 hàng FX, 31 vàng, 1 CPI, 1 ngành sau cutoff; loại 1 dòng GDP dự báo năm 2025.
- [x] Trích 10 điểm cổ phiếu lưu hành theo báo cáo và công bố FPT; lưu ngày tham chiếu, cơ sở ngày và URL từng nguồn.
- [x] Tính đúng EBIT = lợi nhuận trước thuế + trị tuyệt đối chi phí lãi vay; không gán lợi nhuận hoạt động thành EBIT.
- [x] Thêm data/sources.json và viết lại data/README.md; lưu hash/độ phủ/missing trong reports/supplemental_data_audit.json.

Kết quả: OHLCV không thiếu, không trùng ngày; 2 phiên volume=0 và 3 hàng OHLC bất nhất giữ để kiểm toán. Giá theo nghìn VND, volume theo cổ phiếu. Giữ basis VCI của snapshot; lịch sử archive từng được căn OHLC bằng hệ số 0,8875, không thay volume.

Nguồn bổ trợ sau cắt: FX 4.893 quan sát; vàng 1.755; CPI 81; GDP 15 năm 2010–2024; ngành 33 snapshot; tài chính 52 quý có khoảng trống 2007–2013; cổ phiếu lưu hành 10 điểm. Vàng quy đổi VND/ounce, không phải vàng miếng nội địa. Ngành công nghệ được dùng làm proxy ICT.

### 2. Tiền xử lý và hai nhánh

- [x] Áp cutoff trước khi tạo target bằng shift(-1), kể cả khi đầu vào tùy chỉnh có dữ liệu sau cutoff.
- [x] Nhánh 1 gồm 5 OHLCV gốc và 27 chỉ báo/nến: 32 biến.
- [x] Nhánh 2 thêm 12 biến vĩ mô/ngành/tài chính/cổ phiếu lưu hành: 44 biến.
- [x] Chuẩn hóa định dạng ngày riêng từng nguồn; ghép backward as-of, không backfill hoặc nội suy từ kỳ tương lai.
- [x] Dùng độ trễ: chuỗi ngày/ngành/CPI/cổ phiếu +1 ngày, GDP cuối năm +180 ngày, báo cáo quý +45 ngày.
- [x] Áp hạn dữ liệu cũ: FX/vàng 10 ngày, CPI 65, ngành 180, quý 150, GDP/cổ phiếu 550 ngày kể từ hiệu lực.
- [x] Yêu cầu đầy đủ mọi cột bổ trợ đã khai báo; không âm thầm bỏ biến hoặc lùi dự báo về phiên cũ khi thiếu đầu vào mới nhất.
- [x] Dùng một cohort và ranh giới Train/Test chung cho cả hai nhánh; StandardScaler nằm trong Pipeline, chỉ fit Train khi chấm Test.

Cohort chung: 1.683 hàng có đầu vào đầy đủ, gồm 1.682 nhãn và một hàng dự báo cuối. Theo target_date: Train 03/01/2019–24/09/2024 (1.429 hồi quy, 1.339 phân loại); Test 25/09/2024–30/09/2025 (253 hồi quy, 244 phân loại). Phân loại loại các phiên đứng giá sau khi xác định ranh giới.

### 3. Mô hình và đầu ra thực nghiệm

- [x] Khai báo/cài XGBoost; seed 42, siêu tham số cố định; không early stopping hoặc tìm tham số trên Test.
- [x] Huấn luyện Majority, Logistic, Random Forest, XGBoost, HistGradientBoosting trên mỗi nhánh cho phân loại.
- [x] Huấn luyện Last-Close, Linear, Random Forest, XGBoost, HistGradientBoosting trên mỗi nhánh cho hồi quy trực tiếp next_close.
- [x] Xuất 10 dòng metrics mỗi bài toán; Accuracy, Balanced Accuracy, Precision, Recall, F1, ROC-AUC; MAE/RMSE/MAPE/Directional/Tolerance.
- [x] Xuất confusion matrix và dự báo từng phiên cho tất cả 10 bộ phân loại; lưu hyperparameters và feature importance từ mô hình fit Train.
- [x] Vẽ các đường giá từng mô hình/nhánh, so XGBoost với cửa sổ 80 phiên, so cả 4 thuật toán với cửa sổ 80 phiên và biểu đồ cột metrics.
- [x] Lưu mô hình được chọn sau thực nghiệm, fit lại trên toàn bộ cohort có nhãn; chạy dự báo từ phiên cuối 30/09/2025.

Kết quả cuối của thiết kế 32/44 biến: Nhánh 1 chọn Logistic Regression, Accuracy 53,69%, Balanced Accuracy 54,07%, F1 tăng 59,50%, ROC-AUC 55,25%. Nhánh 2 tốt nhất XGBoost, Accuracy 52,87%, Balanced Accuracy 53,52%, F1 tăng 62,30%, ROC-AUC 54,82%. Chưa có cải thiện rõ ràng từ dữ liệu bổ trợ; không dùng kết quả tạm 27/38 biến để kết luận.

Last-Close Baseline tốt nhất MAE 1,1942 nghìn VND, RMSE 1,7129, MAPE 1,2342%, Directional Accuracy=0%; tolerance ±0,5/±1/±2% = 34,39/55,34/82,61%. Dự báo minh họa cuối snapshot: Logistic Nhánh 1 dự đoán Tăng, p_up=52,7852%; baseline giá 82,54 nghìn VND. Hai đầu ra thuộc hai bài toán riêng.

### 4. Tài liệu và proposal

- [x] Proposal Markdown/LaTeX: đúng 8 mục, đủ 3 thành viên/vai trò, hai nhánh, mốc 2025, XGBoost, metrics/biểu đồ và kế hoạch 10 tuần.
- [x] Biên dịch XeLaTeX thành docs/cs114_proposal.pdf, 6 trang; kiểm tra trực quan toàn bộ và kiểm tra các lỗi tiêu đề/thuật ngữ/dung sai đã sửa.
- [x] Thay hình pipeline bằng sơ đồ hai nhánh.
- [x] Hoàn tất README và REPORT từ kết quả cuối; kiểm tra chéo cả 10 dòng phân loại và 10 dòng hồi quy với CSV.
- [x] Hoàn tất cẩm nang riêng 85 KB, 5 phần, ví dụ tính tay và 10 câu vấn đáp; .gitignore loại trừ và Git index không có tệp này.

### 5. Kiểm thử và công bố

- [x] Kiểm thử cuối: python -m pytest -q đạt 34 passed.
- [x] Kiểm thử cutoff trước target, nhãn t+1, chỉ báo không thay khi sửa tương lai, scaler Train-only, ghép không nhìn trước, hạn dữ liệu cũ và dự báo không dùng phiên cũ.
- [x] Chuỗi verify → supplemental → EDA → prepare → train → predict → pytest hoàn tất; nhật ký lệnh được giữ trong tmp/pipeline_logs và bị Git bỏ qua.
- [x] Quét từ khóa bị cấm, kiểm tra links/tài liệu, PDF, diff và kích thước tệp; cẩm nang riêng không nằm trong Git index.
- [x] Commit chính thức ce72fd0 và push main thành công; mọi tệp chính thức đã được công bố, cẩm nang riêng không thuộc commit.

## Giới hạn phải giữ trong tài liệu

Thiết kế đánh giá tại thời điểm này dùng Test để đánh dấu mô hình tốt nhất sau thực nghiệm. Thiết kế đã được thay thế bằng lựa chọn qua CV trong đợt nâng cấp tiếp theo; phạm vi kết luận hiện tại được tập hợp ở cuối REPORT.md.

## Xác nhận hoàn tất

Hoàn tất 100% các giai đoạn của đợt cập nhật. Lần kiểm thử sau stage đạt 34 passed. Commit ce72fd0 đã push lên origin/main. Cẩm nang riêng vẫn tồn tại cục bộ, được git check-ignore xác nhận và git ls-files không liệt kê. Nhật ký này được bổ sung xác nhận sau khi push thành công.


## Cập nhật Proposal theo nội dung chủ dự án gửi (26/10/2026)

- [x] Cập nhật LaTeX thành 7 mục theo bản mới; bỏ tiến độ, mục góp ý, vai trò thành viên và dòng lĩnh vực ở bìa.
- [x] Bổ sung giải nghĩa OHLCV, chỉnh câu về HOSE và nguồn giá FPT; sửa lỗi gõ và escape LaTeX từ tin nhắn.
- [x] Biên dịch XeLaTeX hai lần, mục lục được cập nhật; PDF 6 trang, không có cảnh báo tràn hộp.
- [x] Render và kiểm tra trực quan đủ 6 trang: bìa, bảng, sơ đồ, tiêu đề và ký hiệu dung sai hiển thị đúng.
- [x] Chỉ thay tài liệu Proposal và nhật ký; cẩm nang riêng tiếp tục bị Git bỏ qua.


## Giao diện Jupyter Notebook cho pipeline CS114

- [x] Kiểm tra 7 module nguồn, entrypoint và phụ thuộc của từng bước.
- [x] Tạo 8 notebook: một bản chạy toàn bộ và 7 bản tương ứng module; chia ô, giải thích tiếng Việt.
- [x] Bổ sung môi trường Jupyter và hướng dẫn chạy local/Colab.
- [x] Kiểm định cấu trúc, chạy đủ 8 notebook bằng kernel mới và đối chiếu kết quả với pipeline Python.
- [x] Chạy pytest (34 passed), xác minh dữ liệu nguồn không đổi và cẩm nang riêng bị Git bỏ qua.
- [x] Commit 5e8ee71 và đồng bộ notebook lên origin/main thành công.

Giữ src/*.py và tests/*.py để notebook dùng đúng thuật toán đã kiểm thử; tránh duy trì hai bản thuật toán khác nhau.

Đã tạo 8 notebook với tổng 151 ô (70 ô code, 81 ô hướng dẫn), chú thích tiếng Việt; kiểm định schema nbformat và cú pháp Python của toàn bộ ô đạt. Notebook không chứa output hay đường dẫn máy cá nhân. Cờ tải API mặc định tắt; tải thử ra tmp/ và không ghi đè snapshot. Đang chạy từng notebook bằng kernel mới trong bản sao cách ly tại tmp/notebook_validation để không thay artefact chính thức.

Kết quả thực thi: cả 8 notebook hoàn tất từ đầu đến cuối bằng kernel Python mới (thử cả cwd tại root và notebooks/). Notebook tổng hợp tự chạy 34 kiểm thử đạt. Cả hai CSV metrics đối chiếu từng cột với bản chính thức đạt sai số số học <= 1e-10; JSON dự báo cuối giống hệt; SHA-256 các CSV giá/nguồn bổ trợ/cổ phiếu lưu hành không đổi. Các notebook xuất bản giữ output trống để người học tự chạy; kết quả kiểm định chi tiết ở tmp/notebook_validation/summary.json (không công bố). Nhánh cài/clone riêng của Colab và tải API tùy chọn chưa thực thi trong lần kiểm định local này.


## Nâng cấp theo phản hồi giảng viên — 29/10/2026

- [x] Kiểm toán độ phủ ngành/thị trường; quyết định giữ/loại có căn cứ.
- [x] Tạo nhãn log return, nhóm ablation và cửa sổ đúng phiên giao dịch.
- [x] ADF/KPSS, ACF/PACF, phân rã chuỗi.
- [x] CV 5 fold chỉ trên Train; học máy, ARIMA/SARIMAX, LSTM/GRU nhiều cửa sổ.
- [x] SHAP, permutation importance và ablation cùng cohort.
- [x] Báo cáo/Proposal/LaTeX/cẩm nang riêng/notebook cập nhật kết quả thật.
- [x] Kiểm thử và kiểm tra nguồn/cẩm nang.
- [x] Commit và push main đợt nâng cấp chuỗi thời gian.

Phát hiện notebook 01 có thay đổi cục bộ từ người dùng; giữ nguyên nội dung đó khi nâng cấp.

### Kết quả thực hiện ngày 30/10/2026

- Đã kiểm tra 33 snapshot ngành (2016-02-06–2025-07-24), loại ba biến ngành vì thiếu lịch sử/thành phần theo thời điểm. G5 ghi excluded; VN-Index là biến thị trường chung, không phải chỉ số ngành thay thế.
- Tải trực tiếp DNSE: 4.635 phiên VN-Index, 2007-01-02–2025-09-30, giữ đơn vị điểm. Nguồn và hash trong vnindex_lineage.json.
- Nhánh 1: 32 đầu vào; Nhánh 2: 43. Cùng 1.559 nhãn, Train 1.325 (2019-04-03–2024-10-21), Test 234 (2024-10-22–2025-09-30); Test phân loại 227. Mọi L dùng phiên liên tiếp với chỉ số phiên gốc, không nén lỗ hổng.
- Đã chạy 5-fold CV gap=1, 30 dòng kết quả phân loại và 32 dòng hồi quy trên Test. Chọn HGB nhánh giá theo CV BA 0.550485, Test Accuracy 0.528634/BA 0.529193; hồi quy chọn ARIMA theo CV log RMSE 0.017192, Test RMSE giá 1.753715 nghìn VND.
- ADF log return Train p≈1.05e-17; KPSS p≈0.01638. Ghi nhận hai kiểm định không đồng thuận về tính dừng, không khẳng định chuỗi dừng hoàn toàn.
- SHAP và permutation chạy trên mô hình cây chọn bằng CV, background SHAP chỉ lấy Train. Ablation đánh giá G1/G2/G3/G4/G6; thêm đa nguồn chưa cải thiện đồng thời cả hai bài toán.
- Pipeline EDA → prepare → train → explain → predict hoàn tất sau sửa kiểm tra cửa sổ; 46 pytest đạt. Cảnh báo thư viện statsmodels/NumPy được giữ, không phải lỗi test.
- Đã kiểm định đủ 10 notebook bằng kernel mới: metrics khớp trong dung sai 1e-10, JSON dự báo giống hệt, dữ liệu gốc giữ hash. Bản notebook 01 có output người dùng vẫn giữ cục bộ, không đưa vào commit nâng cấp.
- Đã viết lại cẩm nang riêng 63.858 byte với tính tay chỉ báo, ADF/KPSS, CV, log return, ba họ mô hình, kết quả thật và 10 câu vấn đáp; tiếp tục bị .gitignore loại trừ.
- Proposal LaTeX/PDF 5 trang đã biên dịch hai lần và kiểm tra trực quan toàn bộ: mục 6, công thức, dấu ±, tên 3 sinh viên và sơ đồ hiển thị đúng. Có hai cảnh báo underfull về khoảng cách chữ, không có tràn nội dung.
- README, REPORT, PROPOSAL, tài liệu dữ liệu và notebook đồng bộ 32/43 biến và phương pháp mới; thay biểu đồ/importance cũ bằng artefact hiện tại.
- Kiểm tra cuối 46 passed; SHAP hữu hạn và tổng đóng góp cộng nền khớp raw output; 40/40 fit thống kê CV hội tụ. Snapshot verify đạt và không đổi. Quét tên nguồn không được công bố không có kết quả. Commit 62fa6f7 đã được push lên origin/main thành công.

### Xác nhận công bố

Đã push commit 62fa6f7 lên main: toàn bộ mã nguồn, kết quả thực nghiệm, 64 artefact mô hình (62 bản đánh giá và 2 bản minh họa), biểu đồ, notebook và tài liệu chính thức. Cẩm nang riêng không có trong Git index/commit. Output cục bộ của notebooks/01_fetch_data.ipynb vẫn giữ nguyên và không được stage. Đợt nâng cấp đã hoàn tất; nhật ký xác nhận này được đồng bộ bằng commit tài liệu tiếp theo.

## Rà soát chất lượng và đóng gói — 10/11/2026

- [x] Lưu dấu kiểm tra kết quả hiện tại, rà soát nội dung và notebook.
- [x] Rút gọn bảng theo CV trên Train, sửa thuật ngữ và khoảng trắng.
- [x] Tách logic CV dùng chung, kiểm thử tính bất biến và lọc cảnh báo thư viện cụ thể.
- [x] Cập nhật cẩm nang riêng với kịch bản thuyết trình 10 phút.
- [x] Biên dịch Proposal, kiểm tra toàn bộ trang PDF và cảnh báo căn lề.
- [x] Chạy kiểm thử, notebook và đối chiếu kết quả trước/sau.
- [x] Dọn bản nháp trong tmp, kiểm tra Git, commit và push main.

Giữ nguyên dữ liệu và kết quả thực nghiệm. Bảng chính chọn cấu hình theo CV; hồi quy gộp Linear/Ridge thành một họ để mỗi nhánh có 9 đại diện. Nhận xét về độ dài cửa sổ và tính dừng phải khớp số liệu. Notebook 01 có output cục bộ của người dùng, cần bảo toàn.

Đã rà soát 11 module nguồn và các kiểm thử hiện có. Tách danh mục cấu hình và hàm đánh giá CV dùng chung để tránh lặp giữa benchmark và ablation; thêm bộ chọn 9 đại diện dùng duy nhất điểm CV. Các module còn lại được chuẩn hóa định dạng, không thay thuật toán. 49 kiểm thử đạt; bộ lọc pytest chỉ áp dụng cảnh báo gán shape của statsmodels với NumPy 2.5.

README/REPORT đã có 3 phát hiện chính, bảng đại diện, bảng cửa sổ riêng và một mục giới hạn ở cuối REPORT. Số liệu không ủng hộ kết luận cửa sổ ngắn luôn tốt hơn; bảng giữ đúng lựa chọn CV. Cẩm nang riêng thêm kịch bản 10 phút. Proposal 5 trang đã hết cảnh báo Underfull/Overfull và đã đọc toàn bộ trang; sửa thêm chữ trong sơ đồ cho đồng nhất.

Đối chiếu cuối: 16 CSV báo cáo khớp ở dung sai 1e-10; 6 JSON kiểm tra giống hệt; 113 tệp dữ liệu/kết quả/mô hình ban đầu giữ nguyên SHA-256. 10/10 notebook chạy bằng kernel mới và 49/49 kiểm thử đạt. Notebook 01 giữ nguyên từng byte của bản người dùng. Kiểm tra liên kết Markdown, số hàng bảng, schema notebook và cú pháp các ô code đạt. Đã lưu chứng cứ rút gọn trong reports/polish_validation.json trước khi dọn tmp.

Đã xóa thư mục tmp sau khi kiểm tra đường dẫn tuyệt đối và xác nhận không có reparse point: 302 tệp, khoảng 43,02 MB. Đã dọn cache Python/pytest và tệp phụ biên dịch LaTeX. Cẩm nang riêng vẫn tồn tại và bị Git bỏ qua; bản notebook 01 của người dùng được giữ nguyên. Quét các định danh nguồn bị loại trừ không có kết quả. Đang chuẩn bị commit và công bố thay đổi chính thức lên main.

Hoàn tất đợt rà soát: commit 20741e9 đã được push lên origin/main thành công. Toàn bộ thay đổi chính thức và chứng cứ kiểm định đã được công bố; cẩm nang vẫn ở local và notebook 01 giữ output riêng, không thuộc commit. Nhật ký xác nhận này được đồng bộ bằng commit tài liệu kế tiếp.

## Thống nhất log return và rút gọn thực nghiệm — 19/11/2026

- [x] Kiểm tra trạng thái, bảo toàn output notebook cá nhân và cố định thiết kế mới.
- [x] Một mục tiêu log return, 5 phương pháp; ablation 32/38/43 biến và ARIMA/SARIMAX; GRU L=20/60.
- [x] Chạy lại EDA, chuỗi thời gian, CV/Test, dự báo và giải thích; trích 3 ca lỗi có bằng chứng.
- [x] Viết lại tài liệu theo 7 bước, cẩm nang riêng và Proposal PDF.
- [x] Cập nhật/chạy 10 notebook và kiểm thử; kiểm tra artefact và chống rò rỉ.
- [x] Dọn kết quả cũ và tmp, commit/push main, xác minh cẩm nang không công bố.

Thiết kế: giữ nguyên snapshot đến 30/09/2025 và cohort 1.559 nhãn để đối chiếu. Chọn mô hình bằng RMSE log return CV, không dùng Test. XGBoost chọn tham số trên 32 biến rồi giữ cùng tham số ở 38/43 biến để cô lập ảnh hưởng dữ liệu. GRU giữ hai cửa sổ. Baseline bằng 0 được ghi Đứng giá. Báo cáo quý trễ 45 ngày; cổ phiếu lưu hành dùng mốc hiệu lực đã có cộng 1 ngày (không giả định mọi số cổ phiếu đều là báo cáo quý). ADF/KPSS hỗ trợ lý do đổi thang mục tiêu, không chứng minh việc đổi thang bảo đảm dự báo tốt.

Đã thay luồng classifier bằng một dự báo log return, dấu hướng -1/0/+1 và bộ metrics chung; bỏ mã lựa chọn bảng cũ. Đã xóa artefact đánh giá cũ trước khi chạy lại. Dữ liệu FPT xác minh vẫn 4.671 hàng, cohort chung 1.559 nhãn. CV đang chạy; cả ARIMA và SARIMAX dùng cùng lưới bậc và hằng số để so sánh minh bạch. Output notebook cá nhân 00/01 đã sao lưu ngoài repo tại thư mục private_notebook_outputs_20261119 trong workspace.

Đã chạy xong 13 ứng viên × 5 fold và 9 cấu hình Test; mọi fit thống kê hội tụ. ARIMA (1,0,0) được chọn, CV RMSE 0,017191953; Test MAE 1,239203 nghìn VND. GRU chọn L=60 qua CV (0,017716299), Test MAE 1,221312; baseline 1,224967. XGBoost 32/38/43 giữ độ sâu 2: thêm dữ liệu làm RMSE tăng và đúng hướng giảm từ 51,98% xuống 48,02%. Đã sinh permutation/SHAP và 3 ca lỗi 03/04, 16/04, 03/02/2025, bối cảnh VN-Index từ snapshot gốc. 47 kiểm thử đạt. Tài liệu Markdown đã viết lại; đang biên dịch PDF và chạy notebook cách ly. Rà soát độc lập xác nhận không thấy leakage/metric sai; sẽ bỏ notebook 08 cũ bị trùng và làm rõ số hàng ngữ cảnh của ARIMA.

Kiểm định cuối: 10/10 notebook chạy bằng kernel mới trong bản sao cách ly; 13 CSV báo cáo khớp ở rtol 1e-10 / atol 1e-12 và JSON dự báo giống hệt. 47/47 tests đạt sau sửa khởi tạo tmp cho clone mới. Toàn bộ 15 CSV raw giữ SHA-256; không tải lại hoặc thay dữ liệu gốc. Đã bỏ notebook 08 trùng. Proposal 6 trang biên dịch hai lượt, 0 cảnh báo Underfull/Overfull, đã xem cả 6 trang; hình SHAP đã sửa nhãn trục. Chứng cứ lưu tại reports/restructure_validation.json.

Đã hoàn thiện cẩm nang riêng: kịch bản 10 phút/3 người/7 bước, ví dụ 5 ngày và công thức, 5 phương pháp, 3 bảng thực nghiệm, dòng dữ liệu thật 29/09→30/09/2025, permutation/SHAP, 3 ca lỗi và 10 câu vấn đáp. Tệp vẫn bị Git bỏ qua. Đang kiểm tra đóng gói cuối và công bố main.

Cẩm nang đã kiểm tra đầy đủ 10 phần và 10 câu vấn đáp, không tracked; quy ước giữ nguyên Proposal trong các đợt sau đã ghi ở đầu nhật ký. Mọi kiểm thử/notebook đã hoàn tất; bắt đầu dọn tmp/cache và chuẩn bị commit chính thức.

Hoàn tất: commit 6d2f11a đã push thành công lên origin/main; SHA local và remote khớp. Working tree sạch sau push, tmp/cache và tệp phụ LaTeX đã dọn; cẩm nang không tracked. Nhật ký xác nhận này được đồng bộ bằng commit tài liệu cuối. Tất cả 6 hạng mục của thiết kế rút gọn đã hoàn thành.
