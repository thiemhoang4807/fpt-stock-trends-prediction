# Đọc hiểu EDA và cách tạo đặc trưng của dự án FPT

Từ giá và khối lượng mỗi phiên, pipeline kiểm tra dữ liệu, tính chỉ báo rồi ghép thông tin bổ trợ đã có hiệu lực. Phần 2–3 hướng dẫn đọc các biểu đồ. Phần 4–7 giải thích công thức bằng bảng năm phiên giả định và một phiên FPT thật. [Sổ tay dữ liệu](../data/README.md) · [Cẩm nang huấn luyện và đánh giá](CAM_NANG_HIEU_DU_AN.md)

## 1. Một hàng dữ liệu có ý nghĩa gì?

Dự án đứng tại thời điểm **đã đóng cửa phiên giao dịch `t`**. Lúc đó biết giá mở cửa, cao nhất, thấp nhất, đóng cửa và khối lượng của phiên `t`, cũng như toàn bộ những phiên trước. Dự án dùng các thông tin đó để dự báo biến động đóng cửa của phiên giao dịch quan sát được kế tiếp `t+1`.

Phiên kế tiếp không nhất thiết là ngày mai theo lịch. Ví dụ, sau phiên thứ Sáu thường đến phiên thứ Hai; kỳ nghỉ có thể tạo khoảng cách dài hơn. Dữ liệu không được chèn ngày cuối tuần rồi điền giá lặp để giả thành một phiên giao dịch.

Ký hiệu dùng xuyên suốt:

| Ký hiệu | Nghĩa đời thường | Cột tương ứng |
|---|---|---|
| `C_t` | Giá đóng cửa hôm nay | `close` hoặc `current_close` |
| `O_t`, `H_t`, `L_t` | Giá mở cửa, cao nhất, thấp nhất hôm nay | `open`, `high`, `low` |
| `V_t` | Số cổ phiếu được giao dịch trong phiên | `volume` |
| `k` | Số phiên nhìn lại, không phải số ngày lịch | 5, 10, 20 hoặc 50 tùy công thức |
| `mean` | Cộng các số rồi chia số lượng | Trung bình |
| `std` | Mức độ các số phân tán quanh trung bình | Độ lệch chuẩn |
| `ln` và `exp` | Logarit tự nhiên và phép tính ngược của nó | `ln(1.01)` khoảng 0.00995; `exp(0.00995)` khoảng 1.01 |

**Đặc trưng** là thông tin đưa vào mô hình. **Mục tiêu/nhãn** là đáp án muốn mô hình học cách dự đoán. `next_close`, `next_return`, `next_log_return`, `target_date` và `direction` nằm trong bảng để chấm kết quả hoặc quản lý ngày; chúng không được đưa vào danh sách 32/38/42 đầu vào.

## 2. EDA: xem dữ liệu để trả lời câu hỏi nào?

EDA (*Exploratory Data Analysis*) là phân tích khám phá dữ liệu. Nhóm kiểm tra ngày, đơn vị, độ phủ và quan hệ giữa các mức giá, rồi quan sát các giai đoạn biến động mạnh.

### 2.1. Quy trình kiểm tra và kết quả thật

| Kiểm tra | Vì sao phải kiểm tra? | Kết quả trong snapshot hiện tại | Xử lý trong code |
|---|---|---|---|
| Có đủ `time, open, high, low, close, volume`? | Thiếu một cột có thể khiến công thức dùng nhầm dữ liệu. | Đủ 6 cột. | Thiếu cột thì dừng với lỗi rõ ràng. |
| Ngày và số có đọc được không? | Chuỗi chữ như dấu phẩy ngăn nghìn hoặc định dạng ngày sai không thể được xem là số hợp lệ. | 0 giá trị thiếu ở cả 6 cột. | Chuyển kiểu; giá trị không hợp lệ hoặc thiếu thì dừng, không tự lấy ngày mai bù vào. |
| Ngày có trùng, có theo thứ tự không? | Hai hàng một ngày có thể làm lệch toàn bộ phép trễ và nhãn phiên kế tiếp. | 0 ngày trùng, đã tăng dần. | Báo lỗi nếu trùng; sắp tăng dần trước khi tạo đặc trưng. |
| Có quan sát sau 30/09/2025 không? | Nhãn của hàng cuối chỉ được tính trong phạm vi nghiên cứu. | 4.671 hàng lưu từ 02/01/2007 đến 30/09/2025. | Cắt mốc **trước** khi `shift(-1)` tạo mục tiêu. |
| Giá có dương và hữu hạn không? | Chia cho 0 hoặc lấy log của giá âm làm công thức vô nghĩa. | Giá OHLC nằm trong 1.562–119.36875 nghìn VND/cổ phiếu. | Không cho phép giá ≤ 0, vô cực hoặc `NaN`. |
| Khối lượng có âm hoặc bằng 0? | Đối chiếu lịch giao dịch khi có volume bằng 0. | Hai hàng bằng 0 rơi vào ngày HOSE đóng cửa. | Loại hai ngày đóng cửa, còn 4.669 phiên. Khối lượng thấp nhất 1.820 và cao nhất 23.514.300 cổ phiếu. |
| Nến có hợp lý không? | Giá mở/đóng phải nằm trong khoảng thấp nhất–cao nhất của cùng phiên. | 3 phiên bất nhất: 17/08/2007, 10/06/2009, 07/12/2009. | Ghi trong kiểm toán, không âm thầm sửa. Cả 3 nằm trước cửa sổ thí nghiệm chung. |
| File đầu vào có bị thay sau lần chạy không? | Hai người dùng hai snapshot khác nhau có thể ra kết quả khác dù code giống nhau. | Có mã SHA-256 trong `reports/data_audit.json`. | Băm nội dung với xuống dòng chuẩn hóa để đối chiếu snapshot. |

