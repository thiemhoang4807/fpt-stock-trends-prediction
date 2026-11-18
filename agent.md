# Nhật ký thực hiện CS114

## Mục tiêu và trạng thái hiện tại

Thiết kế hiện hành: cutoff 30/09/2025; một mục tiêu next_log_return suy ra giá và hướng; năm phương pháp chính và ba thí nghiệm, CV 5 fold trong Train 85%, Test 15%. Nhật ký các thiết kế cũ bên dưới được giữ như lịch sử, không phải luồng chạy hiện tại.

**Quy ước từ người dùng ngày 19/11/2026:** Từ các đợt cập nhật sau, không chỉnh docs/PROPOSAL.md, docs/cs114_proposal.tex hoặc docs/cs114_proposal.pdf vì đã nộp giảng viên; chỉ chỉnh các file khác. Bản Proposal của đợt rút gọn này đã hoàn tất trước chỉ dẫn mới và được giữ nguyên.

## Checklist theo giai đoạn

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
- [ ] Dọn kết quả cũ và tmp, commit/push main, xác minh cẩm nang không công bố.

Thiết kế: giữ nguyên snapshot đến 30/09/2025 và cohort 1.559 nhãn để đối chiếu. Chọn mô hình bằng RMSE log return CV, không dùng Test. XGBoost chọn tham số trên 32 biến rồi giữ cùng tham số ở 38/43 biến để cô lập ảnh hưởng dữ liệu. GRU giữ hai cửa sổ. Baseline bằng 0 được ghi Đứng giá. Báo cáo quý trễ 45 ngày; cổ phiếu lưu hành dùng mốc hiệu lực đã có cộng 1 ngày (không giả định mọi số cổ phiếu đều là báo cáo quý). ADF/KPSS hỗ trợ lý do đổi thang mục tiêu, không chứng minh việc đổi thang bảo đảm dự báo tốt.

Đã thay luồng classifier bằng một dự báo log return, dấu hướng -1/0/+1 và bộ metrics chung; bỏ mã lựa chọn bảng cũ. Đã xóa artefact đánh giá cũ trước khi chạy lại. Dữ liệu FPT xác minh vẫn 4.671 hàng, cohort chung 1.559 nhãn. CV đang chạy; cả ARIMA và SARIMAX dùng cùng lưới bậc và hằng số để so sánh minh bạch. Output notebook cá nhân 00/01 đã sao lưu ngoài repo tại thư mục private_notebook_outputs_20261119 trong workspace.

Đã chạy xong 13 ứng viên × 5 fold và 9 cấu hình Test; mọi fit thống kê hội tụ. ARIMA (1,0,0) được chọn, CV RMSE 0,017191953; Test MAE 1,239203 nghìn VND. GRU chọn L=60 qua CV (0,017716299), Test MAE 1,221312; baseline 1,224967. XGBoost 32/38/43 giữ độ sâu 2: thêm dữ liệu làm RMSE tăng và đúng hướng giảm từ 51,98% xuống 48,02%. Đã sinh permutation/SHAP và 3 ca lỗi 03/04, 16/04, 03/02/2025, bối cảnh VN-Index từ snapshot gốc. 47 kiểm thử đạt. Tài liệu Markdown đã viết lại; đang biên dịch PDF và chạy notebook cách ly. Rà soát độc lập xác nhận không thấy leakage/metric sai; sẽ bỏ notebook 08 cũ bị trùng và làm rõ số hàng ngữ cảnh của ARIMA.

Kiểm định cuối: 10/10 notebook chạy bằng kernel mới trong bản sao cách ly; 13 CSV báo cáo khớp ở rtol 1e-10 / atol 1e-12 và JSON dự báo giống hệt. 47/47 tests đạt sau sửa khởi tạo tmp cho clone mới. Toàn bộ 15 CSV raw giữ SHA-256; không tải lại hoặc thay dữ liệu gốc. Đã bỏ notebook 08 trùng. Proposal 6 trang biên dịch hai lượt, 0 cảnh báo Underfull/Overfull, đã xem cả 6 trang; hình SHAP đã sửa nhãn trục. Chứng cứ lưu tại reports/restructure_validation.json.

Đã hoàn thiện cẩm nang riêng: kịch bản 10 phút/3 người/7 bước, ví dụ 5 ngày và công thức, 5 phương pháp, 3 bảng thực nghiệm, dòng dữ liệu thật 29/09→30/09/2025, permutation/SHAP, 3 ca lỗi và 10 câu vấn đáp. Tệp vẫn bị Git bỏ qua. Đang kiểm tra đóng gói cuối và công bố main.

Cẩm nang đã kiểm tra đầy đủ 10 phần và 10 câu vấn đáp, không tracked; quy ước giữ nguyên Proposal trong các đợt sau đã ghi ở đầu nhật ký. Mọi kiểm thử/notebook đã hoàn tất; bắt đầu dọn tmp/cache và chuẩn bị commit chính thức.
