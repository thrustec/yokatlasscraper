"""Optional HTTPS JSON acquisition for OpenAlex and TÜİK JSON endpoints.

No guessed endpoint URLs, transformations, credentials, or SDMX metadata.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import secrets
import tempfile
import time
from urllib.parse import parse_qsl, urlencode, urlsplit

import requests

from .client import decode_json, encode_json


def atomic_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            name = stream.name
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def collect_json(source, url, root, *, timeout=40, session=None, auth_token=None):
    if source not in ('openalex', 'tuik'):
        raise ValueError('Source must be openalex or tuik')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('A real source HTTPS URL is required')
    if source == 'openalex' and parsed.hostname != 'api.openalex.org':
        raise ValueError('OpenAlex source URL must be on api.openalex.org')
    if source == 'tuik' and not (parsed.hostname == 'tuik.gov.tr' or parsed.hostname.endswith('.tuik.gov.tr')):
        raise ValueError('TÜİK source URL must be on an official tuik.gov.tr host')
    if any(re.search(r'(token|secret|password|api.?key|auth)', k, flags=re.I)
           for k, _ in parse_qsl(parsed.query, keep_blank_values=True)):
        raise ValueError('Do not put source secrets in URL query parameters')
    if auth_token is not None and (not isinstance(auth_token, str) or not auth_token):
        raise ValueError('Bearer source token is supported for TÜİK only')
    if not isinstance(timeout, (int, float)) or not 0 < timeout <= 300:
        raise ValueError('Timeout must be in (0, 300] seconds')
    client = session or requests.Session()
    try:
        headers = {'Accept': 'application/json', 'User-Agent': 'YOKAtlasIntelligence/RAW-archiver'}
        if auth_token:
            headers['Authorization'] = 'Bearer ' + auth_token
        with client.get(url, headers=headers, timeout=timeout,
                        allow_redirects=False, stream=True) as response:
            if response.status_code != 200:
                raise RuntimeError(f'Source returned HTTP {response.status_code}; not archived')
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > 32 * 1024 * 1024:
                    raise ValueError('JSON exceeds 32 MiB; use source-specific chunking')
                chunks.append(chunk)
            raw = b''.join(chunks)
            decode_json(raw)  # Reject XML and non-finite malformed JSON.
    finally:
        if session is None:
            client.close()
    identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + secrets.token_hex(5)
    folder = Path(root) / source / identifier
    atomic_bytes(folder / 'body.json', raw)
    receipt = {'source_system': source, 'url': url, 'method': 'GET',
               'captured_at': datetime.now(timezone.utc).isoformat(),
               'http_status': 200, 'sha256': hashlib.sha256(raw).hexdigest()}
    atomic_bytes(folder / 'receipt.json', encode_json(receipt).encode('utf-8'))
    return folder


OPENALEX_TYPES = ('works', 'authors', 'institutions', 'sources', 'topics', 'funders')


def crawl_openalex(entity_type, filter_expression, root, *, per_page=100, max_pages=5,
                   api_key=None, delay=1.0, publish=None):
    """Bounded, source-first OpenAlex cursor collector.

    ``publish`` is called for each fully verified archived page; if provided it
    may write via the durable ledger. Does not hide download or HTTP errors.
    Cursor paging after the first page requires a registered OpenAlex API key.
    """
    if entity_type not in OPENALEX_TYPES:
        raise ValueError('Unsupported OpenAlex collection')
    if not isinstance(filter_expression, str) or not filter_expression or len(filter_expression) > 1000:
        raise ValueError('Require an explicit bounded OpenAlex filter')
    if (type(per_page) is not int or not 1 <= per_page <= 100 or
            type(max_pages) is not int or not 1 <= max_pages <= 50 or
            not isinstance(delay, (float, int)) or not 0 <= delay <= 3600):
        raise ValueError('OpenAlex per-page/pages/delay out of range')
    if max_pages > 1 and not api_key:
        raise ValueError('OpenAlex cursor pagination requires OPENALEX_API_KEY')
    cursor = '*'
    output = []
    seen_cursors = set()
    for index in range(max_pages):
        if cursor in seen_cursors:
            raise ValueError('OpenAlex returned a repeated cursor; stopping')
        seen_cursors.add(cursor)
        url = 'https://api.openalex.org/' + entity_type + '?' + urlencode({
            'filter': filter_expression, 'per_page': per_page, 'cursor': cursor})
        archived = collect_json('openalex', url, root, auth_token=api_key)
        payload = decode_json((archived / 'body.json').read_bytes())
        if not (isinstance(payload, dict) and isinstance(payload.get('results'), list)
                and isinstance(payload.get('meta'), dict)
                and all(isinstance(v, dict) for v in payload['results'])):
            raise ValueError('Invalid OpenAlex paginated response')
        results = payload['results']
        if publish is not None:
            publish(archived, entity_type)
        output.append({'page': index+1, 'archive': str(archived), 'objects': len(results)})
        cursor = payload['meta'].get('next_cursor')
        if not results or cursor is None:
            break
        if not isinstance(cursor, str) or not cursor or len(cursor) > 8000:
            raise ValueError('OpenAlex returned an invalid next_cursor')
        if index + 1 < max_pages and delay:
            time.sleep(delay)
    return output