Điều kiện nến hợp lý là:

$$L_t\leq\min(O_t,C_t),\quad H_t\geq\max(O_t,C_t),\quad L_t\leq H_t.$$

Nếu một hàng vi phạm, công thức nến có thể cho kết quả khó diễn giải. Giữ và đánh dấu giúp kiểm toán được nguồn gốc. Nếu sau này mở rộng cửa sổ nghiên cứu về các ngày này, cần xử lý chất lượng nguồn trước; không nên tự cắt số về biên rồi quên rằng dữ liệu từng có vấn đề.

### 2.2. Bốn biểu đồ EDA cần đọc như thế nào?

| Hình | Câu hỏi cần trả lời | Cách đọc và giới hạn |
|---|---|---|
| [Giá đóng cửa](../figures/01_fpt_close.png) | Mức giá có thay đổi lớn giữa các giai đoạn? | Trục ngang là ngày, trục dọc là nghìn VND/cổ phiếu theo snapshot. Mức giá cao hơn không tự có nghĩa phiên kế tiếp sẽ tăng. |
| [Khối lượng](../figures/02_fpt_volume.png) | Thanh khoản có tăng dần hoặc xuất hiện phiên đột biến? | Trục khối lượng dùng thang `symlog`: phần lớn được nén giống log để nhìn được cả số nhỏ và số rất lớn, nhưng vẫn hiển thị được số 0. Khoảng cách trên hình không phải chênh lệch tuyến tính. |
| [Phân phối lợi nhuận](../figures/03_daily_return_distribution.png) | Đa số phiên đổi ít hay nhiều? Có đuôi biến động lớn? | Mỗi cột đếm số phiên rơi vào một khoảng lợi nhuận; đường 0 phân biệt tăng/giảm. Đây là lợi nhuận đơn từ đóng cửa hôm trước đến hôm nay. |
| [Số phiên tăng/giảm/đứng giá](../figures/04_next_session_class_balance.png) | Nếu luôn nói “tăng” thì đúng được bao nhiêu? | Có 2.118 chuyển tiếp tăng, 2.074 giảm, 476 không đổi trong 4.668 chuyển tiếp. Không thể lấy tỷ lệ này thay cho tỷ lệ trên riêng tập Test. |

Số liệu mô tả toàn snapshot: lợi nhuận đơn trung bình **0.0644%/phiên**, độ lệch chuẩn **1.9193%/phiên**; nhỏ nhất **−6.9896%**, lớn nhất **+6.9922%**. Phân vị 1% là −4.9473%, phân vị 99% là +4.9717%. “Phân vị 1%” nghĩa là khoảng 1% số quan sát nằm dưới ngưỡng này; không phải xác suất cố định của một phiên tương lai.

Trung vị lợi nhuận bằng 0. Không nên suy ra rằng giá không biến động: các phiên tăng và giảm có thể bù nhau quanh giữa phân phối. Code EDA dùng `std(ddof=1)` để mô tả độ lệch chuẩn mẫu; các đặc trưng lăn ở phần sau dùng `ddof=0`. Hai mục đích này khác nhau và đã được ghi rõ.

Giá lịch sử giữ hệ quy chiếu của snapshot tài chính đã chuẩn hóa. Không diễn giải các mức giá đó như bằng chứng rằng chúng chính là giá chưa điều chỉnh mà người dùng từng thấy trên màn hình ở từng ngày quá khứ. Chi tiết hệ số căn lịch sử và đơn vị được giải thích trong [data/README.md](../data/README.md).

## 3. Phân tích chuỗi thời gian bổ sung cho EDA

### 3.1. Giá và lợi nhuận trả lời hai câu hỏi khác nhau

Giá 100 và giá 20 ở hai giai đoạn khác nhau rất khó so trực tiếp. Tăng từ 100 lên 101 và từ 20 lên 20.2 đều là tăng 1%; lợi nhuận đưa chúng về cùng thang so sánh. Dự án dùng:

$$u_t=\frac{C_t}{C_{t-1}}-1\quad\text{(lợi nhuận đơn)},\qquad r_t=\ln\left(\frac{C_t}{C_{t-1}}\right)\quad\text{(lợi nhuận log)}.$$

Ví dụ `100 → 101`: lợi nhuận đơn `101/100 − 1 = 0.01`, tức 1%; lợi nhuận log `ln(1.01) ≈ 0.00995033`. Log return không phải tỷ lệ phần trăm chính xác; muốn đổi ngược về lợi nhuận đơn, tính `exp(r) − 1`.

Lợi nhuận log còn có tính cộng theo thời gian: `ln(110/100) + ln(121/110) = ln(121/100)`. Dù vậy, đổi sang lợi nhuận không làm thông tin tương lai trở nên dễ đoán hoặc tự bảo đảm mọi giả định thống kê.

### 3.2. ADF và KPSS: hai cách đặt câu hỏi

“Dừng” ở đây nói về việc đặc điểm thống kê của chuỗi có ổn định theo thời gian hay không, chứ không phải giá đứng yên. Một chuỗi có thể nhấp nhô nhưng vẫn quanh một mức trung bình ổn định. Mức giá trôi từ vùng rất thấp lên vùng rất cao qua nhiều năm là một tình huống cần kiểm tra.

