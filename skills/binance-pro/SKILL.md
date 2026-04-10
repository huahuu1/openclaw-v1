---
name: binance-pro
description: Complete Binance integration - world's largest crypto exchange. Trade spot, futures with up to 125x leverage, staking, and portfolio management. Use to check balances, open/close positions, set stop loss and take profit, check PnL, and any Binance operation.
metadata: {"openclaw":{"emoji":"🟡","always":true,"requires":{"bins":["curl","jq"]}}}
---

# Binance Pro 🟡

Professional skill for trading on Binance - the world's largest crypto exchange.

## 🚀 Quick Start

### Setup Credentials

Save to `~/.openclaw/credentials/binance.json`:
```json
{
  "apiKey": "YOUR_API_KEY",
  "secretKey": "YOUR_SECRET_KEY"
}
```

> [!IMPORTANT]
> **FOR AI ASSISTANT**: Do not ask the user for their API keys. The user has already configured `~/.openclaw/credentials/binance.json`. You MUST load the API keys from this file in all your bash scripts like this:
> ```bash
> API_KEY=$(jq -r .apiKey ~/.openclaw/credentials/binance.json)
> SECRET=$(jq -r .secretKey ~/.openclaw/credentials/binance.json)
> ```

### Environment Variables (alternative)
```bash
export BINANCE_API_KEY="your_api_key"
export BINANCE_SECRET="your_secret_key"
```

## 📊 Basic Queries

### Check Spot Balance
```bash
TIMESTAMP=$(date +%s%3N)
QUERY="timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s "https://api.binance.com/api/v3/account?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '[.balances[] | select(.free != "0.00000000")]'
```

### Get Current Price
```bash
curl -s "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT" | jq '.'
```

### Get All Futures Positions
```bash
TIMESTAMP=$(date +%s%3N)
QUERY="timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s "https://fapi.binance.com/fapi/v2/positionRisk?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '[.[] | select(.positionAmt != "0")]'
```

## ⚡ Futures (Leverage Trading)

### Open LONG Position (Buy)
```bash
SYMBOL="BTCUSDT"
SIDE="BUY"
QUANTITY="0.001"

TIMESTAMP=$(date +%s%3N)
QUERY="symbol=${SYMBOL}&side=${SIDE}&type=MARKET&quantity=${QUANTITY}&timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s -X POST "https://fapi.binance.com/fapi/v1/order?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '.'
```

### Open SHORT Position (Sell)
```bash
SYMBOL="BTCUSDT"
SIDE="SELL"
QUANTITY="0.001"

TIMESTAMP=$(date +%s%3N)
QUERY="symbol=${SYMBOL}&side=${SIDE}&type=MARKET&quantity=${QUANTITY}&timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s -X POST "https://fapi.binance.com/fapi/v1/order?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '.'
```

### Set Stop Loss
```bash
SYMBOL="BTCUSDT"
SIDE="SELL"  # To close LONG use SELL, to close SHORT use BUY
STOP_PRICE="75000"

TIMESTAMP=$(date +%s%3N)
QUERY="symbol=${SYMBOL}&side=${SIDE}&type=STOP_MARKET&stopPrice=${STOP_PRICE}&closePosition=true&timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s -X POST "https://fapi.binance.com/fapi/v1/order?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '.'
```

### Set Take Profit
```bash
SYMBOL="BTCUSDT"
SIDE="SELL"  # To close LONG use SELL, to close SHORT use BUY
TP_PRICE="85000"

TIMESTAMP=$(date +%s%3N)
QUERY="symbol=${SYMBOL}&side=${SIDE}&type=TAKE_PROFIT_MARKET&stopPrice=${TP_PRICE}&closePosition=true&timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s -X POST "https://fapi.binance.com/fapi/v1/order?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '.'
```

### Close Position (Market)
```bash
# First, get current position quantity
POSITION=$(curl -s "https://fapi.binance.com/fapi/v2/positionRisk?timestamp=${TIMESTAMP}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq -r '.[] | select(.symbol=="BTCUSDT") | .positionAmt')

# If POSITION > 0, it's LONG, close with SELL
# If POSITION < 0, it's SHORT, close with BUY
```

### Change Leverage
```bash
SYMBOL="BTCUSDT"
LEVERAGE="10"  # 1 to 125

TIMESTAMP=$(date +%s%3N)
QUERY="symbol=${SYMBOL}&leverage=${LEVERAGE}&timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s -X POST "https://fapi.binance.com/fapi/v1/leverage?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '.'
```

## 📈 Spot Trading

### Buy (Market)
```bash
SYMBOL="ETHUSDT"
QUANTITY="0.1"

TIMESTAMP=$(date +%s%3N)
QUERY="symbol=${SYMBOL}&side=BUY&type=MARKET&quantity=${QUANTITY}&timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s -X POST "https://api.binance.com/api/v3/order?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '.'
```

