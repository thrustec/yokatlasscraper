#!/usr/bin/env python3
"""KYGM public HTML table research pilot. Read-only; no database writes."""
import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = 'https://kygm.gsb.gov.tr/Sayfalar/2635/2389/yurt-bulunan-il-ve-ilceler.aspx'
VALID_GENDERS = {'KIZ', 'ERKEK', 'KIZ VE ERKEK'}
HEADERS = {'İL', 'İLÇE', 'CİNSİYET'}

def clean(value):
    return re.sub(r'\s+', ' ', value.replace('\xa0', ' ')).strip()

def parse_table(html: bytes):
    soup = BeautifulSoup(html, 'html.parser')
    candidates = []
    for table in soup.find_all('table'):
        trs = table.find_all('tr')
        if not trs:
            continue
        for idx, tr in enumerate(trs):
            header = [clean(c.get_text(' ', strip=True)).upper() for c in tr.find_all(['th', 'td'], recursive=False)]
            if header[:3] == ['İL', 'İLÇE', 'CİNSİYET']:
                candidates.append((table, idx))
                break
    if len(candidates) != 1:
        raise ValueError(f'Expected 1 KYGM table with exact columns, found {len(candidates)}')
    table, header_idx = candidates[0]
    entries, anomalies = [], []
    trs = table.find_all('tr')
    for row_idx, tr in enumerate(trs[header_idx + 1:], start=header_idx + 2):
        cells = [clean(c.get_text(' ', strip=True)) for c in tr.find_all(['th', 'td'], recursive=False)]
        if not any(cells):
            continue
        if len(cells) != 3:
            anomalies.append({'row': row_idx, 'issue': 'unexpected_column_count', 'cells': cells})
            continue
        il, ilce, gender = cells
        if not all((il, ilce, gender)) or gender.upper() not in VALID_GENDERS:
            anomalies.append({'row': row_idx, 'issue': 'invalid_or_empty_field', 'cells': cells})
        entries.append({'il_raw': il, 'ilce_raw': ilce, 'cinsiyet_raw': gender,
                        'source_row_index': row_idx, 'gender_code': {'KIZ': 'FEMALE', 'ERKEK': 'MALE', 'KIZ VE ERKEK': 'BOTH'}.get(gender.upper(), 'UNKNOWN')})
    if not entries:
        raise ValueError('No data rows extracted from KYGM table')
    return entries, anomalies

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html-file', type=Path, help='Parse previously downloaded HTML instead of requesting website')
    parser.add_argument('--output', type=Path, default=Path('kygm_output'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    received = datetime.now(timezone.utc).isoformat()
    status, content_type, final_url = None, None, URL
    if args.html_file:
        body = args.html_file.read_bytes()
        final_url = str(args.html_file)
        status = 'offline_fixture'
        content_type = 'text/html'
    else:
        response = requests.get(URL, timeout=25, headers={'User-Agent': 'YokatlasIntelligenceResearch/0.1 (read-only KYGM public table pilot)', 'Accept': 'text/html'}, allow_redirects=True)
        response.raise_for_status()
        body, status = response.content, response.status_code
        content_type, final_url = response.headers.get('Content-Type'), response.url
        if 'text/html' not in (content_type or '').lower():
            raise ValueError(f'Unexpected Content-Type: {content_type}')
    digest = hashlib.sha256(body).hexdigest()
    rows, anomalies = parse_table(body)
    (args.output / 'kygm_source.html').write_bytes(body)
    with (args.output / 'kygm_rows.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    keys = Counter((r['il_raw'], r['ilce_raw'], r['cinsiyet_raw']) for r in rows)
    report = {'source_url': URL, 'final_url': final_url, 'captured_at_utc': received,
              'http_status': status, 'content_type': content_type, 'source_sha256': digest,
              'byte_size': len(body), 'row_count': len(rows), 'unique_provinces_or_labels': len({r['il_raw'] for r in rows}),
              'gender_counts': dict(Counter(r['gender_code'] for r in rows)),
              'merkez_count': sum(r['ilce_raw'].upper() == 'MERKEZ' for r in rows),
              'kibris_count': sum(r['il_raw'].upper() == 'KIBRIS' for r in rows),
              'duplicate_keys': [{'key': list(k), 'count': v} for k,v in keys.items() if v > 1],
              'anomalies': anomalies,
              'limitations': ['Presence listing, not count/capacity/address of dormitories', 'Missing locality != no dorm', 'MERKEZ cannot be confidently resolved to a present-day administrative district']}
    (args.output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if anomalies or any(v > 1 for v in keys.values()):
        sys.exit(2)

if __name__ == '__main__':
    main()
