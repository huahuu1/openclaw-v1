import argparse
import json
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path('/Users/huuht/.openclaw/workspace')
SCAN = ROOT / 'vn_stock_scan.py'
NEWS = ROOT / 'vn_stock_news.py'
HISTORY_DIR = ROOT / 'memory' / 'vn_stock_reports'

BAN_DO_NHAN = {
    'PROPOSE': 'Đề cử',
    'WATCH': 'Theo dõi',
    'PASS': 'Bỏ qua',
    'PROMOTE_TO_WATCHPLUS': 'Theo dõi sát',
    'CAUTION': 'Thận trọng',
    'positive': 'Tích cực',
    'negative': 'Tiêu cực',
    'neutral': 'Trung tính',
    'bank': 'Ngân hàng',
    'real_estate': 'Bất động sản',
    'securities': 'Chứng khoán',
    'steel': 'Thép',
    'energy': 'Năng lượng',
    'utilities': 'Tiện ích',
    'logistics': 'Cảng biển / logistics',
    'retail': 'Bán lẻ',
    'consumer': 'Tiêu dùng',
    'technology': 'Công nghệ',
    'chemicals': 'Hóa chất',
    'other': 'Khác',
}

BAN_DO_LY_DO = {
    'technical_score_strong': 'Điểm kỹ thuật mạnh',
    'news_supportive': 'Tin tức hỗ trợ',
    'h1_confirmed': 'Khung 1 giờ xác nhận',
    'm15_trigger_ok': 'Khung 15 phút cho tín hiệu',
    'extended_do_not_chase': 'Đã tăng nóng, không nên mua đuổi',
    'news_risk': 'Tin tức có rủi ro',
}


TIMEOUT = 15


def run_json(cmd):
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)


def http_get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://cafef.vn/'})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode('utf-8', errors='ignore'))


def lam_tron_ty(vnd):
    if vnd is None:
        return None
    return round(vnd / 1_000_000_000, 2)


def tom_tat_dong_tien(label, kl_mua, gt_mua, kl_ban, gt_ban, kl_rong=None, gt_rong=None):
    if gt_rong is None:
        if gt_mua is None or gt_ban is None:
            return None
        gt_rong = gt_mua - gt_ban
    if kl_rong is None and kl_mua is not None and kl_ban is not None:
        kl_rong = kl_mua - kl_ban
    huong = 'mua ròng' if gt_rong > 0 else 'bán ròng' if gt_rong < 0 else 'cân bằng'
    return {
        'doi_tuong': label,
        'huong': huong,
        'khoi_luong_mua': kl_mua,
        'gia_tri_mua_ty': lam_tron_ty(gt_mua),
        'khoi_luong_ban': kl_ban,
        'gia_tri_ban_ty': lam_tron_ty(gt_ban),
        'khoi_luong_rong': kl_rong,
        'gia_tri_rong_ty': lam_tron_ty(gt_rong),
    }