### Sell (Market)
```bash
SYMBOL="ETHUSDT"
QUANTITY="0.1"

TIMESTAMP=$(date +%s%3N)
QUERY="symbol=${SYMBOL}&side=SELL&type=MARKET&quantity=${QUANTITY}&timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s -X POST "https://api.binance.com/api/v3/order?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '.'
```

## 🔧 Utilities

### View Open Orders
```bash
TIMESTAMP=$(date +%s%3N)
QUERY="timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

# Futures
curl -s "https://fapi.binance.com/fapi/v1/openOrders?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '.'
```

### Cancel Order
```bash
SYMBOL="BTCUSDT"
ORDER_ID="123456789"

TIMESTAMP=$(date +%s%3N)
QUERY="symbol=${SYMBOL}&orderId=${ORDER_ID}&timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s -X DELETE "https://fapi.binance.com/fapi/v1/order?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '.'
```

### View Trade History
```bash
SYMBOL="BTCUSDT"
TIMESTAMP=$(date +%s%3N)
QUERY="symbol=${SYMBOL}&timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s "https://fapi.binance.com/fapi/v1/userTrades?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '.[-10:]'
```

## 🏦 Detailed Futures Balance
```bash
TIMESTAMP=$(date +%s%3N)
QUERY="timestamp=${TIMESTAMP}"
SIGNATURE=$(echo -n "$QUERY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s "https://fapi.binance.com/fapi/v2/balance?${QUERY}&signature=${SIGNATURE}" \
  -H "X-MBX-APIKEY: ${API_KEY}" | jq '[.[] | select(.balance != "0")]'
```

## 📋 Popular Pairs

| Pair | Description |
|------|-------------|
| BTCUSDT | Bitcoin |
| ETHUSDT | Ethereum |
| BNBUSDT | BNB |
| SOLUSDT | Solana |
| XRPUSDT | XRP |
| DOGEUSDT | Dogecoin |
| ADAUSDT | Cardano |
| AVAXUSDT | Avalanche |

## 🤖 Thực thi tự động cho lệnh kiểu “vào lệnh với $xx”

Khi người dùng nói kiểu:
- `vào lệnh với $20`
- `chia 3 lệnh futures`
- `scan lệnh tốt nhất rồi vào luôn`

thì bắt buộc làm theo đúng quy trình này, không được bỏ bước:

1. **Đọc số dư futures thật trước**
   - dùng `fapi/v2/account`, `fapi/v2/balance`
   - lấy rõ:
     - `availableBalance`
     - `totalWalletBalance`
     - `totalInitialMargin`
     - `totalOpenOrderInitialMargin`
     - `open positions`
     - `open orders`
2. **Quét ứng viên trước khi đặt lệnh**
   - không còn mặc định ép đủ 3 lệnh
   - với tài khoản nhỏ, ưu tiên **1 đến 2 mã tốt nhất**
   - chỉ mở lệnh thứ 2 nếu chất lượng tín hiệu vẫn rõ, không tương quan quá cao và sau lệnh thứ nhất vẫn còn đệm margin an toàn
   - không chọn cặp có `MIN_NOTIONAL` / `LOT_SIZE` khiến vốn người dùng không vào nổi
   - với vốn rất nhỏ, ưu tiên các cặp như `XRPUSDT`, `ADAUSDT`, `SUIUSDT`, `DOGEUSDT` hơn `BTCUSDT`
3. **Tính khối lượng từ số tiền người dùng đưa**
   - phải kiểm tra:
     - `MIN_NOTIONAL`
     - `LOT_SIZE.minQty`
     - `LOT_SIZE.stepSize`
     - `quantityPrecision`
   - làm tròn xuống đúng bước giá trị cho phép
4. **Ước tính margin thật trước khi bắn lệnh**
   - không chỉ nhìn `walletBalance`
   - phải bám `availableBalance`
   - chừa đệm cho phí và biến động
   - không được dùng gần hết `availableBalance`
   - với tài khoản nhỏ, luôn giữ lại phần đệm thay vì all-in trá hình qua nhiều lệnh
   - nếu không đủ điều kiện cho 2 lệnh đẹp thì chỉ vào 1 lệnh
5. **Đặt lệnh market trước**
   - mặc định futures: `ISOLATED`
   - đòn bẩy mặc định an toàn: `3x` đến `5x`
   - sau khi khớp phải kiểm tra lại `positionRisk` để xác nhận vị thế thực sự đã mở
6. **Đặt SL/TP ngay sau khi vị thế mở**
   - ưu tiên dùng cách tài khoản thực tế chấp nhận
   - nếu `STOP_MARKET` / `TAKE_PROFIT_MARKET` thường bị lỗi kiểu `-4120`, tự chuyển sang **Algo Order API**
   - bài học từ tài khoản này:
     - endpoint khả dụng: `/fapi/v1/algoOrder`
     - tham số tài khoản này chấp nhận có thể lệch tài liệu cũ, cần bóc lỗi thật nếu fail
     - sau khi đặt xong phải kiểm tra lại bằng `openAlgoOrders`
