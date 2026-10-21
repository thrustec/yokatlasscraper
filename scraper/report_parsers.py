"""Verified SEGE and URAP PDF layouts; a changed layout fails closed."""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
import math
import re
import unicodedata

import pdfplumber


PARSER_VERSION = 'reports-pdf-1'
DIMENSIONS = ('demografi', 'istihdam', 'egitim', 'saglik', 'rekabetcilik_yenilikcilik',
              'mali', 'erisilebilirlik', 'yasam_kalitesi')
INDICATORS = ('makale', 'atif', 'bilimsel_dokuman', 'doktora', 'ogretim_uyesi_ogrenci',
              'uluslararasi_isbirligi', 'yurtici_isbirligi', 'tubitak_proje')
# shortcut: only these editions have verified layouts; add a parser before accepting a new edition.
REPORTS = {
    'sege-il-2025': {
        'bot': 'sege', 'edition': '2025', 'title': 'SEGE 2025 il ve bölge sonuçları',
        'url': 'https://www.kalkinmakutuphanesi.gov.tr/assets/upload/dosyalar/l-sege-2025.pdf',
        'pages': 113, 'counts': {'il': 81, 'bolge': 26},
    },
    'sege-ilce-2022': {
        'bot': 'sege', 'edition': '2022', 'title': 'SEGE 2022 ilçe sonuçları',
        'url': 'https://www.kalkinmakutuphanesi.gov.tr/assets/upload/dosyalar/2022-ilce-sege.pdf',
        'pages': 71, 'counts': {'ilce': 973},
    },
    'urap-tr-2025-2026': {
        'bot': 'urap', 'edition': '2025-2026', 'title': 'URAP 2025-2026 Türkiye genel sıralaması',
        'url': 'https://newtr.urapcenter.org/cdn/storage/PDFs/mezDn2uAd4mx2mZzW/original/mezDn2uAd4mx2mZzW.pdf',
        'pages': 31, 'counts': {'universite': 198},
    },
}


class ReportError(RuntimeError):
    """An operator-safe error; source bodies and connection secrets are excluded."""


def clean(value):
    return re.sub(r'\s+', ' ', (value or '').replace('-\n', '-')).strip()


def name_key(value):
    value = clean(value).translate(str.maketrans({'ı': 'i', 'İ': 'I'}))
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', value)


def number(value):
    text = clean(value).replace('\u2212', '-')
    if not re.fullmatch(r'-?\d+(?:[,.]\d+)?', text):
        raise ReportError('PDF tablosunda beklenmeyen sayı biçimi var.')
    return float(text.replace(',', '.'))


def stopped(monitor):
    if monitor and monitor.should_stop():
        raise KeyboardInterrupt


def tables(pdf, page_numbers, monitor=None):
    for index, n in enumerate(page_numbers):
        stopped(monitor)
        if monitor:
            monitor.progress(index, len(page_numbers), f'PDF: sayfa {n}')
        for table in pdf.pages[n - 1].extract_tables():
            yield n, table


def _ranked(rows, count, name_field):
    ranks = [r['sira'] for r in rows]
    if len(rows) != count or set(ranks) != set(range(1, count + 1)):
        raise ReportError(f'PDF sıra kapsamı eksik veya yineleniyor; {count} kayıt bekleniyor.')
    keys = [(name_key(r.get('il_adi', '')) if name_field != 'universite_adi' else '',
             name_key(r[name_field])) for r in rows]
    if len(set(keys)) != count or any(not k[1] for k in keys):
        raise ReportError('PDF yerleşim/üniversite adları boş veya yineleniyor.')
    ordered = sorted(rows, key=lambda r: r['sira'])
    score_field = 'toplam_puan' if name_field == 'universite_adi' else 'skor'
    if any(a[score_field] < b[score_field] for a, b in zip(ordered, ordered[1:])):
        raise ReportError('PDF sıralaması ile puanların yönü uyuşmuyor.')


