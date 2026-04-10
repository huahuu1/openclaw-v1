import json
import time
import urllib.request
from pathlib import Path

BASE = 'https://fapi.binance.com'
STATE = Path('/Users/huuht/.openclaw/workspace/paper_trades.json')
JOURNAL = Path('/Users/huuht/.openclaw/workspace/paper_trade_journal.jsonl')
DEFAULT_ACCOUNT = {
    'starting_capital_usdt': 1000.0,
    'risk_per_trade_pct': 1.0
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
        data.setdefault('trades', [])
        return data
    return {'account': DEFAULT_ACCOUNT.copy(), 'trades': []}


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def append_journal(event):
    with JOURNAL.open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')


def compute_pnl_points(side, entry, current):
    return (current - entry) if side == 'LONG' else (entry - current)


def compute_unrealized_usdt(side, entry, current, qty):
    return compute_pnl_points(side, entry, current) * qty


def compute_profit_pct_on_capital(pnl_usdt, capital):
    if capital == 0:
        return 0.0
    return (pnl_usdt / capital) * 100


def compute_r_multiple(side, entry, stop_ref, current):
    risk = abs(entry - stop_ref)
    if risk <= 0:
        return 0.0
    pnl = compute_pnl_points(side, entry, current)
    return pnl / risk


def close_trade(trade, current, capital):
    qty = float(trade.get('qty', 0.0))
    entry = float(trade['entry'])
    side = trade['side']
    open_qty = qty * (0.5 if trade.get('tp1_hit') else 1.0)
    realized_usdt = float(trade.get('realized_usdt_partial', 0.0)) + compute_unrealized_usdt(side, entry, current, open_qty)
    risk_ref = float(trade.get('initial_stop', trade['stop']))
    realized_r = float(trade.get('realized_r_partial', 0.0)) + compute_r_multiple(side, entry, risk_ref, current) * (0.5 if trade.get('tp1_hit') else 1.0)

    trade['status'] = 'MANUAL_CLOSED'
    trade['closed_at'] = int(time.time())
    trade['close_price'] = round(current, 6)
    trade['realized_r'] = round(realized_r, 4)
    trade['realized_usdt'] = round(realized_usdt, 4)
    trade['realized_profit_pct_on_capital'] = round(compute_profit_pct_on_capital(realized_usdt, capital), 4)
    trade['unrealized_usdt'] = 0.0
    trade['profit_pct_on_capital_live'] = 0.0
    trade.setdefault('notes', []).append(f"Manually closed at {round(current, 6)}")

    append_journal({
        'ts': int(time.time()),
        'event': 'trade_manual_closed',
        'id': trade['id'],
        'symbol': trade['symbol'],
        'side': trade['side'],
        'status': trade['status'],
        'entry': trade['entry'],
        'close_price': trade['close_price'],
        'qty': trade['qty'],
        'initial_stop': trade.get('initial_stop', trade['stop']),
        'tp1': trade['tp1'],
        'tp2': trade['tp2'],
        'tp1_hit': trade.get('tp1_hit', False),
        'realized_r': trade['realized_r'],
        'realized_usdt': trade['realized_usdt'],
        'realized_profit_pct_on_capital': trade['realized_profit_pct_on_capital'],
        'mfe_r': trade.get('max_favorable_excursion', 0.0),
        'mae_r': trade.get('max_adverse_excursion', 0.0),
        'thesis': trade.get('thesis')
    })

    return {
        'id': trade['id'],
        'symbol': trade['symbol'],
        'side': trade['side'],
        'close_price': trade['close_price'],
        'realized_usdt': trade['realized_usdt'],
        'realized_profit_pct_on_capital': trade['realized_profit_pct_on_capital'],
        'realized_r': trade['realized_r']
    }


def main():
    state = load_state()
    capital = float(state['account']['starting_capital_usdt'])
    trades = state.get('trades', [])
    open_trades = [t for t in trades if t.get('status') == 'OPEN']

    if not open_trades:
        print(json.dumps({'ok': True, 'closed_count': 0, 'closed': []}, ensure_ascii=False))
        return

    closed = []
    for t in open_trades:
        current = float(http_get('/fapi/v1/ticker/price', {'symbol': t['symbol']})['price'])
        closed.append(close_trade(t, current, capital))

    save_state(state)
    print(json.dumps({'ok': True, 'closed_count': len(closed), 'closed': closed}, ensure_ascii=False))


if __name__ == '__main__':
    main()
