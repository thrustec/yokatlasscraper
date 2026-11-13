"""Admin panel entry point for the existing RAW API bot workflow.

Usage after API health and environment are configured:
    python -m scraper.data_api.panel yokatlas
    python -m scraper.data_api.panel sege
    python -m scraper.data_api.panel urap

No old direct-to-PostgreSQL importer is invoked.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

import requests

from .client import RawWriteClient, encode_json
from .cli import run_report_collector, run_yokatlas_collector
from .ledger import Ledger
from .publish import publish_report, publish_yokatlas


def _check_api(base_url: str, key: str) -> None:
    """Fail before collecting anything if the configured API is not ready."""
    # Reuse the write client's URL validation, without sending a write.
    client = RawWriteClient(base_url=base_url, api_key=key)
    client.close()
    url = base_url.rstrip('/') + '/status'
    # No redirects: the key is not sent on this unauthenticated status request.
    response = requests.get(url, timeout=5, allow_redirects=False)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or body.get('status') != 'ok' or body.get('database') != 'connected':
        raise RuntimeError('RAW API is not ready (status/database).')


def _relative_root(raw: object, default: str) -> Path:
    value = raw if raw is not None else default
    if not isinstance(value, str) or not value:
        raise ValueError('Archive directory must be a nonempty relative path')
    path = Path(value)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Archive directory must remain inside the project')
    return path.resolve()


def run(source: str, settings: dict):
    if not isinstance(settings, dict):
        raise ValueError('Bot settings must be a JSON object')
    base = os.getenv('DATA_API_BASE_URL', '').strip()
    key = os.getenv('DB_WRITE_API_KEY', '').strip()
    _check_api(base, key)
    archive_only = settings.get('sadece_arsiv', False)
    if type(archive_only) is not bool:
        raise ValueError('sadece_arsiv must be a boolean')

    if source == 'yokatlas':
        root = _relative_root(settings.get('arsiv_dizini'), 'outputs/yokatlas_bot')
        max_requests = int(settings.get('azami_istek', 5000))
        page_size = int(settings.get('sayfa_boyutu', 20))
        delay = float(settings.get('bekleme_saniye', 2))
        snapshot = run_yokatlas_collector(root, max_requests=max_requests,
                                           page_size=page_size, delay=delay)
        archives = [snapshot]
    elif source in ('sege', 'urap'):
        # The current API report collector does not implement custom directories,
        # local-PDF overrides or staging/core publication.
        if settings.get('arsiv_dizini') or settings.get('pdf_dosyasi') or settings.get('universite_eslemeleri'):
            raise ValueError('These report settings are not supported by the RAW API panel adapter')
        offline = settings.get('cevrimdisi', False)
        if type(offline) is not bool:
            raise ValueError('cevrimdisi must be a boolean')
        archives = run_report_collector(source, settings.get('rapor', 'tum'), offline)
    else:
        raise ValueError('Unsupported source')

    if archive_only:
        return {'source': source, 'status': 'archived_only',
                'archives': [str(path) for path in archives]}

    ledger = Ledger(Path('outputs/data_api/checkpoint.sqlite3'))
    client = RawWriteClient(base_url=base, api_key=key)
    try:
        if source == 'yokatlas':
            result = publish_yokatlas(archives[0], ledger, client)
        else:
            results = [publish_report(path, ledger, client) for path in archives]
            result = {'source': source, 'reports': results}
        return {**result, 'checkpoint': ledger.stats()}
    finally:
        client.close()
        ledger.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', choices=['yokatlas', 'sege', 'urap'])
    args = parser.parse_args(argv)
    from botkit import Bot
    try:
        with Bot.from_env() as monitor:
            result = run(args.source, monitor.settings)
            monitor.summary(**result)
            monitor.progress(1, 1, 'RAW API işlemi tamamlandı')
            print(encode_json({'source': args.source, 'status': 'ok'}), flush=True)
        return 0
    except KeyboardInterrupt:
        print('WARNING: Interrupted; archives and checkpoints preserved.', file=sys.stderr)
        return 130
    except Exception as exc:
        # Never include connection details or secrets in panel logs.
        print(f'ERROR: RAW API bot stopped ({type(exc).__name__}); check API status, settings and checkpoints.',
              file=sys.stderr)
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