- **ADF** (*Augmented Dickey–Fuller*) khởi đầu từ giả thuyết chuỗi có **nghiệm đơn vị**: hiểu nôm na, tác động của cú sốc có thể không tự mất đi theo cơ chế hồi về mức ổn định. `p < 0.05` là bằng chứng bác bỏ giả thuyết đó trong thiết lập kiểm định.
- **KPSS** khởi đầu từ giả thuyết chuỗi **dừng quanh một mức trung bình hằng** trong cấu hình đang dùng (`regression="c"`). `p < 0.05` là bằng chứng bác bỏ giả thuyết dừng mức đó.
- `p-value` không phải “xác suất chuỗi dừng”. Đó là thước đo mức độ dữ liệu không phù hợp với giả thuyết gốc dưới mô hình kiểm định. Không bác bỏ cũng không có nghĩa đã chứng minh giả thuyết đúng.

Kết quả chính sử dụng lịch sử đến **29/11/2023**, là ngày kết thúc Train. Đây là lịch sử giá đầy đủ để phân tích chuỗi, không phải chỉ 2.576 hàng đủ dữ liệu đa nguồn.

| Chuỗi | Số quan sát | ADF: p-value | KPSS: p-value | Diễn giải vừa đủ theo kiểm định |
|---|---:|---:|---:|---|
| Giá đóng cửa | 4.214 | 0.9991 | < 0.01 | ADF không bác bỏ nghiệm đơn vị; KPSS bác bỏ dừng mức. |
| Lợi nhuận log | 4.213 | ≈ 5.63 × 10⁻¹⁷ | ≈ 0.03382 | Có bằng chứng mạnh chống nghiệm đơn vị, nhưng KPSS vẫn bác bỏ dừng mức. |

File kết quả ghi KPSS của giá là `0.01` kèm cảnh báo: giá trị thật nhỏ hơn giới hạn bảng tra. Vì vậy bảng trên ghi `< 0.01`, không coi `0.01` là giá trị chính xác. Số liệu toàn snapshot cũng được lưu để mô tả, tách khỏi nhóm `train_history`.

ADF kiểm tra nghiệm đơn vị, còn KPSS kiểm tra giả thuyết dừng mức quanh một hằng số. Kết quả KPSS báo hiệu cần tìm hiểu thêm cấu trúc của log return. Hiện tượng nhiều phiên biến động mạnh đi liền nhau cần được khảo sát riêng qua độ biến động theo thời gian hoặc kiểm định dành cho phương sai.

### 3.3. ACF và PACF dùng vào việc gì?

ACF là tương quan của chuỗi với chính nó ở các độ trễ. Ở độ trễ 1, câu hỏi là: “Giá trị hôm nay cao thì giá trị phiên trước có thường cao không?”. PACF cố gắng tách mối liên hệ ở một độ trễ sau khi đã tính đến các độ trễ ngắn hơn. Ví dụ, mối liên hệ giữa hôm nay và hai phiên trước có thể chỉ đi qua phiên ở giữa; PACF giúp xem phần còn lại.

Mở [hình ACF/PACF](../figures/12_acf_pacf.png): mỗi cột ứng với một độ trễ, code vẽ đến 40 phiên. Dải màu biểu diễn khoảng tin cậy xấp xỉ 95% theo cách tính của hàm thống kê. Cột vượt dải là dấu hiệu cần xem xét, không phải bảo đảm xây được mô hình dự báo tốt. Khi nhìn đồng thời nhiều cột, một số cột vượt dải có thể xuất hiện do ngẫu nhiên.

ACF của mức giá có thể kéo dài vì giá trôi theo xu hướng. Vì vậy dự án xem cả giá lẫn lợi nhuận log; không chọn mô hình chỉ từ việc thấy một đường giá trông có xu hướng.

### 3.4. Phân rã STL giúp nhìn điều gì?

[Hình phân rã](../figures/13_time_series_decomposition.png) tách **log của giá đóng cửa** thành:

$$\log(C_t)=\text{Trend}_t+\text{Seasonal}_t+\text{Residual}_t.$$

`Trend` là phần chuyển động chậm, `Seasonal` là phần lặp theo chu kỳ đặt trước, `Residual` là phần còn lại. Code đặt `period=5`, nghĩa là **quy ước chu kỳ 5 quan sát giao dịch**, không khẳng định thị trường có mùa vụ chính xác 5 phiên. Ngày nghỉ khiến 5 phiên không luôn khớp một tuần lịch. `robust=True` giúp phép phân rã bớt bị một vài điểm cực đoan chi phối.

STL trong dự án chỉ là hình mô tả trên lịch sử Train. Các thành phần phân rã không được dùng làm đầu vào dự báo; phép làm trơn này có thể dùng cả điểm trước và sau một thời điểm trong đoạn đang phân tích, nên không được tự chép toàn bộ `Trend` vào bảng đặc trưng rồi gọi là không rò rỉ.

## 4. Danh mục chính xác 32 đặc trưng giá và khối lượng

32 đầu vào gồm **5 trường gốc + 23 chỉ báo kỹ thuật + 4 đặc trưng nến**. Một “chỉ báo kỹ thuật” chỉ là một phép tóm tắt giá/khối lượng quá khứ. Nó cho mô hình một góc nhìn dễ học hơn; bản thân chỉ báo không tự phát ra lệnh mua/bán đúng.

Trong các bảng dưới, tỷ lệ `0.02` đọc là 2%. Cột có hậu tố `_pct` vẫn được lưu dưới dạng tỷ lệ, không tự nhân 100. RSI được đưa về 0–1; CPI bổ trợ lại lưu theo **điểm phần trăm**, chẳng hạn `3.6211` là 3.6211%: cần đọc đúng đơn vị của từng cột.

### 4.1. Năm trường gốc

