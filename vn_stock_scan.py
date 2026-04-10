import argparse
import json
import time
import urllib.request
from statistics import mean

BASE = "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
TIMEOUT = 15
DEFAULT_UNIVERSE = [
    "VHM", "VIC", "VCB", "CTG", "BID", "MBB", "ACB", "TCB",
    "FPT", "HPG", "SSI", "VCI", "HCM", "REE", "GMD", "VNM",
    "MWG", "PNJ", "DGC", "MSN", "GAS", "PVD", "PVS", "KDH", "NLG"
]
EXTENDED_BREADTH_UNIVERSE = [
    "AAA", "ACB", "ANV", "ASM", "BAF", "BCG", "BCM", "BDC", "BFC", "BID",
    "BMP", "BSI", "BSR", "BVH", "C4G", "CII", "CMG", "CMX", "CTD", "CTG",
    "CTR", "DBC", "DCM", "DGC", "DGW", "DHA", "DIG", "DPM", "DRC", "DXG",
    "DXS", "EIB", "EVF", "FCN", "FPT", "FTS", "GAS", "GEX", "GIL", "GMD",
    "GVR", "HAG", "HAH", "HAX", "HBC", "HCM", "HDB", "HDG", "HHV", "HNG",
    "HPG", "HSG", "HT1", "IJC", "KBC", "KDC", "KDH", "KOS", "KSB", "LAS",
    "LCG", "LPB", "MBB", "MIG", "MSB", "MSN", "MWG", "NKG", "NLG", "NT2",
    "OCB", "PAN", "PC1", "PDR", "PET", "PHR", "PLX", "PNJ", "POW", "PVD",
    "PVS", "PVC", "PVT", "REE", "SAB", "SBT", "SCR", "SHB", "SIP", "SJS",
    "SSB", "SSI", "STB", "SZC", "TCB", "TCH", "TLG", "TPB", "VCB", "VCG",
    "VCI", "VGC", "VHC", "VHM", "VIB", "VIC", "VIX", "VJC", "VND", "VNM",
    "VOS", "VPB", "VPI", "VRE", "VSC", "CSV", "DPR", "DTD", "FRT", "GEE",
    "GAS", "GEG", "HDC", "IDC", "IDC", "ITA", "KHG", "MSH", "NAB", "NTP",
    "ORS", "PHR", "QNS", "SCS", "SHS", "TNG", "VEA", "VHC", "VGI", "VGS"
]
EXTENDED_BREADTH_UNIVERSE = list(dict.fromkeys(DEFAULT_UNIVERSE + EXTENDED_BREADTH_UNIVERSE))[:150]
SECTOR_MAP = {
    "VHM": "real_estate", "VIC": "real_estate", "KDH": "real_estate", "NLG": "real_estate",
    "VCB": "bank", "CTG": "bank", "BID": "bank", "MBB": "bank", "ACB": "bank", "TCB": "bank",
    "SSI": "securities", "VCI": "securities", "HCM": "securities",
    "FPT": "technology", "MWG": "retail", "PNJ": "retail", "MSN": "consumer",
    "HPG": "steel", "DGC": "chemicals", "GAS": "energy", "PVD": "energy", "PVS": "energy",
    "REE": "utilities", "GMD": "logistics", "VNM": "consumer"
}


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def fetch_ohlc(symbol, resolution="1D", bars=260):
    now = int(time.time())
    if resolution == "1D":
        lookback = bars * 86400 * 2
    elif resolution in ("1H", "60"):
        lookback = bars * 3600 * 8
    elif resolution == "15":
        lookback = bars * 900 * 4
    else:
        lookback = bars * 3600 * 2
    frm = now - lookback
    url = f"{BASE}?from={frm}&to={now}&symbol={symbol}&resolution={resolution}"
    data = http_get_json(url)
    keys = ["t", "o", "h", "l", "c", "v"]
    if not all(k in data for k in keys):
        raise ValueError(f"Bad OHLC payload for {symbol} {resolution}: {data}")
    rows = []
    for i in range(len(data["t"])):
        rows.append({
            "t": int(data["t"][i]),
            "o": float(data["o"][i]),
            "h": float(data["h"][i]),
            "l": float(data["l"][i]),
            "c": float(data["c"][i]),
            "v": float(data["v"][i]),
        })
    return rows[-bars:]


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


