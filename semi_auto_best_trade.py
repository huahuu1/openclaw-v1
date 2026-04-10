import json
import time
import math
import hmac
import hashlib
import urllib.parse
import urllib.request
from statistics import mean
from decimal import Decimal, ROUND_DOWN, getcontext

getcontext().prec = 28

BASE = "https://fapi.binance.com"
SPOT_BASE = "https://api.binance.com"
TIMEOUT = 12
TREND_INTERVAL = "1h"
TRIGGER_INTERVAL = "15m"
DEFAULT_RISK_PCT = Decimal("0.5")
WATCHLIST = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT"
]

with open('/Users/huuht/.openclaw/credentials/binance.json') as f:
    CREDS = json.load(f)
API_KEY = CREDS['apiKey']
SECRET = CREDS['secretKey'].encode()


def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def fapi_get(path, params=None):
    if params:
        qs = "?" + urllib.parse.urlencode(params)
    else:
        qs = ""
    return http_get(BASE + path + qs)


def signed_get(base, path, params=None):
    params = dict(params or {})
    params['timestamp'] = str(int(time.time() * 1000))
    params['recvWindow'] = '5000'
    q = urllib.parse.urlencode(params)
    sig = hmac.new(SECRET, q.encode(), hashlib.sha256).hexdigest()
    url = f"{base}{path}?{q}&signature={sig}"
    return http_get(url, headers={'X-MBX-APIKEY': API_KEY})


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


def get_total_equity_usdt():
    total = Decimal('0')
    try:
        um = signed_get(BASE, '/fapi/v2/balance')
        for a in um:
            bal = Decimal(str(a.get('balance', '0')))
            if a.get('asset') == 'USDT':
                total += bal
    except Exception:
        pass
    try:
        spot = signed_get(SPOT_BASE, '/api/v3/account')
        for b in spot.get('balances', []):
            asset = b.get('asset')
            amt = Decimal(str(b.get('free', '0'))) + Decimal(str(b.get('locked', '0')))
            if amt == 0:
                continue
            if asset == 'USDT':
                total += amt
            else:
                try:
                    px = http_get(SPOT_BASE + '/api/v3/ticker/price?symbol=' + asset + 'USDT')['price']
                    total += amt * Decimal(str(px))
                except Exception:
                    pass
    except Exception:
        pass
    return total


def get_filters(symbol_info):
    lot = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
    min_notional = next((f for f in symbol_info['filters'] if f['filterType'] in ('MIN_NOTIONAL', 'NOTIONAL')), None)
    price_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'), None)
    return {
        'stepSize': Decimal(str(lot['stepSize'])) if lot else Decimal('0.001'),
        'minQty': Decimal(str(lot['minQty'])) if lot else Decimal('0'),
        'tickSize': Decimal(str(price_filter['tickSize'])) if price_filter else Decimal('0.01'),
        'minNotional': Decimal(str(min_notional.get('notional', min_notional.get('minNotional', '5')))) if min_notional else Decimal('5'),
    }


def round_down(value, step):
    if step == 0:
        return value
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def score_setup(side, close, e50, e200, r_trend, r_trigger, atr_val, support, resistance):
    trend_score = trigger_score = rr_score = entry_score = vol_score = 0
    if side == 'LONG':
        if e50 and e200 and e50 > e200 and close > e50 and (r_trend or 0) >= 55:
            trend_score = 3
        elif e50 and e200 and e50 > e200 and close > e50 and (r_trend or 0) >= 52:
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
    else:
        if e50 and e200 and e50 < e200 and close < e50 and (r_trend or 100) <= 45:
            trend_score = 3
        elif e50 and e200 and e50 < e200 and close < e50 and (r_trend or 100) <= 48:
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
    rr = (abs(tp2 - close) / risk) if risk > 0 else 0
    if rr >= 2.0:
        rr_score = 2
    elif rr >= 1.8:
        rr_score = 1
    stop_pct = (risk / close) if close else 999
    if stop_pct <= 0.012:
        entry_score = 2
    elif stop_pct <= 0.02:
        entry_score = 1
    if atr_val and close and (atr_val / close) <= 0.02:
        vol_score = 1
    total = trend_score + trigger_score + rr_score + entry_score + vol_score
    verdict = 'PROPOSE' if total >= 8 else ('WATCH' if total >= 6 else 'NO TRADE')
    return {
        'score': total,
        'entry': close,
        'stop': stop,
        'tp1': tp1,
        'tp2': tp2,
        'rr': rr,
        'risk_pct': stop_pct * 100,
        'verdict': verdict,
    }


