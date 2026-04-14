# Hướng dẫn sử dụng hệ thống VN Stock

## 1. Quét kỹ thuật nhanh
```bash
python3 vn_stock_scan.py VIC TCB NVL
```

### Compact mode
```bash
python3 vn_stock_scan.py VIC TCB NVL --compact --top 3
```

## 2. Quét tin tức nhanh
```bash
python3 vn_stock_news.py VIC TCB NVL --limit 6
```

## 3. Tạo report tổng hợp
```bash
python3 vn_stock_report.py VIC TCB NVL --top 5 --tai-khoan 30000000 --rui-ro 1 --ti-le-toi-da 0.35
```

## 4. Chọn mode giao dịch
### Cân bằng
```bash
python3 vn_stock_report.py VIC TCB NVL --mode balanced
```

### Đánh T+ nhanh
```bash
python3 vn_stock_report.py VIC TCB NVL --mode scalp
```

### Swing ngắn
```bash
python3 vn_stock_report.py VIC TCB NVL --mode swing
```

### Giữ theo trend
```bash
python3 vn_stock_report.py VIC TCB NVL --mode trend
```

### Phòng thủ
```bash
python3 vn_stock_report.py VIC TCB NVL --mode defensive
```

### Chủ động/rủi ro cao
```bash
python3 vn_stock_report.py VIC TCB NVL --mode aggressive
```

## 5. Dùng kèm portfolio file
Mặc định hệ thống đọc file:
- `memory/vn_portfolio.json`

File ví dụ công khai trong repo:
- `examples/vn_portfolio.example.json`

Ví dụ cấu trúc:
```json
{
  "positions": {
    "VIC": {"quantity": 15, "avg_price": 159.1, "t_plus": 0, "note": "mới mua"},
    "TCB": {"quantity": 900, "avg_price": 32.4, "t_plus": 1},
    "NVL": {"quantity": 100, "avg_price": 17.15, "t_plus": 1}
  }
}
```

Hoặc truyền file khác:
```bash
python3 vn_stock_report.py VIC TCB NVL --portfolio-file memory/vn_portfolio.json
```

Nếu muốn test nhanh bằng file ví dụ trong repo export:
```bash
python3 vn_stock_report.py VIC TCB NVL --portfolio-file examples/vn_portfolio.example.json
```

## 6. Những trường nên chú ý trong output
### Cấp thị trường
- `boi_canh_thi_truong`
- `do_rong_thi_truong`
- `do_rong_thi_truong_mo_rong`
- `chat_luong_du_lieu`

### Cấp từng mã
- `tong_diem`
- `xep_loai`
- `diem_thanh_phan`
- `du_lieu_thoi_gian`
- `canh_bao_du_lieu`
- `danh_muc_hien_tai`
- `ke_hoach_hanh_dong`
- `vung_mua_ly_tuong`
- `khong_mua_duoi_tren`
- `moc_sai`
- `quan_tri_von`

## 7. Cách đọc warning
- `intraday_data_not_fresh`: dữ liệu intraday chưa đủ mới
- `h1_data_stale`: dữ liệu H1 đã cũ
- `daily_data_not_fresh`: dữ liệu daily không còn mới
- warning từ dòng tiền: thiếu ngoại/tự doanh hoặc lỗi lấy dữ liệu

## 8. Gợi ý dùng thực chiến
- Buổi sáng: chạy `vn_stock_news.py` + `vn_stock_scan.py --compact`
- Trước vào lệnh: chạy `vn_stock_report.py ... --mode scalp|swing`
- Cuối ngày: chạy lại report để xem market context + shortlist

## 9. Command dùng nhanh
### Command Python trực tiếp
```bash
python3 vn_stock_scan.py VIC TCB NVL --compact --top 3
python3 vn_stock_news.py VIC TCB NVL --limit 6
python3 vn_stock_report.py --top 6 --mode balanced --tai-khoan 30000000 --rui-ro 1 --ti-le-toi-da 0.35
python3 vn_stock_report.py VIC TCB NVL --mode swing --portfolio-file memory/vn_portfolio.json
```

### Command chat/skill nên dùng
```text
/vn_top
/vn_top 6
/vn_top --mode balanced
/vn_top 6 --mode swing
/vn_top VIC TCB NVL HPG --top 6
/vn_top --top 6 --tai-khoan 30000000 --rui-ro 1 --ti-le-toi-da 0.35
```

### Khi nào dùng command nào
- Muốn quét nhanh kỹ thuật: `vn_stock_scan.py`
- Muốn xem news flow nhanh: `vn_stock_news.py`
- Muốn ra quyết định có vùng mua/dừng lỗ/chốt lời: `vn_stock_report.py`
- Muốn lấy top cơ hội theo format chat: `/vn_top`

## 10. Lưu ý
- Đây là công cụ hỗ trợ quyết định, không phải cam kết lợi nhuận
- Với mã nóng, luôn kiểm tra freshness và warning trước khi hành động
- Nếu market context là `risk_off`, ưu tiên phòng thủ hơn là cố tìm điểm mua đẹp
