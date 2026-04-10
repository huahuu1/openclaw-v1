import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path('/Users/huuht/.openclaw/workspace')
REPORT = ROOT / 'vn_stock_report.py'
OUTPUT_DIR = ROOT / 'memory' / 'vn_stock_evening_briefs'


def run_report(top=5, symbols=None):
    cmd = ['python3', str(REPORT), '--top', str(top)]
    if symbols:
        cmd = ['python3', str(REPORT), *symbols, '--top', str(top)]
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)


def dong_tieu_de(payload):
    dt = datetime.fromtimestamp(payload['thoi_gian']).strftime('%Y-%m-%d')
    return f'Bản tin buổi tối {dt}'


def dong_boi_canh(payload):
    dr = payload.get('do_rong_thi_truong', {})
    tang = dr.get('so_ma_tang')
    giam = dr.get('so_ma_giam')
    ti_le = dr.get('ti_le_ma_manh')
    return f'Thị trường nội bộ: {tang} mã tăng, {giam} mã giảm, tỷ lệ mã mạnh {ti_le}.'


def dong_nhom(payload):
    nhom = payload.get('nhom_nganh_manh', [])[:3]
    if not nhom:
        return 'Chưa xác định rõ nhóm ngành nổi bật.'
    parts = [f"{x['nhom_nganh']} ({x['diem_trung_binh']} điểm)" for x in nhom]
    return 'Nhóm ngành nổi bật: ' + ', '.join(parts) + '.'


def tom_tat_ma(item):
    lines = []
    lines.append(f"- {item['ma']} | {item['xep_loai']} | ưu tiên {item['muc_uu_tien']}")
    lines.append(f"  Giá đóng cửa: {item['gia_dong_cua']} | Tin tức: {item['danh_gia_tin_tuc']} | Tổng điểm: {item['tong_diem']}")
    lines.append(f"  Kế hoạch: {item['ke_hoach_hanh_dong']}")
    lines.append(f"  Vùng mua: {item['vung_mua_ly_tuong']}")
    lines.append(f"  Không mua đuổi trên: {item['khong_mua_duoi_tren']} | Mốc sai: {item['moc_sai']} | Mục tiêu gần: {item['muc_chot_gan']}")
    if item.get('ly_do'):
        lines.append('  Lý do: ' + '; '.join(item['ly_do']))
    return '\n'.join(lines)


def dong_thay_doi(payload):
    ss = payload.get('so_sanh_voi_lan_truoc', {})
    if not ss.get('co_so_sanh'):
        return 'Chưa có dữ liệu cũ để so sánh.'
    moi = ss.get('ma_moi_vao_danh_sach', [])
    bi_loai = ss.get('ma_bi_loai', [])
    return f"Thay đổi so với lần trước: thêm {', '.join(moi) if moi else 'không có'}; loại {', '.join(bi_loai) if bi_loai else 'không có'}."


def dong_ket(payload):
    ds = payload.get('danh_sach_ngan_han', [])
    if not ds:
        return 'Tối nay chưa thấy mã nào đủ hấp dẫn để ưu tiên hành động.'
    ma_dau = ds[0]['ma']
    return f'Mã đáng chú ý nhất tối nay: {ma_dau}. Ưu tiên làm đúng kế hoạch, không mua đuổi vô kỷ luật.'


def tao_ban_tin(payload):
    lines = []
    lines.append(dong_tieu_de(payload))
    lines.append('')
    lines.append(dong_boi_canh(payload))
    lines.append(dong_nhom(payload))
    lines.append(dong_thay_doi(payload))
    lines.append('')
    lines.append('Danh sách cần chú ý:')
    for item in payload.get('danh_sach_ngan_han', [])[:3]:
        lines.append(tom_tat_ma(item))
    lines.append('')
    lines.append(dong_ket(payload))
    return '\n'.join(lines)


def luu_ban_tin(text, ts):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    path = OUTPUT_DIR / f'{dt}.md'
    path.write_text(text, encoding='utf-8')
    return str(path)


def main():
    payload = run_report(top=5)
    text = tao_ban_tin(payload)
    path = luu_ban_tin(text, payload['thoi_gian'])
    print(json.dumps({'thoi_gian': payload['thoi_gian'], 'duong_dan': path, 'ban_tin': text}, ensure_ascii=False))


if __name__ == '__main__':
    main()