| STT | Tên trong code | Giá trị | Vì sao đưa vào? |
|---:|---|---|---|
| 1 | `current_open` | `O_t`, nghìn VND/cổ phiếu | Mức giá bắt đầu phiên, làm bối cảnh cho chuyển động trong ngày. |
| 2 | `current_high` | `H_t`, nghìn VND/cổ phiếu | Mức giá cao nhất phiên, phản ánh biên trên đã chạm tới. |
| 3 | `current_low` | `L_t`, nghìn VND/cổ phiếu | Mức giá thấp nhất phiên, phản ánh biên dưới đã chạm tới. |
| 4 | `current_close` | `C_t`, nghìn VND/cổ phiếu | Mức giá cuối phiên, đồng thời là mốc đổi dự báo lợi nhuận thành giá. |
| 5 | `current_volume` | `V_t`, số cổ phiếu | Quy mô giao dịch hôm nay; cùng giá giúp mô hình quan sát bối cảnh thanh khoản. |

Các mức giá có thể đồng biến mạnh và gây dư thừa. Việc giữ chúng là thiết kế của thí nghiệm hiện tại, không phải khẳng định 5 cột đều đóng góp riêng biệt. Phép hoán vị đặc trưng cũng cần được diễn giải thận trọng khi các cột tương quan.

### 4.2. Năm lợi nhuận nhìn lại

$$\operatorname{return}_{k,t}=C_t/C_{t-k}-1.$$

| STT | Cột | Nhìn lại | Câu hỏi cung cấp cho mô hình |
|---:|---|---:|---|
| 6 | `return_1d` | 1 phiên | Hôm nay tăng/giảm bao nhiêu so với phiên trước? |
| 7 | `return_2d` | 2 phiên | Tổng mức thay đổi qua hai phiên là bao nhiêu? |
| 8 | `return_5d` | 5 phiên | Chuyển động ngắn hạn khoảng năm phiên ra sao? |
| 9 | `return_10d` | 10 phiên | Đà giá trong khoảng mười phiên ra sao? |
| 10 | `return_20d` | 20 phiên | Xu hướng trung hạn khoảng hai mươi phiên ra sao? |

`return_5d` **không phải** lợi nhuận một ngày của năm phiên trước. Nó lấy **giá hiện tại chia giá cách 5 phiên**, rồi trừ 1. Tất cả các cột trên dùng thông tin đến phiên hiện tại; từ “trễ/nhìn lại” không có nghĩa bỏ luôn giá hiện tại đã biết.

### 4.3. Tám tỷ lệ so với trung bình

SMA là trung bình cộng của `k` giá gần nhất, gồm cả hôm nay:

$$SMA_{k,t}=\frac{C_t+C_{t-1}+\cdots+C_{t-k+1}}{k},\qquad sma\_ratio=C_t/SMA_{k,t}-1.$$

EMA là trung bình cho quan sát mới trọng số cao hơn:

$$\alpha=\frac{2}{k+1},\qquad EMA_{k,t}=\alpha C_t+(1-\alpha)EMA_{k,t-1},\qquad ema\_ratio=C_t/EMA_{k,t}-1.$$

Code dùng `adjust=False`: bắt đầu từ giá đầu tiên rồi cập nhật theo công thức lặp; `min_periods=k` ẩn kết quả cho đến khi có ít nhất `k` quan sát. EMA không cắt sạch ảnh hưởng của mọi điểm xa hơn `k` phiên; trọng số của chúng nhỏ dần.

| STT | Cột | Mục đích |
|---:|---|---|
| 11 | `sma_5_ratio` | Giá hiện tại cao/thấp hơn trung bình 5 phiên bao nhiêu phần? |
| 12 | `sma_10_ratio` | So với mức nền 10 phiên. |
| 13 | `sma_20_ratio` | So với mức nền 20 phiên. |
| 14 | `sma_50_ratio` | So với mức nền dài hơn, 50 phiên. |
| 15 | `ema_5_ratio` | So với trung bình nhạy với giá mới, chu kỳ 5. |
| 16 | `ema_10_ratio` | Cùng ý nghĩa, chu kỳ 10. |
| 17 | `ema_20_ratio` | Cùng ý nghĩa, chu kỳ 20. |
| 18 | `ema_50_ratio` | Cùng ý nghĩa, chu kỳ 50. |

Ví dụ giá 105, SMA 100 thì tỷ lệ bằng `105/100 − 1 = 0.05`, tức đang cao hơn trung bình 5%. Đưa vào **tỷ lệ** giúp mức lệch có thể so giữa giai đoạn giá thấp và cao; “cao hơn trung bình” không mặc định có nghĩa phiên sau phải giảm.

### 4.4. RSI: bên tăng hay bên giảm đang chiếm ưu thế?

Đặt `d_t = C_t − C_(t−1)`, mức tăng `g_t = max(d_t, 0)`, mức giảm `l_t = max(−d_t, 0)`. Code lấy trung bình có trọng số theo:

$$G_t=\frac{1}{14}g_t+\frac{13}{14}G_{t-1},\qquad D_t=\frac{1}{14}l_t+\frac{13}{14}D_{t-1}.$$

$$RSI_t=100-\frac{100}{1+G_t/D_t},\qquad\texttt{rsi\_14}=RSI_t/100.$$

| STT | Cột | Mục đích |
|---:|---|---|
| 19 | `rsi_14` | Tóm tắt mức tăng tương đối so với mức giảm gần đây, theo thang 0–1. |

Trọng số `1/14` nghĩa là biến động mới đóng góp một phần, còn phần lớn trí nhớ nằm ở trung bình trước đó. Code khởi tạo từ biến động hợp lệ đầu tiên bằng `ewm(adjust=False)` và chỉ xuất sau ít nhất 14 biến động; không khởi tạo bằng trung bình cộng đúng 14 biến động như một số phần mềm khác. Vì thế các công cụ có thể hơi khác ở đầu chuỗi.

