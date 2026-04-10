import json
from pathlib import Path
from statistics import mean

STATE = Path('/Users/huuht/.openclaw/workspace/paper_trades.json')
JOURNAL = Path('/Users/huuht/.openclaw/workspace/paper_trade_journal.jsonl')
DEFAULT_ACCOUNT = {
    'starting_capital_usdt': 1000.0,
    'risk_per_trade_pct': 1.0
}


def load_state():
    if STATE.exists():
        data = json.loads(STATE.read_text())
        data.setdefault('account', DEFAULT_ACCOUNT.copy())
        data.setdefault('trades', [])
        return data
    return {'account': DEFAULT_ACCOUNT.copy(), 'trades': []}


def realized_r(trade):
    if trade.get('status') in ('TP2_HIT', 'STOPPED', 'BREAKEVEN', 'MANUAL_CLOSED'):
        return float(trade.get('realized_r', 0.0))
    return None


def realized_usdt(trade):
    if trade.get('status') in ('TP2_HIT', 'STOPPED', 'BREAKEVEN', 'MANUAL_CLOSED'):
        return float(trade.get('realized_usdt', 0.0))
    return None


def load_journal_count():
    if not JOURNAL.exists():
        return 0
    return sum(1 for _ in JOURNAL.open('r', encoding='utf-8'))


def summarize_bucket(trades, capital):
    closed = [t for t in trades if t.get('status') in ('TP2_HIT', 'STOPPED', 'BREAKEVEN', 'MANUAL_CLOSED')]
    tp2 = [t for t in closed if t.get('status') == 'TP2_HIT']
    stopped = [t for t in closed if t.get('status') == 'STOPPED']
    breakeven = [t for t in closed if t.get('status') == 'BREAKEVEN']
    manual_closed = [t for t in closed if t.get('status') == 'MANUAL_CLOSED']
    tp1_hit = [t for t in trades if t.get('tp1_hit')]
    r_values = [realized_r(t) for t in closed if realized_r(t) is not None]
    usdt_values = [realized_usdt(t) for t in closed if realized_usdt(t) is not None]
    unrealized_open = [float(t.get('unrealized_usdt', 0.0)) for t in trades if t.get('status') == 'OPEN']
    return {
        'count': len(trades),
        'closed': len(closed),
        'tp1_hit_count': len(tp1_hit),
        'tp2_hits': len(tp2),
        'stopped': len(stopped),
        'breakeven': len(breakeven),
        'winrate_pct': round((len(tp2) / len(closed) * 100) if closed else 0.0, 2),
        'avg_r': round(mean(r_values) if r_values else 0.0, 4),
        'realized_usdt': round(sum(usdt_values), 4),
        'unrealized_usdt': round(sum(unrealized_open), 4),
        'return_pct_on_capital': round((sum(usdt_values) / capital * 100) if capital else 0.0, 4),
    }


def main():
    state = load_state()
    capital = float(state['account']['starting_capital_usdt'])
    trades = state.get('trades', [])
    closed = [t for t in trades if t.get('status') in ('TP2_HIT', 'STOPPED', 'BREAKEVEN', 'MANUAL_CLOSED')]
    open_trades = [t for t in trades if t.get('status') == 'OPEN']

    tp2 = [t for t in closed if t.get('status') == 'TP2_HIT']
    stopped = [t for t in closed if t.get('status') == 'STOPPED']
    breakeven = [t for t in closed if t.get('status') == 'BREAKEVEN']
    manual_closed = [t for t in closed if t.get('status') == 'MANUAL_CLOSED']
    tp1_hit_all = [t for t in trades if t.get('tp1_hit')]
    r_values = [realized_r(t) for t in closed if realized_r(t) is not None]
    usdt_values = [realized_usdt(t) for t in closed if realized_usdt(t) is not None]
    unrealized_values = [float(t.get('unrealized_usdt', 0.0)) for t in open_trades]
    mfe_values = [float(t.get('max_favorable_excursion', 0.0)) for t in closed]
    mae_values = [float(t.get('max_adverse_excursion', 0.0)) for t in closed]

    by_symbol = {}
    by_side = {'LONG': [], 'SHORT': []}
    by_regime = {}
    for t in trades:
        by_symbol.setdefault(t.get('symbol', 'UNKNOWN'), []).append(t)
        if t.get('side') in by_side:
            by_side[t['side']].append(t)
        rg = t.get('market_regime_at_open', 'unknown')
        by_regime.setdefault(rg, []).append(t)

    symbol_stats = []
    for sym, bucket in by_symbol.items():
        base = summarize_bucket(bucket, capital)
        base['symbol'] = sym
        symbol_stats.append(base)
    symbol_stats.sort(key=lambda x: (x['return_pct_on_capital'], x['closed'], x['count']), reverse=True)

    side_stats = {side: summarize_bucket(bucket, capital) for side, bucket in by_side.items()}
    regime_stats = {rg: summarize_bucket(bucket, capital) for rg, bucket in by_regime.items()}

    total_realized_usdt = round(sum(usdt_values), 4)
    total_realized_return_pct = round((total_realized_usdt / capital * 100) if capital else 0.0, 4)
    total_unrealized_usdt = round(sum(unrealized_values), 4)
    total_unrealized_return_pct = round((total_unrealized_usdt / capital * 100) if capital else 0.0, 4)
    total_equity_usdt = round(capital + total_realized_usdt + total_unrealized_usdt, 4)
    total_equity_return_pct = round(((total_equity_usdt - capital) / capital * 100) if capital else 0.0, 4)

    review = {
        'principle': 'Nếu có lời thì để lời nhiều hơn, nếu có lỗ thì cắt lỗ ít hơn.',
        'account': state['account'],
        'starting_capital_usdt': capital,
        'equity_usdt': total_equity_usdt,
        'total_trades': len(trades),
        'open_trades': len(open_trades),
        'closed_trades': len(closed),
        'tp1_hit_count': len(tp1_hit_all),
        'tp2_hits': len(tp2),
        'stopped': len(stopped),
        'breakeven': len(breakeven),
        'manual_closed': len(manual_closed),
        'winrate_pct': round((len(tp2) / len(closed) * 100) if closed else 0.0, 2),
        'avg_r': round(mean(r_values) if r_values else 0.0, 4),
        'expectancy_r': round(mean(r_values) if r_values else 0.0, 4),
        'total_realized_usdt': total_realized_usdt,
        'total_realized_return_pct_on_capital': total_realized_return_pct,
        'total_unrealized_usdt': total_unrealized_usdt,
        'total_unrealized_return_pct_on_capital': total_unrealized_return_pct,
        'total_equity_return_pct_on_capital': total_equity_return_pct,
        'avg_mfe_r': round(mean(mfe_values), 4) if mfe_values else 0.0,
        'avg_mae_r': round(mean(mae_values), 4) if mae_values else 0.0,
        'journal_events': load_journal_count(),
        'by_symbol': symbol_stats,
        'by_side': side_stats,
        'by_regime_at_open': regime_stats,
        'open_symbols': [t['symbol'] for t in open_trades],
        'latest_open': open_trades[-1] if open_trades else None,
        'notes': [
            'All returns are now also tracked against paper starting capital.',
            'TP1 realizes partial USDT profit on 50% size, then stop moves to breakeven.',
            'TP2 adds remaining profit for total asymmetric payoff.',
            'Portfolio equity now includes both realized and unrealized PnL.'
        ]
    }
    print(json.dumps(review, ensure_ascii=False))


if __name__ == '__main__':
    main()
