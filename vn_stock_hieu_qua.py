import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from statistics import mean

BASE = "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
TIMEOUT = 15
REPORT_DIR = Path('/Users/huuht/.openclaw/workspace/memory/vn_stock_reports')
OUTPUT_FILE = REPORT_DIR / 'tong_hop_hieu_qua.json'


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def fetch_daily(symbol, from_ts, to_ts):
    url = f"{BASE}?from={from_ts}&to={to_ts}&symbol={symbol}&resolution=1D"
    data = http_get_json(url)
    keys = ['t', 'o', 'h', 'l', 'c', 'v']
    if not all(k in data for k in keys):
        return []
    rows = []
    for i in range(len(data['t'])):
        rows.append({
            't': int(data['t'][i]),
            'o': float(data['o'][i]),
            'h': float(data['h'][i]),
            'l': float(data['l'][i]),
            'c': float(data['c'][i]),
            'v': float(data['v'][i]),
        })
    return rows


def pct(a, b):
    if not b:
        return None
    return round((a - b) / b * 100, 2)


def doc_bao_cao():
    if not REPORT_DIR.exists():
        return []
    files = sorted(p for p in REPORT_DIR.glob('*.json') if p.name != 'tong_hop_hieu_qua.json')
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text(encoding='utf-8')))
        except Exception:
            continue
    return out


def ket_qua_sau_n_phien(entry_price, future_rows, n):
    if len(future_rows) < n:
        return None
    close_n = future_rows[n - 1]['c']
    return {
        'gia_dong_cua': round(close_n, 2),
        'phan_tram': pct(close_n, entry_price),
        'thoi_gian': future_rows[n - 1]['t'],
    }


def danh_gia_mot_ma(ngay_tin_hieu_ts, item):
    ma = item['ma']
    gia = item['gia_dong_cua']
    start = ngay_tin_hieu_ts - 86400 * 3
    end = int(time.time())
    rows = fetch_daily(ma, start, end)
    future_rows = [r for r in rows if r['t'] > ngay_tin_hieu_ts]
    return {
        'ma': ma,
        'gia_tin_hieu': gia,
        'xep_loai': item.get('xep_loai'),
        'muc_uu_tien': item.get('muc_uu_tien'),
        'ket_qua_sau_1_phien': ket_qua_sau_n_phien(gia, future_rows, 1),
        'ket_qua_sau_3_phien': ket_qua_sau_n_phien(gia, future_rows, 3),
        'ket_qua_sau_5_phien': ket_qua_sau_n_phien(gia, future_rows, 5),
    }


def thong_ke_bucket(items, key):
    buckets = {}
    for it in items:
        name = it.get(key) or 'Không rõ'
        buckets.setdefault(name, []).append(it)
    out = []
    for name, vals in buckets.items():
        def lay_pct(k):
            arr = [x[k]['phan_tram'] for x in vals if x.get(k) and x[k].get('phan_tram') is not None]
            return round(mean(arr), 2) if arr else None
        def lay_win(k):
            arr = [x[k]['phan_tram'] for x in vals if x.get(k) and x[k].get('phan_tram') is not None]
            if not arr:
                return None
            return round(sum(1 for z in arr if z > 0) / len(arr) * 100, 2)
        out.append({
            key: name,
            'so_mau': len(vals),
            'trung_binh_1_phien': lay_pct('ket_qua_sau_1_phien'),
            'trung_binh_3_phien': lay_pct('ket_qua_sau_3_phien'),
            'trung_binh_5_phien': lay_pct('ket_qua_sau_5_phien'),
            'ty_le_dung_1_phien': lay_win('ket_qua_sau_1_phien'),
            'ty_le_dung_3_phien': lay_win('ket_qua_sau_3_phien'),
            'ty_le_dung_5_phien': lay_win('ket_qua_sau_5_phien'),
        })
    return out


def tong_hop():
    reports = doc_bao_cao()
    chi_tiet = []
    for rp in reports:
        ts = rp.get('thoi_gian')
        ngay = datetime.fromtimestamp(ts).strftime('%Y-%m-%d') if ts else 'không rõ'
        for item in rp.get('danh_sach_ngan_han', []):
            kq = danh_gia_mot_ma(ts, item)
            kq['ngay_tin_hieu'] = ngay
            chi_tiet.append(kq)

    tong = {
        'thoi_gian': int(time.time()),
        'tong_so_tin_hieu': len(chi_tiet),
        'theo_muc_uu_tien': thong_ke_bucket(chi_tiet, 'muc_uu_tien'),
        'theo_xep_loai': thong_ke_bucket(chi_tiet, 'xep_loai'),
        'chi_tiet': chi_tiet,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(tong, ensure_ascii=False, indent=2), encoding='utf-8')
    return tong


if __name__ == '__main__':
    print(json.dumps(tong_hop(), ensure_ascii=False))