def atr(rows, period=14):
    if len(rows) <= period:
        return None
    trs = []
    prev_close = rows[0]["c"]
    for row in rows[1:]:
        tr = max(row["h"] - row["l"], abs(row["h"] - prev_close), abs(row["l"] - prev_close))
        trs.append(tr)
        prev_close = row["c"]
    if len(trs) < period:
        return None
    a = mean(trs[:period])
    for t in trs[period:]:
        a = (a * (period - 1) + t) / period
    return a


def pct_change(a, b):
    if not b:
        return None
    return (a - b) / b * 100


def rel_volume(rows, period=20):
    if len(rows) < period + 1:
        return None
    avg = mean([r["v"] for r in rows[-period-1:-1]])
    if avg == 0:
        return None
    return rows[-1]["v"] / avg


def highest(rows, lookback):
    return max(r["h"] for r in rows[-lookback:])


def lowest(rows, lookback):
    return min(r["l"] for r in rows[-lookback:])


def calc_breadth(items):
    adv = sum(1 for x in items if (x.get("change_pct_1d") or 0) > 0)
    dec = sum(1 for x in items if (x.get("change_pct_1d") or 0) < 0)
    strong = sum(1 for x in items if x.get("verdict") == "PROPOSE")
    total = len(items) or 1
    return {
        "advance": adv,
        "decline": dec,
        "advance_ratio": round(adv / total, 2),
        "decline_ratio": round(dec / total, 2),
        "strong_ratio": round(strong / total, 2),
    }


def calc_sector_strength(items):
    sectors = {}
    for x in items:
        sec = x.get("sector", "other")
        sectors.setdefault(sec, []).append(x)
    out = []
    for sec, bucket in sectors.items():
        avg_chg = mean([(b.get("change_pct_1d") or 0) for b in bucket])
        avg_score = mean([b.get("score", 0) for b in bucket])
        out.append({
            "sector": sec,
            "count": len(bucket),
            "avg_change_pct_1d": round(avg_chg, 2),
            "avg_score": round(avg_score, 2),
        })
    out.sort(key=lambda x: (x["avg_score"], x["avg_change_pct_1d"]), reverse=True)
    return out


def score_breadth_symbol(symbol, daily_rows):
    dclose = [r["c"] for r in daily_rows]
    close = dclose[-1]
    prev_close = dclose[-2] if len(dclose) >= 2 else close
    e20 = ema(dclose[-60:], 20)
    rv20 = rel_volume(daily_rows, 20)
    chg1 = pct_change(close, prev_close)
    return {
        "symbol": symbol,
        "close": round(close, 2),
        "change_pct_1d": round(chg1, 2) if chg1 is not None else None,
        "ema20": round(e20, 2) if e20 is not None else None,
        "rel_volume20": round(rv20, 2) if rv20 is not None else None,
        "above_ema20": bool(e20 and close > e20),
        "sector": SECTOR_MAP.get(symbol, "other"),
    }


def scan_extended_breadth(symbols=None):
    symbols = symbols or EXTENDED_BREADTH_UNIVERSE
    out = []
    errors = []
    for symbol in symbols:
        try:
            daily_rows = fetch_ohlc(symbol, resolution="1D", bars=80)
            if len(daily_rows) < 25:
                raise ValueError(f"Not enough daily bars: D={len(daily_rows)}")
            out.append(score_breadth_symbol(symbol, daily_rows))
        except Exception as e:
            errors.append({"symbol": symbol, "error": str(e)})
    adv = sum(1 for x in out if (x.get("change_pct_1d") or 0) > 0)
    dec = sum(1 for x in out if (x.get("change_pct_1d") or 0) < 0)
    flat = sum(1 for x in out if (x.get("change_pct_1d") or 0) == 0)
    above_ema20 = sum(1 for x in out if x.get("above_ema20"))
    strong_volume = sum(1 for x in out if (x.get("rel_volume20") or 0) >= 1.2)
    total = len(out) or 1
    sector_strength = []
    sectors = {}
    for x in out:
        sec = x.get("sector", "other")
        sectors.setdefault(sec, []).append(x)
    for sec, bucket in sectors.items():
        sector_strength.append({
            "sector": sec,
            "count": len(bucket),
            "avg_change_pct_1d": round(mean([(b.get("change_pct_1d") or 0) for b in bucket]), 2),
            "above_ema20_ratio": round(sum(1 for b in bucket if b.get("above_ema20")) / len(bucket), 2),
        })
    sector_strength.sort(key=lambda x: (x["above_ema20_ratio"], x["avg_change_pct_1d"]), reverse=True)
    return {
        "universe_size": len(symbols),
        "valid_count": len(out),
        "error_count": len(errors),
        "advance": adv,
        "decline": dec,
        "flat": flat,
        "advance_ratio": round(adv / total, 2),
        "decline_ratio": round(dec / total, 2),
        "flat_ratio": round(flat / total, 2),
        "above_ema20": above_ema20,
        "above_ema20_ratio": round(above_ema20 / total, 2),
        "strong_volume": strong_volume,
        "strong_volume_ratio": round(strong_volume / total, 2),
        "sector_strength": sector_strength,
        "errors": errors[:10],
    }


