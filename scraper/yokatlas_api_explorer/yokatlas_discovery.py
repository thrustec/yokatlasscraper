#!/usr/bin/env python3
"""YOK Atlas read-only API discovery and field profiling. Python 3.10+."""
import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    raise SystemExit('Install dependency: pip install requests')

BASE = 'https://yokatlas.yok.gov.tr'
LOOKUPS = {
    'universiteler': '/api/tercih-kilavuz/universiteler',
    'program_gruplari': '/api/tercih-kilavuz/universite-programlar',
    'iller': '/api/tercih-kilavuz/universite-iller',
}
PROGRAM_PATH = '/api/tercih-kilavuz/search'
NET_PATH = '/api/netler/search'
SCORES = ['SAY', 'EA', 'SÖZ', 'DİL', 'TYT']


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding='utf-8')


def kind(v):
    if v is None: return 'null'
    if isinstance(v, bool): return 'boolean'
    if isinstance(v, int): return 'integer'
    if isinstance(v, float): return 'number'
    if isinstance(v, str): return 'string'
    if isinstance(v, list): return 'array'
    return 'object' if isinstance(v, dict) else type(v).__name__


def walk(v, path, observations):
    """Profile nested JSON, preserving array item paths and optional fields."""
    if path:
        item = observations[path]
        item['occurrences'] += 1
        item['types'][kind(v)] += 1
        if v is not None and len(item['examples']) < 3:
            example = json.dumps(v, ensure_ascii=False, default=str)
            if len(example) <= 250 and example not in item['examples']:
                item['examples'].append(example)
    if isinstance(v, dict):
        for k, val in v.items():
            walk(val, f'{path}.{k}' if path else k, observations)
    elif isinstance(v, list):
        for child in v:
            walk(child, f'{path}[]', observations)


def new_obs():
    return defaultdict(lambda: {'occurrences': 0, 'types': defaultdict(int), 'examples': []})


class API:
    def __init__(self, base, delay, timeout, max_requests):
        self.base = base.rstrip('/')
        self.delay = delay
        self.timeout = timeout
        self.max_requests = max_requests
        self.count = 0
        self.last = 0
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json', 'User-Agent': 'YOKAtlasResearchDiscovery/1.0 (read-only)'})
        self.log = []

    def request(self, label, method, path, payload=None):
        if self.count >= self.max_requests:
            raise RuntimeError(f'Request cap reached ({self.max_requests})')
        pause = max(0, self.delay - (time.monotonic() - self.last))
        if pause:
            time.sleep(pause)
        self.count += 1
        start = time.monotonic()
        record = {'name': label, 'method': method, 'path': path, 'request': payload}
        try:
            response = self.session.request(method, self.base + path, json=payload, timeout=self.timeout)
            record.update({'status': response.status_code, 'elapsed_seconds': round(time.monotonic()-start, 2), 'content_type': response.headers.get('Content-Type', '')})
            if response.status_code in (418, 429):
                record['error'] = 'rate limited; stopped without retry'
                raise RuntimeError(f'Rate limit HTTP {response.status_code}, stopping.')
            if response.status_code >= 400:
                record['error'] = response.text[:300]
                return None
            if 'json' not in response.headers.get('Content-Type','').lower():
                record['error'] = 'non-JSON response: ' + response.text[:200]
                return None
            return response.json()
        except requests.RequestException as exc:
            record['error'] = str(exc)
            return None
        finally:
            self.last = time.monotonic()
            self.log.append(record)
            print(f"[{self.count}/{self.max_requests}] {label}: HTTP {record.get('status','network error')}", flush=True)


def page_content(data):
    if isinstance(data, dict) and isinstance(data.get('content'), list):
        return data['content']
    if isinstance(data, list):
        return data
    return []


