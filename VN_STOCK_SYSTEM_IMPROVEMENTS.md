# VN Stock System Improvements

## Mục tiêu
Nâng hệ thống đề xuất mã chứng khoán từ mức dùng được lên mức thực chiến hơn, giảm lỗi dữ liệu và tăng tính hành động.

## Những phần đã improve

### 1. Path và tính di động
- Bỏ path cứng `/Users/huuht/.openclaw/workspace`
- Chuyển sang `Path(__file__).resolve().parent`
- Các script nay chạy đúng trong môi trường `/home/node/.openclaw/workspace` và các máy khác

### 2. Tách rõ intraday vs EOD
- Thêm timestamp cho từng khung:
  - daily
  - h1
  - m15
- Thêm freshness status:
  - `fresh`
  - `delayed`
  - `stale`
- Thêm cảnh báo khi intraday/h1/daily không còn tươi

### 3. Chấm điểm tin tức tốt hơn
- Mỗi tin có thêm:
  - freshness
  - impact level
  - loại tin
  - price relevance
- Ưu tiên tin mới và nguồn mạnh hơn khi sắp xếp

### 4. Score breakdown rõ hơn
- Scan nay trả thêm `score_breakdown`:
  - trend_score
  - quality_score
  - momentum_score
  - risk_score
  - trigger_score
  - penalty
- Report cộng thêm:
  - news_score_clamped
  - sector_leadership_score
  - market_context_score
  - final_score

### 5. Có market context
- Scan tạo thêm `market_context`:
  - `risk_on`
  - `mixed`
  - `risk_off`
- Report dùng market context để điều chỉnh xếp hạng và hành động

### 6. Có mode giao dịch
Hỗ trợ các mode:
- `balanced`
- `scalp`
- `swing`
- `trend`
- `defensive`
- `aggressive`

Mode ảnh hưởng đến:
- risk buffer
- chase tolerance
- max position factor

### 7. Hỗ trợ portfolio file
- Report có thể đọc file danh mục JSON
- Tự gắn:
  - quantity
  - avg_price
  - P/L tạm tính
  - note
  - t_plus

### 8. Cảnh báo dữ liệu thiếu/lỗi
- Tổng hợp warning ở cấp report
- Gắn warning cho từng mã
- Báo thiếu portfolio file nếu chưa cấu hình

### 9. Tài liệu hóa
- Thêm file này để mô tả các cải tiến
- Thêm file hướng dẫn sử dụng riêng

## Các file đã thay đổi
- `vn_stock_scan.py`
- `vn_stock_news.py`
- `vn_stock_report.py`

## Kết quả kỳ vọng
- Ít lỗi path hơn
- Ít nhầm EOD với intraday hơn
- Khuyến nghị bám thị trường tốt hơn
- Dễ hiểu vì có score breakdown và warning
- Dễ dùng hơn cho giao dịch thực chiến nhờ mode + portfolio context