def score_symbol(symbol, daily_rows, h1_rows, m15_rows):
    dclose = [r["c"] for r in daily_rows]
    hclose = [r["c"] for r in h1_rows]
    mclose = [r["c"] for r in m15_rows]

    close = dclose[-1]
    prev_close = dclose[-2] if len(dclose) >= 2 else close
    e20 = ema(dclose[-60:], 20)
    e50 = ema(dclose[-120:], 50)
    e200 = ema(dclose, 200)
    r14 = rsi(dclose[-120:], 14)
    a14 = atr(daily_rows[-40:], 14)
    rv20 = rel_volume(daily_rows, 20)
    chg1 = pct_change(close, prev_close)
    chg5 = pct_change(close, dclose[-6]) if len(dclose) >= 6 else None
    chg20 = pct_change(close, dclose[-21]) if len(dclose) >= 21 else None
    hi20 = highest(daily_rows, 20)
    lo20 = lowest(daily_rows, 20)
    hi55 = highest(daily_rows, 55) if len(daily_rows) >= 55 else hi20
    lo55 = lowest(daily_rows, 55) if len(daily_rows) >= 55 else lo20

    h_e20 = ema(hclose[-80:], 20) if len(hclose) >= 20 else None
    h_e50 = ema(hclose[-120:], 50) if len(hclose) >= 50 else None
    h_rsi = rsi(hclose[-120:], 14) if len(hclose) >= 20 else None
    m_e20 = ema(mclose[-80:], 20) if len(mclose) >= 20 else None
    m_rsi = rsi(mclose[-120:], 14) if len(mclose) >= 20 else None

    trend_score = 0
    quality_score = 0
    momentum_score = 0
    risk_score = 0
    trigger_score = 0
    penalty = 0

    if e20 and e50 and e200 and close > e20 > e50 > e200:
        trend_score = 4
    elif e20 and e50 and close > e20 > e50:
        trend_score = 3
    elif e50 and e200 and close > e50 > e200:
        trend_score = 2
    elif e20 and e50 and close > e20 and close > e50:
        trend_score = 1

    if r14 is not None:
        if 52 <= r14 <= 68:
            quality_score += 2
        elif 48 <= r14 <= 72:
            quality_score += 1

    if rv20 is not None:
        if rv20 >= 1.5:
            quality_score += 2
        elif rv20 >= 1.1:
            quality_score += 1

    if chg20 is not None:
        if chg20 > 8:
            momentum_score += 2
        elif chg20 > 3:
            momentum_score += 1

    if close >= hi20 * 0.98:
        momentum_score += 2
    elif close >= hi20 * 0.95:
        momentum_score += 1

    stop_ref = max(lo20, close - (a14 or 0)) if a14 else lo20
    risk_pct = ((close - stop_ref) / close * 100) if close else 999
    if 0 < risk_pct <= 3.5:
        risk_score = 2
    elif risk_pct <= 6:
        risk_score = 1

    if h_e20 and h_e50 and h_rsi is not None and hclose[-1] > h_e20 and h_e20 >= h_e50 and h_rsi >= 50:
        trigger_score += 1
    if m_e20 and m_rsi is not None and mclose[-1] > m_e20 and m_rsi >= 50:
        trigger_score += 1

    if chg1 is not None and rv20 is not None and chg1 >= 6 and rv20 >= 2.5:
        penalty += 2
    if r14 is not None and r14 >= 68 and close >= hi20 * 0.995:
        penalty += 1

    total = trend_score + quality_score + momentum_score + risk_score + trigger_score - penalty

    if total >= 9:
        verdict = "PROPOSE"
    elif total >= 7:
        verdict = "WATCH"
    else:
        verdict = "PASS"

    notes = []
    if close >= hi20 * 0.995:
        notes.append("near_20d_breakout")
    if rv20 and rv20 >= 1.5:
        notes.append("high_relative_volume")
    if r14 and r14 > 70:
        notes.append("extended")
    if e20 and close < e20:
        notes.append("below_ema20")
    if penalty >= 2:
        notes.append("avoid_chasing")
    if h_e20 and hclose[-1] < h_e20:
        notes.append("h1_not_confirmed")
    if m_e20 and mclose[-1] < m_e20:
        notes.append("m15_not_confirmed")

    return {
        "symbol": symbol,
        "sector": SECTOR_MAP.get(symbol, "other"),
        "close": round(close, 2),
        "change_pct_1d": round(chg1, 2) if chg1 is not None else None,
        "change_pct_5d": round(chg5, 2) if chg5 is not None else None,
        "change_pct_20d": round(chg20, 2) if chg20 is not None else None,
        "ema20": round(e20, 2) if e20 else None,
        "ema50": round(e50, 2) if e50 else None,
        "ema200": round(e200, 2) if e200 else None,
        "rsi14": round(r14, 2) if r14 is not None else None,
        "atr14": round(a14, 2) if a14 else None,
        "rel_volume20": round(rv20, 2) if rv20 is not None else None,
        "high20": round(hi20, 2),
        "low20": round(lo20, 2),
        "high55": round(hi55, 2),
        "low55": round(lo55, 2),
        "stop_ref": round(stop_ref, 2),
        "risk_pct_to_stop": round(risk_pct, 2),
        "h1_trend_ok": bool(h_e20 and h_e50 and hclose[-1] > h_e20 and h_e20 >= h_e50),
        "m15_trigger_ok": bool(m_e20 and mclose[-1] > m_e20),
        "score": total,
        "penalty": penalty,
        "verdict": verdict,
        "notes": notes,
        "as_of": daily_rows[-1]["t"],
    }


