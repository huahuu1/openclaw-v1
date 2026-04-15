import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path('/home/node/.openclaw/workspace')
SCAN = ROOT / 'vn_stock_scan.py'
NEWS = ROOT / 'vn_stock_news.py'

MARKET_NEWS_QUERIES = [
    'VN-Index chứng khoán',
    'thị trường chứng khoán Việt Nam',
    'VN-Index ngân hàng bất động sản chứng khoán',
]


def run_json(cmd):
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)


def score_market_news(limit_per_query=4, keep=8):
    sys.path.insert(0, str(ROOT))
    import vn_stock_news as news_mod

    merged = []
    seen = set()
    for query in MARKET_NEWS_QUERIES:
        items = news_mod.parse_google_news_rss(query, limit=limit_per_query)
        for it in items:
            key = (it.get('title') or '').strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            age = news_mod.hours_ago(it.get('pubDate'))
            sc, hits, freshness = news_mod.score_headline(
                it.get('title', ''),
                (it.get('link', '') + ' ' + it.get('source', '')),
                age,
            )
            merged.append({
                **it,
                'age_hours': round(age, 1) if age is not None else None,
                'score': sc,
                'hits': hits,
                'summary': news_mod.tom_tat_tieu_de(it.get('title', '')),
                'nguon_hien_thi': it.get('source') or '',
                'duong_dan_goc': it.get('link') or '',
                'diem_uu_tien_nguon': news_mod.diem_uu_tien_nguon(it.get('source')),
                'freshness': freshness,
                'impact_level': news_mod.impact_from_score(sc),
                'news_type': news_mod.classify_news_type(it.get('title', '')),
            })
    merged.sort(key=lambda x: (x.get('freshness') == 'fresh', x.get('diem_uu_tien_nguon', 0), x.get('score', 0), -(x.get('age_hours') or 9999)), reverse=True)
    total = sum(x.get('score', 0) for x in merged)
    trend = news_mod.danh_gia_xu_the_tin(merged, total)
    return {
        'query_set': MARKET_NEWS_QUERIES,
        'news_score': total,
        'verdict': 'positive' if total >= 5 else 'negative' if total <= -5 else 'neutral',
        'items': merged[:keep],
        **trend,
    }


def pick_symbols(scan_payload, top, watch_limit=None):
    proposals = scan_payload.get('proposals', [])
    watch = scan_payload.get('watch', [])
    picked = []
    seen = set()
    watch_limit = top if watch_limit is None else watch_limit

    for item in proposals[:top]:
        symbol = item.get('symbol')
        if symbol and symbol not in seen:
            seen.add(symbol)
            picked.append(symbol)

    for item in watch[:watch_limit]:
        symbol = item.get('symbol')
        if symbol and symbol not in seen:
            seen.add(symbol)
            picked.append(symbol)

    return picked


def tier_symbols(scan_payload):
    buy_now = []
    wait_pullback = []
    observe_only = []

    for item in scan_payload.get('proposals', []):
        notes = set(item.get('notes', []))
        risk = item.get('risk_pct_to_stop') or 999
        score = item.get('score', 0)
        if 'extended' in notes or 'avoid_chasing' in notes or 'near_20d_breakout' in notes or risk > 4.0:
            wait_pullback.append(item)
        elif score >= 12 and risk <= 3.8:
            buy_now.append(item)
        else:
            wait_pullback.append(item)

    for item in scan_payload.get('watch', []):
        observe_only.append(item)

    return {
        'mua_duoc_ngay': buy_now,
        'cho_dieu_chinh': wait_pullback,
        'chi_quan_sat': observe_only,
    }


def compact_news_lines(news_payload, topn=3):
    lines = []
    for it in (news_payload or {}).get('tin_tom_tat', [])[:topn]:
        title = it.get('tieu_de') or it.get('tom_tat') or ''
        source = it.get('nguon') or ''
        hours = it.get('so_gio_truoc')
        hours_text = f"{hours:.1f}h" if isinstance(hours, (int, float)) else 'n/a'
        link = it.get('duong_dan') or ''
        lines.append(f"{title} | {source} | {hours_text} | {link}")
    return lines


def has_usable_news(news_payload):
    if not news_payload:
        return False
    return bool(news_payload.get('tin_tom_tat') or news_payload.get('items'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['core', 'broad'], default='broad')
    parser.add_argument('--top', type=int, default=6)
    parser.add_argument('--news-top', type=int, default=8)
    parser.add_argument('--watch-top', type=int, default=6)
    parser.add_argument('--breadth-mode', choices=['core', 'broad', 'auto'], default='broad')
    parser.add_argument('--compact', action='store_true')
    parser.add_argument('symbols', nargs='*')
    args = parser.parse_args()

    scan_cmd = ['python3', str(SCAN), '--top', str(args.top), '--mode', args.mode, '--breadth-mode', args.breadth_mode]
    if args.compact:
        scan_cmd.append('--compact')
    if args.symbols:
        scan_cmd.extend(args.symbols)

    scan_payload = run_json(scan_cmd)
    if args.compact:
        out = {'scan': scan_payload, 'market_news': score_market_news(), 'news': {}}
        print(json.dumps(out, ensure_ascii=False))
        return

    symbols = pick_symbols(scan_payload, args.news_top, watch_limit=args.watch_top)
    news_payload = run_json(['python3', str(NEWS), *symbols, '--limit', '6']) if symbols else {'results': []}
    market_news = score_market_news()
    tiers = tier_symbols(scan_payload)

    news_by_symbol = {item.get('symbol'): item for item in news_payload.get('results', [])}

    out = {
        'ts': scan_payload.get('ts'),
        'scan_mode': args.mode,
        'breadth_mode': args.breadth_mode,
        'market_context': scan_payload.get('market_context'),
        'market_news': market_news,
        'breadth': scan_payload.get('breadth'),
        'breadth_extended': scan_payload.get('breadth_extended'),
        'sector_strength': scan_payload.get('sector_strength'),
        'tiers': {
            'mua_duoc_ngay': [x.get('symbol') for x in tiers['mua_duoc_ngay'][:args.top]],
            'cho_dieu_chinh': [x.get('symbol') for x in tiers['cho_dieu_chinh'][:args.top]],
            'chi_quan_sat': [x.get('symbol') for x in tiers['chi_quan_sat'][:args.watch_top]],
        },
        'symbols': [],
        'errors': scan_payload.get('errors', []),
    }

    filtered_buy = [x for x in tiers['mua_duoc_ngay'] if x.get('symbol') in out['tiers']['mua_duoc_ngay']]
    filtered_wait = [x for x in tiers['cho_dieu_chinh'] if x.get('symbol') in out['tiers']['cho_dieu_chinh']]
    filtered_watch = [x for x in tiers['chi_quan_sat'] if x.get('symbol') in out['tiers']['chi_quan_sat']]

    ordered = filtered_buy + filtered_wait + filtered_watch
    seen = set()
    for item in ordered:
        symbol = item.get('symbol')
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        news = news_by_symbol.get(symbol, {})
        news_lines = compact_news_lines(news)
        if item in filtered_watch and not has_usable_news(news):
            continue
        out['symbols'].append({
            'symbol': symbol,
            'tier': 'mua_duoc_ngay' if symbol in out['tiers']['mua_duoc_ngay'] else 'cho_dieu_chinh' if symbol in out['tiers']['cho_dieu_chinh'] else 'chi_quan_sat',
            'technical': item,
            'news': news,
            'nguon_doc_nhanh': news_lines,
        })

    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