def _province(pdf, monitor):
    rows = []
    for page, table in tables(pdf, [47], monitor):
        if [clean(c) for c in table[0]] != ['Sıra', 'İl Adı', 'Skor', 'Kademe']:
            continue
        for rank, name, score, tier in table[1:]:
            rows.append({'yerlesim_duzeyi': 'il', 'yerlesim_adi': clean(name), 'il_adi': clean(name),
                         'sira': int(rank), 'skor': number(score), 'kademe': int(tier),
                         'source_page': page, 'source_table': 'Tablo 12'})
    by_name = {name_key(r['il_adi']): r for r in rows}
    dimensions = {}
    for page, table in tables(pdf, [86, 87], monitor):
        for cells in table:
            if len(cells) != 10 or not clean(cells[1]).isdigit():
                continue
            key = name_key(cells[0])
            if key not in by_name or key in dimensions or int(cells[1]) != by_name[key]['sira']:
                raise ReportError('SEGE alt boyut tablosu il sıralamasıyla uyuşmuyor.')
            dimensions[key] = dict(zip(DIMENSIONS, (int(c) for c in cells[2:])))
            by_name[key].update(alt_boyut_siralari=dimensions[key], dimension_source_page=page)
    if len(dimensions) != 81:
        raise ReportError('SEGE alt boyut tablosunda 81 il bulunamadı.')
    for page, table in tables(pdf, [89], monitor):
        for cells in table:
            if len(cells) != 5 or not re.fullmatch(r'TR[A-C0-9][0-9]', clean(cells[0])):
                continue
            code, members, score, tier, rank = cells
            rows.append({'yerlesim_duzeyi': 'bolge', 'yerlesim_adi': clean(code), 'bolge_kodu': clean(code),
                         'bolge_illeri': [clean(v) for v in clean(members).split(',')],
                         'sira': int(rank), 'skor': number(score), 'kademe': int(tier),
                         'source_page': page, 'source_table': 'Tablo 21'})
    return rows


def _district(pdf, monitor):
    general = {}
    for page, table in tables(pdf, list(range(42, 50)), monitor):
        for cells in table:
            if len(cells) != 4 or not clean(cells[0]).isdigit():
                continue
            rank, province, district, score = cells
            rank = int(rank)
            if rank in general:
                raise ReportError('SEGE ilçe genel sırasında yinelenen satır var.')
            general[rank] = {'yerlesim_duzeyi': 'ilce', 'yerlesim_adi': clean(district),
                             'il_adi': clean(province), 'sira': rank, 'skor': number(score),
                             'source_page': page, 'source_table': 'Ek-1'}
    supplemental = set()
    for page, table in tables(pdf, list(range(49, 71)), monitor):
        for cells in table:
            if len(cells) != 5 or not clean(cells[1]).isdigit():
                continue
            district, rank, province_rank, score, tier = cells
            rank = int(rank)
            row = general.get(rank)
            if (not row or rank in supplemental or name_key(row['yerlesim_adi']) != name_key(district)
                    or row['skor'] != number(score)):
                raise ReportError('SEGE Ek-1 ve Ek-2 ilçe kayıtları uyuşmuyor.')
            row.update(il_ici_sira=int(province_rank), kademe=int(tier), supplement_source_page=page)
            supplemental.add(rank)
    if supplemental != set(general):
        raise ReportError('SEGE ilçe kademesi veya il içi sıralaması eksik.')
    return list(general.values())


def _urap(pdf, monitor):
    rows = []
    for page, table in tables(pdf, list(range(18, 27)), monitor):
        for cells in table:
            # The rotated header introduces empty border cells on the first table page.
            cells = [clean(c) for c in cells if clean(c)]
            if len(cells) != 12 or not cells[0].isdigit():
                continue
            values = [number(c) for c in cells[3:]]
            rows.append({'universite_adi': cells[1], 'il_adi': cells[2], 'sira': int(cells[0]),
                         'puanlar': dict(zip(INDICATORS, values[:8])), 'toplam_puan': values[8],
                         'source_page': page, 'source_table': 'Tablo 10'})
    return rows