def lay_dong_tien_ma(symbol, so_phien=5):
    hom_nay = datetime.now().strftime('%Y-%m-%d')
    start_date = '2026-01-01'
    ma = urllib.parse.quote(symbol)
    ngoai_url = (
        f'https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/GDKhoiNgoai.ashx?'
        f'Symbol={ma}&StartDate={start_date}&EndDate={hom_nay}&PageIndex=1&PageSize={so_phien}'
    )
    tu_doanh_url = (
        f'https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/GDTuDoanh.ashx?'
        f'Symbol={ma}&StartDate={start_date}&EndDate={hom_nay}&PageIndex=1&PageSize={so_phien}'
    )

    dong_tien = {
        'khối_ngoại': None,
        'tự_doanh': None,
    }

    try:
        ngoai = http_get_json(ngoai_url)
        rows = ((ngoai or {}).get('Data') or {}).get('Data') or []
        if rows:
            moi_nhat = rows[0]
            dong_tien['khối_ngoại'] = tom_tat_dong_tien(
                'khối ngoại',
                moi_nhat.get('KLMua'),
                moi_nhat.get('GtMua'),
                moi_nhat.get('KLBan'),
                moi_nhat.get('GtBan'),
                moi_nhat.get('KLGDRong'),
                moi_nhat.get('GTDGRong'),
            )
            dong_tien['khối_ngoại']['ngày'] = moi_nhat.get('Ngay')
            dong_tien['khối_ngoại']['sở_hữu_pct'] = moi_nhat.get('DangSoHuu')
    except Exception:
        pass

    try:
        tu_doanh = http_get_json(tu_doanh_url)
        data = ((tu_doanh or {}).get('Data') or {}).get('Data') or {}
        rows = data.get('ListDataTudoanh') or []
        if rows:
            moi_nhat = rows[0]
            kl_mua = moi_nhat.get('KLcpMua')
            kl_ban = moi_nhat.get('KlcpBan')
            gt_mua = moi_nhat.get('GtMua')
            gt_ban = moi_nhat.get('GtBan')
            dong_tien['tự_doanh'] = tom_tat_dong_tien(
                'tự doanh',
                kl_mua,
                gt_mua,
                kl_ban,
                gt_ban,
                (kl_mua or 0) - (kl_ban or 0),
                (gt_mua or 0) - (gt_ban or 0),
            )
            dong_tien['tự_doanh']['ngày'] = moi_nhat.get('Date')
    except Exception:
        pass

    return dong_tien


def clamp_news_score(v):
    return max(-3, min(3, v))


def dinh_dang_ngay(ts):
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')


def lam_dep_nguon_tin(ds_nguon_tin):
    ket_qua = []
    for item in ds_nguon_tin or []:
        tieu_de = item.get('tieu_de') or 'Tin tham khảo'
        nguon = item.get('nguon') or 'Nguồn chưa rõ'
        duong_dan = item.get('duong_dan') or ''
        so_gio = item.get('so_gio_truoc')
        if isinstance(so_gio, (int, float)):
            thoi_gian = f'{so_gio} giờ trước'
        else:
            thoi_gian = 'không rõ thời gian'
        dong = {
            'tieu_de': tieu_de,
            'nguon': nguon,
            'duong_dan': duong_dan,
            'thoi_gian': thoi_gian,
            'hien_thi': f'{tieu_de} | {nguon} | {thoi_gian} | <{duong_dan}>' if duong_dan else f'{tieu_de} | {nguon} | {thoi_gian}',
        }
        ket_qua.append(dong)
    return ket_qua


