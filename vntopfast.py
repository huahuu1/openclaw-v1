import argparse
import json
import subprocess
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Load .env from the same directory as this script
_SCRIPT_DIR = Path(__file__).resolve().parent
_ENV_FILE = _SCRIPT_DIR / '.env'
if _ENV_FILE.exists():
    with open(_ENV_FILE) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _val = _line.split('=', 1)
                os.environ.setdefault(_key.strip(), _val.strip())

ROOT = Path(os.environ.get('VNTOP_ROOT', '/home/node/.openclaw/workspace'))
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


def _fmt(x, decimals=2):
    if x is None:
        return 'n/a'
    if isinstance(x, float):
        return f'{x:.{decimals}f}'.rstrip('0').rstrip('.')
    return str(x)


def _sign(x):
    if x is None:
        return 'n/a'
    prefix = '+' if x > 0 else ''
    return f'{prefix}{_fmt(x)}%'


def format_markdown(out):
    """Convert the scan output dict into a readable Vietnamese markdown report."""
    vn_tz = timezone(timedelta(hours=7))
    ts = out.get('ts')
    time_str = datetime.fromtimestamp(ts, tz=vn_tz).strftime('%H:%M %d/%m/%Y') if ts else 'n/a'

    lines = []
    lines.append(f'# 📊 VNTop Scan Report')
    lines.append(f'> Cập nhật: **{time_str}** | Mode: `{out.get("scan_mode", "broad")}` | Breadth: `{out.get("breadth_mode", "broad")}`')
    lines.append('')

    # --- Market context ---
    mc = out.get('market_context') or {}
    regime = mc.get('regime', 'n/a')
    regime_emoji = {'risk_on': '🟢', 'risk_off': '🔴', 'mixed': '🟡'}.get(regime, '⚪')
    lines.append('## 🌐 Bối cảnh thị trường')
    lines.append(f'- Trạng thái: {regime_emoji} **{regime.upper()}** — {mc.get("regime_text", "")}')

    be = out.get('breadth_extended') or {}
    lines.append(f'- Độ rộng: tăng **{be.get("advance", "?")}** / giảm **{be.get("decline", "?")}** / đứng **{be.get("flat", "?")}** ({be.get("valid_count", "?")} mã)')
    lines.append(f'- Trên EMA20: **{_fmt(mc.get("above_ema20_ratio"))}** | Volume mạnh: **{_fmt(mc.get("strong_volume_ratio"))}** | Advance ratio: **{_fmt(mc.get("advance_ratio"))}**')

    leaders = ', '.join(mc.get('leading_sectors') or [])
    if leaders:
        lines.append(f'- Nhóm dẫn dắt: **{leaders}**')
    lines.append('')

    # --- Market news ---
    mn = out.get('market_news') or {}
    mn_items = mn.get('items') or []
    if mn_items:
        lines.append('## 📰 Tin thị trường')
        verdict_emoji = {'positive': '🟢', 'negative': '🔴', 'neutral': '🟡'}.get(mn.get('verdict'), '⚪')
        lines.append(f'> {verdict_emoji} News score: **{mn.get("news_score", 0)}** | Verdict: **{mn.get("verdict", "neutral")}**')
        catalyst_flag = mn.get('catalyst_flag', '')
        if catalyst_flag == 'co_catalyst_moi':
            lines.append('> 🔥 Có tin mới đáng chú ý cho thị trường')
        elif catalyst_flag == 'chi_co_tin_trung_han':
            lines.append('> 📋 Chủ yếu tin trung hạn / câu chuyện cũ')
        lines.append('')
        for it in mn_items[:6]:
            age = it.get('age_hours')
            age_str = f'`{age:.0f}h`' if isinstance(age, (int, float)) else ''
            src = it.get('nguon_hien_thi') or it.get('source') or ''
            title = it.get('summary') or it.get('title') or ''
            link = it.get('duong_dan_goc') or it.get('link') or ''
            impact = it.get('impact_level') or ''
            impact_badge = {'high': '🔴', 'medium': '🟡', 'low': '⚪'}.get(impact, '')
            line_parts = [f'{impact_badge} **{title}**']
            extras = []
            if src:
                extras.append(f'_{src}_')
            if age_str:
                extras.append(age_str)
            if extras:
                line_parts.append(' · '.join(extras))
            line = ' — '.join(line_parts)
            if link:
                line += f' [↗]({link})'
            lines.append(f'- {line}')
        lines.append('')

    # --- Sector strength ---
    sectors = out.get('sector_strength') or []
    if sectors:
        lines.append('## 🏭 Sức mạnh ngành')
        lines.append('| Ngành | Số mã | Thay đổi 1D | Điểm TB |')
        lines.append('|:------|:-----:|:----------:|:-------:|')
        for s in sectors[:10]:
            chg = s.get('avg_change_pct_1d')
            chg_emoji = '📈' if chg and chg > 0 else '📉' if chg and chg < 0 else '➖'
            lines.append(f'| {s.get("sector", "?")} | {s.get("count", 0)} | {chg_emoji} {_sign(chg)} | {_fmt(s.get("avg_score", 0))} |')
        lines.append('')

    # --- Symbols by tier ---
    tier_config = [
        ('mua_duoc_ngay', '🟢 Mua được ngay', 'Điểm kỹ thuật tốt, risk hợp lý — có thể vào vị thế thăm dò.'),
        ('cho_dieu_chinh', '🟡 Chờ điều chỉnh', 'Cấu trúc mạnh nhưng nên chờ nhịp về hỗ trợ hoặc nền mới.'),
        ('chi_quan_sat', '👁️ Chỉ quan sát', 'Đang theo dõi, chưa đủ điều kiện để hành động.'),
    ]

    symbols_data = {item.get('symbol'): item for item in out.get('symbols', [])}

    for tier_key, tier_title, tier_desc in tier_config:
        tier_symbols_list = out.get('tiers', {}).get(tier_key, [])
        lines.append(f'## {tier_title}')
        lines.append(f'> {tier_desc}')
        lines.append('')

        if not tier_symbols_list:
            lines.append('_Chưa có mã phù hợp trong nhóm này._')
            lines.append('')
            continue

        for symbol in tier_symbols_list:
            sym_data = symbols_data.get(symbol)
            if not sym_data:
                lines.append(f'### {symbol}')
                lines.append('_Không có dữ liệu chi tiết._')
                lines.append('')
                continue

            t = sym_data.get('technical') or {}
            lv = build_levels(t)

            # Header with verdict badge
            verdict = t.get('verdict', '?')
            verdict_badge = {'PROPOSE': '🟢', 'WATCH': '🟡', 'PASS': '⚪'}.get(verdict, '⚪')
            lines.append(f'### {verdict_badge} {symbol} — Score **{t.get("score", 0)}** | {verdict}')
            lines.append('')

            # Nhận định + Hành động
            lines.append(f'> 💡 {nhan_dinh_ngan(sym_data)}')
            lines.append(f'> 🎯 {hanh_dong(sym_data)}')
            lines.append('')

            # Buy / Stop / TP levels
            lines.append('**Vùng giá hành động:**')
            lines.append('')
            lines.append(f'| | Giá |')
            lines.append(f'|:---|:---:|')
            lines.append(f'| 🟢 Vùng mua | **{fmt_price(lv["buy_low"])}** – **{fmt_price(lv["buy_high"])}** |')
            lines.append(f'| 🚫 Không đuổi | > {fmt_price(lv["no_chase"])} |')
            lines.append(f'| 🔴 Dừng lỗ | {fmt_price(lv["stop"])} |')
            lines.append(f'| 🎯 Chốt lời | {fmt_price(lv["tp1"])} – {fmt_price(lv["tp2"])} |')
            lines.append('')

            # Technical details
            lines.append('<details>')
            lines.append(f'<summary>📊 Chi tiết kỹ thuật {symbol}</summary>')
            lines.append('')
            lines.append('| Chỉ số | Giá trị |')
            lines.append('|:-------|:--------|')
            lines.append(f'| Close | **{_fmt(t.get("close"))}** |')
            lines.append(f'| Thay đổi 1D / 5D / 20D | {_sign(t.get("change_pct_1d"))} / {_sign(t.get("change_pct_5d"))} / {_sign(t.get("change_pct_20d"))} |')
            lines.append(f'| RSI(14) | {_fmt(t.get("rsi14"))} |')
            lines.append(f'| Rel Volume | {_fmt(t.get("rel_volume20"))} |')
            lines.append(f'| EMA 20 / 50 / 200 | {_fmt(t.get("ema20"))} / {_fmt(t.get("ema50"))} / {_fmt(t.get("ema200"))} |')
            lines.append(f'| Range 20D | {_fmt(t.get("low20"))} – {_fmt(t.get("high20"))} |')
            lines.append(f'| Stop ref | {_fmt(t.get("stop_ref"))} (risk {_fmt(t.get("risk_pct_to_stop"))}%) |')
            lines.append(f'| ATR(14) | {_fmt(t.get("atr14"))} |')
            sb = t.get('score_breakdown', {})
            lines.append(f'| Score | **{t.get("score", 0)}** = trend({sb.get("trend_score", 0)}) + qual({sb.get("quality_score", 0)}) + mom({sb.get("momentum_score", 0)}) + risk({sb.get("risk_score", 0)}) + trig({sb.get("trigger_score", 0)}) − pen({sb.get("penalty", 0)}) |')
            h1_ok = '✅' if t.get('h1_trend_ok') else '❌'
            m15_ok = '✅' if t.get('m15_trigger_ok') else '❌'
            lines.append(f'| H1 trend / M15 trigger | {h1_ok} / {m15_ok} |')

            notes = t.get('notes') or []
            if notes:
                lines.append(f'| Notes | `{", ".join(notes)}` |')

            warnings = t.get('data_quality_warnings') or []
            if warnings:
                lines.append(f'| ⚠️ Cảnh báo | `{", ".join(warnings)}` |')

            lines.append('')
            lines.append('</details>')
            lines.append('')

            # Catalyst
            cat_flag = sym_data.get('catalyst_flag', 'thieu_catalyst_moi')
            cat_emoji = {'co_catalyst_moi': '🔥', 'chi_co_tin_trung_han': '📋'}.get(cat_flag, '⚪')
            lines.append(f'{cat_emoji} **Catalyst:** {catalyst_text(sym_data)}')
            lines.append('')

            # News
            news_lines_data = sym_data.get('nguon_doc_nhanh') or []
            if news_lines_data:
                lines.append('**📰 Tin liên quan:**')
                for nl in news_lines_data[:3]:
                    lines.append(f'- {nl}')
            else:
                lines.append('_Chưa có tin đủ chất lượng._')
            lines.append('')
            lines.append('---')
            lines.append('')

    # --- Chốt nhanh ---
    tier_map = {'mua_duoc_ngay': [], 'cho_dieu_chinh': [], 'chi_quan_sat': []}
    for item in out.get('symbols', []):
        tier_map.setdefault(item.get('tier'), []).append(item)

    uu_tien = [x.get('symbol') for x in tier_map.get('mua_duoc_ngay', [])[:3]]
    if not uu_tien:
        uu_tien = [x.get('symbol') for x in tier_map.get('cho_dieu_chinh', [])[:3]]

    lines.append('## ⚡ Chốt nhanh')
    if uu_tien:
        lines.append(f'- 🎯 Mã ưu tiên theo dõi: **{", ".join(uu_tien)}**')
    else:
        lines.append('- Chưa có mã nào đủ đẹp để ưu tiên mạnh tay.')
    lines.append('- Ưu tiên chọn mã có volume tốt, risk về stop thấp và chưa bị extended.')
    lines.append('')

    # --- Errors ---
    errs = out.get('errors') or []
    if errs:
        lines.append('## ⚠️ Lỗi')
        for e in errs[:10]:
            lines.append(f'- `{e.get("symbol", "?")}`: {e.get("error", "unknown")}')
        lines.append('')

    # --- Footer ---
    lines.append('---')
    lines.append(f'_Generated at {time_str} by vntopfast.py_')

    return '\n'.join(lines)

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

    # Write markdown report to fixed file
    md_path = _SCRIPT_DIR / 'vntop_report.md'
    md_content = format_markdown(out)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f'\n📄 Report saved: {md_path}', file=sys.stderr)


if __name__ == '__main__':
    main()
