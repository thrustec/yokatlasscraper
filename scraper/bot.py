"""Sequential YOK Atlas collector with resumable JSON archives and PostgreSQL ETL.

Run from the repository root: python -m scraper.bot run --archive-only
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import secrets
import time

import requests

from scraper.yokatlas_api_explorer.yokatlas_full_validator import dump, now, SCORES
from scripts.database.load_archive import ENTITIES, PATHS, import_archive

BASE_URL = 'https://yokatlas.yok.gov.tr'
LOG = logging.getLogger('yokatlas.bot')


class Paused(RuntimeError):
    def __init__(self, message, delay=300):
        super().__init__(message)
        self.delay = delay


class AccessBlocked(RuntimeError):
    pass


class SnapshotChanged(RuntimeError):
    pass


@contextmanager
def process_lock(root):
    """OS locks are released on crash, including on Windows; no stale PID cleanup."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'bot.lock').open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('Another bot is using this archive directory') from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def retry_after(value):
    if not value:
        return 0
    try:
        return max(0, int(value))
    except ValueError:
        try:
            return max(0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return 0


class API:
    def __init__(self, args):
        self.args = args
        self.bot = getattr(args, 'bot', None)
        self.calls = 0
        self.previous = 0.0
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json',
            'User-Agent': 'YOKAtlasIntelligenceBot/1.0 (read-only; sequential collection)'})

    def fetch(self, method, endpoint, payload):
        key = endpoint + ':' + json.dumps(payload, sort_keys=True, ensure_ascii=False)
        failed_id = next((r['failed_id'] for r in self.bot.retry_requests
            if r['request_key'] == key), None) if self.bot else None

        def failed(error, status=None):
            if self.bot:
                self.bot.request_failed(key, url=BASE_URL + endpoint,
                    params={'method': method, 'payload': payload}, http_status=status,
                    error=error, failed_id=failed_id)

        def sleep(seconds):
            if self.bot:
                self.bot.sleep(seconds)
                if self.bot.should_stop():
                    raise KeyboardInterrupt
            else:
                time.sleep(seconds)

        for attempt in range(self.args.retries + 1):
            if self.calls >= self.args.max_requests:
                raise Paused('Request budget reached; resume with the same archive directory')
            sleep(max(0, self.args.delay - (time.monotonic() - self.previous)))
            self.calls += 1
            self.previous = time.monotonic()
            wait = 0
            try:
                response = self.session.request(method, BASE_URL + endpoint,
                    json=payload, timeout=self.args.timeout, allow_redirects=False)
            except requests.exceptions.SSLError:
                failed('TLS verification failed')
                raise AccessBlocked('TLS verification failed; configure the trusted CA, do not disable verification') from None
            except requests.RequestException:
                response = None
            if response is not None:
                if response.status_code in (403, 418):
                    failed('Access blocked; operator review required', response.status_code)
                    raise AccessBlocked(f'HTTP {response.status_code}: collection stopped for operator review')
                if response.status_code == 429:
                    wait = retry_after(response.headers.get('Retry-After'))
                elif response.status_code not in (408, 500, 502, 503, 504):
                    if response.status_code != 200:
                        failed('Unexpected HTTP status', response.status_code)
                        raise AccessBlocked(f'Unexpected HTTP {response.status_code}; review the endpoint')
                    content_type = response.headers.get('Content-Type', '').lower()
                    scalar_parameter = endpoint in ('/api/parameters/yil', '/api/parameters/sonuc-aciklandi')
                    if 'json' not in content_type and not (scalar_parameter and content_type.startswith('text/plain')):
                        failed('Expected JSON content')
                        raise AccessBlocked('Expected JSON; received another content type')
                    if self.bot:
                        self.bot.request_ok(failed_id=failed_id)
                    return response.content
            if attempt == self.args.retries or wait > 30:
                failed('HTTP/network retries exhausted', response.status_code if response is not None else None)
                raise Paused('HTTP/network retries exhausted', max(300, wait))
            sleep(max(wait, 2 ** (attempt + 1)))
        raise AssertionError('Unreachable')


