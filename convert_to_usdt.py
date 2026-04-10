#!/usr/bin/env python3
import json, time, hmac, hashlib, urllib.parse, urllib.request
from decimal import Decimal, ROUND_DOWN

with open('/Users/huuht/.openclaw/credentials/binance.json') as f:
    creds = json.load(f)
KEY = creds['apiKey']
SECRET = creds['secretKey'].encode()
HDR = {'X-MBX-APIKEY': KEY}

BASE = 'https://api.binance.com'

def ts_ms():
    return str(int(time.time()*1000))

def signed_get(path, params=None):
    if params is None: params = {}
    params.update({'timestamp': ts_ms(), 'recvWindow': '5000'})
    q = urllib.parse.urlencode(params)
    sig = hmac.new(SECRET, q.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE}{path}?{q}&signature={sig}"
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode())

def signed_post(path, params=None):
    if params is None: params = {}
    params.update({'timestamp': ts_ms(), 'recvWindow': '5000'})
    q = urllib.parse.urlencode(params)
    sig = hmac.new(SECRET, q.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE}{path}"
    data = (q+"&signature="+sig).encode()
    req = urllib.request.Request(url, data=data, headers=HDR, method='POST')
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode())

def get_json(url):
    with urllib.request.urlopen(url, timeout=12) as r:
        return json.loads(r.read().decode())

# Load exchange info
ex = get_json(BASE + '/api/v3/exchangeInfo')
symbols = {s['symbol']: s for s in ex['symbols'] if s.get('status') == 'TRADING'}

# Mapping ASSET -> symbol ASSETUSDT if exists
asset_to_symbol = {}
for s in symbols.values():
    if s['quoteAsset'] == 'USDT':
        asset_to_symbol[s['baseAsset']] = s

# helper to get filters
def get_filter(s, ftype):
    for f in s.get('filters', []):
        if f.get('filterType') == ftype:
            return f
    return None

# price cache
price_cache = {}

def ticker_price(sym):
    if sym in price_cache:
        return price_cache[sym]
    try:
        data = get_json(BASE + '/api/v3/ticker/price?symbol=' + sym)
        p = Decimal(str(data['price']))
    except Exception:
        p = None
    price_cache[sym] = p
    return p

# Quantize helpers

def step_floor(x: Decimal, step: Decimal) -> Decimal:
    if step == 0:
        return x
    return (x // step) * step

# Fetch balances
acct = signed_get('/api/v3/account')
nonzero = []
for b in acct.get('balances', []):
    free = Decimal(str(b.get('free', '0')))
    locked = Decimal(str(b.get('locked', '0')))
    amt = free  # only trade free
    if amt > 0 and b['asset'] != 'USDT':
        nonzero.append({'asset': b['asset'], 'free': free, 'locked': locked})

results = []
converted_usdt = Decimal('0')
for it in nonzero:
    a = it['asset']
    if a.endswith('USDT'):  # e.g., LDUSDT token; skip (no ASSETUSDT pair expected)
        results.append({'asset': a, 'action': 'skip', 'reason': 'asset_looks_like_usdt_token'})
        continue
    if a not in asset_to_symbol:
        results.append({'asset': a, 'action': 'skip', 'reason': 'no_USDT_pair'})
        continue
    s = asset_to_symbol[a]
    sym = s['symbol']
    # Filters
    lot = get_filter(s, 'LOT_SIZE') or {}
    stepSize = Decimal(lot.get('stepSize', '0.00000001'))
    minQty = Decimal(lot.get('minQty', '0'))
    # Min notional (legacy or new)
    f_notional = get_filter(s, 'MIN_NOTIONAL') or get_filter(s, 'NOTIONAL') or {}
    minNotional = Decimal(str(f_notional.get('minNotional', '0')))
    # Price
    p = ticker_price(sym)
    if p is None:
        results.append({'asset': a, 'symbol': sym, 'action': 'skip', 'reason': 'no_price'})
        continue
    qty_raw = it['free']
    # Floor to step and >= minQty
    qty = step_floor(qty_raw, stepSize)
    if qty <= 0 or qty < minQty:
        results.append({'asset': a, 'symbol': sym, 'action': 'skip', 'reason': 'below_minQty', 'qty': str(qty), 'minQty': str(minQty)})
        continue
    notional = (qty * p)
    if minNotional > 0 and notional < minNotional:
        results.append({'asset': a, 'symbol': sym, 'action': 'skip', 'reason': 'below_minNotional', 'qty': str(qty), 'notional': str(notional), 'minNotional': str(minNotional)})
        continue
    # Place MARKET SELL
    try:
        od = signed_post('/api/v3/order', {
            'symbol': sym,
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': str(qty)
        })
        results.append({'asset': a, 'symbol': sym, 'action': 'sold', 'qty': str(qty), 'orderId': od.get('orderId')})
    except Exception as e:
        try:
            err = json.loads(e.read().decode())
        except Exception:
            err = {'msg': str(e)}
        results.append({'asset': a, 'symbol': sym, 'action': 'error', 'error': err})

# Refresh USDT free
acct2 = signed_get('/api/v3/account')
free_usdt = Decimal('0')
for b in acct2.get('balances', []):
    if b['asset'] == 'USDT':
        free_usdt = Decimal(str(b.get('free','0')))
        break

out = {
    'trades': results,
    'free_usdt': str(free_usdt)
}
print(json.dumps(out))
