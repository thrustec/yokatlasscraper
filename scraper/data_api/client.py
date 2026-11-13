"""Strict single-row RAW write client for the 25 Oct 2026 HTTP contract."""
from __future__ import annotations

from decimal import Decimal
import json
import math
import os
from urllib.parse import urlsplit

import requests


class RejectedWrite(RuntimeError):
    """A definite HTTP refusal; caller must not silently retry."""

    def __init__(self, status: int):
        self.status = status
        super().__init__(f'RAW write rejected with HTTP {status}; operator review required')


class UncertainWrite(RuntimeError):
    """A write may have committed; no automatic replay is permitted."""


def decode_json(raw: bytes | str):
    """Preserve JSON decimal tokens rather than converting them to binary float."""
    def fail(v):
        raise ValueError('Source contains a non-finite JSON value')
    return json.loads(raw, parse_float=Decimal, parse_constant=fail)


def encode_json(obj):
    """Serialize JSON without rounding Decimal source numbers or emitting NaN."""
    if obj is None:
        return 'null'
    if obj is True:
        return 'true'
    if obj is False:
        return 'false'
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False)
    if isinstance(obj, int):
        return str(obj)
    if isinstance(obj, Decimal):
        if not obj.is_finite():
            raise ValueError('Non-finite decimal in source')
        return str(obj)
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError('Non-finite float in source')
        return json.dumps(obj, allow_nan=False)
    if isinstance(obj, (tuple, list)):
        return '[' + ','.join(encode_json(v) for v in obj) + ']'
    if isinstance(obj, dict):
        if any(not isinstance(k, str) for k in obj):
            raise ValueError('JSON object keys must be strings')
        return '{' + ','.join(encode_json(k) + ':' + encode_json(obj[k]) for k in sorted(obj)) + '}'
    raise TypeError(f'Unsupported JSON value: {type(obj).__name__}')


class RawWriteClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 *, timeout: float = 30, session=None):
        base_url = (base_url or os.getenv('DATA_API_BASE_URL') or '').strip().rstrip('/')
        api_key = api_key or os.getenv('DB_WRITE_API_KEY')
        if not base_url or not api_key:
            raise ValueError('DATA_API_BASE_URL and DB_WRITE_API_KEY are required')
        parsed = urlsplit(base_url)
        # HTTP is allowed only for loopback or the specifically named API service
        # on the shared private Docker network. All external hosts require TLS.
        loopback_http = parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost')
        docker_http = (parsed.scheme == 'http' and parsed.hostname == 'yokatlas-data-api'
                       and parsed.port == 8000 and parsed.path in ('', '/'))
        if parsed.scheme != 'https' and not (loopback_http or docker_http):
            raise ValueError('HTTPS required except loopback and the private Docker RAW API service')
        if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.netloc:
            raise ValueError('Invalid DATA_API_BASE_URL')
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Timeout must be positive')
        self.url = base_url + '/api/db/write'
        self.timeout = timeout
        self._session = session or requests.Session()
        self._owns_session = session is None
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-API-Key': api_key}

    def close(self):
        if self._owns_session:
            self._session.close()

    def insert(self, table: str, data: dict) -> dict:
        if not isinstance(table, str) or not table.isidentifier() or not isinstance(data, dict):
            raise ValueError('Expected unqualified table name and one JSON object')
        body = encode_json({'table': table, 'data': data}).encode('utf-8')
        try:
            response = self._session.post(self.url, data=body, headers=self.headers,
                                          timeout=self.timeout, allow_redirects=False)
        except requests.RequestException:
            raise UncertainWrite('Network failure; remote commit status is unknown') from None
        if response.status_code == 201:
            try:
                payload = response.json()
                if payload['table'] != table or not isinstance(payload['key'], dict):
                    raise ValueError('Unexpected response shape')
                return payload['key']
            except (ValueError, KeyError, TypeError):
                raise UncertainWrite('201 received but primary-key response is invalid') from None
        if response.status_code == 503 or response.status_code in (200, 202, 301, 302, 307, 308):
            raise UncertainWrite(f'HTTP {response.status_code}; commit status cannot be proven')
        if response.status_code in (401, 404, 409, 422, 400, 403):
            raise RejectedWrite(response.status_code)
        # Any unknown 5xx or upstream status is treated conservatively.
        if response.status_code >= 500:
            raise UncertainWrite(f'HTTP {response.status_code}; commit status cannot be proven')
        raise RejectedWrite(response.status_code)
