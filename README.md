# Phân tích hiệu quả chiến dịch quảng cáo đa nền tảng – Shopee Sale 5.5

Bài tập lớn giữa kỳ môn Phân tích dữ liệu · Nhóm đề tài: **Marketing Analytics**

## 1. Giới thiệu

Bài phân tích 1.000 chiến dịch quảng cáo trong đợt sale Shopee 5.5 (28/04/2024 – 10/05/2024) chạy trên 5 nền tảng: Facebook, TikTok, Google, Instagram và Shopee Ads.

**Câu hỏi nghiên cứu**
1. Nền tảng nào hiệu quả nhất (ROAS cao, CPA thấp)?
2. Loại nhóm quảng cáo (ad set) nào hiệu quả nhất và kém nhất?
3. Hiệu quả thay đổi thế nào theo thời gian, quanh ngày sale 5/5?
4. Nên phân bổ lại ngân sách như thế nào?

## 2. Cấu trúc thư mục

```
BTL/
├── README.md                                  ← file này
├── [Huydata] shopee_sale_5_5_cleandata.xlsx   ← dữ liệu gốc
├── Shopee_5_5_Marketing_Analytics.ipynb       ← notebook: làm sạch + phân tích (đã chạy sẵn kết quả)
├── shopee_5_5_cleaned.csv                     ← dữ liệu đã làm sạch (notebook xuất ra, dashboard đọc)
├── app.py                                     ← dashboard (giao diện)
├── cleaning.py                                ← bộ làm sạch dữ liệu dùng trong dashboard
├── requirements.txt                           ← thư viện cho dashboard
├── .streamlit/config.toml                     ← cấu hình ẩn nút Deploy
├── charts/                                    ← 6 biểu đồ PNG xuất từ notebook
├── du_lieu_mau/                               ← 2 file mẫu để thử dashboard (chưa sạch / đã sạch)
└── Huong_dan_doc_hieu_code.docx               ← tài liệu giải thích code, khung báo cáo, câu hỏi bảo vệ
```

Notebook đọc được cả `.xlsx` lẫn `.csv`: đổi biến `FILE_PATH` ở đầu notebook thành tên file muốn dùng (file đặt cùng thư mục với notebook).

## 3. Quy trình phân tích

| Bước | Nội dung |
|---|---|
| 1 | Đọc dữ liệu (đọc mọi cột dạng chữ để không mất giá trị bẩn) và khám phá ban đầu |
| 2 | Kiểm tra chất lượng dữ liệu |
| 3 | Làm sạch dữ liệu |
| 4 | Tạo chỉ số marketing (CTR, CPC, CVR, CPA, ROAS, AOV) và biến mới |
| 5 | Phân tích theo nền tảng, ad set, thời gian; kiểm định Kruskal-Wallis; mô phỏng ngân sách |
| 6 | Kết luận, đề xuất, hạn chế |

**Dữ liệu gốc còn rất bẩn dù tên file ghi "cleandata".** Các lỗi đã xử lý:

- Tên nền tảng có 30 cách viết cho 5 nền tảng → chuẩn hóa về 5.
- Số lẫn ký tự: `1,035`, `1601$`, `850usd`, `1726đ`, `1.2k`, `1 210`, `1029,00`, `1O0`, `ten thousand`.
- Chi phí âm (17 dòng) và bằng 0 (12 dòng); clicks lớn hơn impressions (23 dòng); conversions bất thường (26 dòng).
- Ngày có 8 định dạng, 28 dòng ngày không hợp lệ.
- **Không điền giá trị thiếu**: mỗi chỉ số chỉ tính trên các dòng đủ dữ liệu cần thiết.

## 4. Cách chạy

**Yêu cầu:** Python 3.9 trở lên (tải ở python.org, nhớ tick "Add Python to PATH").

### 4.1 Notebook

```bash
pip install pandas numpy matplotlib seaborn scipy openpyxl jupyter
jupyter notebook Shopee_5_5_Marketing_Analytics.ipynb
```

Mở notebook rồi chọn **Run All**. Chạy xong sẽ tạo thư mục `charts/` và file `shopee_5_5_cleaned.csv`. Nếu chỉ cần xem kết quả thì không cần chạy lại, vì notebook đã có sẵn output.

### 4.2 Dashboard

```bash
pip install -r requirements.txt
streamlit run app.py
```

Trình duyệt tự mở `http://localhost:8501`. Dừng bằng `Ctrl + C` ở cửa sổ terminal.