def decode(raw):
    def reject(value):
        raise ValueError(f'Non-finite JSON constant: {value}')
    def number(value):
        result = float(value)
        if not math.isfinite(result):
            reject(value)
        return result
    return json.loads(raw, parse_constant=reject, parse_float=number)


def validate(entity, data, payload):
    if entity in ENTITIES[:3]:
        if not isinstance(data, list) or not data or not all(isinstance(row, dict) for row in data):
            raise ValueError(f'{entity}: expected a nonempty list of objects')
        return data
    if not isinstance(data, dict) or not isinstance(data.get('content'), list):
        raise ValueError(f'{entity}: missing content array')
    rows = data['content']
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f'{entity}: non-object record')
    for key in ('number', 'size', 'numberOfElements', 'totalElements', 'totalPages'):
        if type(data.get(key)) is not int or data[key] < 0:
            raise ValueError(f'{entity}: invalid {key}')
    page, size = payload['page'], payload['size']
    expected_pages = (data['totalElements'] + size - 1) // size
    expected_rows = max(0, min(size, data['totalElements'] - page * size))
    if (data['number'] != page or data['size'] != size or data['totalPages'] != expected_pages
            or data['numberOfElements'] != len(rows) or len(rows) != expected_rows
            or data.get('last') is not (page >= expected_pages - 1)):
        raise ValueError(f'{entity}: inconsistent paging metadata')
    if any(row.get('puanTuru') != payload['filters']['puanTuru'] for row in rows):
        raise ValueError(f'{entity}: score filter was ignored')
    if entity == 'programs' and (type(data.get('yil')) is not int
            or any(row.get('yil') != data['yil'] for row in rows)):
        raise ValueError('programs: catalog year and record years disagree')
    return rows


