# Paper Trade Mode

## Mục tiêu
Test signal mà không cần vốn thật, theo nguyên tắc cốt lõi:
**nếu có lời thì để lời nhiều, nếu có lỗ thì giữ lỗ ít.**

## Paper account
- Starting capital mặc định: **1000 USDT**
- Risk mỗi lệnh mặc định: **1% vốn**
- Fixed leverage mặc định: **5x**
- Mỗi lệnh vẫn được tính quantity giả lập từ khoảng cách entry -> stop
- Leverage 5x dùng như mức vận hành cố định; risk vẫn bị khóa bằng risk-based sizing

## 6 nâng cấp chính
1. **Exposure control**
2. **TP1 partial**
3. **Move stop to breakeven**
4. **Auto journal**
5. **Regime-aware opening**
6. **Deeper review**

## Điều mới quan trọng
Hệ thống giờ không chỉ báo biến động giá hay R nữa, mà còn báo:
- unrealized PnL USDT
- realized PnL USDT
- % lời/lỗ trên **vốn gốc paper account**
- fixed leverage đang dùng

## Files
- `paper_trade_open.py`
- `paper_trade_status.py`
- `paper_trade_review.py`
- `paper_trade_watch.py`
- `paper_trades.json`
- `paper_trade_journal.jsonl`

## Quy ước payoff hiện tại
- Stop trước TP1 = **-1R**
- Hit TP1 rồi quay về BE = **+0.5R**
- Hit TP1 rồi hit TP2 = **+1.5R**

## Ý nghĩa
Dashboard giờ sẽ dễ hiểu hơn theo góc nhìn tài khoản:
- vốn gốc là bao nhiêu
- đang lời/lỗ bao nhiêu USDT
- tương đương bao nhiêu % trên vốn gốc
- đang vận hành với leverage cố định bao nhiêu
