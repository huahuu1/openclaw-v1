import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

TIMEOUT = 15
POSITIVE_KEYWORDS = [
    'tăng trần', 'bứt phá', 'mua ròng', 'cổ tức', 'lợi nhuận', 'kỷ lục',
    'hưởng lợi', 'tăng trưởng', 'vượt đỉnh', 'khuyến nghị mua', 'mở rộng',
    'động lực', 'hồi phục', 'bệ đỡ', 'tích cực', 'đỡ thị trường', 'dẫn sóng',
    'kế hoạch', 'thoái vốn', 'mục tiêu', 'mua vào', 'hé lộ kết quả kinh doanh'
]
NEGATIVE_KEYWORDS = [
    'bán ròng', 'giảm sàn', 'chốt lời', 'áp lực bán', 'điều chỉnh', 'suy giảm',
    'cảnh báo', 'rủi ro', 'khởi tố', 'thanh tra', 'thua lỗ', 'nợ xấu',
    'pha loãng', 'trì hoãn', 'tiêu cực', 'xả', 'bị bán', 'thoát hàng', 'ngập ngừng'
]
SHORT_TERM_POSITIVE = ['tăng trần', 'bứt phá', 'đỡ thị trường', 'dẫn sóng', 'mua ròng', 'khuyến nghị mua', 'vượt đỉnh', 'hồi phục']
SHORT_TERM_NEGATIVE = ['bán ròng', 'giảm sàn', 'chốt lời', 'áp lực bán', 'điều chỉnh', 'xả', 'thoát hàng']
MEDIUM_TERM_POSITIVE = ['cổ tức', 'lợi nhuận', 'kỷ lục', 'tăng trưởng', 'mở rộng', 'thoái vốn', 'mục tiêu', 'kế hoạch', 'hưởng lợi', 'kết quả kinh doanh']
MEDIUM_TERM_NEGATIVE = ['thua lỗ', 'nợ xấu', 'pha loãng', 'trì hoãn', 'khởi tố', 'thanh tra', 'cảnh báo', 'rủi ro']
SOURCE_BONUS = {
    'vnexpress.net': 2,
    'cafef.vn': 2,
    'vietstock.vn': 2,
    'fili.vn': 2,
    'nguoiquansat.vn': 2,
    'dantri.com.vn': 1,
}
SOURCE_PRIORITY = {
    'cafef': 100,
    'vietstock': 95,
    'fili': 92,
    'vnexpress': 90,
    'nguoiquansat': 88,
    'tinnhanhchungkhoan': 86,
    'stockbiz': 84,
    'ndh': 82,
    'dantri': 78,
}


def http_get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode('utf-8', errors='ignore')


def parse_google_news_rss(query, limit=8):
    q = urllib.parse.quote(query)
    url = f'https://news.google.com/rss/search?q={q}&hl=vi&gl=VN&ceid=VN:vi'
    xml_text = http_get(url)
    root = ET.fromstring(xml_text)
    items = []
    for item in root.findall('./channel/item')[:limit]:
        title = (item.findtext('title') or '').strip()
        link = (item.findtext('link') or '').strip()
        pub = (item.findtext('pubDate') or '').strip()
        source = ''
        source_el = item.find('source')
        if source_el is not None:
            source = (source_el.text or '').strip()
        items.append({
            'title': title,
            'link': link,
            'pubDate': pub,
            'source': source,
        })
    return items


def hours_ago(pub_date):
    if not pub_date:
        return None
    try:
        dt = parsedate_to_datetime(pub_date)
        return max(0.0, (time.time() - dt.timestamp()) / 3600)
    except Exception:
        return None


def score_headline(title, source='', age_hours=None):
    text = title.lower()
    score = 0
    hits = []
    for kw in POSITIVE_KEYWORDS:
        if kw in text:
            score += 2
            hits.append(f'+:{kw}')
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            score -= 2
            hits.append(f'-:{kw}')
    for host_kw, bonus in SOURCE_BONUS.items():
        if host_kw in source.lower():
            score += bonus
            hits.append(f'source:{host_kw}')
            break
    freshness = 'unknown'
    if age_hours is not None:
        if age_hours <= 24:
            score += 1
            hits.append('fresh')
            freshness = 'fresh'
        elif age_hours <= 72:
            freshness = 'recent'
        else:
            score -= 1
            hits.append('stale')
            freshness = 'stale'
    return score, hits, freshness


def tom_tat_tieu_de(title):
    t = (title or '').strip()
    if not t:
        return ''
    parts = [x.strip(' -–—') for x in t.replace('“', '"').replace('”', '"').split(' - ') if x.strip()]
    if parts:
        return parts[0]
    return t


def diem_theo_nhom_tu_khoa(title, keywords):
    text = (title or '').lower()
    return sum(1 for kw in keywords if kw in text)


def impact_from_score(score):
    if score >= 4:
        return 'mạnh'
    if score >= 1:
        return 'vừa'
    if score <= -4:
        return 'mạnh'
    if score <= -1:
        return 'vừa'
    return 'yếu'