Nếu báo `'streamlit' is not recognized`, dùng `python -m streamlit run app.py`.

Dashboard gồm bộ lọc (nền tảng, nhóm ad set, tên chiến dịch, khoảng ngày), các chỉ số chính và 5 tab: Nền tảng, Ad set, Theo thời gian, Chuyển ngân sách, Dữ liệu.

Có thể tải thẳng file CSV hoặc Excel **gốc chưa làm sạch**: dashboard tự làm sạch (cùng quy tắc với notebook) và hiện báo cáo đã sửa những gì ở tab Dữ liệu. Có thể tải nhiều file lần lượt; các file đã tải hiện trong danh sách ở thanh bên để bấm xem lại (bộ lọc của từng file được nhớ riêng). Danh sách chỉ lưu trong phiên làm việc, tải lại trang sẽ mất.

## 5. Các chỉ số sử dụng

| Chỉ số | Công thức | Ý nghĩa |
|---|---|---|
| CTR | clicks / impressions | Tỉ lệ người thấy quảng cáo và bấm vào |
| CPC | spend / clicks | Chi phí mỗi lượt click |
| CVR | conversions / clicks | Tỉ lệ click chuyển thành đơn |
| CPA | spend / conversions | Chi phí để có một đơn |
| ROAS | revenue / spend | Doanh thu thu về trên mỗi 1 đồng chi quảng cáo |
| AOV | revenue / conversions | Giá trị trung bình mỗi đơn |

Chỉ số của một nhóm được tính bằng **tổng tử / tổng mẫu** trên các dòng đủ dữ liệu, không lấy trung bình các tỉ lệ từng dòng.

## 6. Kết quả chính

| Nền tảng | ROAS | CPA | % chi phí | % doanh thu |
|---|---|---|---|---|
| Shopee Ads | 5,85 | 18,63 | 8,5% | 10,0% |
| Facebook | 5,73 | 20,02 | 24,0% | 27,5% |
| Instagram | 5,50 | 23,15 | 10,1% | 11,2% |
| Google | 4,76 | 26,03 | 23,9% | 22,8% |
| TikTok | 4,25 | 27,91 | 33,5% | 28,5% |

- ROAS toàn chiến dịch ≈ **4,99**.
- Chênh lệch ROAS giữa các nền tảng **có ý nghĩa thống kê** (p < 0,001); giữa các nhóm ad set thì chưa (p ≈ 0,18).
- TikTok chiếm nhiều ngân sách nhất nhưng hiệu quả thấp nhất.
- Không thấy đỉnh hiệu quả vào đúng ngày sale 5/5.
- **Đề xuất:** chuyển bớt ngân sách TikTok sang Facebook và Shopee Ads. Mô phỏng cho thấy chuyển 10–20% có thể tăng doanh thu thêm khoảng 1–2% (giả định ROAS không đổi).

## 7. Hạn chế

- Chỉ có 13 ngày của một sự kiện, chưa thể khái quát cho giai đoạn khác.
- Đơn vị tiền trong dữ liệu gốc không thống nhất (`usd`, `$`, `đ`); bài giả định cùng một đơn vị.
- Còn 4,5–8,2% giá trị thiếu mỗi cột; một số giá trị bất thường đã bị loại.
- ROAS tính theo doanh thu, chưa trừ giá vốn nên chưa phải lợi nhuận.
- Mô phỏng ngân sách mang tính minh họa; tương quan không đồng nghĩa với nhân quả.
- Code làm sạch và dashboard viết riêng cho bộ cột của file này (`campaign_id, campaign_name, platform, ad_set, spend, clicks, impressions, conversions, revenue, date`). File có cột khác cần chỉnh lại code.

## 8. Công nghệ

Python · pandas · numpy · matplotlib · seaborn · scipy · Streamlit · Altair

## 9. Nguồn dữ liệu

Bộ dữ liệu `_Huydata__shopee_sale_5_5_cleandata.xlsx` được lấy từ video TikTok của kênh **@huydata2025**:

- Link: https://www.tiktok.com/@huydata2025/video/7630316767084039432?lang=vi-VN

Dữ liệu gốc thuộc quyền của tác giả nguồn; bài này chỉ sử dụng cho mục đích học tập.

## 10. Tác giả

Bài tập lớn giữa kỳ do nhóm thực hiện:

- **Phan Phúc Lộc**
- **Nguyễn Hữu Vàng**

Phần phân tích, source code (notebook và dashboard) và tài liệu trong thư mục này thuộc về nhóm tác giả nêu trên.