def main():
    risk_pct = DEFAULT_RISK_PCT
    exinfo = fapi_get('/fapi/v1/exchangeInfo')
    symbol_map = {s['symbol']: s for s in exinfo['symbols'] if s.get('contractType') == 'PERPETUAL' and s.get('quoteAsset') == 'USDT' and s.get('status') == 'TRADING'}

    equity = get_total_equity_usdt()
    risk_amount = (equity * risk_pct / Decimal('100'))

    proposals = []
    errors = []

    for sym in WATCHLIST:
        if sym not in symbol_map:
            continue
        try:
            k_trend = fapi_get('/fapi/v1/klines', {'symbol': sym, 'interval': TREND_INTERVAL, 'limit': 300})
            k_trigger = fapi_get('/fapi/v1/klines', {'symbol': sym, 'interval': TRIGGER_INTERVAL, 'limit': 300})
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
            long_setup = score_setup('LONG', close, e50, e200, r_trend, r_trigger, atr_val, support, resistance)
            short_setup = score_setup('SHORT', close, e50, e200, r_trend, r_trigger, atr_val, support, resistance)
            picked = long_setup if long_setup['score'] >= short_setup['score'] else short_setup
            side = 'LONG' if picked is long_setup else 'SHORT'
            if picked['verdict'] != 'PROPOSE':
                continue

            filters = get_filters(symbol_map[sym])
            entry = Decimal(str(picked['entry']))
            stop = Decimal(str(picked['stop']))
            stop_distance = abs(entry - stop)
            if stop_distance <= 0:
                continue
            raw_qty = risk_amount / stop_distance
            qty = round_down(raw_qty, filters['stepSize'])
            notional = qty * entry
            if qty < filters['minQty'] or notional < filters['minNotional']:
                continue
            leverage = max(1, min(5, math.ceil(float(notional / equity)) if equity > 0 else 1))
            proposals.append({
                'symbol': sym,
                'side': side,
                'score': picked['score'],
                'entry': round(float(entry), 6),
                'stop': round(float(stop), 6),
                'tp1': round(float(Decimal(str(picked['tp1']))), 6),
                'tp2': round(float(Decimal(str(picked['tp2']))), 6),
                'rr': round(float(picked['rr']), 2),
                'risk_pct_trade': round(float(picked['risk_pct']), 3),
                'account_equity_usdt': round(float(equity), 2),
                'risk_amount_usdt': round(float(risk_amount), 4),
                'qty': float(qty),
                'notional_usdt': round(float(notional), 4),
                'suggested_leverage': leverage,
                'rsi_trend': round(r_trend, 2) if r_trend is not None else None,
                'rsi_trigger': round(r_trigger, 2) if r_trigger is not None else None,
                'thesis': f'{TREND_INTERVAL} trend + {TRIGGER_INTERVAL} trigger, score {picked["score"]}/10',
            })
        except Exception as e:
            errors.append({'symbol': sym, 'error': str(e)})

    proposals.sort(key=lambda x: (x['score'], x['rr'], -x['risk_pct_trade']), reverse=True)
    best = proposals[0] if proposals else None
    out = {
        'ts': int(time.time()),
        'risk_pct_account': float(risk_pct),
        'account_equity_usdt': round(float(equity), 2),
        'best_trade': best,
        'alternatives': proposals[1:4],
        'errors': errors[:5],
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
