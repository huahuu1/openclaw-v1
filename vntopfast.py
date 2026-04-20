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


def fmt_price(x):
    if x is None:
        return 'n/a'
    if abs(x) >= 100:
        return f'{x:.1f}'
    return f'{x:.2f}'.rstrip('0').rstrip('.')


def price_band(low, high):
    return f'{fmt_price(low)} - {fmt_price(high)}'


def build_levels(t):
    close = t.get('close') or 0
    stop = t.get('stop_ref')
    high20 = t.get('high20') or close
    atr = t.get('atr14') or 0
    buy_low = max(stop or close, close - atr * 0.6) if stop else close - atr * 0.6
    buy_high = close
    no_chase = high20 if high20 and high20 > close else close + atr * 0.6
    tp1 = close + atr * 1.0 if atr else close * 1.03
    tp2 = close + atr * 2.0 if atr else close * 1.06
    return {
        'buy_low': round(buy_low, 2),
        'buy_high': round(buy_high, 2),
        'no_chase': round(no_chase, 2),
        'stop': round(stop, 2) if stop is not None else None,
        'tp1': round(tp1, 2),
        'tp2': round(tp2, 2),
    }


def nhan_dinh_ngan(item):
    t = item.get('technical', {})
    notes = set(t.get('notes', []))
    score = t.get('score', 0)
    risk = t.get('risk_pct_to_stop') or 999
    relv = t.get('rel_volume20') or 0
    parts = []
    if score >= 13:
        parts.append('điểm kỹ thuật rất cao')
    elif score >= 10:
        parts.append('cấu trúc kỹ thuật khá mạnh')
    else:
        parts.append('đang giữ trạng thái theo dõi tích cực')
    if relv >= 1.5:
        parts.append('dòng tiền tốt hơn bình thường')
    if 'extended' in notes:
        parts.append('đã hơi kéo nóng')
    if 'avoid_chasing' in notes or 'near_20d_breakout' in notes:
        parts.append('không hợp mua đuổi')
    if risk <= 2.5:
        parts.append('risk đến stop khá thấp')
    elif risk > 4:
        parts.append('risk đến stop tương đối rộng')
    return ', '.join(parts).capitalize() + '.'


def hanh_dong(item):
    tier = item.get('tier')
    t = item.get('technical', {})
    notes = set(t.get('notes', []))
    if tier == 'mua_duoc_ngay':
        if 'm15_not_confirmed' in notes:
            return 'Có thể mua, nhưng ưu tiên canh nhịp thay vì đuổi ngay.'
        return 'Có thể mua theo vị thế thăm dò hoặc gom khi giữ nền.'
    if tier == 'cho_dieu_chinh':
        return 'Ưu tiên chờ nhịp điều chỉnh hoặc nền mới, không mua đuổi.'
    return 'Quan sát thêm, chỉ nâng hạng nếu tín hiệu ngắn hạn xác nhận rõ hơn.'


