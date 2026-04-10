#!/usr/bin/env python3
import json, time, hmac, hashlib, urllib.parse, urllib.request, os
from decimal import Decimal

CRED_PATH = '/Users/huuht/.openclaw/credentials/binance.json'
STATE_PATH = '/Users/huuht/.openclaw/workspace/doge_monitor_state.json'
BASE = 'https://fapi.binance.com'
SYM = 'DOGEUSDT'
SLEEP_SEC = 3

with open(CRED_PATH) as f:
    creds = json.load(f)
KEY = creds['apiKey']
SECRET = creds['secretKey'].encode()
HDR = {'X-MBX-APIKEY': KEY}

def ts_ms():
    return str(int(time.time()*1000))

def signed_get(path, params=None, timeout=12):
    if params is None:
        params = {}
    params.update({'timestamp': ts_ms(), 'recvWindow': '5000'})
    q = urllib.parse.urlencode(params)
    sig = hmac.new(SECRET, q.encode(), hashlib.sha256).hexdigest()
    url = BASE + path + '?' + q + '&signature=' + sig
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

def signed_post(path, params, timeout=12):
    params.update({'timestamp': ts_ms(), 'recvWindow': '5000'})
    q = urllib.parse.urlencode(params)
    sig = hmac.new(SECRET, q.encode(), hashlib.sha256).hexdigest()
    data = (q + '&signature=' + sig).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=HDR, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

def mark_price():
    with urllib.request.urlopen(BASE + '/fapi/v1/premiumIndex?symbol=' + SYM, timeout=8) as r:
        return Decimal(str(json.loads(r.read().decode())['markPrice']))

# Initialize state
pos = signed_get('/fapi/v2/positionRisk', {'symbol': SYM})[0]
entry = Decimal(pos['entryPrice']) if Decimal(pos['positionAmt']) != 0 else None
if entry is None:
    print('NO_POSITION')
    raise SystemExit(0)
# Use fixed SL from earlier plan
sl0 = Decimal('0.09626')
R = sl0 - entry  # short
r1 = entry - R
state = {'hit_r1': False, 'entry': str(entry), 'sl_current': str(sl0), 'r1': str(r1)}
# Load previous if exists
if os.path.exists(STATE_PATH):
    try:
        prev = json.load(open(STATE_PATH))
        # keep previous hit_r1 or sl_current if consistent with current entry
        if Decimal(prev.get('entry','0')) == entry:
            state['hit_r1'] = prev.get('hit_r1', False)
            state['sl_current'] = prev.get('sl_current', str(sl0))
    except Exception:
        pass

json.dump(state, open(STATE_PATH, 'w'))
print(json.dumps({'monitor':'started','entry':str(entry),'sl0':str(sl0),'r1':str(r1)}))

while True:
    # Refresh position
    pos = signed_get('/fapi/v2/positionRisk', {'symbol': SYM})[0]
    amt = Decimal(pos['positionAmt'])
    if amt == 0:
        print('POSITION_CLOSED')
        break
    mp = mark_price()
    entry = Decimal(state['entry'])
    sl_cur = Decimal(state['sl_current'])
    r1 = Decimal(state['r1'])
    # Check 1R hit for short
    if (not state['hit_r1']) and mp <= r1:
        state['hit_r1'] = True
        state['sl_current'] = str(entry)  # move SL to breakeven logically
        json.dump(state, open(STATE_PATH, 'w'))
        print(json.dumps({'event':'HIT_1R','markPrice':str(mp),'new_sl':'BE'}))
    # Check SL condition
    sl_level = Decimal(state['sl_current'])
    if mp >= sl_level:
        # Close position reduce-only market
        try:
            res = signed_post('/fapi/v1/order', {
                'symbol': SYM,
                'side': 'BUY',
                'type': 'MARKET',
                'reduceOnly': 'true',
                'quantity': str(abs(int(amt)))
            })
            print(json.dumps({'event':'SL_CLOSE','markPrice':str(mp),'order':res}))
            break
        except Exception as e:
            print(json.dumps({'event':'SL_CLOSE_ERROR','error':str(e)}))
    time.sleep(SLEEP_SEC)
