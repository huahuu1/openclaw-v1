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


def compute_pnl_points(side, entry, current):
    return (current - entry) if side == 'LONG' else (entry - current)


def compute_unrealized_usdt(side, entry, current, qty):
    pnl_points = compute_pnl_points(side, entry, current)
    return pnl_points * qty


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


def tp1_reached(side, current, tp1):
    return current >= tp1 if side == 'LONG' else current <= tp1


def tp2_reached(side, current, tp2):
    return current >= tp2 if side == 'LONG' else current <= tp2


def stop_reached(side, current, stop):
    return current <= stop if side == 'LONG' else current >= stop


def append_journal(event):
    with JOURNAL.open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')


def finalize_trade(trade, current, final_status, capital):
    trade['status'] = final_status
    trade['closed_at'] = int(time.time())
    trade['close_price'] = round(current, 6)
    realized_usdt = float(trade.get('realized_usdt_partial', 0.0))
    if final_status == 'TP2_HIT':
        remaining_qty = float(trade['qty']) * 0.5
        realized_usdt += compute_unrealized_usdt(trade['side'], float(trade['entry']), current, remaining_qty)
        trade['realized_r'] = round(float(trade.get('realized_r_partial', 0.0)) + 1.0, 4)
    elif final_status == 'STOPPED':
        realized_usdt = -float(trade['risk_amount_usdt'])
        trade['realized_r'] = -1.0
    elif final_status == 'BREAKEVEN':
        trade['realized_r'] = round(float(trade.get('realized_r_partial', 0.0)), 4)
    else:
        trade['realized_r'] = round(float(trade.get('realized_r_partial', 0.0)), 4)

    trade['realized_usdt'] = round(realized_usdt, 4)
    trade['realized_profit_pct_on_capital'] = round(compute_profit_pct_on_capital(realized_usdt, capital), 4)
    trade['unrealized_usdt'] = 0.0
    trade['profit_pct_on_capital_live'] = 0.0

    append_journal({
        'ts': int(time.time()),
        'event': 'trade_closed',
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


def main():
    state = load_state()
    capital = float(state['account']['starting_capital_usdt'])
    trades = state.get('trades', [])
    if not trades:
        print(json.dumps({'ok': False, 'reason': 'no_trades'}, ensure_ascii=False))
        return

    changed = []
    snapshots = []
    for t in trades:
        current = float(http_get('/fapi/v1/ticker/price', {'symbol': t['symbol']})['price'])
        risk_ref = float(t.get('initial_stop', t['stop']))
        qty = float(t.get('qty', 0.0))
        pnl_points = compute_pnl_points(t['side'], float(t['entry']), current)
        unrealized_usdt_full = compute_unrealized_usdt(t['side'], float(t['entry']), current, qty)
        r_mult = compute_r_multiple(t['side'], float(t['entry']), risk_ref, current)
        mfe = max(float(t.get('max_favorable_excursion', 0.0)), r_mult)
        mae = min(float(t.get('max_adverse_excursion', 0.0)), r_mult)
        t['max_favorable_excursion'] = round(mfe, 4)
        t['max_adverse_excursion'] = round(mae, 4)

        prev = t['status']
        if prev == 'OPEN':
            if (not t.get('tp1_hit')) and tp1_reached(t['side'], current, float(t['tp1'])):
                t['tp1_hit'] = True
                t['break_even_armed'] = True
                t['realized_r_partial'] = 0.5
                partial_qty = qty * 0.5
                partial_realized = compute_unrealized_usdt(t['side'], float(t['entry']), current, partial_qty)
                t['realized_usdt_partial'] = round(partial_realized, 4)
                t['stop'] = t['entry']
                note = f"TP1 hit at {round(current, 6)}; moved stop to breakeven"
                t.setdefault('notes', []).append(note)
                append_journal({
                    'ts': int(time.time()),
                    'event': 'tp1_hit',
                    'id': t['id'],
                    'symbol': t['symbol'],
                    'side': t['side'],
                    'price': round(current, 6),
                    'realized_usdt_partial': t['realized_usdt_partial'],
                    'realized_profit_pct_on_capital': round(compute_profit_pct_on_capital(partial_realized, capital), 4),
                    'new_stop': t['stop']
                })
                changed.append({'id': t['id'], 'from': prev, 'to': 'TP1_ARMED'})

            if tp2_reached(t['side'], current, float(t['tp2'])):
                finalize_trade(t, current, 'TP2_HIT', capital)
                changed.append({'id': t['id'], 'from': prev, 'to': 'TP2_HIT'})
            elif stop_reached(t['side'], current, float(t['stop'])):
                final_status = 'BREAKEVEN' if t.get('tp1_hit') else 'STOPPED'
                finalize_trade(t, current, final_status, capital)
                changed.append({'id': t['id'], 'from': prev, 'to': final_status})

        open_qty = qty * (0.5 if t.get('tp1_hit') and t['status'] == 'OPEN' else 1.0)
        live_unrealized_usdt = compute_unrealized_usdt(t['side'], float(t['entry']), current, open_qty) if t['status'] == 'OPEN' else 0.0
        live_profit_pct_on_capital = compute_profit_pct_on_capital(live_unrealized_usdt, capital) if t['status'] == 'OPEN' else 0.0
        t['unrealized_usdt'] = round(live_unrealized_usdt, 4)
        t['profit_pct_on_capital_live'] = round(live_profit_pct_on_capital, 4)

        snapshots.append({
            'id': t['id'],
            'symbol': t['symbol'],
            'side': t['side'],
            'status': t['status'],
            'entry': t['entry'],
            'current': round(current, 6),
            'qty': round(qty, 8),
            'risk_amount_usdt': t.get('risk_amount_usdt', 0.0),
            'stop': t['stop'],
            'initial_stop': t.get('initial_stop', t['stop']),
            'tp1': t['tp1'],
            'tp2': t['tp2'],
            'tp1_hit': t.get('tp1_hit', False),
            'pnl_points': round(pnl_points, 6),
            'unrealized_usdt': round(live_unrealized_usdt, 4),
            'profit_pct_on_capital_live': round(live_profit_pct_on_capital, 4),
            'r_multiple_live': round(r_mult, 4),
            'realized_r': round(float(t.get('realized_r_partial', 0.0)), 4) if t['status'] == 'OPEN' else round(float(t.get('realized_r', 0.0)), 4),
            'realized_usdt': round(float(t.get('realized_usdt_partial', 0.0)), 4) if t['status'] == 'OPEN' else round(float(t.get('realized_usdt', 0.0)), 4),
            'realized_profit_pct_on_capital': round(compute_profit_pct_on_capital(float(t.get('realized_usdt_partial', 0.0)), capital), 4) if t['status'] == 'OPEN' else round(float(t.get('realized_profit_pct_on_capital', 0.0)), 4),
            'mfe_r': t['max_favorable_excursion'],
            'mae_r': t['max_adverse_excursion'],
        })
    save_state(state)
    print(json.dumps({'ok': True, 'account': state['account'], 'trades': snapshots, 'changed': changed}, ensure_ascii=False))


if __name__ == '__main__':
    main()