def catalyst_text(item):
    flag = item.get('catalyst_flag') or 'thieu_catalyst_moi'
    short_score = item.get('news_score_short_term', 0)
    medium_score = item.get('news_score_medium_term', 0)
    if flag == 'co_catalyst_moi':
        return f'Có catalyst mới, nghiêng ngắn hạn tốt hơn (short={short_score}, medium={medium_score}).'
    if flag == 'chi_co_tin_trung_han':
        return f'Chủ yếu còn câu chuyện trung hạn, thiếu catalyst mới cho T+ gần (short={short_score}, medium={medium_score}).'
    return f'Thiếu catalyst mới rõ ràng, không nên dựa vào news để đẩy kỳ vọng ngắn hạn (short={short_score}, medium={medium_score}).'


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
                'is_reference_like': news_mod.is_reference_headline(it.get('title', '')),
            })
    merged.sort(key=lambda x: (x.get('freshness') == 'fresh', x.get('freshness') == 'recent', x.get('diem_uu_tien_nguon', 0), x.get('score', 0), -(x.get('age_hours') or 9999)), reverse=True)
    usable = [
        x for x in merged
        if x.get('freshness') in ('fresh', 'recent', 'aging') and not x.get('is_reference_like')
    ]
    display_items = [
        x for x in usable
        if (x.get('age_hours') is not None and x.get('age_hours') <= 7 * 24)
    ]
    total = sum(x.get('score', 0) for x in usable)
    trend = news_mod.danh_gia_xu_the_tin(usable, total)
    return {
        'query_set': MARKET_NEWS_QUERIES,
        'news_score': total,
        'verdict': 'positive' if total >= 5 else 'negative' if total <= -5 else 'neutral',
        'items': display_items[:keep],
        'news_quality_flag': 'fresh_or_recent' if any(x.get('freshness') in ('fresh', 'recent') for x in usable) else 'aging_only' if usable else 'no_usable_news',
        **trend,
        'tin_ngan_han': trend.get('tin_ngan_han', [])[:3],
        'tin_trung_han': trend.get('tin_trung_han', [])[:3],
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
    return bool(news_payload.get('tin_tom_tat'))


def render_text_report(payload):
    market = payload.get('market_context', {})
    market_news = payload.get('market_news', {})
    tier_map = {'mua_duoc_ngay': [], 'cho_dieu_chinh': [], 'chi_quan_sat': []}
    for item in payload.get('symbols', []):
        tier_map.setdefault(item.get('tier'), []).append(item)

    def section_lines(title, items):
        out = [f'## {title}']
        if not items:
            out.append('- Chưa có mã phù hợp trong nhóm này.')
            out.append('')
            return out
        for item in items:
            symbol = item.get('symbol')
            t = item.get('technical', {})
            lv = build_levels(t)
            out.append(f'### {symbol}')
            out.append(f'- Nhận định ngắn: {nhan_dinh_ngan(item)}')
            out.append(f'- Hành động: {hanh_dong(item)}')
            out.append(f'- Catalyst/tin tức: {catalyst_text(item)}')
            out.append('- Vùng mua / không mua đuổi / dừng lỗ / chốt lời:')
            out.append(f'  - Vùng mua: {price_band(lv["buy_low"], lv["buy_high"])}')
            out.append(f'  - Không mua đuổi: trên {fmt_price(lv["no_chase"])}')
            out.append(f'  - Dừng lỗ: {fmt_price(lv["stop"])}')
            out.append(f'  - Chốt lời: {price_band(lv["tp1"], lv["tp2"])}')
            out.append('- Nguồn đọc nhanh:')
            src = item.get('nguon_doc_nhanh') or []
            if src:
                out.extend([f'  - {x}' for x in src[:3]])
            else:
                out.append('  - Chưa có tin đủ chất lượng để đưa vào block nhanh.')
            out.append('')
        return out

    lines = []
    lines.append('**Bối cảnh thị trường**')
    lines.append(f"- Trạng thái: **{market.get('regime', 'n/a')}** — {market.get('regime_text', '')}")
    lines.append(f"- Độ rộng: tăng/giảm = **{payload.get('breadth_extended', {}).get('advance', 'n/a')} / {payload.get('breadth_extended', {}).get('decline', 'n/a')}**, advance ratio **{market.get('advance_ratio', 'n/a')}**")
    lines.append(f"- Trên EMA20: **{market.get('above_ema20_ratio', 'n/a')}** | Volume mạnh: **{market.get('strong_volume_ratio', 'n/a')}**")
    leaders = ', '.join(market.get('leading_sectors', []) or [])
    if leaders:
        lines.append(f'- Nhóm dẫn dắt: **{leaders}**')
    lines.append('- Tin chung thị trường:')
    market_flag = market_news.get('catalyst_flag') or 'thieu_catalyst_moi'
    if market_flag == 'co_catalyst_moi':
        lines.append('  - Trạng thái catalyst thị trường: có tin mới đáng chú ý.')
    elif market_flag == 'chi_co_tin_trung_han':
        lines.append('  - Trạng thái catalyst thị trường: chủ yếu là tin trung hạn/câu chuyện cũ.')
    else:
        lines.append('  - Trạng thái catalyst thị trường: chưa có tin mới đủ mạnh.')
    market_news_lines = []
    for it in (market_news.get('tin_tom_tat') or [])[:3]:
        title = it.get('tieu_de') or it.get('tom_tat') or ''
        source = it.get('nguon') or ''
        hours = it.get('so_gio_truoc')
        hours_text = f'{hours:.1f}h' if isinstance(hours, (int, float)) else 'n/a'
        link = it.get('duong_dan') or ''
        market_news_lines.append(f'  - {title} | {source} | {hours_text} | {link}')
    if market_news_lines:
        lines.extend(market_news_lines)
    else:
        lines.append('  - Chưa lấy được block tin chung thị trường.')
    lines.append('')

    lines.extend(section_lines('Mua được ngay', tier_map.get('mua_duoc_ngay', [])))
    lines.extend(section_lines('Chờ điều chỉnh', tier_map.get('cho_dieu_chinh', [])))
    lines.extend(section_lines('Chỉ quan sát nhưng đang mạnh', tier_map.get('chi_quan_sat', [])))

    uu_tien = [x.get('symbol') for x in tier_map.get('mua_duoc_ngay', [])[:3]]
    if not uu_tien:
        uu_tien = [x.get('symbol') for x in tier_map.get('cho_dieu_chinh', [])[:3]]
    lines.append('## Chốt nhanh')
    if uu_tien:
        lines.append(f"- Mã nên ưu tiên theo dõi lúc này: **{', '.join(uu_tien)}**")
    else:
        lines.append('- Chưa có mã nào đủ đẹp để ưu tiên mạnh tay.')
    lines.append('- Nếu thị trường tiếp tục giữ breadth tốt, ưu tiên chọn mã có volume tốt, risk về stop thấp và chưa bị extended.')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['core', 'broad'], default='broad')
    parser.add_argument('--top', type=int, default=6)
    parser.add_argument('--news-top', type=int, default=8)
    parser.add_argument('--watch-top', type=int, default=6)
    parser.add_argument('--breadth-mode', choices=['core', 'broad', 'auto'], default='broad')
    parser.add_argument('--compact', action='store_true')
    parser.add_argument('--json', action='store_true', dest='as_json')
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
            'catalyst_flag': news.get('catalyst_flag', 'thieu_catalyst_moi'),
            'news_score_short_term': news.get('news_score_short_term', 0),
            'news_score_medium_term': news.get('news_score_medium_term', 0),
        })

    if args.as_json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(render_text_report(out))


if __name__ == '__main__':
    main()