def validate_extraction(data, report_id):
    spec = REPORTS[report_id]
    if (data.get('report_id') != report_id or data.get('edition') != spec['edition']
            or data.get('parser_version') != PARSER_VERSION or data.get('source_system') != spec['bot']):
        raise ReportError('Arşiv rapor kimliği veya ayrıştırıcı sürümü uyuşmuyor.')
    rows = data.get('records')
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ReportError('Ayrıştırılmış rapor kayıt listesi geçersiz.')
    counts = Counter(r.get('yerlesim_duzeyi', 'universite') for r in rows)
    if dict(counts) != spec['counts'] or data.get('counts') != spec['counts']:
        raise ReportError('Ayrıştırılmış raporun kayıt sayıları beklenen kapsamla uyuşmuyor.')
    for row in rows:
        for key in ['sira', 'source_page']:
            if (type(row.get(key)) is not int or row[key] < 1
                    or (key == 'source_page' and row[key] > spec['pages'])):
                raise ReportError('PDF satırında sıra/sayfa alanı geçersiz.')
        for key in ['source_table', 'universite_adi' if spec['bot'] == 'urap' else 'yerlesim_adi']:
            if not isinstance(row.get(key), str) or not clean(row[key]):
                raise ReportError('PDF satırında ad veya kaynak tablo alanı boş.')
        if row.get('yerlesim_duzeyi') != 'bolge' and (not isinstance(row.get('il_adi'), str) or not clean(row['il_adi'])):
            raise ReportError('PDF satırında il adı boş.')
        value = row.get('toplam_puan' if spec['bot'] == 'urap' else 'skor')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ReportError('PDF satırında geçersiz puan var.')
        if spec['bot'] == 'urap':
            scores = row.get('puanlar', {})
            if set(scores) != set(INDICATORS) or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in scores.values()):
                raise ReportError('URAP bileşen puanları eksik veya geçersiz.')
            if abs(sum(Decimal(str(v)) for v in scores.values()) - Decimal(str(value))) > Decimal('0.05'):
                raise ReportError('URAP toplam puanı bileşenlerin toplamıyla uyuşmuyor.')
        else:
            maximum = 4 if row['yerlesim_duzeyi'] == 'bolge' else 6
            if type(row.get('kademe')) is not int or not 1 <= row['kademe'] <= maximum:
                raise ReportError('SEGE gelişmişlik kademesi geçersiz.')
            if row['yerlesim_duzeyi'] == 'il':
                dims = row.get('alt_boyut_siralari', {})
                if set(dims) != set(DIMENSIONS) or any(type(v) is not int or not 1 <= v <= 81 for v in dims.values()):
                    raise ReportError('SEGE alt boyut sıraları eksik veya geçersiz.')
    if spec['bot'] == 'urap':
        _ranked(rows, 198, 'universite_adi')
    else:
        for level, count in spec['counts'].items():
            _ranked([r for r in rows if r['yerlesim_duzeyi'] == level], count, 'yerlesim_adi')
        if 'ilce' in spec['counts']:
            by_province = defaultdict(list)
            for row in rows:
                if type(row.get('il_ici_sira')) is not int or row['il_ici_sira'] < 1:
                    raise ReportError('SEGE il içi sırası geçersiz.')
                by_province[name_key(row['il_adi'])].append(row.get('il_ici_sira'))
            if len(by_province) != 81 or any(set(ranks) != set(range(1, len(ranks) + 1)) for ranks in by_province.values()):
                raise ReportError('SEGE il içi sıraları eksik veya yineleniyor.')
        else:
            provinces = {name_key(r['il_adi']) for r in rows if r['yerlesim_duzeyi'] == 'il'}
            members = [name_key(m) for r in rows if r['yerlesim_duzeyi'] == 'bolge' for m in r.get('bolge_illeri', [])]
            if len(members) != 81 or set(members) != provinces:
                raise ReportError('SEGE bölge-il kapsamı eksik veya yineleniyor.')
    return data


def parse_report(path, report_id, monitor=None):
    spec = REPORTS[report_id]
    try:
        with pdfplumber.open(path) as pdf:
            if len(pdf.pages) != spec['pages']:
                raise ReportError('PDF sayfa sayısı değişmiş; rapor sürümü incelenmeli.')
            identity = name_key(' '.join(p.extract_text() or '' for p in pdf.pages[:3]))
            if name_key(spec['edition']) not in identity or name_key(spec['bot']) not in identity:
                raise ReportError('PDF başlığı seçilen rapor/dönem ile uyuşmuyor.')
            parser = {'sege-il-2025': _province, 'sege-ilce-2022': _district,
                      'urap-tr-2025-2026': _urap}[report_id]
            rows = parser(pdf, monitor)
        data = {'report_id': report_id, 'source_system': spec['bot'], 'edition': spec['edition'],
                'parser_version': PARSER_VERSION, 'counts': dict(Counter(r.get('yerlesim_duzeyi', 'universite') for r in rows)),
                'records': sorted(rows, key=lambda r: (r.get('yerlesim_duzeyi', ''), r['sira']))}
        return validate_extraction(data, report_id)
    except (ReportError, KeyboardInterrupt):
        raise
    except Exception as exc:
        raise ReportError(f'PDF ayrıştırılamadı ({type(exc).__name__}); kaynak biçimini kontrol edin.') from None
