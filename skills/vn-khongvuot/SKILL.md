---
name: vn-khongvuot
description: Tạo báo cáo cổ phiếu Việt Nam ở chế độ nghiêm ngặt không dùng quy tắc vượt. Dùng khi người dùng gọi /vn_khongvuot để lọc cơ hội còn hợp lệ nếu giữ đúng giới hạn vốn mặc định, không nới cho mã dẫn sóng.
user-invocable: true
metadata: {"openclaw":{"emoji":"🛡️","always":true}}
---

# VN Không Vượt

Dùng báo cáo nghiêm ngặt, không áp dụng quy tắc vượt cho mã dẫn sóng.

## Cách làm

- Chạy:
  - `python3 /Users/huuht/.openclaw/workspace/vn_stock_report.py --top 6 --tai-khoan 30000000 --rui-ro 1 --ti-le-toi-da 0.35`
- Nếu người dùng nhập thêm mã hoặc tham số sau `/vn_khongvuot`, nối chúng vào cuối lệnh trên.
- Khi trả lời, nhấn mạnh đây là chế độ nghiêm ngặt.
- Chốt lại danh sách mua ưu tiên theo mặc định không vượt.
- Kết quả hoàn toàn bằng tiếng Việt.