Nếu trung bình giảm bằng 0 còn tăng dương, RSI = 100; nếu cả hai bằng 0, RSI = 50. Ngưỡng quen gọi “quá mua” trên 70 và “quá bán” dưới 30 tương ứng trên 0.7/dưới 0.3 trong file. Đó là cách mô tả sự thiên lệch của biến động gần đây, không bảo đảm đảo chiều.

### 4.5. MACD: xu hướng nhanh lệch xu hướng chậm bao nhiêu?

Đặt `M_t = EMA12_t − EMA26_t`; đường tín hiệu `S_t = EMA9(M)_t`. “Histogram” là hiệu `M_t − S_t`, không phải histogram đếm số phiên của biểu đồ EDA.

| STT | Cột | Công thức chính xác | Vai trò |
|---:|---|---|---|
| 20 | `macd_ratio` | `M_t / C_t` | Độ lệch giữa mức giá nền nhanh và chậm. |
| 21 | `macd_signal_ratio` | `S_t / C_t` | Mức nền được làm bớt dao động của chính MACD. |
| 22 | `macd_histogram_ratio` | `(M_t − S_t) / C_t` | MACD hiện mạnh/yếu hơn đường tín hiệu bao nhiêu. |

Chia cho giá hiện tại giúp các giá trị có thang tương đối. Code tính EMA của **MACD chưa chia giá** rồi mới chia đường tín hiệu cho `C_t`; không lấy EMA9 của `macd_ratio`. Khác thứ tự có thể cho ra số khác.

### 4.6. Bollinger: vị trí giá trong vùng dao động gần đây

Với 20 giá đóng cửa gần nhất, lấy trung bình `m` và độ lệch chuẩn `s`:

$$s=\sqrt{\frac{1}{20}\sum_{i=0}^{19}(C_{t-i}-m)^2},\quad U=m+2s,\quad B=m-2s.$$

`ddof=0` trong code nghĩa là chia tổng bình phương cho đúng số quan sát 20; không phải chia 19. `U` là dải trên, `B` là dải dưới.

| STT | Cột | Công thức | Vai trò |
|---:|---|---|---|
| 23 | `bollinger_percent_b_20` | `(C_t − B)/(U − B)` | 0 tại dải dưới, 0.5 ở giữa, 1 tại dải trên. Có thể âm hoặc lớn hơn 1 nếu giá vượt dải. |
| 24 | `bollinger_width_20` | `(U − B)/m` | Độ rộng vùng dao động so với mức giá nền. |

Hai dải là thống kê mô tả, không phải giới hạn mà giá không thể vượt. Nếu 20 giá hoàn toàn bằng nhau, độ rộng bằng 0, `%B` không xác định; hàng đó không được lấp bằng số từ tương lai.

### 4.7. Độ biến động và khối lượng

Với lợi nhuận một phiên `u`, độ biến động trong `k` phiên là:

$$\sigma_{k,t}=\sqrt{\frac{1}{k}\sum_{i=0}^{k-1}(u_{t-i}-\bar u)^2}.$$

| STT | Cột | Công thức | Mục đích |
|---:|---|---|---|
| 25 | `volatility_5d` | Độ lệch chuẩn của 5 lợi nhuận đơn gần nhất, `ddof=0` | Thị trường vừa biến động êm hay mạnh trong ngắn hạn? |
| 26 | `volatility_20d` | Như trên với 20 lợi nhuận đơn | So với bối cảnh biến động dài hơn. |
| 27 | `log_volume_change_1d` | `ln(1+V_t) − ln(1+V_(t−1))` | Khối lượng đang tăng hay giảm tương đối, giảm ảnh hưởng của thang số rất lớn. |
| 28 | `log_volume_zscore_20d` | `(ln(1+V_t) − mean20(ln(1+V)))/std20(ln(1+V))` | Hôm nay nhộn nhịp hay vắng hơn mức thường thấy của chính cổ phiếu? |

Độ biến động không cho biết hướng: giảm mạnh và tăng mạnh đều làm độ phân tán tăng. `0.02` nghĩa là độ lệch chuẩn 2%/phiên trong cửa sổ đó; code không nhân căn 252 để quy đổi sang năm.

`z-score` là khoảng cách tới trung bình tính bằng số độ lệch chuẩn. Ví dụ trung bình log-khối lượng là 10, độ lệch chuẩn là 2, hôm nay bằng 12 thì `(12−10)/2 = 1`: cao hơn mức nền một độ lệch chuẩn. Nếu mẫu số bằng 0, code để thiếu và loại khỏi bảng đủ đặc trưng. `ln(1+V)` dùng được cả khi `V=0`, còn `ln(V)` thì không.

### 4.8. Bốn đặc trưng nến

| STT | Cột | Công thức | Mục đích |
|---:|---|---|---|
| 29 | `candle_range_pct` | `(H_t − L_t)/C_t` | Biên độ đi lại trong ngày so với mức giá. |
| 30 | `candle_body_pct` | `(C_t − O_t)/O_t` | Từ lúc mở đến lúc đóng, giá tăng hay giảm bao nhiêu? |
| 31 | `overnight_gap_pct` | `O_t/C_(t−1) − 1` | Mở cửa hôm nay nhảy bao nhiêu so với đóng cửa phiên trước? |
| 32 | `close_location_in_range` | `(C_t − L_t)/(H_t − L_t)` | Đóng cửa gần đáy hay gần đỉnh của phiên? |

Nếu `H_t=L_t`, khoảng ngày bằng 0, code đặt vị trí đóng cửa là 0.5 làm giá trị trung tính, tránh chia cho 0. Với nến hợp lệ, vị trí thường ở [0,1]; code không tự cắt các hàng nguồn bất nhất về khoảng này.

