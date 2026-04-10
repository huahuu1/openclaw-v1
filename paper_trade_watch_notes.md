# Paper Trade Watch

## Mục đích
Dùng cho heartbeat để tự theo dõi paper-trade portfolio.

## Script
- `paper_trade_watch.py`

## Hành vi
- chạy `paper_trade_status.py`
- chạy `paper_trade_review.py`
- nếu không có thay đổi đáng kể => in `HEARTBEAT_OK`
- nếu có TP1 / BE / TP2 / STOP hoặc thay đổi quan trọng => in alert text ngắn gọn

## State
- `memory/paper_trade_watch_state.json`

## Lợi ích
Biến paper trading thành vòng lặp gần như tự vận hành:
- quét
- mở
- theo dõi
- review
- chỉ gọi người khi có chuyện đáng nói
