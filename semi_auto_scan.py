import json
import math
import time
import urllib.request
from statistics import mean

BASE = "https://fapi.binance.com"
TIMEOUT = 12
TOPN = 15
TREND_INTERVAL = "1h"
TRIGGER_INTERVAL = "15m"

WATCHLIST = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT"
]


def http_get(path, params=None):
    if params:
        qs = "?" + "&".join(f"{k}={v}" for k, v in params.items())
    else:
        qs = ""
    with urllib.request.urlopen(BASE + path + qs, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def ema(seq, period):
    if len(seq) < period:
        return None
    k = 2 / (period + 1)
    e = seq[0]
    for v in seq[1:]:
        e = v * k + e * (1 - k)
    return e


def rsi(seq, period=14):
    if len(seq) <= period:
        return None
    gains, losses = [], []
    for i in range(1, len(seq)):
        d = seq[i] - seq[i - 1]
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
    if len(klines) <= period:
        return None
    trs = []
    prev_close = float(klines[0][4])
    for k in klines[1:]:
        high = float(k[2])
        low = float(k[3])
        close = float(k[4])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
        prev_close = close
    if len(trs) < period:
        return None
    a = mean(trs[:period])
    for t in trs[period:]:
        a = (a * (period - 1) + t) / period
    return a


def nearest_levels(klines, lookback=40):
    highs = [float(k[2]) for k in klines[-lookback:]]
    lows = [float(k[3]) for k in klines[-lookback:]]
    return max(highs), min(lows)


def pct(a, b):
    if not b:
        return None
    return abs(a - b) / b


def score_setup(side, close, e50, e200, r_trend, r_trigger, atr_val, support, resistance):
    trend_score = 0
    trigger_score = 0
    rr_score = 0
    entry_score = 0
    vol_score = 0

    if side == "LONG":
        if e50 and e200 and e50 > e200 and close > e50 and (r_trend is not None and r_trend >= 55):
            trend_score = 3
        elif e50 and e200 and e50 > e200 and close > e50 and (r_trend is not None and r_trend >= 52):
            trend_score = 2
        elif e50 and e200 and e50 > e200:
            trend_score = 1

        if r_trigger is not None and r_trigger >= 55:
            trigger_score = 2
        elif r_trigger is not None and r_trigger >= 50:
            trigger_score = 1

        stop = min(support, close - (atr_val or 0))
        risk = close - stop
        tp1 = close + risk
        tp2 = close + 2 * risk
        room = resistance - close
    else:
        if e50 and e200 and e50 < e200 and close < e50 and (r_trend is not None and r_trend <= 45):
            trend_score = 3
        elif e50 and e200 and e50 < e200 and close < e50 and (r_trend is not None and r_trend <= 48):
            trend_score = 2
        elif e50 and e200 and e50 < e200:
            trend_score = 1

        if r_trigger is not None and r_trigger <= 45:
            trigger_score = 2
        elif r_trigger is not None and r_trigger <= 50:
            trigger_score = 1

        stop = max(resistance, close + (atr_val or 0))
        risk = stop - close
        tp1 = close - risk
        tp2 = close - 2 * risk
        room = close - support

    rr2 = (abs(tp2 - close) / risk) if risk > 0 else 0
    if rr2 >= 2.0:
        rr_score = 2
    elif rr2 >= 1.8:
        rr_score = 1

    stop_pct = (risk / close) if close else 999
    if stop_pct <= 0.012:
        entry_score = 2
    elif stop_pct <= 0.02:
        entry_score = 1

    if atr_val and close and (atr_val / close) <= 0.02:
        vol_score = 1

    total = trend_score + trigger_score + rr_score + entry_score + vol_score

    if total >= 8:
        verdict = "PROPOSE"
    elif total >= 6:
        verdict = "WATCH"
    else:
        verdict = "NO TRADE"

    if room <= 0 or risk <= 0:
        verdict = "NO TRADE"

    rr_to_tp2 = round((abs(tp2 - close) / risk), 2) if risk > 0 else 0

    return {
        "score": total,
        "trend_score": trend_score,
        "trigger_score": trigger_score,
        "rr_score": rr_score,
        "entry_score": entry_score,
        "vol_score": vol_score,
        "entry": round(close, 6),
        "stop": round(stop, 6),
        "tp1": round(tp1, 6),
        "tp2": round(tp2, 6),
        "risk_pct": round(stop_pct * 100, 3),
        "rr": rr_to_tp2,
        "verdict": verdict,
    }


def market_regime(btc_close, btc_e50, btc_e200, btc_rsi):
    if btc_e50 and btc_e200 and btc_close > btc_e50 and btc_e50 > btc_e200 and (btc_rsi or 0) >= 52:
        return "bullish"
    if btc_e50 and btc_e200 and btc_close < btc_e50 and btc_e50 < btc_e200 and (btc_rsi or 100) <= 48:
        return "bearish"
    return "mixed"


ex = http_get("/fapi/v1/exchangeInfo")
perp = {
    s["symbol"]
    for s in ex["symbols"]
    if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING"
}
all24 = http_get("/fapi/v1/ticker/24hr")
ranked = []
for t in all24:
    sym = t["symbol"]
    if sym in perp:
        try:
            qv = float(t.get("quoteVolume", "0"))
        except Exception:
            qv = 0.0
        ranked.append((sym, qv))
ranked.sort(key=lambda x: x[1], reverse=True)
top_syms = [s for s, _ in ranked[:TOPN]]
syms = []
for s in WATCHLIST + top_syms:
    if s in perp and s not in syms:
        syms.append(s)

results = []
errors = []
btc_ctx = None

for sym in syms:
    try:
        k_trend = http_get("/fapi/v1/klines", {"symbol": sym, "interval": TREND_INTERVAL, "limit": 300})
        k_trigger = http_get("/fapi/v1/klines", {"symbol": sym, "interval": TRIGGER_INTERVAL, "limit": 300})
        c_trend = [float(k[4]) for k in k_trend]
        c_trigger = [float(k[4]) for k in k_trigger]
        if len(c_trend) < 200 or len(c_trigger) < 100:
            continue

        close = c_trigger[-1]
        e50 = ema(c_trend[-200:], 50)
        e200 = ema(c_trend[-200:], 200)
        r_trend = rsi(c_trend[-200:], 14)
        r_trigger = rsi(c_trigger[-100:], 14)
        atr_val = atr(k_trigger[-100:], 14)
        resistance, support = nearest_levels(k_trigger, lookback=40)

        long_setup = score_setup("LONG", close, e50, e200, r_trend, r_trigger, atr_val, support, resistance)
        short_setup = score_setup("SHORT", close, e50, e200, r_trend, r_trigger, atr_val, support, resistance)

        picked = long_setup if long_setup["score"] >= short_setup["score"] else short_setup
        side = "LONG" if picked is long_setup else "SHORT"

        item = {
            "symbol": sym,
            "side": side,
            "score": picked["score"],
            "verdict": picked["verdict"],
            "entry": picked["entry"],
            "stop": picked["stop"],
            "tp1": picked["tp1"],
            "tp2": picked["tp2"],
            "rr": picked["rr"],
            "risk_pct": picked["risk_pct"],
            "rsi_trend": round(r_trend, 2) if r_trend is not None else None,
            "rsi_trigger": round(r_trigger, 2) if r_trigger is not None else None,
            "ema50": round(e50, 6) if e50 else None,
            "ema200": round(e200, 6) if e200 else None,
            "atr": round(atr_val, 6) if atr_val else None,
            "support": round(support, 6),
            "resistance": round(resistance, 6),
            "thesis": f"{TREND_INTERVAL} trend + {TRIGGER_INTERVAL} trigger, score {picked['score']}/10",
        }
        results.append(item)

        if sym == "BTCUSDT":
            btc_ctx = (close, e50, e200, r_trend)
    except Exception as e:
        errors.append({"symbol": sym, "error": str(e)})

results.sort(key=lambda x: (x["score"], x["rr"]), reverse=True)

if btc_ctx:
    regime = market_regime(*btc_ctx)
else:
    regime = "unknown"

payload = {
    "ts": int(time.time()),
    "timeframes": {"trend": TREND_INTERVAL, "trigger": TRIGGER_INTERVAL},
    "market_regime": regime,
    "proposals": [x for x in results if x["verdict"] == "PROPOSE"][:8],
    "watch": [x for x in results if x["verdict"] == "WATCH"][:8],
    "no_trade_count": len([x for x in results if x["verdict"] == "NO TRADE"]),
    "errors": errors[:5],
}

print(json.dumps(payload, ensure_ascii=False))