## 5. Tự tính bằng bảng 5 phiên nhỏ

Đây là dữ liệu **giả định để học phép tính**, không phải dữ liệu FPT và không dùng để báo cáo kết quả mô hình. Chu kỳ được rút xuống 2–5 để có đủ số tính nhẩm; dự án thật vẫn dùng đúng các chu kỳ đã nêu ở phần 4.

| Phiên | Giá đóng cửa | Khối lượng |
|---:|---:|---:|
| 1 | 10 | 100 |
| 2 | 12 | 120 |
| 3 | 11 | 110 |
| 4 | 14 | 140 |
| 5 | 13 | 130 |

### 5.1. Return: thay đổi tương đối

Từ phiên 1 sang 2: `(12−10)/10 = 2/10 = 0.2 = 20%`.

Từ phiên 2 sang 3: `(11−12)/12 = −1/12 ≈ −8.3333%`.

Từ phiên 3 sang 4: `3/11 ≈ 27.2727%`. Từ phiên 4 sang 5: `−1/14 ≈ −7.1429%`.

Lợi nhuận nhìn lại 2 phiên tại phiên 5 là `13/11−1 ≈ 18.1818%`; không phải cộng máy móc `27.2727% − 7.1429%`. Giá gốc của hai tỷ lệ một phiên khác nhau.

### 5.2. SMA và EMA: hai cách tính mức nền

SMA3 tại phiên 5: `(11+14+13)/3 = 38/3 ≈ 12.6667`. Tỷ lệ so SMA3: `13/12.6667 − 1 ≈ 0.026316 = 2.6316%`.

EMA3 có `alpha = 2/(3+1)=0.5`, tức chia đều trọng số cho giá mới và EMA cũ:

1. Khởi đầu `EMA1=10`.
2. `EMA2 = 0.5×12 + 0.5×10 = 11`.
3. `EMA3 = 0.5×11 + 0.5×11 = 11`.
4. `EMA4 = 0.5×14 + 0.5×11 = 12.5`.
5. `EMA5 = 0.5×13 + 0.5×12.5 = 12.75`.

Tỷ lệ so EMA3 tại phiên 5 là `13/12.75−1 ≈ 1.9608%`. EMA và SMA khác nhau vì EMA xem trọng những quan sát gần hơn.

### 5.3. RSI rút gọn: so mức tăng và mức giảm

Các biến động giá là `+2, −1, +3, −1`; phần tăng tương ứng `2,0,3,0`; phần giảm `0,1,0,1`. Minh họa cùng cách cập nhật của code nhưng với chu kỳ **3**, trọng số mới `1/3`, trọng số cũ `2/3`:

| Sau biến động | Trung bình tăng G | Trung bình giảm D |
|---|---|---|
| +2 | Khởi tạo `2` | Khởi tạo `0` |
| −1 | `(2/3)×2 + (1/3)×0 = 4/3` | `(2/3)×0 + (1/3)×1 = 1/3` |
| +3 | `(2/3)×(4/3) + 1 = 17/9` | `(2/3)×(1/3) = 2/9` |
| −1 | `(2/3)×(17/9) = 34/27` | `(2/3)×(2/9) + 1/3 = 13/27` |

Cuối cùng `RS=G/D=34/13≈2.6154`. `RSI = 100−100/(1+34/13) = 100×34/47 ≈ 72.34`; chia 100 được `0.7234`. Điều này chỉ nói mức tăng có trọng số đang lớn hơn mức giảm; không phải xác suất ngày mai tăng là 72.34%.

### 5.4. MACD rút gọn: mức nền nhanh trừ mức nền chậm

Dùng EMA2 làm đường nhanh và EMA3 ở trên làm đường chậm. EMA2 có trọng số mới `2/3`:

- Phiên 2: `(2/3)×12 + (1/3)×10 = 11.3333`.
- Phiên 3: `(2/3)×11 + (1/3)×11.3333 ≈ 11.1111`.
- Phiên 4: `(2/3)×14 + (1/3)×11.1111 ≈ 13.0370`.
- Phiên 5: `(2/3)×13 + (1/3)×13.0370 ≈ 13.0123`.

MACD minh họa ở phiên 5 là `13.0123−12.75≈0.2623`; chia giá 13 được khoảng `0.02018`. Đường tín hiệu là tiếp tục lấy EMA của dãy hiệu này; histogram lấy MACD trừ đường tín hiệu. Dự án thật dùng cặp **12/26** và đường tín hiệu **9**, không phải cặp 2/3 của ví dụ.

### 5.5. Bollinger: từ độ phân tán thành hai dải

Trung bình 5 giá là `(10+12+11+14+13)/5=12`.

Sai lệch so với 12: `−2,0,−1,2,1`. Bình phương: `4,0,1,4,1`. Cộng được 10; chia **5** được 2; lấy căn được `s≈1.4142`. Đây chính là ý nghĩa `ddof=0`.

Dải trên `12+2×1.4142=14.8284`; dải dưới `12−2×1.4142=9.1716`.

Tại giá 13: `%B=(13−9.1716)/(14.8284−9.1716)≈0.6768`. Giá đang ở khoảng 67.68% quãng đường từ dải dưới tới dải trên. `Bandwidth=(14.8284−9.1716)/12≈0.4714`, nghĩa là độ rộng hai dải bằng khoảng 47.14% mức trung bình trong ví dụ có dao động rất lớn này.

### 5.6. Volatility: lợi nhuận có nhảy thất thường không?

Với 5 giá chỉ có **4** lợi nhuận: `0.2, −0.083333, 0.272727, −0.071429`. Trung bình của chúng khoảng `0.079491`. Trừ trung bình khỏi từng số, bình phương các sai lệch, cộng rồi chia **4**, cuối cùng lấy căn: độ lệch chuẩn khoảng `0.159021`, tức **15.9021%/phiên**.

