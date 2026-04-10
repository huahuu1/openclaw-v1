import json
import subprocess
from pathlib import Path

STATE = Path('/Users/huuht/.openclaw/workspace/memory/paper_trade_watch_state.json')
WORKDIR = '/Users/huuht/.openclaw/workspace'
R_MILESTONES = [1.0, 0.5, -0.5]
PORTFOLIO_PCT_MILESTONES = [1.0, 0.5, 0.25, -0.25, -0.5, -1.0]
RECAP_THRESHOLD_PCT = 1.0


def load_watch_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {
        'last_changed_ids': [],
        'last_open_ids': [],
        'last_summary': '',
        'milestones': {},
        'portfolio_milestones': [],
        'portfolio_sign': 'flat'
    }


def save_watch_state(data):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def run_json(script):
    out = subprocess.check_output(['python3', script], cwd=WORKDIR, text=True)
    return json.loads(out)


def milestone_crossed(current_r, milestone):
    if milestone > 0:
        return current_r >= milestone
    return current_r <= milestone


def pct_str(v):
    sign = '+' if v > 0 else ''
    return f"{sign}{round(v, 3)}%"


def usdt_str(v):
    sign = '+' if v > 0 else ''
    return f"{sign}{round(v, 2)} USDT"


def sign_of(v, eps=1e-9):
    if v > eps:
        return 'positive'
    if v < -eps:
        return 'negative'
    return 'flat'


def main():
    watch = load_watch_state()
    watch.setdefault('milestones', {})
    watch.setdefault('portfolio_milestones', [])
    watch.setdefault('portfolio_sign', 'flat')

    status = run_json('paper_trade_status.py')
    review = run_json('paper_trade_review.py')

    changed = status.get('changed', [])
    trades = status.get('trades', [])
    open_ids = [t['id'] for t in trades if t['status'] == 'OPEN']
    changed_ids = [c['id'] + ':' + c['to'] for c in changed]

    alerts = []
    if changed_ids and changed_ids != watch.get('last_changed_ids', []):
        lookup = {t['id']: t for t in trades}
        for c in changed:
            t = lookup.get(c['id'])
            if t:
                if c['to'] == 'TP1_ARMED':
                    alerts.append(
                        f"{t['symbol']} {t['side']} -> TP1 hit | realized={usdt_str(float(t.get('realized_usdt', 0)))} ({pct_str(float(t.get('realized_profit_pct_on_capital', 0)))})"
                    )
                else:
                    alerts.append(
                        f"{t['symbol']} {t['side']} -> {c['to']} | realized={usdt_str(float(t.get('realized_usdt', 0)))} ({pct_str(float(t.get('realized_profit_pct_on_capital', 0)))})"
                    )
            else:
                alerts.append(f"{c['id']} -> {c['to']}")

    tp1_open = [t for t in trades if t.get('tp1_hit') and t['status'] == 'OPEN']
    for t in tp1_open:
        marker = f"TP1:{t['id']}"
        if marker not in watch.get('last_changed_ids', []):
            alerts.append(
                f"{t['symbol']} hit TP1, stop moved to BE | realized={usdt_str(float(t.get('realized_usdt', 0)))} ({pct_str(float(t.get('realized_profit_pct_on_capital', 0)))})"
            )

    for t in trades:
        if t['status'] != 'OPEN':
            continue
        tid = t['id']
        current_r = float(t.get('r_multiple_live', 0.0))
        seen = set(watch['milestones'].get(tid, []))
        for m in R_MILESTONES:
            key = str(m)
            if key in seen:
                continue
            if milestone_crossed(current_r, m):
                label = f"+{m}R" if m > 0 else f"{m}R"
                alerts.append(
                    f"{t['symbol']} {t['side']} reached {label} | unrealized={usdt_str(float(t.get('unrealized_usdt', 0)))} ({pct_str(float(t.get('profit_pct_on_capital_live', 0)))})"
                )
                seen.add(key)
        watch['milestones'][tid] = sorted(seen)

    portfolio_pct = float(review.get('total_equity_return_pct_on_capital', 0.0))
    portfolio_seen = set(watch.get('portfolio_milestones', []))
    for m in PORTFOLIO_PCT_MILESTONES:
        key = str(m)
        if key in portfolio_seen:
            continue
        if milestone_crossed(portfolio_pct, m):
            alerts.append(
                f"Portfolio crossed {pct_str(m)} | equity={usdt_str(float(review.get('equity_usdt', 0)))} | totalPnL={usdt_str(float(review.get('total_realized_usdt', 0)) + float(review.get('total_unrealized_usdt', 0)))} ({pct_str(portfolio_pct)})"
            )
            portfolio_seen.add(key)
    watch['portfolio_milestones'] = sorted(portfolio_seen)

    current_sign = sign_of(portfolio_pct)
    prev_sign = watch.get('portfolio_sign', 'flat')
    if current_sign != prev_sign and current_sign != 'flat':
        alerts.append(
            f"Portfolio turned {current_sign} | equity={usdt_str(float(review.get('equity_usdt', 0)))} | totalPnL={usdt_str(float(review.get('total_realized_usdt', 0)) + float(review.get('total_unrealized_usdt', 0)))} ({pct_str(portfolio_pct)})"
        )
    watch['portfolio_sign'] = current_sign

    top_lines = []
    for t in sorted(trades, key=lambda x: float(x.get('profit_pct_on_capital_live', 0)), reverse=True)[:3]:
        if t['status'] == 'OPEN':
            top_lines.append(f"{t['symbol']} {t['side']} {pct_str(float(t.get('profit_pct_on_capital_live', 0)))}")

    summary = (
        f"capital={review.get('starting_capital_usdt', 0)} USDT | "
        f"equity={usdt_str(float(review.get('equity_usdt', 0)))} | "
        f"totalPnL={usdt_str(float(review.get('total_realized_usdt', 0)) + float(review.get('total_unrealized_usdt', 0)))} ({pct_str(float(review.get('total_equity_return_pct_on_capital', 0)))}) | "
        f"open={review.get('open_trades', 0)} | closed={review.get('closed_trades', 0)}"
    )

    if not alerts and open_ids and abs(portfolio_pct) >= RECAP_THRESHOLD_PCT and summary != watch.get('last_summary', ''):
        recap = f"Paper account recap | {summary}"
        if top_lines:
            recap += " | top: " + ", ".join(top_lines)
        alerts.append(recap)

    watch['last_changed_ids'] = changed_ids + [f"TP1:{t['id']}" for t in tp1_open]
    watch['last_open_ids'] = open_ids
    watch['last_summary'] = summary
    save_watch_state(watch)

    if alerts:
        print("Paper trade update:\n- " + "\n- ".join(alerts) + f"\nSummary: {summary}")
        return

    print('HEARTBEAT_OK')


if __name__ == '__main__':
    main()
