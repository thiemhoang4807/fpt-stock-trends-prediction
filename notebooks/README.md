# Chạy và học dự án bằng Notebook

Notebook là tài liệu có các ô chữ và ô code. Ô chữ giải thích việc sắp làm; ô code thực hiện việc đó và hiển thị bảng, ảnh hoặc thông báo ngay bên dưới. Bạn có thể chạy từng ô bằng **Shift + Enter** để theo dõi dữ liệu biến đổi, hoặc dùng **Run All** để chạy từ đầu đến cuối.

Các notebook dùng chung những hàm trong `src/`. Thư mục Python và các bài kiểm thử vẫn được giữ để mỗi công đoạn có một cách tính thống nhất. Khi sửa công thức hoặc thuật toán trong `src/`, hãy khởi động lại kernel rồi chạy notebook từ đầu để Python nạp mã mới.

## 1. Chọn cách chạy

| Mục đích | Notebook nên mở |
|---|---|
| Muốn chạy trọn dự án và xem đầu ra ngay | [00_RUN_ALL.ipynb](00_RUN_ALL.ipynb) |
| Muốn hiểu dữ liệu đầu vào | [01_fetch_data.ipynb](01_fetch_data.ipynb), [02_fetch_supplemental.ipynb](02_fetch_supplemental.ipynb), [03_eda.ipynb](03_eda.ipynb) |
| Muốn học cách tạo biến đầu vào và nhãn | [04_features.ipynb](04_features.ipynb), [05_prepare.ipynb](05_prepare.ipynb) |
| Muốn huấn luyện, đọc độ đo và biểu đồ | [06_train.ipynb](06_train.ipynb) |
| Chỉ muốn dự báo bằng mô hình đã lưu | [07_predict.ipynb](07_predict.ipynb) |

Không cần chạy cả notebook tổng hợp lẫn toàn bộ notebook lẻ: hai cách này sử dụng cùng quy trình. Notebook tổng hợp phù hợp để chạy nhanh; notebook lẻ giúp đọc sâu từng công đoạn.

## 2. Chạy trên máy cá nhân

Bạn cần toàn bộ thư mục repository, gồm `src/`, `data/`, `models/` và `notebooks/`, thay vì chỉ tải một tệp notebook. Mở terminal tại thư mục gốc rồi cài môi trường:

```bash
python -m pip install -r requirements-notebooks.txt
python -m jupyterlab
```

`requirements-notebooks.txt` bao gồm thư viện mô hình của dự án và các công cụ notebook như JupyterLab, kernel Python và công cụ đọc/chạy notebook. Nếu đã dùng môi trường ảo cho dự án, hãy kích hoạt môi trường đó trước khi cài.

Trong cửa sổ JupyterLab:

1. Mở `notebooks/00_RUN_ALL.ipynb`.
2. Chọn kernel Python của môi trường vừa cài.
3. Chạy ô thiết lập đầu tiên, kiểm tra đường dẫn thư mục dự án được in ra.
4. Chọn **Run → Run All Cells**, hoặc dùng **Shift + Enter** lần lượt từng ô.

Với VS Code, mở cả thư mục repository, mở tệp `.ipynb`, nhấn **Select Kernel** và chọn đúng môi trường Python. Sau đó dùng **Run All** hoặc nút chạy bên trái từng ô.

Ô thiết lập tự tìm thư mục gốc từ thư mục hiện tại hoặc các thư mục cha. Vì vậy có thể mở Jupyter từ thư mục gốc hoặc từ `notebooks/`. Nếu thông báo không tìm thấy dự án, hãy mở Jupyter tại repository; việc đặt notebook trong một thư mục Downloads riêng sẽ không tự cung cấp các tệp dữ liệu cần thiết.

## 3. Chạy trên Google Colab

Trong Colab, chọn **File → Open notebook → GitHub**, nhập repository:

```text
https://github.com/thiemhoang4807/fpt-stock-trends-prediction
```