def scan(symbols):
    out = []
    errors = []
    for symbol in symbols:
        try:
            daily_rows = fetch_ohlc(symbol, resolution="1D", bars=260)
            h1_rows = fetch_ohlc(symbol, resolution="1H", bars=140)
            m15_rows = fetch_ohlc(symbol, resolution="15", bars=180)
            if len(daily_rows) < 80 or len(h1_rows) < 40 or len(m15_rows) < 40:
                raise ValueError(f"Not enough bars: D={len(daily_rows)} H1={len(h1_rows)} M15={len(m15_rows)}")
            out.append(score_symbol(symbol, daily_rows, h1_rows, m15_rows))
        except Exception as e:
            errors.append({"symbol": symbol, "error": str(e)})
    out.sort(key=lambda x: (x["score"], x["change_pct_20d"] or -999, x["rel_volume20"] or 0), reverse=True)

    breadth = calc_breadth(out)
    sectors = calc_sector_strength(out)
    breadth_extended = scan_extended_breadth()

    return {
        "ts": int(time.time()),
        "market": "VN",
        "timeframes": {"trend": "1D", "confirm": "1H", "trigger": "15m"},
        "universe": symbols,
        "breadth": breadth,
        "breadth_extended": breadth_extended,
        "sector_strength": sectors,
        "proposals": [x for x in out if x["verdict"] == "PROPOSE"],
        "watch": [x for x in out if x["verdict"] == "WATCH"],
        "pass_count": len([x for x in out if x["verdict"] == "PASS"]),
        "errors": errors,
        "all": out,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbols", nargs="*", help="Symbols to scan, e.g. VHM VCB HPG")
    parser.add_argument("--top", type=int, default=5, help="How many top names to print in compact mode")
    parser.add_argument("--compact", action="store_true", help="Print only compact shortlist")
    args = parser.parse_args()

    symbols = args.symbols or DEFAULT_UNIVERSE
    payload = scan(symbols)

    if args.compact:
        compact = {
            "ts": payload["ts"],
            "breadth": payload["breadth"],
            "sector_strength": payload["sector_strength"][:5],
            "proposals": payload["proposals"][:args.top],
            "watch": payload["watch"][:args.top],
            "errors": payload["errors"][:5],
        }
        print(json.dumps(compact, ensure_ascii=False))
        return

    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
