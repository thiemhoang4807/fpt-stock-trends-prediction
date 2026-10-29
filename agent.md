# Nhật ký thực hiện CS114

## Mục tiêu và trạng thái hiện tại

Cắt nghiên cứu về 30/09/2025; dựng hai nhánh giá và đa nguồn, so sánh 5 mô hình phân loại và 5 mô hình hồi quy trên cùng Train 85% / Test 15%; hoàn thiện tài liệu, proposal LaTeX và giữ riêng cẩm nang.

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

Test được dùng để đánh dấu mô hình tốt nhất sau thực nghiệm theo yêu cầu; điểm mô hình được chọn vì vậy chưa phải đánh giá độc lập. Độ trễ báo cáo quý/GDP là giả định mô phỏng, dữ liệu có thể đã điều chỉnh lại, chưa phải kho lịch sử từng phiên bản. Lịch sử cổ phiếu là các mốc đã thu thập, không phải sổ thay đổi hằng ngày đầy đủ. Không nội suy dựa vào báo cáo tương lai. Một cổ phiếu và một cửa sổ Test chưa chứng minh hiệu quả đầu tư.

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
- [x] CV5fold chỉ trên Train; học máy, ARIMA/SARIMAX, LSTM/GRU nhiều cửa sổ.
- [x] SHAP, permutation importance và ablation cùng cohort.
- [x] Báo cáo/Proposal/LaTeX/cẩm nang riêng/notebook cập nhật kết quả thật.
- [x] Kiểm thử và kiểm tra nguồn/cẩm nang.
- [x] Commit và push main đợt nâng cấp chuỗi thời gian.

Phát hiện notebook 01 có thay đổi cục bộ từ người dùng; giữ nguyên nội dung đó khi nâng cấp. Test cũ đã từng được xem trong các phiên bản trước, nên holdout mới chỉ độc lập với quy trình lựa chọn lần này, không phải tập chưa từng được nhóm quan sát.

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
