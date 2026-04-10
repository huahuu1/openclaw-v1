# Bộ lọc cổ phiếu Việt Nam

Bộ công cụ này dùng dữ liệu giá công khai để lọc cổ phiếu Việt Nam, cộng thêm lớp chấm điểm tin tức, lập kế hoạch giao dịch sơ bộ, theo dõi hiệu quả tín hiệu, tạo bản tin buổi tối và tính quản trị vốn.

## Chạy báo cáo cho ngày mai

```bash
python3 /Users/huuht/.openclaw/workspace/vn_stock_report.py --top 5
```

## Chạy báo cáo có quản trị vốn

Ví dụ tài khoản 100 triệu, rủi ro mỗi lệnh 1%, tỷ trọng tối đa mỗi lệnh 20%:

```bash
python3 /Users/huuht/.openclaw/workspace/vn_stock_report.py --top 5 --tai-khoan 100000000 --rui-ro 1 --ti-le-toi-da 0.2
```

## Chạy bản tin buổi tối

```bash
python3 /Users/huuht/.openclaw/workspace/vn_stock_ban_tin_toi.py
```

## Chạy bộ tính quản trị vốn riêng

```bash
python3 /Users/huuht/.openclaw/workspace/vn_stock_quan_tri_von.py --tai-khoan 100000000 --rui-ro 1 --gia-vao 26.96 --moc-sai 26.58
```

## Phiên bản 8b có gì

### 1) Quản trị vốn theo rủi ro
Cho từng mã trong báo cáo, nếu có truyền quy mô tài khoản, hệ thống sẽ tính thêm:
- số tiền rủi ro tối đa mỗi lệnh
- số cổ tối đa theo rủi ro
- số cổ tối đa theo tỷ trọng vốn
- số cổ đề xuất
- giá trị lệnh đề xuất
- rủi ro thực tế của lệnh
- nhiều mốc chốt lời: gần / chính / mở rộng
- nhiều mốc dừng lỗ: chặt / chuẩn / rộng
- có thể bật rule vượt cho mã dẫn sóng bằng:
  - `--cho-phep-vuot`
  - `--he-so-vuot 1.2857`  # ví dụ từ 35% lên khoảng 45%
- báo cáo hiện đã tự lấy thêm dữ liệu dòng tiền theo mã:
  - khối ngoại: mua / bán / ròng
  - tự doanh: mua / bán / ròng
- báo cáo hiện có thêm lớp phân tích tin:
  - tóm tắt 3 tin đáng chú ý nhất
  - tác động tin ngắn hạn
  - tác động tin trung hạn
  - kết luận xu thế từ tin
  - độ tin cậy của kết luận

### 2) Tham số đầu vào
- `--tai-khoan`: quy mô tài khoản
- `--rui-ro`: % rủi ro tối đa cho mỗi lệnh
- `--ti-le-toi-da`: tỷ trọng tối đa vốn cho một lệnh

## Ghi chú

- Tính kích thước vị thế hiện dùng lô 100 cổ.
- Đây là lớp quản trị vốn cơ bản, đủ tốt để tránh vào lệnh quá lớn.
- Có thể nâng cấp tiếp với chia lệnh nhiều phần, dời điểm dừng lỗ, và quản trị danh mục nhiều mã cùng lúc.