def archive_page(snapshot, manifest, entity, score, page, api):
    monitor = getattr(api, 'bot', None)
    if monitor and monitor.should_stop():
        raise KeyboardInterrupt
    method, endpoint = PATHS[entity]
    payload = None
    if score:
        payload = {'filters': {'puanTuru': score}, 'page': page, 'size': manifest['page_size']}
        if entity == 'programs':
            payload.update(sortBy='basariSirasi', direction='ASC')
        path = snapshot / 'complete_data' / entity / score / f'page_{page:06d}.json'
    else:
        path = snapshot / 'complete_data' / entity / 'all.json'
    receipt_path = path.with_suffix('.meta.json')
    manifest['current'] = {'entity': entity, 'score': score, 'page': page}
    manifest['updated_at'] = now()
    dump(snapshot / 'manifest.json', manifest)
    if path.exists():
        raw = path.read_bytes()
        if receipt_path.exists():
            receipt = read_json(receipt_path)
            if (receipt['sha256'] != hashlib.sha256(raw).hexdigest()
                    or receipt['request'] != payload or receipt['endpoint'] != endpoint):
                raise ValueError(f'Archive receipt mismatch: {path.name}; restore the file before resuming')
    else:
        if receipt_path.exists():
            raise ValueError(f'Archived body is missing: {path.name}')
        raw = api.fetch(method, endpoint, payload)
    data = decode(raw)
    rows = validate(entity, data, payload)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        with temp.open('wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(path)
        LOG.info('%s %s page=%s rows=%s', entity, score or '', page, len(rows))
        if monitor and api.args.archive_only:
            monitor.records(len(rows))
    if not receipt_path.exists():
        dump(receipt_path, {'endpoint': endpoint, 'method': method, 'request': payload,
            'http_status': 200, 'captured_at': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            'sha256': hashlib.sha256(raw).hexdigest(), 'records': len(rows)})
    if monitor:
        monitor.progress(page + 1 if score else 1,
            max(1, data['totalPages']) if score else 1, f'İndirme: {entity} {score or ""}')
    return data


def collect(snapshot, manifest, api):
    parameters = manifest.setdefault('parameters', {})
    for name, endpoint in [('catalog_year', '/api/parameters/yil'),
            ('results_announced', '/api/parameters/sonuc-aciklandi')]:
        if name not in parameters:
            manifest['current'] = {'entity': 'parameters', 'parameter': name}
            dump(snapshot / 'manifest.json', manifest)
            raw = api.fetch('GET', endpoint, None)
            value = decode(raw)
            if type(value) is not int or (name == 'results_announced' and value not in (0, 1)):
                raise ValueError(f'Invalid source parameter: {name}')
            parameters[name] = {'value': value, 'endpoint': endpoint,
                'captured_at': now(), 'sha256': hashlib.sha256(raw).hexdigest()}
            dump(snapshot / 'manifest.json', manifest)
    for entity in ENTITIES[:3]:
        data = archive_page(snapshot, manifest, entity, None, None, api)
        manifest['partitions'][entity] = {'rows': len(data), 'pages': 1}
    for entity in ENTITIES[3:]:
        for score in SCORES:
            page, count, signature = 0, 0, None
            while True:
                data = archive_page(snapshot, manifest, entity, score, page, api)
                if entity == 'programs' and data['yil'] != parameters['catalog_year']['value']:
                    raise SnapshotChanged('Program catalog year changed after reading source parameters')
                current = (data['totalElements'], data['totalPages'], data.get('yil'))
                if signature is not None and current != signature:
                    raise SnapshotChanged(f'{entity}/{score}: source totals/year changed during pagination')
                signature = current
                count += len(data['content'])
                page += 1
                if data['last']:
                    break
            manifest['partitions'][f'{entity}/{score}'] = {'rows': count, 'pages': page, 'year': data.get('yil')}
    for entity in ENTITIES[3:]:
        if not sum(value['rows'] for key, value in manifest['partitions'].items() if key.startswith(entity + '/')):
            raise ValueError(f'{entity}: all score types were empty; snapshot requires review')
    # shortcut: the API exposes no snapshot token; same-sized changes during pagination can escape detection.
    manifest.update(phase='collected', collected_at=now(), current=None)
    dump(snapshot / 'manifest.json', manifest)


def cycle(root, args):
    state_path = root / 'state.json'
    state = read_json(state_path) if state_path.exists() else {'active_snapshot': None}
    name = state.get('active_snapshot')
    if name and (not isinstance(name, str) or Path(name).name != name or name in ('.', '..')):
        raise ValueError('Invalid snapshot name in state.json')
    if not name:
        name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + secrets.token_hex(3)
        snapshot = root / 'snapshots' / name
        dump(snapshot / 'manifest.json', {'version': 1, 'snapshot_id': name, 'created_at': now(),
            'phase': 'collecting', 'page_size': args.page_size, 'partitions': {}})
        state.update(active_snapshot=name, status='running')
        dump(state_path, state)
    snapshot = root / 'snapshots' / name
    manifest = read_json(snapshot / 'manifest.json')
    state['status'] = 'running'
    dump(state_path, state)
    try:
        if manifest['phase'] == 'collecting':
            api = API(args)
            try:
                collect(snapshot, manifest, api)
            finally:
                api.session.close()
        if args.archive_only:
            manifest['phase'] = 'archived'
        elif manifest['phase'] != 'completed':
            manifest['phase'] = 'importing'
            dump(snapshot / 'manifest.json', manifest)

            def progress(entity, score, page, done, total, stats):
                monitor = getattr(args, 'bot', None)
                if monitor:
                    if monitor.should_stop():
                        raise KeyboardInterrupt
                    monitor.progress(done, total, f'PostgreSQL: {entity} {score or ""}')
                    written = sum(stats.get(name, 0) for name in ENTITIES)
                    monitor.records(written - progress.written)
                    progress.written = written
                previous = manifest.get('import_progress', {}).get('files')
                manifest.update(current={'entity': entity, 'score': score, 'page': page},
                    import_progress={'files': done, 'total_files': total, 'stats': stats}, updated_at=now())
                dump(snapshot / 'manifest.json', manifest)
                if done != previous and (done % 20 == 0 or done == total):
                    LOG.info('PostgreSQL %s/%s pages', done, total)

            progress.written = 0
            manifest['database_result'] = import_archive(snapshot, args.env_file, on_progress=progress)
            manifest['phase'] = 'completed'
        manifest.update(completed_at=now(), current=None, error=None)
        dump(snapshot / 'manifest.json', manifest)
        state.update(active_snapshot=None, last_snapshot=name, status=manifest['phase'],
            last_completed_at=now(), next_run_at=time.time() + args.interval)
        if manifest.get('database_result', {}).get('status') == 'completed_with_issues':
            state['status'] = 'completed_with_issues'
            LOG.warning('Snapshot completed with data quality issues; inspect run statistics and quality tables: %s',
                manifest['database_result'])
        dump(state_path, state)
        LOG.info('Snapshot %s: %s', name, manifest['phase'])
        return manifest
    except BaseException as exc:
        manifest['error'] = {'type': type(exc).__name__, 'at': now()}
        if isinstance(exc, (ValueError, Paused, AccessBlocked, SnapshotChanged)):
            manifest['error']['message'] = str(exc)
        state.update(status='paused' if isinstance(exc, (Paused, KeyboardInterrupt)) else 'failed')
        if isinstance(exc, SnapshotChanged):
            manifest['phase'] = 'superseded'
            state['active_snapshot'] = None
        dump(snapshot / 'manifest.json', manifest)
        dump(state_path, state)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['run', 'status'])
    parser.add_argument('--root', type=Path, default=Path('outputs/yokatlas_bot'))
    parser.add_argument('--archive-only', action='store_true', help='collect JSON without a database connection')
    parser.add_argument('--continuous', action='store_true', help='repeat snapshots and automatically retry transient failures')
    parser.add_argument('--interval', type=float, default=86400, help='seconds after a completed snapshot')
    parser.add_argument('--page-size', type=int, default=20)
    parser.add_argument('--delay', type=float, default=2)
    parser.add_argument('--timeout', type=float, default=30)
    parser.add_argument('--retries', type=int, default=3)
    parser.add_argument('--max-requests', type=int, default=5000, help='per attempt; reaching this budget preserves the checkpoint')
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args(argv)
    if (not all(math.isfinite(value) for value in (args.delay, args.timeout, args.interval))
            or not 1 <= args.page_size <= 100 or args.delay < 1 or args.timeout <= 0
            or args.retries < 0 or args.max_requests < 1 or args.interval < 60):
        parser.error('Require page size 1..100, delay >=1s, timeout >0, retries >=0, requests >=1, interval >=60s')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    root = args.root.resolve()
    if args.command == 'status':
        state_path = root / 'state.json'
        state = read_json(state_path) if state_path.exists() else {'status': 'not_started'}
        name = state.get('active_snapshot') or state.get('last_snapshot')
        if name and isinstance(name, str) and Path(name).name == name:
            state['snapshot'] = read_json(root / 'snapshots' / name / 'manifest.json')
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    try:
        with process_lock(root):
            while True:
                if args.continuous and (root / 'state.json').exists():
                    state = read_json(root / 'state.json')
                    if not state.get('active_snapshot'):
                        time.sleep(max(0, state.get('next_run_at', 0) - time.time()))
                try:
                    result = cycle(root, args)
                except (Paused, SnapshotChanged) as exc:
                    LOG.warning('%s', exc)
                    if not args.continuous:
                        return 2
                    time.sleep(getattr(exc, 'delay', 300))
                    continue
                except Exception as exc:
                    if args.continuous and not args.archive_only:
                        import psycopg
                    if args.continuous and not args.archive_only and isinstance(exc, psycopg.OperationalError):
                        LOG.error('Database unavailable; archived pages retained. Retrying in 300 seconds.')
                        time.sleep(300)
                        continue
                    raise
                if not args.continuous:
                    return 4 if result.get('database_result', {}).get('status') == 'completed_with_issues' else 0
    except KeyboardInterrupt:
        LOG.info('Stopped; checkpoint retained')
        return 130
    except Exception as exc:
        # Driver errors may contain connection details; retain the type, not an arbitrary exception string.
        LOG.error('Stopped: %s. Check the snapshot manifest and database configuration.', type(exc).__name__)
        if isinstance(exc, (ValueError, Paused, AccessBlocked, SnapshotChanged)):
            LOG.error('%s', exc)
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