Đây là ví dụ độ biến động 4 lợi nhuận. Không thể lấy 5 giá để tính đúng `volatility_5d`: cần 6 giá để có đủ 5 chuyển tiếp. Trong dữ liệu thật, code đợi đủ số lợi nhuận rồi mới cho giá trị.

### 5.7. Khối lượng và nến

Khối lượng phiên 4→5 từ 140 xuống 130: log-volume change là `ln(131)−ln(141)=ln(131/141)`, khoảng **−0.07356**. Dấu âm nói khối lượng giảm; đây không phải lợi nhuận giá và cũng không phải tỷ lệ phần trăm đã nhân 100.

Để minh họa nến phiên 5, giả sử mở 12.5, cao 14, thấp 12, đóng 13; đóng cửa phiên 4 là 14:

- Biên độ ngày: `(14−12)/13≈0.15385`, tức 15.385%.
- Thân nến: `(13−12.5)/12.5=0.04`, tức tăng 4% từ mở đến đóng.
- Khoảng trống mở cửa: `12.5/14−1≈−0.10714`, tức thấp hơn đóng cửa phiên trước 10.714%.
- Vị trí đóng: `(13−12)/(14−12)=0.5`, đúng giữa biên độ ngày.

Một ngày có thể có thân nến dương nhưng vẫn giảm so với đóng cửa hôm trước. Vì thế thân nến và nhãn hướng phiên kế tiếp là hai đại lượng khác nhau.

## 6. Từ công thức thành bảng học máy: thiếu dữ liệu được xử lý ra sao?

### 6.1. Vì sao mất những hàng đầu tiên?

SMA50 cần 50 giá. Tại phiên đầu tiên chỉ có 1 giá, không thể tính đúng SMA50 nếu chưa biết tương lai. Code để ô thiếu (`NaN`), rồi loại các hàng chưa đủ 23 chỉ báo kỹ thuật. Đây là giai đoạn **tích lũy đủ lịch sử**, đôi khi gọi là *warm-up*.

Snapshot có 4.671 hàng. Hai ngày HOSE đóng cửa 23–24/01/2018 được bỏ trước khi tạo đặc trưng. Bảng kỹ thuật có **4.620 hàng** bắt đầu ở ngày đầu vào **20/03/2007**, tức 49 hàng đầu chưa đủ chỉ báo dài nhất. Trong dữ liệu khác, khoảng giá/khối lượng hoàn toàn không đổi có thể làm mẫu số bằng 0 và tạo thêm hàng không hợp lệ; không được mặc định rằng mọi lần chạy đều chỉ mất 49 hàng.

Bảng kỹ thuật giữ hàng cuối 30/09/2025 dù chưa có đáp án phiên sau. Vì vậy có 4.620 hàng đủ đặc trưng nhưng chỉ **4.619 hàng có nhãn**. Không điền nhãn chưa biết bằng 0: đó sẽ thành một đáp án đứng giá giả.

### 6.2. Vì sao so sánh thực nghiệm bắt đầu muộn hơn năm 2007?

Các nguồn bổ trợ không có cùng độ dài với giá FPT. Sau khi căn ngày công bố/hiệu lực, nhiều hàng cũ thiếu một hoặc nhiều biến. Dự án tạo một cửa sổ so sánh chung để mọi cấu hình được chấm trên cùng ngày, tránh việc mô hình dùng ít biến được thử trên giai đoạn dễ hơn mô hình nhiều biến.

`prepare.py` yêu cầu:

1. Đủ **42 đầu vào** tại mỗi hàng trong cửa sổ lịch sử cần dùng.
2. Có **60 phiên giao dịch liên tiếp** thỏa điều kiện đó, để GRU 20 và GRU 60 cũng so công bằng.
3. Giữ `session_index`, tức vị trí của phiên trong chuỗi gốc, để kiểm tra thật sự liên tiếp. Xóa một hàng thiếu không được làm hai ngày vốn cách nhau một phiên biến thành hai hàng liền ngày giả.

Kết quả là **3.032 hàng**, ngày đầu vào từ 06/08/2013 đến 30/09/2025; **3.031 nhãn** có ngày mục tiêu từ 07/08/2013 đến 30/09/2025. Sự thu hẹp này đến từ **độ phủ thực tế + ngày hiệu lực + yêu cầu cửa sổ 60 phiên**, trong khi kho giá bắt đầu vào năm 2007.

Dữ liệu bổ trợ được chọn bằng cách tìm bản ghi gần nhất đã có hiệu lực trước/ngay ngày đầu vào, đồng thời kiểm tra nó có quá cũ không. Không nội suy một đường đi qua báo cáo quý tương lai để lấp các ngày của quý hiện tại. [Hướng dẫn dữ liệu](../data/README.md) trình bày riêng độ trễ, giới hạn tuổi và số hàng thiếu của từng biến.

### 6.3. Chuẩn hóa để các thang đo không lấn át nhau

Một cột giá có số khoảng 80, một cột khối lượng khoảng 10 triệu, lợi nhuận khoảng 0.01, còn doanh thu có thể hàng nghìn tỷ đồng. Mô hình tuyến tính hoặc mạng GRU dễ bị ảnh hưởng bởi thang số nếu không xử lý phù hợp.

`StandardScaler` tính:

$$z=(x-\mu_{Train})/\sigma_{Train}.$$

Ví dụ Train có trung bình 100, độ lệch chuẩn 10; giá trị 120 đổi thành `(120−100)/10=2`. Giá trị 90 đổi thành `−1`. Nó thay thang đo, không biến phân phối bất kỳ thành phân phối chuẩn và không tự tạo thêm thông tin.

