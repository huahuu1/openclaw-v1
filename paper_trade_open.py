import json
import time
import urllib.request
from pathlib import Path
import subprocess

BASE = 'https://fapi.binance.com'
STATE = Path('/Users/huuht/.openclaw/workspace/paper_trades.json')
SCAN_CMD = '/Users/huuht/.openclaw/workspace/semi_auto_scan.py'
BASE_MAX_OPEN_TRADES = 5
MAX_PER_SIDE = 3
MAX_ALT_EXPOSURE_PER_SIDE = 2
MAJOR_SYMBOLS = {'BTCUSDT', 'ETHUSDT'}
DEFAULT_ACCOUNT = {
    'starting_capital_usdt': 1000.0,
    'risk_per_trade_pct': 1.0,
    'fixed_leverage': 5.0
}


def http_get(path, params=None):
    if params:
        qs = '?' + '&'.join(f'{k}={v}' for k, v in params.items())
    else:
        qs = ''
    with urllib.request.urlopen(BASE + path + qs, timeout=12) as r:
        return json.loads(r.read().decode())


def load_state():
    if STATE.exists():
        data = json.loads(STATE.read_text())
        data.setdefault('account', DEFAULT_ACCOUNT.copy())
        data['account'].setdefault('fixed_leverage', DEFAULT_ACCOUNT['fixed_leverage'])
        data.setdefault('trades', [])
        return data
    return {'account': DEFAULT_ACCOUNT.copy(), 'trades': []}


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def load_scan():
    out = subprocess.check_output(['python3', SCAN_CMD], text=True)
    return json.loads(out)


def current_open_trades(state):
    return [t for t in state['trades'] if t.get('status') == 'OPEN']


def side_counts(open_trades):
    counts = {'LONG': 0, 'SHORT': 0}
    alt_counts = {'LONG': 0, 'SHORT': 0}
    for t in open_trades:
        side = t['side']
        counts[side] += 1
        if t['symbol'] not in MAJOR_SYMBOLS:
            alt_counts[side] += 1
    return counts, alt_counts


def max_open_by_regime(regime):
    if regime == 'mixed':
        return 2
    return BASE_MAX_OPEN_TRADES


def allowed_side_for_regime(regime):
    if regime == 'bullish':
        return 'LONG'
    if regime == 'bearish':
        return 'SHORT'
    return None


def signal_allowed(signal, regime, open_symbols, counts, alt_counts):
    side = signal['side']
    symbol = signal['symbol']
    wanted_side = allowed_side_for_regime(regime)
    if wanted_side and side != wanted_side:
        return False
    if regime == 'mixed' and signal['score'] < 9:
        return False
    if symbol in open_symbols:
        return False
    if counts[side] >= MAX_PER_SIDE:
        return False
    if symbol not in MAJOR_SYMBOLS and alt_counts[side] >= MAX_ALT_EXPOSURE_PER_SIDE:
        return False
    return True


def build_trade(signal, regime, account):
    ticker = http_get('/fapi/v1/ticker/price', {'symbol': signal['symbol']})
    entry = float(ticker['price'])
    stop = float(signal['stop'])
    tp1 = float(signal['tp1'])
    tp2 = float(signal['tp2'])
    side = signal['side']
    risk_per_unit = abs(entry - stop)
    if risk_per_unit <= 0:
        return None

    starting_capital = float(account['starting_capital_usdt'])
    risk_pct = float(account['risk_per_trade_pct'])
    leverage = float(account.get('fixed_leverage', 5.0))
    risk_amount = starting_capital * risk_pct / 100.0
    qty = risk_amount / risk_per_unit
    notional = qty * entry
    margin_used = notional / leverage if leverage else notional

    return {
        'id': f"paper-{signal['symbol']}-{int(time.time())}",
        'opened_at': int(time.time()),
        'symbol': signal['symbol'],
        'side': side,
        'entry': round(entry, 6),
        'initial_stop': round(stop, 6),
        'stop': round(stop, 6),
        'tp1': round(tp1, 6),
        'tp2': round(tp2, 6),
        'score': signal['score'],
        'rr': signal['rr'],
        'thesis': signal['thesis'],
        'source': 'semi_auto_scan_v1',
        'market_regime_at_open': regime,
        'status': 'OPEN',
        'tp1_hit': False,
        'break_even_armed': False,
        'realized_r_partial': 0.0,
        'realized_usdt_partial': 0.0,
        'realized_profit_pct_on_capital': 0.0,
        'risk_amount_usdt': round(risk_amount, 6),
        'fixed_leverage': leverage,
        'qty': round(qty, 8),
        'notional_usdt': round(notional, 6),
        'margin_used_usdt': round(margin_used, 6),
        'max_favorable_excursion': 0.0,
        'max_adverse_excursion': 0.0,
        'notes': []
    }


def main():
    state = load_state()
    account = state['account']
    open_trades = current_open_trades(state)
    open_symbols = {t['symbol'] for t in open_trades}

    scan = load_scan()
    regime = scan.get('market_regime', 'unknown')
    max_open = max_open_by_regime(regime)
    remaining_slots = max_open - len(open_trades)

    if remaining_slots <= 0:
        print(json.dumps({'ok': False, 'reason': 'max_open_reached', 'open_count': len(open_trades), 'max_open_trades': max_open, 'market_regime': regime}, ensure_ascii=False))
        return

    counts, alt_counts = side_counts(open_trades)
    proposals = scan.get('proposals', [])
    selected = []

    for p in proposals:
        if not signal_allowed(p, regime, open_symbols, counts, alt_counts):
            continue
        trade = build_trade(p, regime, account)
        if trade:
            selected.append(trade)
            open_symbols.add(trade['symbol'])
            counts[trade['side']] += 1
            if trade['symbol'] not in MAJOR_SYMBOLS:
                alt_counts[trade['side']] += 1
        if len(selected) >= remaining_slots:
            break

    if not selected:
        print(json.dumps({'ok': False, 'reason': 'no_new_signal', 'market_regime': regime, 'open_side_counts': counts, 'open_alt_counts': alt_counts}, ensure_ascii=False))
        return

    state['trades'].extend(selected)
    save_state(state)
    print(json.dumps({
        'ok': True,
        'account': account,
        'opened': selected,
        'opened_count': len(selected),
        'open_count_after': len(current_open_trades(state)),
        'market_regime': regime,
        'risk_principle': 'cut losers, let winners run'
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