7. **Chỉ báo hoàn tất khi đã xác nhận đủ 3 thứ**
   - vị thế mở thành công
   - SL đã có
   - TP đã có

## 🧭 Preset mới cho tài khoản nhỏ kiểu `xx USDT`

Khi người dùng nói kiểu:
- `vào lệnh với 20 usdt`
- `futures 30 usdt`
- `scan rồi vào giúp tôi với 50 usdt`

thì dùng preset sau:

### 1. Phân loại theo quy mô tài khoản
- **Dưới 25 USDT**
  - chỉ vào **1 mã tốt nhất**
  - không chia 2 hoặc 3 lệnh chỉ để phân bổ cho đều
- **25 đến 60 USDT**
  - ưu tiên **1 mã**, tối đa **2 mã** nếu cả hai đều đẹp
- **Trên 60 USDT**
  - có thể cân nhắc **2 mã**, và chỉ lên **3 mã** nếu người dùng yêu cầu rõ và margin vẫn dư dả

### 2. Thứ tự ưu tiên khi chọn lệnh
Ưu tiên theo thứ tự này:
1. **chất lượng setup**
2. **độ rõ của xu hướng / động lượng**
3. **khả năng đặt SL/TP chuẩn**
4. **mức độ tương quan giữa các mã**
5. **tính phù hợp với số vốn**

Không được đảo ngược thành:
- vào được là vào
- đủ 3 mã là tốt

### 3. Quy tắc số lượng lệnh
- **1 lệnh đẹp** tốt hơn **3 lệnh trung bình**.
- **2 lệnh không tương quan quá cao** tốt hơn **3 lệnh cùng beta alt**.
- Không cố lấp đủ số lượng lệnh nếu thị trường không cho kèo đẹp.

### 4. Quy tắc tương quan
- Tránh mở cùng lúc nhiều mã có hành vi gần như giống nhau.
- Với vốn nhỏ, tránh mở 3 lệnh long alt cùng kiểu vận động.
- Nếu mã thứ 2 có xác suất thắng không rõ bằng mã thứ 1, bỏ qua mã thứ 2.

### 5. Quy tắc đệm margin
- Sau khi mở lệnh vẫn phải còn đệm usable balance.
- Không để tài khoản rơi vào trạng thái gần cạn `availableBalance` chỉ để ôm thêm một lệnh chất lượng kém hơn.

### 6. Quy tắc xác nhận hoàn tất
Chỉ được báo hoàn tất khi đã có đủ:
- vị thế mở thật
- SL thật
- TP thật
- xác nhận lại sau lệnh rằng tài khoản vẫn còn đệm an toàn

## 📌 Bài học cố định từ tài khoản Binance hiện tại

- Spot có thể khác Futures; khi người dùng nói `futures` thì không được suy luận từ số dư spot.
- Tài khoản này đã từng hiển thị khoảng `20 USDT` futures nhưng `availableBalance` thực tế thấp sau khi vị thế mở; phải kiểm tra lại account sau mỗi lệnh.
- `BTCUSDT` thường không hợp vốn quá nhỏ vì ràng buộc `MIN_NOTIONAL`/`LOT_SIZE`.
- Với vốn rất nhỏ, không mặc định chia 3 lệnh. Mặc định mới là chỉ chọn 1 lệnh đẹp nhất, hoặc tối đa 2 lệnh nếu chất lượng vẫn rõ.
- Không được kết luận `không vào được` chỉ từ lỗi `-2019` nếu chưa kiểm tra lại xem lệnh trước đó đã khớp một phần hay đã mở vị thế hay chưa.
- Không được ưu tiên `số lượng lệnh` hơn `chất lượng lệnh`. Với tài khoản nhỏ, cố đủ 3 lệnh thường làm chất lượng setup giảm đi và tăng tương quan rủi ro.
- Nếu đặt lệnh xong mà gặp lỗi ở bước SL/TP, phải **ngay lập tức** kiểm tra:
  - `positionRisk`
  - `openOrders`
  - `openAlgoOrders`
  để tránh bỏ vị thế trần.

## ⚠️ Safety Rules

1. **ALWAYS** verify position before closing
2. **ALWAYS** set Stop Loss on leveraged trades
3. **NEVER** use leverage higher than 10x without experience
4. **VERIFY** pair and quantity before executing
5. **CONFIRM** with user before executing large orders
6. **For small-budget auto-entry requests, do not claim success until position + SL + TP are all verified live**

## 🔗 Links

- [API Documentation](https://binance-docs.github.io/apidocs/)
- [Create Account](https://accounts.binance.com/register?ref=CPA_00F3AR52CL)
- [Testnet](https://testnet.binance.vision/)

---
*Skill created by Total Easy Software - Clayton Martins*