Chọn nhánh `main` và notebook muốn chạy. Bạn cũng có thể mở trực tiếp [notebook tổng hợp trên Colab](https://colab.research.google.com/github/thiemhoang4807/fpt-stock-trends-prediction/blob/main/notebooks/00_RUN_ALL.ipynb).

Chạy từ ô đầu tiên. Khi phát hiện đang ở Colab nhưng chưa có thư mục dự án, ô thiết lập sẽ clone repository chính thức. Cài thư viện được bật mặc định trên Colab; trên máy cá nhân, bước này mặc định tắt vì đã có lệnh cài ở trên. Nếu Colab báo cần khởi động lại phiên sau khi thay thư viện, chọn khởi động lại rồi chạy lại từ đầu. Điều này đặc biệt cần thiết khi pandas, NumPy hoặc scikit-learn đã được import trước lúc cài.

Không cần bật GPU cho các mô hình hiện tại: Logistic/Linear Regression, Random Forest, XGBoost và HistGradientBoosting trong dự án đang chạy bằng CPU. Khi phiên Colab bị ngắt hoặc xóa, những tệp vừa sinh trong phiên cũng có thể mất; tải các kết quả cần giữ về máy trước khi kết thúc.

## 4. Thứ tự các công đoạn và tệp kết quả

| Notebook | Nội dung chính | Kết quả được tạo hoặc đọc |
|---|---|---|
| `01_fetch_data` | Xem 6 cột OHLCV, kiểm tra snapshot và khoảng ngày | Đọc `data/raw/fpt/fpt_historical_price.csv`; tải mới chỉ khi chủ động bật ô tùy chọn |
| `02_fetch_supplemental` | Chuẩn hóa CSV nguồn; ghép dữ liệu từ ngày có thể sử dụng | Các CSV chuẩn hóa trong `data/raw/supplemental/`, `data/processed/fpt_multisource_features.csv`, `reports/supplemental_data_audit.json` |
| `03_eda` | Kiểm toán, xem giá, khối lượng, lợi nhuận và phân bố nhãn | `reports/data_audit.json` và các biểu đồ EDA trong `figures/` |
| `04_features` | Xem 32 biến giá/kỹ thuật, kiểm tra nhãn phiên kế tiếp | Các bảng minh họa trong notebook; dùng hàm trong `src/features.py` |
| `05_prepare` | Ghép 12 biến bổ trợ và giữ cùng những ngày đầy đủ cho hai nhánh | `data/processed/fpt_next_session_features.csv`, `data/processed/fpt_two_branch_features.csv` |
| `06_train` | Xem chia thời gian 85/15, mô hình, huấn luyện và bảng điểm | Các bảng metrics, dự báo Test và metadata trong `reports/`; ảnh trong `figures/`; mô hình trong `models/` |
| `07_predict` | Dùng mô hình đã lưu cho phiên sau ngày cuối snapshot | `reports/latest_prediction.json` |
| `00_RUN_ALL` | Thực hiện quy trình đầy đủ và kiểm thử ở ô cuối | Cùng các đầu ra chính thức ở trên |

Khi chạy các notebook lẻ từ đầu, dùng thứ tự `01 → 02 → 03 → 04 → 05 → 06 → 07`. Mỗi notebook có ô thiết lập riêng; biến Python trong notebook trước không tự xuất hiện trong notebook sau. Các công đoạn trao đổi thông tin qua tệp dữ liệu và mô hình đã lưu.

Repository đã đóng gói dữ liệu và các artefact của lần thực nghiệm trước. Vì vậy notebook dự báo có thể đọc mô hình sẵn có; nếu bạn thay dữ liệu hoặc đặc trưng, cần chạy lại notebook huấn luyện trước khi dự báo.

## 5. Hiểu các lựa chọn mặc định

**Dữ liệu cố định đến 30/09/2025.** Các notebook mặc định kiểm định và tái sử dụng snapshot đã đóng gói. Phần dữ liệu bổ trợ chuẩn hóa các tệp xuất nguồn có sẵn; chạy được phần này không có nghĩa là vừa tải trực tuyến mọi chỉ tiêu vĩ mô.

**Tải OHLCV mới là bước tùy chọn.** Ô tải lại mặc định tắt, cần bạn chủ động bật. Kết quả tải thử được lưu tại `tmp/notebook_download.csv`, tách khỏi snapshot nghiên cứu chính thức. Dịch vụ VCI/vnstock có thể yêu cầu tài khoản, giới hạn truy cập hoặc trả giá đã điều chỉnh ở một thời điểm khác. Không thay snapshot nghiên cứu rồi sử dụng lại mô hình cũ mà chưa chạy lại toàn bộ quy trình.

**Run All ghi lại kết quả thực nghiệm.** Các bảng chuẩn hóa, bảng đặc trưng, ảnh, metrics và mô hình được tạo tại các đường dẫn chính thức của dự án. Nếu muốn giữ một lần thực nghiệm riêng, sao lưu các đầu ra cần so sánh trước khi đổi cấu hình.

**Hai nhánh được so sánh trên cùng các ngày.** Nhánh 1 có 32 biến, Nhánh 2 có 44 biến. Dù lịch sử giá bắt đầu năm 2007, cửa sổ so sánh chung chỉ bắt đầu khi các biến bổ trợ có đủ dữ liệu. Không sửa notebook thành chia ngẫu nhiên hoặc fit bộ chuẩn hóa trên toàn bộ dữ liệu.

**Ảnh được hiển thị từ tệp kết quả.** Các hàm huấn luyện/EDA lưu ảnh bằng matplotlib; notebook mở lại các ảnh đó để bạn xem ngay. Có thể tải ảnh gốc trong `figures/` để đưa vào báo cáo.

## 6. Các lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `ModuleNotFoundError` cho thư viện ngoài | Cài `requirements-notebooks.txt` bằng đúng Python của kernel; khởi động lại kernel sau khi cài nếu cần. |
| Không tìm thấy module `features` hoặc tệp dữ liệu | Chạy ô thiết lập đầu tiên; kiểm tra thư mục root được in ra và mở đủ repository. |
| Báo thiếu bảng bổ trợ | Chạy `02_fetch_supplemental.ipynb` trước `05_prepare` hoặc `06_train`. |
| Báo thiếu mô hình `.joblib` | Chạy `06_train.ipynb` trước `07_predict`. |
| Đã sửa hàm trong `src/` nhưng notebook vẫn dùng cách tính cũ | Chọn **Restart Kernel**, rồi **Run All**; Python có thể giữ module đã import trong bộ nhớ. |
| Chạy một ô phía dưới báo biến chưa tồn tại | Chạy lại các ô trước theo thứ tự; sau khi restart, mọi biến trong bộ nhớ đã bị xóa. |
| Tải dữ liệu trực tuyến thất bại | Giữ chế độ snapshot để tái chạy thí nghiệm; chỉ dùng ô tải tùy chọn khi dịch vụ và quyền truy cập cho phép. |
| Huấn luyện đang chạy nhưng chưa hiện bảng điểm | Chờ ô kết thúc; ký hiệu đang chạy của kernel cho biết Python còn xử lý. Không chạy đồng thời cùng ô huấn luyện nhiều lần. |

Ô kiểm thử ở cuối notebook tổng hợp chạy `python -m pytest -q` trong một tiến trình Python riêng. Nếu báo lỗi, đọc thông báo lỗi trước khi dùng artefact vừa tạo; không coi việc đã hiện vài biểu đồ là bằng chứng toàn bộ pipeline đã hoàn tất.


## 7. Nếu muốn thay tham số mô hình

Ô xem cấu hình trong notebook 06 tạo các đối tượng để bạn đọc tham số, không truyền những đối tượng đó vào bước huấn luyện. Hàm `run_training` tự tạo mô hình từ `_classifier_models()` và `_regressor_models()` trong `src/train.py`. Để đổi tham số thật, sửa hai hàm này rồi khởi động lại kernel và chạy lại notebook từ đầu. Cần phân biệt việc đọc bảng cấu hình với việc thay cấu hình được dùng trong thực nghiệm.


## 8. Kiểm định lần bổ sung notebook

Cả 8 notebook đã được chạy từ đầu đến cuối bằng kernel Python mới trên máy Windows trong một bản sao dự án cách ly. Đã thử tìm root khi thư mục chạy là root hoặc notebooks/. Hai bảng metrics khớp pipeline Python (đối chiếu số học với dung sai 1e-10), JSON dự báo cuối giống hệt và các tệp giá/nguồn bổ trợ được giữ nguyên. Notebook tổng hợp cũng chạy đủ 34 kiểm thử pytest thành công.

Các file ipynb công bố để trống output; chạy ô sẽ hiện bảng/ảnh trong môi trường của bạn. Phần clone/cài riêng cho Colab và tải API tùy chọn không thuộc lần kiểm định local này. Phiên bản thư viện khác có thể làm số học hoặc khả năng nạp joblib khác; khi đó hãy huấn luyện lại trong môi trường đang dùng.
