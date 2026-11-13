"""Archive-first publication into the currently supported RAW write endpoint.

This module NEVER writes staging/core/analytics, marks a remote run complete,
or assumes 409 means a successful earlier insert.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlsplit

from .client import decode_json


# Keep checkpoints created before the version label changed.
_LEGACY_RUN_PAYLOAD_SHA256 = {
    'yokatlas': 'b425c03767126cf08668b8bf6fb30ea28e654e704b1d77ac0bfc34037154c683',
    'tuik': '7c4368678657bd7e8bf49812e23b12dfb971b5d0d2dbac6441b3b88b504e17d9',
    'openalex': 'f67f28238178fc03aab4c89968272c1c5d758bbe51b4ba561028af5b97240fab',
}


def _publish_run(root, source, ledger, client):
    return ledger.execute(f'{root}/run', 'ingestion_runs',
                          {'source_system': source, 'scraper_version': 'raw-api-bots-v1'}, client,
                          previous_payload_sha256=_LEGACY_RUN_PAYLOAD_SHA256[source])


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(path: Path):
    return decode_json(path.read_bytes())


def _date(value):
    if not isinstance(value, str) or not value:
        raise ValueError('Archive lacks a real capture timestamp')
    datetime.fromisoformat(value.replace('Z', '+00:00')).utcoffset()
    if datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('Captured timestamp requires a timezone')
    return value


def _required(condition, message):
    if not condition:
        raise ValueError(message)


def _archive_page(snapshot, path, entity, score, page, paths):
    raw = path.read_bytes()
    receipt = _json(path.with_suffix('.meta.json'))
    _required(isinstance(receipt, dict) and receipt.get('sha256') == _sha(raw),
              f'Archive receipt checksum mismatch: {path}')
    method, endpoint = paths[entity]
    _required((receipt.get('method'), receipt.get('endpoint')) == (method, endpoint),
              f'Archive receipt endpoint mismatch: {path}')
    _required(type(receipt.get('http_status')) is int and receipt['http_status'] == 200,
              f'Unverified HTTP status: {path}')
    if score is not None:
        request = receipt.get('request')
        _required(isinstance(request, dict) and request.get('page') == page and
                  request.get('filters', {}).get('puanTuru') == score,
                  f'Archive pagination/filter mismatch: {path}')
    data = decode_json(raw)
    rows = data if isinstance(data, list) else data.get('content') if isinstance(data, dict) else None
    _required(isinstance(rows, list) and all(isinstance(row, dict) for row in rows),
              f'Expected array of source objects: {path}')
    _required(type(receipt.get('records')) is int and receipt['records'] == len(rows),
              f'Archive record count mismatch: {path}')
    return {'entity': entity, 'score': score, 'page': page, 'path': path,
            'payload': data, 'rows': rows, 'receipt': receipt,
            'captured_at': _date(receipt.get('captured_at')),
            'hash': _sha(raw), 'method': method, 'endpoint': endpoint}


def prepare_yokatlas(snapshot: Path):
    """Validate the entire snapshot (including missing pages) BEFORE any INSERT."""
    from scripts.database.load_archive import ENTITIES, PATHS, source_files
    snapshot = Path(snapshot).resolve()
    manifest = _json(snapshot / 'manifest.json')
    _required(isinstance(manifest, dict) and manifest.get('phase') in
              ('collected', 'archived', 'completed'), 'YÖK collection is not complete')
    expected = manifest.get('partitions')
    _required(isinstance(expected, dict), 'YÖK manifest has no partitions')
    pages = []
    seen = {}
    for entity, score, page, path in source_files(snapshot):
        item = _archive_page(snapshot, path, entity, score, page, PATHS)
        pages.append(item)
        name = entity if score is None else f'{entity}/{score}'
        seen.setdefault(name, []).append(item)
    _required(set(seen) == set(expected), 'Missing or unexpected archive partition(s)')
    for name, values in seen.items():
        expectation = expected[name]
        _required(isinstance(expectation, dict) and type(expectation.get('pages')) is int and
                  type(expectation.get('rows')) is int, f'Invalid partition manifest: {name}')
        _required(len(values) == expectation['pages'] and
                  sum(len(v['rows']) for v in values) == expectation['rows'],
                  f'Incomplete archive partition: {name}')
        page_indices = [v['page'] for v in values]
        _required(page_indices == [None] if '/' not in name else
                  sorted(page_indices) == list(range(expectation['pages'])),
                  f'Missing page index in {name}')
    _required(bool(pages), 'Empty archive is not accepted')
    return manifest, pages


def publish_yokatlas(snapshot, ledger, client):
    snapshot = Path(snapshot).resolve()
    manifest, pages = prepare_yokatlas(snapshot)
    snapshot_id = manifest.get('snapshot_id')
    _required(isinstance(snapshot_id, str) and snapshot_id and '/' not in snapshot_id,
              'Invalid snapshot identity')
    root = f'yokatlas/{snapshot_id}'
    run = _publish_run(root, 'yokatlas', ledger, client)
    run_id = run['ingestion_run_id']
    record_count = 0
    for item in pages:
        rel = item['path'].relative_to(snapshot).as_posix()
        payload = {
            'ingestion_run_id': run_id,
            'endpoint': item['endpoint'], 'method': item['method'],
            'captured_at': item['captured_at'], 'http_status': item['receipt']['http_status'],
            'source_hash_sha256': item['hash'], 'source_path': str(item['path']),
            'payload': item['payload'],
        }
        if item['score'] is not None:
            payload['score_type'] = item['score']
            payload['page_number'] = item['page']
        response = ledger.execute(f'{root}/{rel}/response', 'api_responses', payload, client)
        response_id = response['api_response_id']
        for index, record in enumerate(item['rows']):
            # Record hash is a source-content fingerprint, not a uniqueness claim.
            from .client import encode_json
            record_hash = _sha(encode_json(record).encode('utf-8'))
            ledger.execute(f'{root}/{rel}/record/{index}', 'source_records', {
                'api_response_id': response_id,
                'source_entity': item['entity'],
                'source_array_index': index,
                'record': record,
                'record_hash_sha256': record_hash,
            }, client)
            record_count += 1
    return {'source': 'yokatlas', 'run_id': run_id, 'responses': len(pages),
            'records': record_count, 'local_publication': 'complete', 'remote_run_status': 'running'}


def publish_report(archive, ledger, client):
    """Only the supported report_documents RAW contract. No staging writes."""
    from scraper.report_bot import read_archive
    from scraper.report_parsers import REPORTS
    archive = Path(archive).resolve()
    meta0 = _json(archive / 'manifest.json')
    _required(isinstance(meta0, dict) and meta0.get('report_id') in REPORTS,
              'Unknown report_id or archive metadata')
    report_id = meta0['report_id']
    meta, extraction = read_archive(archive, report_id)
    spec = REPORTS[report_id]
    root = f"{spec['bot']}/report/{report_id}/{meta['source_sha256']}/{meta['parser_version']}"
    run = ledger.execute(root + '/run', 'ingestion_runs', {
        'source_system': spec['bot'], 'scraper_version': meta['parser_version'],
        'details': {'report_id': report_id, 'source_sha256': meta['source_sha256']},
    }, client)
    key = ledger.execute(root + '/document', 'report_documents', {
        'ingestion_run_id': run['ingestion_run_id'], 'report_id': report_id,
        'source_system': spec['bot'], 'edition': spec['edition'],
        'source_url': meta['source_url'], 'captured_at': _date(meta['captured_at']),
        'source_sha256': meta['source_sha256'],
        'parser_version': meta['parser_version'],
        'extracted_sha256': meta['extracted_sha256'],
        'archive_path': str(archive), 'payload': extraction,
    }, client)
    return {'source': spec['bot'], 'report_id': report_id,
            'run_id': run['ingestion_run_id'], 'document_id': key['document_id'],
            'local_publication': 'complete', 'remote_run_status': 'running'}


def publish_capture(directory, ledger, client, *, source_entity=None, records_key=None,
                    openalex_entity_type=None):
    """Publish a verified JSON capture from TÜİK/OpenAlex without invented transforms.

    - TÜİK legacy: optional source_records for an existing source_entity.
    - OpenAlex: optional source snapshots; entity_type must already exist in RAW.
    Native TÜİK SDMX, and OpenAlex normalized-object upserts are NOT implemented.
    """
    directory = Path(directory).resolve()
    receipt = _json(directory / 'receipt.json')
    raw = (directory / 'body.json').read_bytes()
    _required(isinstance(receipt, dict) and receipt.get('sha256') == _sha(raw),
              'Source receipt is missing or does not match body bytes')
    source = receipt.get('source_system')
    _required(source in ('tuik', 'openalex'), 'Only OpenAlex and TÜİK captures are supported')
    _required(receipt.get('http_status') == 200 and receipt.get('method') == 'GET',
              'Expected verified successful GET response')
    _date(receipt.get('captured_at'))
    _required(isinstance(receipt.get('url'), str) and urlsplit(receipt['url']).scheme == 'https',
              'Expected real HTTPS source URL')
    origin = urlsplit(receipt['url'])
    if source == 'openalex':
        _required(origin.hostname == 'api.openalex.org', 'Invalid OpenAlex API origin')
    else:
        _required(origin.hostname == 'tuik.gov.tr' or
                  (origin.hostname or '').endswith('.tuik.gov.tr'), 'Invalid TÜİK API origin')
    _required(not origin.username and not origin.password and not origin.fragment,
              'Unexpected source URL credentials or fragments')
    _required(not any(re.search(r'(token|secret|password|api.?key|auth)', name, re.I)
                      for name, _ in parse_qsl(origin.query, keep_blank_values=True)),
              'Source URL appears to contain credentials; keep tokens in headers')
    data = decode_json(raw)
    identity = _sha(receipt['url'].encode('utf-8') + b'\x00' + raw)
    root = f'{source}/json/{identity}'
    # Validate the ENTIRE source batch before the first remote INSERT. This
    # avoids creating a run/response for a source that cannot be published.
    records = []
    if source_entity:
        _required(source == 'tuik' and source_entity == 'tuik_df_adnks_t16',
                  'Only the documented legacy TÜİK entity can use source_records')
        records = data.get(records_key) if records_key and isinstance(data, dict) else data
        _required(isinstance(records, list) and all(isinstance(v, dict) for v in records),
                  'Expected TÜİK JSON record array')
        _required(all('TIME_PERIOD' in r and 'DATAFLOW' in r for r in records),
                  'TÜİK records must retain their source coordinates')
    if openalex_entity_type:
        _required(source == 'openalex' and openalex_entity_type in
                  ('works', 'authors', 'institutions', 'sources', 'topics', 'funders'),
                  'Unsupported OpenAlex snapshot entity type')
        records = data.get('results') if isinstance(data, dict) and 'results' in data else [data]
        _required(isinstance(records, list) and all(isinstance(v, dict) for v in records),
                  'Expected OpenAlex results[] objects or one object')
        prefix = {'works': 'W', 'authors': 'A', 'institutions': 'I',
                  'sources': 'S', 'topics': 'T', 'funders': 'F'}[openalex_entity_type]
        _required(all(isinstance(r.get('id'), str) and
                      re.fullmatch(r'https://openalex\.org/' + prefix + r'[0-9]+', r['id'])
                      for r in records), 'Missing or invalid OpenAlex source ID')
    if source_entity and openalex_entity_type:
        raise ValueError('Choose a single source entity publication mode')

    # Requests remain single-row and non-atomic across the whole batch.
    # A durable checkpoint prevents unknown responses from being replayed.
    run = _publish_run(root, source, ledger, client)
    uri = urlsplit(receipt['url'])
    endpoint = uri.path + ('?' + uri.query if uri.query else '')
    response = ledger.execute(root + '/response', 'api_responses', {
        'ingestion_run_id': run['ingestion_run_id'], 'endpoint': endpoint,
        'method': 'GET', 'captured_at': receipt['captured_at'], 'http_status': 200,
        'payload': data, 'source_hash_sha256': receipt['sha256'],
        'source_path': str(directory / 'body.json'),
    }, client)
    rows_written = 0
    for i, record in enumerate(records):
        if source_entity:
            ledger.execute(f'{root}/legacy-record/{i}', 'source_records', {
                'api_response_id': response['api_response_id'],
                'source_entity': source_entity, 'source_array_index': i,
                'record': record,
            }, client)
        else:
            ledger.execute(f'{root}/snapshot/{i}', 'openalex_object_snapshots', {
                'entity_type': openalex_entity_type, 'openalex_id': record['id'],
                'api_response_id': response['api_response_id'],
                'source_array_index': i, 'captured_at': receipt['captured_at'],
                'source_payload': record,
            }, client)
        rows_written += 1
    return {'source': source, 'run_id': run['ingestion_run_id'],
            'api_response_id': response['api_response_id'], 'child_records': rows_written,
            'local_publication': 'complete', 'remote_run_status': 'running'}
