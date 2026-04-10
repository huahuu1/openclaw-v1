# Mr.Smith Semi-Auto Trading Playbook

## Mục tiêu
Tạo quy trình trade bán tự động trên Binance Futures theo hướng:
- lọc ít nhưng chất lượng hơn
- ưu tiên không trade hơn là trade bừa
- luôn quản trị rủi ro trước khi vào lệnh
- assistant chỉ đề xuất; user là người duyệt lệnh cuối cùng

## Triết lý
1. Risk trước, entry sau.
2. Không có setup đẹp = NO TRADE.
3. Thuận xu hướng lớn dễ sống hơn bắt đỉnh đáy.
4. RR thấp thì dù win nhiều vẫn dễ chết dần.
5. Leverage chỉ là công cụ, không phải edge.

## Chế độ vận hành
### 1) Scan
Assistant quét các cặp USDT perpetual có thanh khoản cao.
Ưu tiên mặc định:
- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT
- XRPUSDT
- DOGEUSDT
- ADAUSDT
- AVAXUSDT

Có thể mở rộng thêm top-volume pairs khi cần.

### 2) Chấm điểm setup
Mỗi setup được chấm theo scorecard chuẩn.
Chỉ đề xuất khi vượt ngưỡng tối thiểu.

### 3) Gửi đề xuất
Mỗi đề xuất phải có:
- side: LONG / SHORT / NO TRADE
- entry vùng giá đề xuất
- stop loss
- take profit 1 / take profit 2
- RR ước tính
- leverage đề xuất
- lý do ngắn gọn
- mức tự tin theo score

### 4) User duyệt
Chỉ khi user xác nhận thì mới được mở lệnh.

### 5) Quản lý lệnh sau entry
Ngay khi vào lệnh:
- đặt stop loss
- đặt take profit
- ghi lại luận điểm vào lệnh
- nếu thesis bị phá: thoát, không cầu nguyện

## Timeframe chuẩn v1
- Trend timeframe: 1h
- Trigger timeframe: 15m

Có thể dùng biến thể scalp:
- Trend timeframe: 15m
- Trigger timeframe: 5m

## Điều kiện lọc setup
### LONG
Ưu tiên khi:
- EMA50 > EMA200 trên timeframe trend
- giá nằm trên EMA50 trend
- RSI trend >= 52
- trigger timeframe giữ được momentum tăng
- giá không quá xa vùng invalidation

### SHORT
Ưu tiên khi:
- EMA50 < EMA200 trên timeframe trend
- giá nằm dưới EMA50 trend
- RSI trend <= 48
- trigger timeframe giữ được momentum giảm
- giá không quá xa vùng invalidation

## Quy tắc NO TRADE
Không đề xuất lệnh nếu:
- RR < 1.8
- stop quá xa khiến size quá nhỏ hoặc leverage quá cao
- giá ở giữa range, không gần vùng xác nhận
- trend và trigger mâu thuẫn
- biến động quá loạn / spread bất thường
- vừa có nến xả/bơm mạnh khiến entry xấu

## Risk management mặc định
- Risk mỗi lệnh: 0.5% tài khoản
- Tối đa 1% nếu user nói rõ
- Tối đa 2 lệnh cùng lúc nếu correlation cao
- Leverage mặc định: 3x đến 5x
- Tránh >10x trừ khi user chủ động yêu cầu

## Position sizing
Công thức khung:
- risk_amount = account_equity * risk_pct
- stop_distance_pct = abs(entry - stop) / entry
- position_notional ~= risk_amount / stop_distance_pct

Sau đó làm tròn theo step size của Binance và kiểm tra minimum notional.

## Exit logic v1
- TP1 tại khoảng 1R
- TP2 tại 2R hoặc vùng cản/hỗ trợ gần nhất
- Sau TP1 có thể dời SL về hòa vốn nếu market thuận lợi
- Nếu momentum yếu đi rõ rệt trước TP, ưu tiên bảo toàn vốn

## Output format chuẩn
Mỗi scan nên trả về:
- top long ideas
- top short ideas
- no-trade warnings
- market regime summary

## Kỷ luật
- Không revenge trade
- Không tăng risk sau chuỗi thua chỉ để gỡ
- Không move SL xa hơn để “cho thở thêm”
- Nếu không chắc: đứng ngoài

## Roadmap nâng cấp
v1:
- trend + momentum + ATR stop + RR filter

v2:
- support/resistance gần nhất
- breakout vs pullback classification
- volume confirmation
- correlation filter

v3:
- regime detection nâng cao
- backtest nhanh trên dữ liệu lịch sử
- watchlist cá nhân hóa

## Lưu ý quan trọng
Playbook này nhằm tăng tính kỷ luật và chất lượng quyết định, không đảm bảo lợi nhuận. Mọi lệnh futures đều có rủi ro thua lỗ và thanh lý.