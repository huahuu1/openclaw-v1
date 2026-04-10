import json, time, hmac, hashlib, urllib.parse, urllib.request
from decimal import Decimal

with open('/Users/huuht/.openclaw/credentials/binance.json') as f:
    creds = json.load(f)
KEY = creds['apiKey']
SECRET = creds['secretKey'].encode()

BASE_API = 'https://api.binance.com'
BASE_UM = 'https://fapi.binance.com'

hdr = {'X-MBX-APIKEY': KEY}

def ts_ms():
    return str(int(time.time()*1000))

def signed_req(method, base, path, params=None):
    if params is None:
        params = {}
    params.update({'timestamp': ts_ms(), 'recvWindow': '5000'})
    q = urllib.parse.urlencode(params)
    sig = hmac.new(SECRET, q.encode(), hashlib.sha256).hexdigest()
    url = f"{base}{path}?{q}&signature={sig}"
    req = urllib.request.Request(url, headers=hdr, method=method)
    if method == 'POST':
        body = q + '&signature=' + sig  # Binance accepts query or body; keep empty body for urllib
        req = urllib.request.Request(f"{base}{path}", data=(q+'&signature='+sig).encode(), headers=hdr, method='POST')
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

# Get spot USDT free
spot = signed_req('GET', BASE_API, '/api/v3/account')
free_usdt = Decimal('0')
for b in spot.get('balances', []):
    if b.get('asset') == 'USDT':
        free_usdt = Decimal(str(b.get('free', '0')))
        break

# Get UM futures USDT before
um_before = Decimal('0')
um_acc = signed_req('GET', BASE_UM, '/fapi/v2/account')
for a in um_acc.get('assets', []):
    if a.get('asset') == 'USDT':
        um_before = Decimal(str(a.get('walletBalance','0')))
        break

result = { 'attempted': False, 'transferred': '0', 'free_spot_usdt': str(free_usdt), 'um_before': str(um_before) }

if free_usdt > 0:
    # Attempt transfer
    params = {
        'type': 'MAIN_UMFUTURE',
        'asset': 'USDT',
        'amount': str(free_usdt)
    }
    try:
        res = signed_req('POST', BASE_API, '/sapi/v1/asset/transfer', params)
        result['attempted'] = True
        result['api_response'] = res
        # Fetch after
        um_after_acc = signed_req('GET', BASE_UM, '/fapi/v2/account')
        um_after = Decimal('0')
        for a in um_after_acc.get('assets', []):
            if a.get('asset') == 'USDT':
                um_after = Decimal(str(a.get('walletBalance','0')))
                break
        result['um_after'] = str(um_after)
        result['transferred'] = str(um_after - um_before)
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
        except Exception:
            err = {'code': e.code, 'msg': e.reason}
        result['attempted'] = True
        result['error'] = err
    except Exception as e:
        result['attempted'] = True
        result['error'] = {'msg': str(e)}
else:
    result['note'] = 'No free USDT in Spot to transfer.'

print(json.dumps(result))
