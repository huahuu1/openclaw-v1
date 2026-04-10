---
name: vn-danhmuc
description: Đề xuất danh mục cổ phiếu Việt Nam thực chiến cho tài khoản 30 triệu khi người dùng gọi /vn_danhmuc. Dùng để chọn 1 đến 3 mã theo nguyên tắc quản trị vốn hiện tại, ưu tiên mã A trước, tránh dồn cùng nhóm ngành và không ép đủ số lượng vị thế.
user-invocable: true
metadata: {"openclaw":{"emoji":"🧺","always":true}}
---

# VN Danh Mục

Đề xuất danh mục thực chiến theo bộ quy tắc hiện tại.

## Cách làm

- Chạy trước:
  - `python3 /Users/huuht/.openclaw/workspace/vn_stock_report.py --top 6 --tai-khoan 30000000 --rui-ro 1 --ti-le-toi-da 0.35`
- Nếu người dùng cung cấp danh sách mã, chạy lại với các mã đó thay cho quét chung.
- Sau khi có kết quả, đề xuất danh mục theo các nguyên tắc:
  - tối đa 3 mã
  - tối đa 35 phần trăm một lệnh
  - rủi ro 1 phần trăm một lệnh
  - tổng rủi ro mở khoảng 2.5 đến 3 phần trăm
  - không ép đủ 3 mã nếu thị trường không đẹp
  - ưu tiên cấu trúc 1 mã mạnh nhất cộng 1 mã bổ trợ, hoặc thêm 1 mã ngoại lệ nếu rất rõ
- Kết quả hoàn toàn bằng tiếng Việt và phải có kết luận cuối cùng thật dứt khoát.
