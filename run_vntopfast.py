import argparse
import json
import os
import subprocess
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
FAST = ROOT / 'vntopfast.py'


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


def news_lines(item, n=3):
    lines = item.get('nguon_doc_nhanh') or []
    return lines[:n]


def catalyst_text(item):
    flag = item.get('catalyst_flag') or 'thieu_catalyst_moi'
    short_score = item.get('news_score_short_term', 0)
    medium_score = item.get('news_score_medium_term', 0)
    if flag == 'co_catalyst_moi':
        return f'Có catalyst mới, nghiêng ngắn hạn tốt hơn (short={short_score}, medium={medium_score}).'
    if flag == 'chi_co_tin_trung_han':
        return f'Chủ yếu còn câu chuyện trung hạn, thiếu catalyst mới cho T+ gần (short={short_score}, medium={medium_score}).'
    return f'Thiếu catalyst mới rõ ràng, không nên dựa vào news để đẩy kỳ vọng ngắn hạn (short={short_score}, medium={medium_score}).'


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
        src = news_lines(item)
        if src:
            out.extend([f'  - {x}' for x in src])
        else:
            out.append('  - Chưa có tin đủ chất lượng để đưa vào block nhanh.')
        out.append('')
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['core', 'broad'], default='broad')
    parser.add_argument('--top', type=int, default=5)
    parser.add_argument('--watch-top', type=int, default=4)
    parser.add_argument('symbols', nargs='*')
    args = parser.parse_args()

    cmd = ['python3', str(FAST), '--mode', args.mode, '--top', str(args.top), '--watch-top', str(args.watch_top)]
    if args.symbols:
        cmd.extend(args.symbols)

    result = subprocess.run(cmd, text=True)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
