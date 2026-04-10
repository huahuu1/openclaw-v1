import json


def lam_tron_lo(quantity):
    if quantity <= 0:
        return 0
    # Cổ phiếu Việt Nam thường giao dịch theo lô 100 cp
    return int(quantity // 100) * 100


def tinh_kich_thuoc_vi_the(tai_khoan, rui_ro_phan_tram, gia_vao, moc_sai, ti_le_toi_da_vao_lenh=0.2):
    if gia_vao <= 0 or moc_sai <= 0 or gia_vao <= moc_sai or tai_khoan <= 0:
        return {
            'hop_le': False,
            'ly_do': 'Dữ liệu đầu vào không hợp lệ để tính vị thế'
        }

    # Giá cổ phiếu Việt Nam trong feed thường ở đơn vị nghìn đồng
    gia_vao_vnd = gia_vao * 1000
    moc_sai_vnd = moc_sai * 1000

    tien_rui_ro_toi_da = tai_khoan * rui_ro_phan_tram / 100
    rui_ro_moi_co = gia_vao_vnd - moc_sai_vnd
    so_co_theo_rui_ro = tien_rui_ro_toi_da / rui_ro_moi_co
    so_co_lam_tron = lam_tron_lo(so_co_theo_rui_ro)

    gia_tri_lenh_theo_rui_ro = so_co_lam_tron * gia_vao_vnd
    tran_theo_ty_trong = tai_khoan * ti_le_toi_da_vao_lenh
    so_co_theo_ty_trong = lam_tron_lo(tran_theo_ty_trong / gia_vao_vnd)

    so_co_de_xuat = min(so_co_lam_tron, so_co_theo_ty_trong)
    gia_tri_lenh_de_xuat = round(so_co_de_xuat * gia_vao_vnd, 2)
    rui_ro_thuc_te = round(so_co_de_xuat * rui_ro_moi_co, 2)

    return {
        'hop_le': True,
        'tai_khoan': tai_khoan,
        'rui_ro_phan_tram': rui_ro_phan_tram,
        'tien_rui_ro_toi_da': round(tien_rui_ro_toi_da, 2),
        'rui_ro_moi_co': round(rui_ro_moi_co, 2),
        'so_co_theo_rui_ro': so_co_lam_tron,
        'so_co_theo_ty_trong': so_co_theo_ty_trong,
        'so_co_de_xuat': so_co_de_xuat,
        'gia_tri_lenh_de_xuat': gia_tri_lenh_de_xuat,
        'rui_ro_thuc_te': rui_ro_thuc_te,
        'ti_le_toi_da_vao_lenh': ti_le_toi_da_vao_lenh,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--tai-khoan', type=float, required=True)
    parser.add_argument('--rui-ro', type=float, default=1.0)
    parser.add_argument('--gia-vao', type=float, required=True)
    parser.add_argument('--moc-sai', type=float, required=True)
    parser.add_argument('--ti-le-toi-da', type=float, default=0.2)
    args = parser.parse_args()
    payload = tinh_kich_thuoc_vi_the(args.tai_khoan, args.rui_ro, args.gia_vao, args.moc_sai, args.ti_le_toi_da)
    print(json.dumps(payload, ensure_ascii=False))
