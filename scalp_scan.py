import json, time, urllib.request
from statistics import mean

BASE = "https://fapi.binance.com"
TIMEOUT = 12
TOPN = 20

# HTTP helper

def http_get(path, params=None):
    if params:
        qs = "?" + "&".join(f"{k}={v}" for k,v in params.items())
    else:
        qs = ""
    with urllib.request.urlopen(BASE + path + qs, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())

# Indicators

def ema(seq, period):
    if len(seq) < period:
        return None
    k = 2/(period+1)
    e = seq[0]
    for v in seq[1:]:
        e = v*k + e*(1-k)
    return e

def rsi(seq, period=14):
    if len(seq) <= period:
        return None
    gains = []
    losses = []
    for i in range(1, len(seq)):
        d = seq[i] - seq[i-1]
        gains.append(max(d,0))
        losses.append(max(-d,0))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    for i in range(period, len(gains)):
        avg_gain = (avg_gain*(period-1) + gains[i]) / period
        avg_loss = (avg_loss*(period-1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain/avg_loss
    return 100 - (100/(1+rs))

def atr(klines, period=14):
    if len(klines) <= period:
        return None
    trs = []
    prev_close = float(klines[0][4])
    for k in klines[1:]:
        high = float(k[2]); low = float(k[3]); close = float(k[4])
        tr = max(high-low, abs(high-prev_close), abs(low-prev_close))
        trs.append(tr)
        prev_close = close
    if len(trs) < period:
        return None
    a = mean(trs[:period])
    for t in trs[period:]:
        a = (a*(period-1) + t)/period
    return a

# Universe: USDT perpetual, rank by quoteVolume
ex = http_get("/fapi/v1/exchangeInfo")
perp = {s["symbol"] for s in ex["symbols"] if s.get("contractType")=='PERPETUAL' and s.get("quoteAsset")=='USDT' and s.get("status")=='TRADING'}
all24 = http_get("/fapi/v1/ticker/24hr")
ranked = []
for t in all24:
    sym = t['symbol']
    if sym in perp:
        try:
            qv = float(t.get('quoteVolume','0'))
        except Exception:
            qv = 0.0
        ranked.append((sym, qv))
ranked.sort(key=lambda x: x[1], reverse=True)
SYMS = [s for s,_ in ranked[:TOPN]]

longs = []
shorts = []
errors = []

for sym in SYMS:
    try:
        k15 = http_get("/fapi/v1/klines", {"symbol": sym, "interval": "15m", "limit": 300})
        k5 = http_get("/fapi/v1/klines", {"symbol": sym, "interval": "5m", "limit": 300})
        c15 = [float(k[4]) for k in k15]
        c5 = [float(k[4]) for k in k5]
        if len(c15) < 200 or len(c5) < 100:
            continue
        close = c5[-1]
        e50 = ema(c15[-200:], 50)
        e200 = ema(c15[-200:], 200)
        r15 = rsi(c15[-200:], 14)
        e20_5 = ema(c5[-100:], 20)
        r5 = rsi(c5[-100:], 14)
        a5 = atr(k5[-100:], 14)
        swing_low = min(float(k[3]) for k in k5[-20:])
        swing_high = max(float(k[2]) for k in k5[-20:])

        trend_up = e50 and e200 and (e50>e200) and (close>e50) and (r15 is not None and r15>=52)
        momo_up = e20_5 and (close>e20_5) and (r5 is not None and r5>=50)
        trend_dn = e50 and e200 and (e50<e200) and (close<e50) and (r15 is not None and r15<=48)
        momo_dn = e20_5 and (close<e20_5) and (r5 is not None and r5<=50)

        score_l = (2 if trend_up else 0) + (1 if momo_up else 0)
        score_s = (2 if trend_dn else 0) + (1 if momo_dn else 0)

        if score_l >= 3:
            longs.append({
                "symbol": sym,
                "price": round(close, 6),
                "ema50_15m": round(e50, 6) if e50 else None,
                "ema200_15m": round(e200, 6) if e200 else None,
                "rsi15": round(r15, 2) if r15 is not None else None,
                "rsi5": round(r5, 2) if r5 is not None else None,
                "atr5": round(a5, 6) if a5 else None,
                "stop": round(min(swing_low, close - (a5 or 0)), 6),
                "timeframe": "15m trend + 5m momentum"
            })
        if score_s >= 3:
            shorts.append({
                "symbol": sym,
                "price": round(close, 6),
                "ema50_15m": round(e50, 6) if e50 else None,
                "ema200_15m": round(e200, 6) if e200 else None,
                "rsi15": round(r15, 2) if r15 is not None else None,
                "rsi5": round(r5, 2) if r5 is not None else None,
                "atr5": round(a5, 6) if a5 else None,
                "stop": round(max(swing_high, close + (a5 or 0)), 6),
                "timeframe": "15m trend + 5m momentum"
            })
    except Exception as e:
        errors.append({"symbol": sym, "error": str(e)})

# Sort by simple momentum (distance above/below EMA20_5) then recent volatility
def sort_key_long(x):
    return (x.get('rsi5') or 0, x.get('atr5') or 0)

def sort_key_short(x):
    return ((100-(x.get('rsi5') or 0)), x.get('atr5') or 0)

longs.sort(key=sort_key_long, reverse=True)
shorts.sort(key=sort_key_short, reverse=True)

print(json.dumps({"longs": longs[:6], "shorts": shorts[:6], "errors": errors[:3]}))
