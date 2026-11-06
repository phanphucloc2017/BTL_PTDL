# Cách chạy dashboard

1. Cài thư viện (một lần):  `pip install -r requirements.txt`
2. Đặt `app.py` và `shopee_5_5_cleaned.csv` cùng một thư mục.
3. Chạy:  `python -m streamlit run app.py`  → trình duyệt tự mở http://localhost:8501

File `shopee_5_5_cleaned.csv` được xuất ra từ notebook `Shopee_5_5_Marketing_Analytics.ipynb`.

## Tải nhiều file và xem lại

- Dùng ô "Tải file CSV đã làm sạch" ở thanh bên. Tải file nào, app chuyển sang xem file đó.
- Các file đã tải nằm trong danh sách "Các file đã tải lên", bấm vào tên để xem lại. Bộ lọc của mỗi file được nhớ riêng.
- Tab "Dữ liệu" có bảng so sánh nhanh các file đã tải (số dòng, tổng chi phí, ROAS chung).
- File phải là CSV đã chạy qua notebook làm sạch (cần có các cột ROAS, ad_set_group, phase, day_type...). File Excel gốc chưa làm sạch sẽ bị báo thiếu cột.
- Danh sách chỉ lưu trong phiên làm việc, tải lại trang sẽ mất.
