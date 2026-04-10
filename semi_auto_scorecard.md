# Semi-Auto Setup Scorecard

Tổng điểm: 10

## 1. Trend alignment (0-3)
- 3: EMA50/EMA200 trend rõ + giá cùng phía EMA50 + cấu trúc giá thuận xu hướng
- 2: Xu hướng hợp lệ nhưng chưa quá mạnh
- 1: Mới chớm hình thành
- 0: Sideways / mâu thuẫn

## 2. Trigger confirmation (0-2)
- 2: Trigger timeframe xác nhận rõ bằng momentum / giữ EMA ngắn / phá vùng đẹp
- 1: Có tín hiệu nhưng còn yếu
- 0: Chưa xác nhận

## 3. Risk/Reward quality (0-2)
- 2: RR >= 2.0
- 1: 1.8 <= RR < 2.0
- 0: RR < 1.8

## 4. Entry location quality (0-2)
- 2: Entry gần invalidation, không đuổi giá, gần vùng support/resistance hợp lý
- 1: Entry tạm ổn nhưng chưa đẹp
- 0: Entry xấu / đang ở giữa range / quá xa stop

## 5. Volatility sanity (0-1)
- 1: ATR hợp lý, không quá nhiễu, không thấy dấu hiệu liquidation candle vừa xảy ra
- 0: market quá bạo lực hoặc stop dễ bị quét

## Kết luận
- 8-10: mạnh, có thể đề xuất
- 6-7: theo dõi, chỉ đề xuất nếu market sạch
- <=5: NO TRADE

## Guardrails
Dù điểm cao vẫn NO TRADE nếu vi phạm một trong các điều kiện:
- leverage cần quá cao mới vào được size mong muốn
- stop loss không đặt được hợp lệ
- pair thanh khoản kém
- có tin tức/rủi ro sự kiện lớn ngay trước mắt
- setup mâu thuẫn với bias thị trường chung

## Mẫu output
- Symbol
- Side
- Score
- Entry
- Stop
- TP1
- TP2
- RR
- Leverage đề xuất
- Thesis ngắn gọn
- Verdict: PROPOSE / WATCH / NO TRADE
