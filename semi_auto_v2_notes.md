# Semi-Auto v2 Notes

## Mục tiêu
Từ scanner v1 tiến lên advisor v2:
- đọc equity Binance thực tế
- tính risk amount theo % tài khoản
- tính quantity theo stop distance
- loại bỏ kèo không đạt min qty / min notional
- chọn ra 1 kèo tốt nhất + vài lựa chọn thay thế

## Script
- `semi_auto_best_trade.py`

## Output chính
- `best_trade`
- `alternatives`
- `account_equity_usdt`
- `risk_amount_usdt`
- `qty`
- `notional_usdt`
- `suggested_leverage`

## Ý nghĩa
Đây là lớp “advisor trước khi bấm lệnh”, chưa phải auto execution.
User vẫn duyệt cuối cùng.
