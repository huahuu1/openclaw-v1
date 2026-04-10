import json, time, urllib.request
from statistics import mean

BASE = "https://fapi.binance.com"
TIMEOUT = 12

def http_get(path, params=None):
    if params:
        qs = "?" + "&".join(f"{k}={v}" for k,v in params.items())
    else:
        qs = ""
    with urllib.request.urlopen(BASE + path + qs, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())

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

# Build universe
ex = http_get("/fapi/v1/exchangeInfo")
perp = {s["symbol"] for s in ex["symbols"] if s.get("contractType")=='PERPETUAL' and s.get("quoteAsset")=='USDT' and s.get("status")=='TRADING'}
all24 = http_get("/fapi/v1/ticker/24hr")
ranked = []
for t in all24:
    sym = t["symbol"]
    if sym in perp:
        try:
            qv = float(t.get("quoteVolume","0"))
        except:
            qv = 0.0
        ranked.append((sym, qv, t))
ranked.sort(key=lambda x: x[1], reverse=True)
TOP = [s for s,_,_ in ranked[:15]]

longs = []
shorts = []
errs = []

for sym in TOP:
    try:
        k1h = http_get("/fapi/v1/klines", {"symbol": sym, "interval": "1h", "limit": 300})
        k15 = http_get("/fapi/v1/klines", {"symbol": sym, "interval": "15m", "limit": 300})
        c1h = [float(k[4]) for k in k1h]
        c15 = [float(k[4]) for k in k15]
        if len(c1h) < 200 or len(c15) < 100:
            continue
        close = c1h[-1]
        e50 = ema(c1h[-200:], 50)
        e200 = ema(c1h[-200:], 200)
        r1h = rsi(c1h[-200:], 14)
        e20_15 = ema(c15[-100:], 20)
        r15 = rsi(c15[-100:], 14)
        a = atr(k15[-100:], 14)
        swing_low = min(float(k[3]) for k in k15[-20:])
        swing_high = max(float(k[2]) for k in k15[-20:])

        trend_up = e50 and e200 and e50>e200 and close>e50 and (r1h is not None and r1h>=52)
        momo_up = e20_15 and close>e20_15 and (r15 is not None and r15>=50)
        trend_dn = e50 and e200 and e50<e200 and close<e50 and (r1h is not None and r1h<=48)
        momo_dn = e20_15 and close<e20_15 and (r15 is not None and r15<=50)

        score_l = (2 if trend_up else 0) + (1 if momo_up else 0)
        score_s = (2 if trend_dn else 0) + (1 if momo_dn else 0)

        if score_l >= 3:
            longs.append({
                "symbol": sym, "price": round(close,6),
                "ema50": round(e50,6) if e50 else None,
                "ema200": round(e200,6) if e200 else None,
                "rsi1h": round(r1h,2) if r1h is not None else None,
                "rsi15": round(r15,2) if r15 is not None else None,
                "atr15": round(a,6) if a else None,
                "stop": round(min(swing_low, close - (a or 0)), 6)
            })
        if score_s >= 3:
            shorts.append({
                "symbol": sym, "price": round(close,6),
                "ema50": round(e50,6) if e50 else None,
                "ema200": round(e200,6) if e200 else None,
                "rsi1h": round(r1h,2) if r1h is not None else None,
                "rsi15": round(r15,2) if r15 is not None else None,
                "atr15": round(a,6) if a else None,
                "stop": round(max(swing_high, close + (a or 0)), 6)
            })
    except Exception as e:
        errs.append({"symbol": sym, "err": str(e)})

print(json.dumps({"longs": longs[:6], "shorts": shorts[:6], "errors": errs[:4]}))
