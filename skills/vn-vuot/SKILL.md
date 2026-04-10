---
name: vn-vuot
description: Tạo báo cáo cổ phiếu Việt Nam có bật quy tắc vượt cho một mã dẫn sóng ngoại lệ. Dùng khi người dùng gọi /vn_vuot để xem thêm kịch bản nới tỷ trọng hợp lý nhưng vẫn giữ rủi ro một phần trăm một lệnh.
user-invocable: true
metadata: {"openclaw":{"emoji":"🚀","always":true}}
---

# VN Vượt

Dùng báo cáo có bật quy tắc vượt cho một mã dẫn sóng ngoại lệ.

## Cách làm

- Chạy mặc định:
  - `python3 /Users/huuht/.openclaw/workspace/vn_stock_report.py --top 6 --tai-khoan 30000000 --rui-ro 1 --ti-le-toi-da 0.35 --cho-phep-vuot --he-so-vuot 1.2857`
- Nếu người dùng nhập thêm mã hoặc tham số sau `/vn_vuot`, nối chúng vào cuối lệnh trên.
- Khi trả lời, phải nói rõ:
  - mã nào thật sự xứng đáng dùng quy tắc vượt
  - mã nào vẫn chỉ nên theo dõi
  - không mua đuổi nếu đã xa vùng mua
- Kết quả hoàn toàn bằng tiếng Việt.
