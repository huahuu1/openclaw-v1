import json, time, hmac, hashlib, urllib.parse, urllib.request
from decimal import Decimal, getcontext
getcontext().prec = 28

# Load API keys
with open('/Users/huuht/.openclaw/credentials/binance.json') as f:
    creds = json.load(f)
KEY = creds['apiKey']
SECRET = creds['secretKey'].encode()

def ts_ms():
    return str(int(time.time()*1000))

def signed_get(base, path, params=None):
    if params is None:
        params = {}
    params.update({'timestamp': ts_ms(), 'recvWindow': '5000'})
    q = urllib.parse.urlencode(params)
    sig = hmac.new(SECRET, q.encode(), hashlib.sha256).hexdigest()
    url = f"{base}{path}?{q}&signature={sig}"
    req = urllib.request.Request(url, headers={'X-MBX-APIKEY': KEY})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

def price_usdt(asset):
    if asset == 'USDT':
        return Decimal('1')
    sym = f'{asset}USDT'
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={sym}'
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read().decode())
            p = Decimal(str(data['price']))
            return p
    except Exception:
        return None

summary = {
    'spot': [],
    'um': [],
    'cm': [],
    'margin': []
}
unknown = []

# Fetch accounts (graceful on errors)
try:
    spot = signed_get('https://api.binance.com', '/api/v3/account')
    for b in spot.get('balances', []):
        free = Decimal(str(b.get('free','0')))
        locked = Decimal(str(b.get('locked','0')))
        amt = free + locked
        if amt != 0:
            summary['spot'].append({'asset': b['asset'], 'amount': str(amt)})
except Exception:
    pass

try:
    um = signed_get('https://fapi.binance.com', '/fapi/v2/account')
    for a in um.get('assets', []):
        amt = Decimal(str(a.get('walletBalance','0')))
        if amt != 0:
            summary['um'].append({'asset': a['asset'], 'amount': str(amt)})
except Exception:
    pass

try:
    cm = signed_get('https://dapi.binance.com', '/dapi/v1/account')
    for a in cm.get('assets', []):
        amt = Decimal(str(a.get('walletBalance','0')))
        if amt != 0:
            summary['cm'].append({'asset': a['asset'], 'amount': str(amt)})
except Exception:
    pass

try:
    margin = signed_get('https://api.binance.com', '/sapi/v1/margin/account')
    for a in margin.get('userAssets', []):
        amt = Decimal(str(a.get('netAsset','0')))
        if amt != 0:
            summary['margin'].append({'asset': a['asset'], 'amount': str(amt)})
except Exception:
    pass

# Compute USDT values
out = {'spot_usdt':'0', 'um_usdt':'0', 'cm_usdt':'0', 'margin_usdt':'0', 'total_usdt':'0', 'lines': [], 'unknown': []}

def sum_cat(cat):
    total = Decimal('0')
    for it in summary[cat]:
        a = it['asset']
        amt = Decimal(it['amount'])
        p = price_usdt(a)
        if p is None:
            out['unknown'].append({'where': cat, 'asset': a, 'amount': str(amt)})
            continue
        val = (amt * p).quantize(Decimal('0.00000001'))
        total += val
        out['lines'].append({'where': cat, 'asset': a, 'amount': str(amt), 'price': str(p), 'usdt': str(val)})
    return total

s = sum_cat('spot')
u = sum_cat('um')
c = sum_cat('cm')
m = sum_cat('margin')

total = s+u+c+m
out['spot_usdt'] = str(s)
out['um_usdt'] = str(u)
out['cm_usdt'] = str(c)
out['margin_usdt'] = str(m)
out['total_usdt'] = str(total)

print(json.dumps(out))
