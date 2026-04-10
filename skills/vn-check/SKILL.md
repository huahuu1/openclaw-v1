---
name: vn-check
description: Phân tích nhanh một hoặc nhiều mã cổ phiếu Việt Nam khi người dùng gọi /vn_check. Dùng để kiểm tra riêng từng mã, kèm vùng mua, không mua đuổi, dừng lỗ, chốt lời, dòng tiền khối ngoại, tự doanh và xu thế tin tức.
user-invocable: true
metadata: {"openclaw":{"emoji":"📈","always":true}}
---

# VN Check

Kiểm tra nhanh một hoặc nhiều mã cụ thể bằng báo cáo chi tiết.

## Cách làm

- Nếu người dùng không cung cấp mã, yêu cầu họ nhập 1 hoặc nhiều mã như `HPG MSN VHM`.
- Nếu có mã, chạy:
  - `python3 /Users/huuht/.openclaw/workspace/vn_stock_report.py <danh_sach_ma> --top 10 --tai-khoan 30000000 --rui-ro 1 --ti-le-toi-da 0.35`
- Giữ nguyên thứ tự mã người dùng nhập khi tóm tắt lại.
- Dù ở DM hay channel, luôn bám cùng một khung trả lời để tránh lệch nhau.
- Khung trả lời cố định cho mỗi mã:
  1. `Kết luận nhanh`
  2. `Nhận định`
  3. `Hành động`
  4. `Vùng mua / không mua đuổi / dừng lỗ / chốt lời`
  5. `Dòng tiền`
  6. `Nguồn đọc nhanh`
- Tóm tắt theo hướng hành động:
  - mã nào đáng ưu tiên
  - vùng mua nào đẹp hơn
  - mã nào chỉ nên theo dõi
  - mã nào không nên đuổi
- Với mỗi mã được nhắc tới trong phần trả lời, tự động chèn thêm mục `Nguồn đọc nhanh` gồm 2 đến 3 dòng lấy từ `nguon_tin_hien_thi_nhanh` hoặc `nguon_tin_tham_khao` nếu có.
- Ưu tiên nguồn mới hơn, sát mã hơn, dễ đọc hơn.
- Trên Discord, giữ định dạng mỗi dòng kiểu: `Tiêu đề | Nguồn | thời gian | <đường_dẫn>` để dễ bấm và hạn chế embed rối.
- Kết quả phải hoàn toàn bằng tiếng Việt.
