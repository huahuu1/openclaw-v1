---
name: vn-top
description: Tạo danh sách cổ phiếu Việt Nam mạnh nhất cho giao dịch ngắn hạn hoặc swing ngắn. Dùng khi người dùng gọi /vn_top để lấy báo cáo top cơ hội hiện tại, kèm vùng mua, không mua đuổi, dừng lỗ, chốt lời và quản trị vốn mặc định 30 triệu, rủi ro 1 phần trăm, tối đa 35 phần trăm một lệnh.
user-invocable: true
metadata: {"openclaw":{"emoji":"🇻🇳","always":true}}
---

# VN Top

Dùng bộ công cụ có sẵn trong workspace để tạo báo cáo top cơ hội.

## Cách làm

- Chạy:
  - `python3 /Users/huuht/.openclaw/workspace/vn_stock_report.py --top 6 --tai-khoan 30000000 --rui-ro 1 --ti-le-toi-da 0.35`
- Nếu người dùng nhập thêm mã hoặc tham số sau `/vn_top`, nối chúng vào cuối lệnh trên.
- Nếu người dùng chỉ nhập số lượng top, ưu tiên hiểu thành `--top <số>`.
- Trả kết quả hoàn toàn bằng tiếng Việt, gọn, dễ dùng.
- Dù ở DM hay channel, luôn bám cùng một khung trả lời để tránh lệch nhau.
- Khung trả lời cố định:
  1. `Bối cảnh thị trường`
  2. `Mua được ngay`
  3. `Chờ điều chỉnh`
  4. `Chỉ quan sát nhưng đang mạnh`
  5. Với mỗi mã được nêu: `Nhận định ngắn` → `Hành động` → `Vùng mua / không mua đuổi / dừng lỗ / chốt lời` → `Nguồn đọc nhanh`
  6. `Chốt nhanh`
- Không chỉ liệt kê mã lọt shortlist hẹp. Hãy phản ánh sát hơn bối cảnh thị trường bằng cách phân tầng mã.
- Nhấn mạnh các mã đáng chú ý nhất trước.
- Với mỗi mã được nhắc tới trong phần trả lời, tự động chèn thêm mục `Nguồn đọc nhanh` gồm 2 đến 3 dòng lấy từ `nguon_tin_hien_thi_nhanh` hoặc `nguon_tin_tham_khao` nếu có.
- Trên Discord, giữ định dạng mỗi dòng kiểu: `Tiêu đề | Nguồn | thời gian | <đường_dẫn>` để dễ bấm và hạn chế embed rối.
- Cách phân tầng mã:
  - `Mua được ngay`: chỉ dành cho các mã có xếp loại mạnh nhất, hành động thiên về có thể mua khi khỏe, và không nằm quá xa vùng mua hợp lý.
  - `Chờ điều chỉnh`: dành cho mã vẫn đáng chú ý nhưng điểm vào hiện tại chưa đẹp, hoặc phù hợp hơn với kiểu chờ nhịp lùi.
  - `Chỉ quan sát nhưng đang mạnh`: dành cho mã có biểu hiện khỏe hoặc đang nổi bật trong thị trường, nhưng không nên mua đuổi hoặc chưa đủ đẹp để xếp vào hai nhóm trên.
- Nếu số mã trong `danh_sach_ngan_han` ít nhưng bối cảnh thị trường rộng đang lan tỏa, hãy nói rõ điều đó trong phần `Bối cảnh thị trường`, tránh để người dùng hiểu nhầm là toàn thị trường chỉ có vài mã tăng.
- Nếu `danh_sach_ngan_han` rỗng, đừng dừng ở câu “không có mã”. Hãy chuyển sang phần `danh_sach_theo_doi_thi_truong_xau`, nêu 2 đến 3 mã đáng theo dõi nhất trong bối cảnh phòng thủ và vẫn chèn `Nguồn đọc nhanh` cho từng mã.
- Nếu có thể, chốt lại 1 đến 3 mã nên ưu tiên theo nguyên tắc danh mục hiện tại.