def tinh_quan_tri_von(tai_khoan, rui_ro_phan_tram, gia_vao, moc_sai, ti_le_toi_da_vao_lenh, he_so_vuot=1.0):
    if not tai_khoan or gia_vao <= 0 or moc_sai <= 0 or gia_vao <= moc_sai:
        return None
    gia_vao_vnd = gia_vao * 1000
    moc_sai_vnd = moc_sai * 1000
    tien_rui_ro_toi_da = tai_khoan * rui_ro_phan_tram / 100
    rui_ro_moi_co = gia_vao_vnd - moc_sai_vnd
    so_co_theo_rui_ro = int((tien_rui_ro_toi_da / rui_ro_moi_co) // 100) * 100
    ty_trong_thuc_te = ti_le_toi_da_vao_lenh * he_so_vuot
    so_co_theo_ty_trong = int(((tai_khoan * ty_trong_thuc_te) / gia_vao_vnd) // 100) * 100
    so_co_de_xuat = max(0, min(so_co_theo_rui_ro, so_co_theo_ty_trong))
    return {
        'tai_khoan': tai_khoan,
        'rui_ro_toi_da_phan_tram': rui_ro_phan_tram,
        'tien_rui_ro_toi_da': round(tien_rui_ro_toi_da, 2),
        'ty_trong_toi_da_thuc_te': round(ty_trong_thuc_te, 4),
        'he_so_vuot': he_so_vuot,
        'so_luong_co_theo_rui_ro': so_co_theo_rui_ro,
        'so_luong_co_theo_ty_trong': so_co_theo_ty_trong,
        'so_luong_co_de_xuat': so_co_de_xuat,
        'gia_tri_lenh_de_xuat': round(so_co_de_xuat * gia_vao_vnd, 2),
        'rui_ro_thuc_te': round(so_co_de_xuat * rui_ro_moi_co, 2),
    }


def xay_dung_ke_hoach(row, tai_khoan=None, rui_ro_phan_tram=1.0, ti_le_toi_da_vao_lenh=0.2, cho_phep_vuot=False, he_so_vuot_mac_dinh=1.0):
    close = row['close']
    stop_ref = row.get('stop_ref') or close
    atr = row.get('atr14') or 0
    high20 = row.get('high20') or close
    ema20 = row.get('ema20') or close
    risk_pct = row.get('risk_pct_to_stop') or 999

    diem_mua_vung_chinh = round(max(ema20, close - atr * 0.5), 2)
    diem_mua_vuot_dinh = round(high20 * 1.005, 2)
    khong_mua_duoi_tren = round(close + atr * 0.8, 2) if atr else round(close * 1.02, 2)
    moc_sai = round(stop_ref, 2)
    rui_ro_gia = max(0.01, diem_mua_vung_chinh - moc_sai)
    dung_lo_chat = round(max(moc_sai, diem_mua_vung_chinh - atr * 0.6), 2) if atr else moc_sai
    dung_lo_chuan = moc_sai
    dung_lo_rong = round(max(0.01, diem_mua_vung_chinh - rui_ro_gia * 1.5), 2)
    muc_chot_gan = round(diem_mua_vung_chinh + rui_ro_gia * 1.5, 2)
    muc_chot_chinh = round(diem_mua_vung_chinh + rui_ro_gia * 2.5, 2)
    muc_chot_mo_rong = round(diem_mua_vung_chinh + rui_ro_gia * 4.0, 2)

    if 'avoid_chasing' in row.get('notes', []):
        hanh_dong = 'Chỉ chờ nhịp điều chỉnh, không mua đuổi'
        vung_mua = f'{diem_mua_vung_chinh}–{close}'
    elif row.get('final_label') in ('PROPOSE', 'PROMOTE_TO_WATCHPLUS'):
        hanh_dong = 'Có thể mua khi khỏe hoặc chờ nhịp điều chỉnh'
        vung_mua = f'{diem_mua_vung_chinh}–{diem_mua_vuot_dinh}'
    elif row.get('final_label') == 'WATCH':
        hanh_dong = 'Theo dõi phản ứng giá trước khi mua'
        vung_mua = f'Ưu tiên chờ điều chỉnh quanh {diem_mua_vung_chinh}'
    else:
        hanh_dong = 'Chưa nên mở vị thế mới'
        vung_mua = 'Chưa có vùng mua phù hợp'

    if row.get('final_label') == 'PROPOSE' and risk_pct <= 3.5 and row.get('news_verdict') != 'negative':
        do_uu_tien = 'A'
    elif row.get('final_label') in ('PROMOTE_TO_WATCHPLUS', 'WATCH', 'PROPOSE'):
        do_uu_tien = 'B'
    else:
        do_uu_tien = 'C'

    ly_do = []
    if row.get('score', 0) >= 9:
        ly_do.append('technical_score_strong')
    if row.get('news_verdict') == 'positive':
        ly_do.append('news_supportive')
    if row.get('h1_trend_ok'):
        ly_do.append('h1_confirmed')
    if row.get('m15_trigger_ok'):
        ly_do.append('m15_trigger_ok')
    if 'avoid_chasing' in row.get('notes', []):
        ly_do.append('extended_do_not_chase')
    if row.get('news_verdict') == 'negative':
        ly_do.append('news_risk')

    la_ma_dan_song = row.get('final_label') == 'PROMOTE_TO_WATCHPLUS' and row.get('news_verdict') == 'positive' and 'avoid_chasing' in row.get('notes', [])
    he_so_vuot = he_so_vuot_mac_dinh if (cho_phep_vuot and la_ma_dan_song) else 1.0
    quan_tri_von = tinh_quan_tri_von(tai_khoan, rui_ro_phan_tram, diem_mua_vung_chinh, moc_sai, ti_le_toi_da_vao_lenh, he_so_vuot)

    return {
        'muc_uu_tien': do_uu_tien,
        'ke_hoach_hanh_dong': hanh_dong,
        'vung_mua_ly_tuong': vung_mua,
        'moc_mua_dieu_chinh': diem_mua_vung_chinh,
        'moc_mua_vuot_dinh': diem_mua_vuot_dinh,
        'khong_mua_duoi_tren': khong_mua_duoi_tren,
        'moc_sai': moc_sai,
        'dung_lo_chat': dung_lo_chat,
        'dung_lo_chuan': dung_lo_chuan,
        'dung_lo_rong': dung_lo_rong,
        'muc_chot_gan': muc_chot_gan,
        'muc_chot_chinh': muc_chot_chinh,
        'muc_chot_mo_rong': muc_chot_mo_rong,
        'ly_do': [BAN_DO_LY_DO.get(x, x) for x in ly_do],
        'quan_tri_von': quan_tri_von,
        'duoc_ap_dung_rule_vuot': bool(he_so_vuot > 1.0),
    }


def viet_hoa_mot_dong(row, tai_khoan=None, rui_ro_phan_tram=1.0, ti_le_toi_da_vao_lenh=0.2, cho_phep_vuot=False, he_so_vuot_mac_dinh=1.0):
    dong_tien = lay_dong_tien_ma(row['symbol'])
    nguon_tin_tham_khao = lam_dep_nguon_tin(row.get('news_source_links', []))
    return {
        'ma': row['symbol'],
        'nhom_nganh': BAN_DO_NHAN.get(row.get('sector'), row.get('sector')),
        'gia_dong_cua': row['close'],
        'phan_tram_1_phien': row.get('change_pct_1d'),
        'phan_tram_5_phien': row.get('change_pct_5d'),
        'phan_tram_20_phien': row.get('change_pct_20d'),
        'ema20': row.get('ema20'),
        'ema50': row.get('ema50'),
        'ema200': row.get('ema200'),
        'rsi14': row.get('rsi14'),
        'atr14': row.get('atr14'),
        'ti_le_khoi_luong_20_phien': row.get('rel_volume20'),
        'dinh_20_phien': row.get('high20'),
        'day_20_phien': row.get('low20'),
        'moc_dung_lo_tham_chieu': row.get('stop_ref'),
        'rui_ro_den_dung_lo_pct': row.get('risk_pct_to_stop'),
        'diem_tin_tuc': row.get('news_score'),
        'danh_gia_tin_tuc': BAN_DO_NHAN.get(row.get('news_verdict'), row.get('news_verdict')),
        'tong_diem': row.get('final_score'),
        'xep_loai': BAN_DO_NHAN.get(row.get('final_label'), row.get('final_label')),
        'tin_noi_bat': row.get('top_news', []),
        'tom_tat_tin': row.get('news_summary_items', []),
        'nguon_tin_tham_khao': nguon_tin_tham_khao,
        'nguon_tin_hien_thi_nhanh': [x.get('hien_thi') for x in nguon_tin_tham_khao],
        'tac_dong_tin_ngan_han': row.get('news_impact_short'),
        'tac_dong_tin_trung_han': row.get('news_impact_medium'),
        'ket_luan_xu_the_tin': row.get('news_trend_view'),
        'do_tin_cay_xu_the_tin': row.get('news_trend_confidence'),
        'dong_tien': dong_tien,
        **xay_dung_ke_hoach(row, tai_khoan, rui_ro_phan_tram, ti_le_toi_da_vao_lenh, cho_phep_vuot, he_so_vuot_mac_dinh),
    }


def tron_du_lieu(scan_payload, news_payload):
    news_map = {x['symbol']: x for x in news_payload['results']}

    breadth_extended = scan_payload.get('breadth_extended', {}) or {}
    sector_strength = breadth_extended.get('sector_strength', []) or []
    sector_strength_map = {x.get('sector'): x for x in sector_strength}
    nhom_dan_song = {
        x.get('sector')
        for x in sector_strength
        if (x.get('count', 0) >= 2 and (x.get('above_ema20_ratio') or 0) >= 0.5)
    }

    rows = []
    for item in scan_payload['all']:
        n = news_map.get(item['symbol'], {'news_score': 0, 'verdict': 'neutral', 'items': []})
        final_score = item['score'] + clamp_news_score(n['news_score'])

        diem_nganh_dan_song = 0
        sec = item.get('sector')
        sec_info = sector_strength_map.get(sec, {})
        ti_le_tren_ema20 = sec_info.get('above_ema20_ratio') or 0
        bien_dong_nganh = sec_info.get('avg_change_pct_1d') or 0
        la_nhom_dan_song = sec in nhom_dan_song

        if la_nhom_dan_song:
            diem_nganh_dan_song += 1
        if la_nhom_dan_song and item.get('h1_trend_ok'):
            diem_nganh_dan_song += 1
        if la_nhom_dan_song and item.get('m15_trigger_ok'):
            diem_nganh_dan_song += 1
        if ti_le_tren_ema20 >= 0.75:
            diem_nganh_dan_song += 1
        if bien_dong_nganh > 0:
            diem_nganh_dan_song += 1

        final_score += diem_nganh_dan_song
        label = item['verdict']
        if item['verdict'] == 'WATCH' and n['verdict'] == 'positive' and final_score >= 9:
            label = 'PROMOTE_TO_WATCHPLUS'
        if item['verdict'] == 'PROPOSE' and n['verdict'] == 'negative':
            label = 'CAUTION'
        if item['verdict'] == 'WATCH' and la_nhom_dan_song and item.get('h1_trend_ok') and item.get('change_pct_1d', 0) > 0:
            label = 'PROMOTE_TO_WATCHPLUS'

        merged = {
            **item,
            'news_score': n['news_score'],
            'news_verdict': n['verdict'],
            'top_news': [z['title'] for z in n.get('items', [])[:3]],
            'news_summary_items': n.get('tin_tom_tat', []),
            'news_source_links': [
                {
                    'tieu_de': z.get('summary') or z.get('title'),
                    'nguon': z.get('source') or z.get('nguon_hien_thi'),
                    'duong_dan': z.get('link') or z.get('duong_dan_goc'),
                    'gio_dang': z.get('pubDate'),
                    'so_gio_truoc': z.get('age_hours'),
                }
                for z in n.get('items', [])[:3]
                if z.get('link') or z.get('duong_dan_goc')
            ],
            'news_impact_short': n.get('tac_dong_ngan_han'),
            'news_impact_medium': n.get('tac_dong_trung_han'),
            'news_trend_view': n.get('ket_luan_xu_the_tin'),
            'news_trend_confidence': n.get('do_tin_cay_xu_the_tin'),
            'diem_nganh_dan_song': diem_nganh_dan_song,
            'la_nhom_dan_song': la_nhom_dan_song,
            'final_score': final_score,
            'final_label': label,
        }
        rows.append(merged)
    rows.sort(
        key=lambda x: (
            (x.get('final_label') == 'PROPOSE'),
            (x.get('la_nhom_dan_song') is True),
            x['final_score'],
            x.get('diem_nganh_dan_song', 0),
            x['score'],
            x['change_pct_20d'] or -999,
        ),
        reverse=True,
    )
    return rows


def luu_lich_su(payload_viet):
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ngay = dinh_dang_ngay(payload_viet['thoi_gian'])
    path = HISTORY_DIR / f'{ngay}.json'
    path.write_text(json.dumps(payload_viet, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(path)


def doc_lich_su_hom_truoc():
    if not HISTORY_DIR.exists():
        return None
    files = sorted(HISTORY_DIR.glob('*.json'))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding='utf-8'))


def so_sanh_voi_hom_truoc(payload_viet):
    truoc = doc_lich_su_hom_truoc()
    if not truoc:
        return {
            'co_so_sanh': False,
            'ma_moi_vao_danh_sach': [x['ma'] for x in payload_viet['danh_sach_ngan_han']],
            'ma_bi_loai': [],
        }
    cu = {x['ma'] for x in truoc.get('danh_sach_ngan_han', [])}
    moi = {x['ma'] for x in payload_viet.get('danh_sach_ngan_han', [])}
    return {
        'co_so_sanh': True,
        'ma_moi_vao_danh_sach': sorted(moi - cu),
        'ma_bi_loai': sorted(cu - moi),
    }


def dien_giai_do_rong_mo_rong(scan):
    breadth = scan.get('breadth_extended', {}) or {}
    sector_rows = breadth.get('sector_strength', []) or []
    adv_ratio = breadth.get('advance_ratio') or 0
    above_ema20_ratio = breadth.get('above_ema20_ratio') or 0
    strong_volume_ratio = breadth.get('strong_volume_ratio') or 0

    if adv_ratio >= 0.55:
        xung_luc_ngan_han = 'lan tỏa mạnh'
    elif adv_ratio >= 0.45:
        xung_luc_ngan_han = 'trung tính'
    elif adv_ratio >= 0.3:
        xung_luc_ngan_han = 'yếu'
    else:
        xung_luc_ngan_han = 'rất yếu'

    if above_ema20_ratio >= 0.6:
        nen_xu_huong = 'nền xu hướng tích cực'
    elif above_ema20_ratio >= 0.45:
        nen_xu_huong = 'nền xu hướng trung tính'
    else:
        nen_xu_huong = 'nền xu hướng suy yếu'

    if strong_volume_ratio >= 0.2:
        dong_tien_ngan_han = 'dòng tiền ngắn hạn vào khá rõ'
    elif strong_volume_ratio >= 0.12:
        dong_tien_ngan_han = 'dòng tiền ngắn hạn có chọn lọc'
    else:
        dong_tien_ngan_han = 'dòng tiền ngắn hạn còn dè dặt'

    if adv_ratio < 0.3 and above_ema20_ratio >= 0.45:
        ket_luan = 'Bề rộng ngắn hạn xấu nhưng nền xu hướng trung bình chưa gãy hẳn.'
        khuyen_nghi_hanh_dong = 'Ưu tiên giữ nhịp phòng thủ chủ động: chỉ nên chọn 1 đến 2 mã khỏe nhất, mua ở điểm điều chỉnh đẹp, không mua đuổi và không mở danh mục dàn trải.'
    elif adv_ratio < 0.3 and above_ema20_ratio < 0.45:
        ket_luan = 'Bề rộng ngắn hạn yếu và nền xu hướng cũng đang xấu đi, nên ưu tiên phòng thủ.'
        khuyen_nghi_hanh_dong = 'Hạn chế mở vị thế mới. Nếu tham gia thì giữ tỷ trọng thấp, ưu tiên đứng ngoài quan sát hoặc chỉ thăm dò rất nhỏ ở mã đặc biệt mạnh.'
    elif adv_ratio >= 0.45 and above_ema20_ratio >= 0.55:
        ket_luan = 'Thị trường có độ lan tỏa tốt, có thể chủ động hơn với các mã khỏe.'
        khuyen_nghi_hanh_dong = 'Có thể chủ động hơn: giải ngân từng phần vào 2 đến 3 mã khỏe, ưu tiên nhóm dẫn dắt và có thể nâng dần tỷ trọng nếu thị trường giữ nhịp tốt.'
    else:
        ket_luan = 'Thị trường đang phân hóa, nên chọn lọc kỹ thay vì mở rộng danh mục.'
        khuyen_nghi_hanh_dong = 'Đi theo chiến lược chọn lọc: giữ danh mục gọn, ưu tiên mã có dòng tiền rõ và chỉ vào lệnh khi điểm mua thật sự thuận lợi.'

    nhom_dan_dat = []
    nhom_yeu = []
    for row in sector_rows:
        ten = BAN_DO_NHAN.get(row.get('sector'), row.get('sector'))
        ti_le = row.get('above_ema20_ratio') or 0
        bien_dong = row.get('avg_change_pct_1d') or 0
        if row.get('count', 0) >= 2 and ti_le >= 0.5:
            nhom_dan_dat.append({
                'nhom_nganh': ten,
                'ti_le_tren_ema20': ti_le,
                'bien_dong_trung_binh_1_phien': bien_dong,
            })
        if row.get('count', 0) >= 2 and ti_le <= 0.25:
            nhom_yeu.append({
                'nhom_nganh': ten,
                'ti_le_tren_ema20': ti_le,
                'bien_dong_trung_binh_1_phien': bien_dong,
            })

    return {
        'xung_luc_ngan_han': xung_luc_ngan_han,
        'nen_xu_huong': nen_xu_huong,
        'dong_tien_ngan_han': dong_tien_ngan_han,
        'ket_luan': ket_luan,
        'khuyen_nghi_hanh_dong': khuyen_nghi_hanh_dong,
        'nhom_dan_dat': nhom_dan_dat[:4],
        'nhom_yeu': nhom_yeu[:4],
    }


def bao_cao_ngay_mai(symbols, top=5, tai_khoan=None, rui_ro_phan_tram=1.0, ti_le_toi_da_vao_lenh=0.2, cho_phep_vuot=False, he_so_vuot_mac_dinh=1.0):
    scan = run_json(['python3', str(SCAN), *symbols])
    news = run_json(['python3', str(NEWS), *symbols, '--limit', '6'])
    merged = tron_du_lieu(scan, news)
    shortlist = []
    for row in merged:
        if row['final_label'] in ('PROPOSE', 'PROMOTE_TO_WATCHPLUS', 'WATCH', 'CAUTION'):
            shortlist.append(viet_hoa_mot_dong(row, tai_khoan, rui_ro_phan_tram, ti_le_toi_da_vao_lenh, cho_phep_vuot, he_so_vuot_mac_dinh))
    shortlist = shortlist[:top]

    danh_sach_theo_doi_thi_truong_xau = []
    if not shortlist:
        ung_vien_theo_doi = [
            row for row in merged
            if row.get('final_score') is not None and (
                row.get('score', 0) >= 6
                or row.get('change_pct_20d', 0) >= 3
                or row.get('h1_trend_ok')
                or row.get('m15_trigger_ok')
                or row.get('news_verdict') == 'positive'
            )
        ]
        if not ung_vien_theo_doi:
            ung_vien_theo_doi = merged[:3]
        danh_sach_theo_doi_thi_truong_xau = [
            viet_hoa_mot_dong(row, tai_khoan, rui_ro_phan_tram, ti_le_toi_da_vao_lenh, cho_phep_vuot, he_so_vuot_mac_dinh)
            for row in ung_vien_theo_doi[:3]
        ]

    payload_viet = {
        'thoi_gian': scan['ts'],
        'tham_so_quan_tri_von': {
            'tai_khoan': tai_khoan,
            'rui_ro_moi_lenh_phan_tram': rui_ro_phan_tram,
            'ti_le_toi_da_vao_lenh': ti_le_toi_da_vao_lenh,
        },
        'do_rong_thi_truong': {
            'so_ma_tang': scan.get('breadth', {}).get('advance'),
            'so_ma_giam': scan.get('breadth', {}).get('decline'),
            'ti_le_ma_tang': scan.get('breadth', {}).get('advance_ratio'),
            'ti_le_ma_giam': scan.get('breadth', {}).get('decline_ratio'),
            'ti_le_ma_manh': scan.get('breadth', {}).get('strong_ratio'),
            'ghi_chu': 'Đây là độ rộng của rổ trọng tâm đang quét, không phải toàn thị trường.',
        },
        'do_rong_thi_truong_mo_rong': {
            'kich_thuoc_ro': scan.get('breadth_extended', {}).get('valid_count'),
            'so_ma_tang': scan.get('breadth_extended', {}).get('advance'),
            'so_ma_giam': scan.get('breadth_extended', {}).get('decline'),
            'so_ma_dung_gia': scan.get('breadth_extended', {}).get('flat'),
            'ti_le_ma_tang': scan.get('breadth_extended', {}).get('advance_ratio'),
            'ti_le_ma_giam': scan.get('breadth_extended', {}).get('decline_ratio'),
            'ti_le_ma_dung_gia': scan.get('breadth_extended', {}).get('flat_ratio'),
            'so_ma_tren_ema20': scan.get('breadth_extended', {}).get('above_ema20'),
            'ti_le_ma_tren_ema20': scan.get('breadth_extended', {}).get('above_ema20_ratio'),
            'so_ma_khoi_luong_manh': scan.get('breadth_extended', {}).get('strong_volume'),
            'ti_le_ma_khoi_luong_manh': scan.get('breadth_extended', {}).get('strong_volume_ratio'),
            'so_ma_loi_du_lieu': scan.get('breadth_extended', {}).get('error_count'),
        },
        'dien_giai_do_rong_thi_truong_mo_rong': dien_giai_do_rong_mo_rong(scan),
        'nhom_nganh_manh': [
            {
                'nhom_nganh': BAN_DO_NHAN.get(x.get('sector'), x.get('sector')),
                'so_ma': x.get('count'),
                'bien_dong_trung_binh_1_phien': x.get('avg_change_pct_1d'),
                'diem_trung_binh': x.get('avg_score'),
            }
            for x in scan.get('sector_strength', [])[:5]
        ],
        'nhom_nganh_manh_mo_rong': [
            {
                'nhom_nganh': BAN_DO_NHAN.get(x.get('sector'), x.get('sector')),
                'so_ma': x.get('count'),
                'bien_dong_trung_binh_1_phien': x.get('avg_change_pct_1d'),
                'ti_le_tren_ema20': x.get('above_ema20_ratio'),
            }
            for x in scan.get('breadth_extended', {}).get('sector_strength', [])[:8]
        ],
        'danh_sach_ngan_han': shortlist,
        'danh_sach_theo_doi_thi_truong_xau': danh_sach_theo_doi_thi_truong_xau,
    }
    payload_viet['so_sanh_voi_lan_truoc'] = so_sanh_voi_hom_truoc(payload_viet)
    duong_dan = luu_lich_su(payload_viet)
    payload_viet['tep_lich_su'] = duong_dan
    return payload_viet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('symbols', nargs='*')
    parser.add_argument('--top', type=int, default=5)
    parser.add_argument('--tai-khoan', type=float, default=None)
    parser.add_argument('--rui-ro', type=float, default=1.0)
    parser.add_argument('--ti-le-toi-da', type=float, default=0.2)
    parser.add_argument('--cho-phep-vuot', action='store_true')
    parser.add_argument('--he-so-vuot', type=float, default=1.0)
    args = parser.parse_args()
    symbols = args.symbols or [
        'VHM', 'VIC', 'VCB', 'CTG', 'BID', 'MBB', 'ACB', 'TCB',
        'FPT', 'HPG', 'SSI', 'VCI', 'HCM', 'REE', 'GMD', 'VNM',
        'MWG', 'PNJ', 'DGC', 'MSN', 'GAS', 'PVD', 'PVS', 'KDH', 'NLG'
    ]
    payload = bao_cao_ngay_mai(
        symbols,
        top=args.top,
        tai_khoan=args.tai_khoan,
        rui_ro_phan_tram=args.rui_ro,
        ti_le_toi_da_vao_lenh=args.ti_le_toi_da,
        cho_phep_vuot=args.cho_phep_vuot,
        he_so_vuot_mac_dinh=args.he_so_vuot,
    )
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == '__main__':
    main()