Trung bình/độ lệch chuẩn phải học từ phần Train tương ứng của từng fold. `Pipeline` là cách đóng các bước xử lý và mô hình thành một chuỗi để khi gọi `fit`, bước chuẩn hóa cũng chỉ học trên đúng dữ liệu được giao. Cây quyết định/XGBoost không cần chuẩn hóa theo cách giống Ridge; không nên áp dụng một scaler chung cho toàn bộ bảng rồi mới chia tập.

## 7. Theo dõi một dòng FPT có thật

Chọn ngày đầu vào **29/09/2025**, dự báo phiên mục tiêu **30/09/2025**. Snapshot ghi:

| Trường | Giá trị |
|---|---:|
| Open, High | 86.7975 nghìn VND/cổ phiếu |
| Low, Close | 84.75625 nghìn VND/cổ phiếu |
| Volume | 10.430.900 cổ phiếu |
| Close phiên kế tiếp | 82.54 nghìn VND/cổ phiếu |

Sau khi tạo đặc trưng:

- Biên độ nến `(86.7975−84.75625)/84.75625≈0.02408377`, tức 2.4084%.
- Thân nến `(84.75625−86.7975)/86.7975≈−0.02351738`, tức −2.3517%.
- Vị trí đóng cửa bằng 0 vì giá đóng ở đúng mức thấp nhất.
- `return_1d = −0.02051282`, tức −2.0513% so với đóng cửa phiên trước.
- `sma_5_ratio = −0.02251791`: thấp hơn trung bình 5 phiên khoảng 2.2518%.
- `rsi_14 = 0.35085516`, tương ứng RSI khoảng 35.09/100.
- `bollinger_percent_b_20 = −0.07948260`: giá nằm dưới dải dưới; số âm ở đây hợp lệ.

Đáp án học máy của hàng này là:

$$next\_log\_return=\ln(82.54/84.75625)\approx-0.02649647.$$

Lợi nhuận đơn tương ứng là `82.54/84.75625−1≈−0.02614851`, tức −2.6149%; nhãn hướng suy ra là −1 (giảm). Hai số −0.02649647 và −0.02614851 gần nhau nhưng không giống nhau.

Điểm cần kiểm tra khi mở bảng: giá **82.54 của ngày mục tiêu** chỉ nằm trong `next_close`/đáp án của hàng 29/09, không được trộn vào các cột đầu vào của hàng đó. Ngược lại, ở hàng đầu vào 30/09, `current_close=82.54` đã là thông tin biết được sau khi đóng cửa, còn nhãn phiên sau vẫn trống.

Khi mô hình đưa ra một dự báo log return `r_hat`, phần quy đổi sử dụng `C_t × exp(r_hat)`. Việc dùng `current_close` để đổi thang là hợp lệ vì đó là giá đã biết tại thời điểm dự báo. Dấu của `r_hat` cho hướng tăng, giảm hoặc đứng giá, nên chỉ cần một mục tiêu học để có hai đầu ra dễ hiểu.

## 8. Cách đọc và chạy để tự kiểm tra

**Kiểm tra mất cả hàng.** `isna()` chỉ thấy ô trống trong các hàng hiện có. `python src/audit_data_quality.py` còn đối chiếu danh sách ngày và quý. Sau khi bổ sung 33 phiên và hiệu chỉnh 16 mức giá VN-Index bằng CafeF, lịch ghép còn một ngày lệch trước năm 2013, ngày 23/07/2007. Trong phạm vi nghiên cứu, mọi phiên FPT đều có quan sát VN-Index tương ứng. Tệp tài chính có 52 hàng quý, với 22 quý thiếu trước năm 2013 và 50 quý liên tục từ quý I/2013 đến quý II/2025. [Kết quả kiểm toán](../reports/data_quality_review.json)

Đọc [hướng dẫn kiểm tra và bổ sung](HUONG_DAN_KIEM_TRA_VA_BO_SUNG_DU_LIEU.md) trước khi thay snapshot: chọn đúng chuỗi, đơn vị, ngày công bố, so phần giao nhau và giải trình xung đột. Không tự tạo số để làm cho một biểu đồ trông liên tục.

1. Mở [notebook 03](../notebooks/03_eda.ipynb), đọc kiểm toán rồi xem 4 hình để hiểu dữ liệu ban đầu.
2. Mở [notebook 04](../notebooks/04_features.ipynb), so hai hàng cuối của bảng với phần 7. Đối chiếu tên cột trong danh mục 32 biến thay vì đoán ý nghĩa từ tên viết tắt.
3. Mở [notebook 05](../notebooks/05_prepare.ipynb) và [data/README.md](../data/README.md), kiểm tra vì sao các nguồn ngắn hơn làm cửa sổ so sánh thu hẹp.
4. Mở [notebook 08](../notebooks/08_time_series_analysis.ipynb), phân biệt ADF/KPSS, ACF/PACF và STL. Đây là các công cụ giúp đặt câu hỏi về chuỗi, không phải các đáp án đúng/sai thay thế đánh giá mô hình.
5. Đọc [báo cáo](REPORT.md) để xem việc thêm biến thực sự cải thiện hay làm giảm kết quả. Một biến có lý do kinh tế hợp lý vẫn có thể không hữu ích cho dự báo một phiên sau.

Các file kết quả dùng để kiểm chứng nội dung: `reports/data_audit.json`, `reports/stationarity_tests.json`, `data/processed/fpt_next_session_features.csv` và `data/processed/fpt_experiment_features.csv`. Các công thức bên trên mô tả phép tính đang chạy; ví dụ thu nhỏ không thay thế chu kỳ và tham số của code thật.