def classify_news_type(title):
    text = (title or '').lower()
    if any(x in text for x in ['lợi nhuận', 'kết quả kinh doanh', 'cổ tức', 'đhcđ', 'mục tiêu', 'kế hoạch']):
        return 'tin doanh nghiệp'
    if any(x in text for x in ['mua ròng', 'bán ròng', 'cổ đông lớn', 'gom thêm', 'thoái vốn']):
        return 'tin dòng tiền'
    if any(x in text for x in ['lãi suất', 'vĩ mô', 'tỷ giá', 'vn-index', 'thị trường']):
        return 'tin vĩ mô/thị trường'
    return 'tin tổng hợp'


def danh_gia_xu_the_tin(items, total_score):
    short_score = 0
    medium_score = 0
    cac_anh_huong = []
    for it in items[:5]:
        title = it.get('title', '')
        short_score += diem_theo_nhom_tu_khoa(title, SHORT_TERM_POSITIVE)
        short_score -= diem_theo_nhom_tu_khoa(title, SHORT_TERM_NEGATIVE)
        medium_score += diem_theo_nhom_tu_khoa(title, MEDIUM_TERM_POSITIVE)
        medium_score -= diem_theo_nhom_tu_khoa(title, MEDIUM_TERM_NEGATIVE)

        score = it.get('score', 0)
        if score > 0:
            nghieng = 'tích cực'
        elif score < 0:
            nghieng = 'tiêu cực'
        else:
            nghieng = 'trung tính'

        if title:
            cac_anh_huong.append({
                'tieu_de': title,
                'tom_tat': tom_tat_tieu_de(title),
                'nguon': it.get('source'),
                'duong_dan': it.get('link'),
                'gio_dang': it.get('pubDate'),
                'so_gio_truoc': it.get('age_hours'),
                'nghieng': nghieng,
                'muc_anh_huong': impact_from_score(score),
                'thoi_gian_anh_huong': 'ngắn hạn' if abs(short_score) >= abs(medium_score) else 'trung hạn',
                'loai_tin': it.get('news_type'),
                'freshness': it.get('freshness'),
            })

    if short_score >= 3:
        tac_dong_ngan_han = 'nghiêng tăng'
    elif short_score <= -3:
        tac_dong_ngan_han = 'nghiêng giảm'
    else:
        tac_dong_ngan_han = 'trung tính'

    if medium_score >= 3:
        tac_dong_trung_han = 'nghiêng tăng'
    elif medium_score <= -3:
        tac_dong_trung_han = 'nghiêng giảm'
    else:
        tac_dong_trung_han = 'trung tính'

    if total_score >= 8:
        ket_luan = 'nghiêng tăng rõ'
        do_tin_cay = 'khá cao'
    elif total_score >= 3:
        ket_luan = 'nghiêng tăng'
        do_tin_cay = 'trung bình'
    elif total_score <= -8:
        ket_luan = 'nghiêng giảm rõ'
        do_tin_cay = 'khá cao'
    elif total_score <= -3:
        ket_luan = 'nghiêng giảm'
        do_tin_cay = 'trung bình'
    else:
        ket_luan = 'trung tính'
        do_tin_cay = 'thấp'

    return {
        'tac_dong_ngan_han': tac_dong_ngan_han,
        'tac_dong_trung_han': tac_dong_trung_han,
        'ket_luan_xu_the_tin': ket_luan,
        'do_tin_cay_xu_the_tin': do_tin_cay,
        'tin_tom_tat': cac_anh_huong[:3],
    }


def diem_uu_tien_nguon(source):
    text = (source or '').lower().replace(' ', '').replace('.', '')
    for key, diem in SOURCE_PRIORITY.items():
        if key in text:
            return diem
    return 50


def score_symbol_news(symbol, limit=8):
    query = f'{symbol} chứng khoán'
    items = parse_google_news_rss(query, limit=limit)
    scored = []
    total = 0
    for it in items:
        age = hours_ago(it.get('pubDate'))
        sc, hits, freshness = score_headline(it.get('title', ''), it.get('link', '') + ' ' + it.get('source', ''), age)
        total += sc
        scored.append({
            **it,
            'age_hours': round(age, 1) if age is not None else None,
            'score': sc,
            'hits': hits,
            'summary': tom_tat_tieu_de(it.get('title', '')),
            'nguon_hien_thi': it.get('source') or '',
            'duong_dan_goc': it.get('link') or '',
            'diem_uu_tien_nguon': diem_uu_tien_nguon(it.get('source')),
            'freshness': freshness,
            'impact_level': impact_from_score(sc),
            'news_type': classify_news_type(it.get('title', '')),
            'price_relevance': 'cao' if freshness == 'fresh' and abs(sc) >= 3 else 'vừa' if abs(sc) >= 1 else 'thấp',
        })
    scored.sort(key=lambda x: (x.get('freshness') == 'fresh', x.get('diem_uu_tien_nguon', 0), x.get('score', 0), -(x.get('age_hours') or 9999)), reverse=True)
    verdict = 'neutral'
    if total >= 5:
        verdict = 'positive'
    elif total <= -5:
        verdict = 'negative'
    xu_the_tin = danh_gia_xu_the_tin(scored, total)
    return {
        'symbol': symbol,
        'query': query,
        'news_score': total,
        'verdict': verdict,
        'items': scored,
        **xu_the_tin,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('symbols', nargs='+')
    parser.add_argument('--limit', type=int, default=8)
    args = parser.parse_args()
    payload = {'ts': int(time.time()), 'results': [score_symbol_news(s, args.limit) for s in args.symbols]}
    print(json.dumps(payload, ensure_ascii=False))