def main():
    p = argparse.ArgumentParser(description='Read-only discovery of documented YOK Atlas JSON endpoints')
    p.add_argument('--out', default='yokatlas_discovery_output')
    p.add_argument('--base-url', default=BASE)
    p.add_argument('--delay', type=float, default=1.5, help='Minimum seconds between requests')
    p.add_argument('--timeout', type=float, default=25)
    p.add_argument('--size', type=int, default=20, help='Page size (1..100)')
    p.add_argument('--pages-per-score', type=int, default=1, help='Program pages per score')
    p.add_argument('--net-pages-per-score', type=int, default=1)
    p.add_argument('--max-requests', type=int, default=30)
    p.add_argument('--save-all-pages', action='store_true', help='Save every sampled page, not just first')
    args = p.parse_args()
    if args.delay < 1 or not 1 <= args.size <= 100 or args.pages_per_score < 1 or args.net_pages_per_score < 1 or args.max_requests < 5:
        p.error('Require delay >= 1s, size 1..100, page counts >= 1, max-requests >= 5')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    api = API(args.base_url, args.delay, args.timeout, args.max_requests)
    obs = {k: new_obs() for k in [*LOOKUPS, 'program_arama', 'net_arama']}
    summary = {'started_at': datetime.now(timezone.utc).isoformat(), 'endpoint_results': {}, 'score_results': {}}
    try:
        for name, path in LOOKUPS.items():
            data = api.request(name, 'GET', path)
            if data is None:
                summary['endpoint_results'][name] = {'ok': False}
                continue
            save_json(out / 'lookups' / (name + '.json'), data)
            walk(data, '', obs[name])
            summary['endpoint_results'][name] = {'ok': True, 'records': len(page_content(data)) if isinstance(data, list) else len(data) if isinstance(data, dict) else None}

        for kind_name, path, max_pages in [('program_arama', PROGRAM_PATH, args.pages_per_score), ('net_arama', NET_PATH, args.net_pages_per_score)]:
            for score in SCORES:
                total_records = 0
                for page_no in range(max_pages):
                    payload = {'filters': {'puanTuru': score}, 'page': page_no, 'size': args.size}
                    if kind_name == 'program_arama':
                        payload.update({'sortBy': 'basariSirasi', 'direction': 'ASC'})
                    name = f'{kind_name}_{score}_page{page_no}'
                    data = api.request(name, 'POST', path, payload)
                    if data is None:
                        break
                    walk(data, '', obs[kind_name])
                    records = page_content(data)
                    total_records += len(records)
                    if page_no == 0 or args.save_all_pages:
                        save_json(out / 'samples' / (name + '.json'), data)
                    if not records or (isinstance(data, dict) and data.get('last') is True):
                        break
                summary['score_results'][f'{kind_name}_{score}'] = {'sampled_records': total_records}
    except RuntimeError as exc:
        summary['stopped_reason'] = str(exc)
        print(f'Stopped: {exc}', file=sys.stderr)
    finally:
        api.session.close()
        summary['finished_at'] = datetime.now(timezone.utc).isoformat()
        summary['request_count'] = api.count
        save_json(out / 'summary.json', summary)
        save_json(out / 'requests.json', api.log)
        fields = []
        for endpoint, mapping in obs.items():
            for path, values in sorted(mapping.items()):
                fields.append({'endpoint': endpoint, 'json_path': path,
                               'occurrences': values['occurrences'],
                               'types': '|'.join(f'{k}:{v}' for k, v in sorted(values['types'].items())),
                               'examples': ' | '.join(values['examples'])})
        with (out / 'field_inventory.csv').open('w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['endpoint','json_path','occurrences','types','examples'])
            writer.writeheader()
            writer.writerows(fields)
        save_json(out / 'field_inventory.json', fields)
        print(f'\nSaved {len(fields)} observed JSON paths under {out.resolve()}')
        print(f'Requests: {api.count}; successful sample files: {len(list((out / "samples").glob("*.json"))) if (out / "samples").exists() else 0}')


if __name__ == '__main__':
    main()
