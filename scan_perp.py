import json, time, urllib.request
from statistics import mean

BASE = "https://fapi.binance.com"

def http_get(path, params=None, timeout=20):
    if params:
        qs = "?" + "&".join(f"{k}={v}" for k, v in params.items())
    else:
        qs = ""
    with urllib.request.urlopen(BASE + path + qs, timeout=timeout) as r:
        return json.loads(r.read().decode())

# Technical helpers

def ema(series, period):
    if len(series) < period:
        return None
    k = 2 / (period + 1)
    e = series[0]
    for v in series[1:]:
        e = v * k + e * (1 - k)
    return e

def rsi(series, period=14):
    if len(series) <= period:
        return None
    gains = []
    losses = []
    for i in range(1, len(series)):
        d = series[i] - series[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(klines, period=14):
    # klines: list of [open time, open, high, low, close, volume, ...]
    if len(klines) <= period:
        return None
    trs = []
    prev_close = float(klines[0][4])
    for k in klines[1:]:
        high = float(k[2])
        low = float(k[3])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
        prev_close = float(k[4])
    if len(trs) < period:
        return None
    a = mean(trs[:period])
    for t in trs[period:]:
        a = (a * (period - 1) + t) / period
    return a

# Universe: top N USDT perpetual by quoteVolume
exinfo = http_get("/fapi/v1/exchangeInfo")
perp = {s["symbol"]: s for s in exinfo["symbols"] if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING"}

all24 = http_get("/fapi/v1/ticker/24hr")
ranked = []
for t in all24:
    sym = t["symbol"]
    if sym in perp:
        try:
            qv = float(t.get("quoteVolume", "0"))
        except Exception:
            qv = 0.0
        ranked.append((sym, qv, t))
ranked.sort(key=lambda x: x[1], reverse=True)
TOPN = ranked[:20]

longs = []
shorts = []
errors = []

for sym, qv, t in TOPN:
    try:
        k1h = http_get("/fapi/v1/klines", {"symbol": sym, "interval": "1h", "limit": 300})
        k15 = http_get("/fapi/v1/klines", {"symbol": sym, "interval": "15m", "limit": 300})
        c1h = [float(k[4]) for k in k1h]
        c15 = [float(k[4]) for k in k15]
        if len(c1h) < 200 or len(c15) < 100:
            continue
        close = c1h[-1]
        ema50 = ema(c1h[-200:], 50)
        ema200 = ema(c1h[-200:], 200)
        rsi1h = rsi(c1h[-200:], 14)
        ema20_15 = ema(c15[-100:], 20)
        rsi15 = rsi(c15[-100:], 14)
        a = atr(k15[-100:], 14)

        high24 = float(t["highPrice"]) if float(t["highPrice"])>0 else close
        low24 = float(t["lowPrice"]) if float(t["lowPrice"])>0 else close
        near_high = (high24 - close) / high24 if high24 else 1
        near_low = (close - low24) / low24 if low24 else 1

        swing_low = min(float(k[3]) for k in k15[-20:])
        swing_high = max(float(k[2]) for k in k15[-20:])

        trend_up = ema50 and ema200 and ema50 > ema200 and close > ema50 and (rsi1h is not None and rsi1h >= 52)
        momo_up = ema20_15 and close > ema20_15 and (rsi15 is not None and rsi15 >= 50)
        trend_dn = ema50 and ema200 and ema50 < ema200 and close < ema50 and (rsi1h is not None and rsi1h <= 48)
        momo_dn = ema20_15 and close < ema20_15 and (rsi15 is not None and rsi15 <= 50)

        score_long = 0
        if trend_up: score_long += 2
        if momo_up: score_long += 1
        if near_high <= 0.005: score_long += 1

        score_short = 0
        if trend_dn: score_short += 2
        if momo_dn: score_short += 1
        if near_low <= 0.005: score_short += 1

        if score_long >= 3:
            longs.append({
                "symbol": sym,
                "qVol": qv,
                "price": round(close, 6),
                "ema50": round(ema50, 6) if ema50 else None,
                "ema200": round(ema200, 6) if ema200 else None,
                "rsi1h": round(rsi1h, 2) if rsi1h is not None else None,
                "rsi15": round(rsi15, 2) if rsi15 is not None else None,
                "near_high_pct": round(near_high * 100, 3),
                "stop": round(min(swing_low, close - (a or 0)), 6),
                "atr15": round(a, 6) if a else None,
                "score": score_long
            })
        if score_short >= 3:
            shorts.append({
                "symbol": sym,
                "qVol": qv,
                "price": round(close, 6),
                "ema50": round(ema50, 6) if ema50 else None,
                "ema200": round(ema200, 6) if ema200 else None,
                "rsi1h": round(rsi1h, 2) if rsi1h is not None else None,
                "rsi15": round(rsi15, 2) if rsi15 is not None else None,
                "near_low_pct": round(near_low * 100, 3),
                "stop": round(max(swing_high, close + (a or 0)), 6),
                "atr15": round(a, 6) if a else None,
                "score": score_short
            })
    except Exception as e:
        errors.append({"symbol": sym, "error": str(e)})

longs.sort(key=lambda x: (x["score"], x["qVol"]), reverse=True)
shorts.sort(key=lambda x: (x["score"], x["qVol"]), reverse=True)

print(json.dumps({
    "ts": int(time.time()),
    "longs": longs[:8],
    "shorts": shorts[:8],
    "errors": errors[:4]
}))
