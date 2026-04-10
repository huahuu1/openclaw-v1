# Paper Trade Review

## Script
- `paper_trade_review.py`

## Mục đích
Tổng kết hiệu quả paper trade sau khi có các lệnh đóng.

## Metrics v1
- total trades
- open trades
- closed trades
- wins / losses
- winrate %
- average R
- expectancy R
- average MFE / MAE
- thống kê theo symbol

## Quy ước hiện tại
- TP2_HIT = +2R
- STOPPED = -1R
- lệnh OPEN chưa tính vào expectancy

## Hạn chế
- chưa tính phí
- chưa tính slippage
- chưa có partial TP1
- chưa có dời stop về hòa vốn
