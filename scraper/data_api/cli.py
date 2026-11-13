"""Explicit, opt-in RAW HTTP ingestion; never rewrites the existing bot's DB path.

Usage: python -m scraper.data_api.cli --help
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from .client import RawWriteClient, RejectedWrite, UncertainWrite, encode_json
from .collect import collect_json, crawl_openalex
from .ledger import Ledger, ReconciliationRequired
from .publish import prepare_yokatlas, publish_capture, publish_report, publish_yokatlas


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ledger', type=Path, default=Path('outputs/data_api/checkpoint.sqlite3'),
                   help='Kalıcı operasyon kaydı; bu dosyayı kaybetmeyin')
    p.add_argument('--env-file', type=Path,
                   help='Yalnız DATA_API_BASE_URL ve DB_WRITE_API_KEY için gizli KEY=value dosyası')
    commands = p.add_subparsers(dest='command', required=True)
    yok = commands.add_parser('yokatlas', help='Mevcut YÖK JSON snapshot arşivini API ile RAW’a yaz')
    yok.add_argument('--snapshot', type=Path, required=True)
    yok.add_argument('--verify-only', action='store_true')
    yok_live = commands.add_parser('yokatlas-live', help='Mevcut YÖK botunu sadece arşiv için çalıştır, sonra RAW API’ye aktar')
    yok_live.add_argument('--root', type=Path, default=Path('outputs/yokatlas_bot'))
    yok_live.add_argument('--max-requests', type=int, default=5000)
    yok_live.add_argument('--page-size', type=int, default=20)
    yok_live.add_argument('--delay', type=float, default=2)
    yok_live.add_argument('--archive-only', action='store_true', help='HTTP arşivle, RAW’a yazma')
    report = commands.add_parser('report', help='SEGE/URAP PDF arşivini RAW report_documents’e yaz')
    report.add_argument('--archive', type=Path, required=True)
    report_live = commands.add_parser('report-live', help='Mevcut SEGE/URAP PDF botunu sadece arşiv için çalıştır, RAW API’ye aktar')
    report_live.add_argument('--source', choices=['sege', 'urap'], required=True)
    report_live.add_argument('--report-id', default='tum')
    report_live.add_argument('--offline', action='store_true', help='Daha önce arşivlenmiş PDF kullan')
    report_live.add_argument('--archive-only', action='store_true', help='PDF arşivle, RAW’a yazma')
    capture = commands.add_parser('capture', help='OpenAlex/TÜİK JSON arşivini RAW’a yaz')
    capture.add_argument('--directory', type=Path, required=True)
    group = capture.add_mutually_exclusive_group()
    group.add_argument('--tuik-legacy', action='store_true', help='Yalnız doğrulanmış legacy tuik_df_adnks_t16 kayıtları')
    group.add_argument('--openalex-type', choices=['works', 'authors', 'institutions', 'sources', 'topics', 'funders'])
    capture.add_argument('--records-key', help='Legacy TÜİK JSON response içinde kayıt dizisinin alan adı')
    fetch = commands.add_parser('fetch-json', help='İzinli resmî HTTPS kaynaktan tek JSON response arşivle')
    fetch.add_argument('--source', required=True, choices=['openalex', 'tuik'])
    fetch.add_argument('--url', required=True)
    fetch.add_argument('--root', type=Path, default=Path('outputs/source_json'))
    fetch.add_argument('--token-env', help='Kaynak bearer token içeren ortam değişkeni')
    oa = commands.add_parser('openalex-crawl', help='OpenAlex nesnelerini cursor sayfalama ile topla ve RAW snapshot olarak yaz')
    oa.add_argument('--entity-type', required=True, choices=['works', 'authors', 'institutions', 'sources', 'topics', 'funders'])
    oa.add_argument('--filter', required=True, help='Örn: country_code:TR; filtre olmadan toplama yok')
    oa.add_argument('--pages', type=int, default=5)
    oa.add_argument('--per-page', type=int, default=100)
    oa.add_argument('--delay', type=float, default=1.0)
    oa.add_argument('--root', type=Path, default=Path('outputs/source_json'))
    oa.add_argument('--archive-only', action='store_true')
    stats = commands.add_parser('status', help='Checkpoint durum sayılarını göster')
    stats.add_argument('--operation-id', help='Belirli işlemin kimliği')
    recon = commands.add_parser('reconcile', help='Yalnız DB tarafından doğrulanmış bir işlemi uzlaştır')
    recon.add_argument('--operation-id', required=True)
    recon.add_argument('--verified-by-db', action='store_true', required=True,
                       help='Celal’in bağımsız DB doğrulaması tamamlandı')
    decisions = recon.add_mutually_exclusive_group(required=True)
    decisions.add_argument('--committed-key', help='DB’de doğrulanmış PK JSON nesnesi')
    decisions.add_argument('--not-committed', action='store_true')
    return p.parse_args(argv)


def read_env_values(path: Path):
    """Intentionally small dotenv reader. Shell expansion and eval are not allowed."""
    data = {}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError('Expected KEY=value in env file')
        key, value = line.split('=', 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key.strip() in ('DATA_API_BASE_URL', 'DB_WRITE_API_KEY'):
            data[key.strip()] = value
    return data


def run_yokatlas_collector(root: Path, *, max_requests: int, page_size: int, delay: float):
    """Delegates acquisition to the existing bot; never invokes its direct DB loader."""
    if type(max_requests) is not int or max_requests < 1 or not 1 <= page_size <= 100 or delay < 1:
        raise ValueError('Invalid YÖK request budget, page size or delay')
    command = [sys.executable, '-m', 'scraper.bot', 'run', '--archive-only',
               '--root', str(root), '--max-requests', str(max_requests),
               '--page-size', str(page_size), '--delay', str(delay)]
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise ValueError(f'YÖK collection has not finished (exit={result.returncode}); continue with the same --root')
    state = json.loads((root / 'state.json').read_text(encoding='utf-8'))
    name = state.get('last_snapshot')
    if not isinstance(name, str) or Path(name).name != name or name in ('', '.', '..'):
        raise ValueError('YÖK collector did not produce a valid completed snapshot')
    return root / 'snapshots' / name


def run_report_collector(source: str, report_id: str, offline: bool):
    """Delegates parsing to existing verified PDF parsers; prevents DB import."""
    from scraper import report_bot
    from scraper.report_parsers import PARSER_VERSION, REPORTS
    valid = [rid for rid, spec in REPORTS.items() if spec['bot'] == source]
    if report_id not in (*valid, 'tum'):
        raise ValueError('Report selection is not defined for this source')
    results = report_bot.run(source, {'rapor': report_id, 'cevrimdisi': offline,
                                      'sadece_arsiv': True})
    root = report_bot.local_path(f'outputs/{source}_bot')
    archives = []
    for item in results:
        rid = item['report_id']
        value = json.loads((root / rid / 'latest.json').read_text(encoding='utf-8'))
        sha = value['source_sha256']
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('Invalid archived report checksum')
        archives.append(root / rid / sha / PARSER_VERSION)
    return archives


def main(argv=None):
    args = parse_args(argv)
    try:
        if args.command == 'yokatlas-live':
            snapshot = run_yokatlas_collector(args.root.resolve(), max_requests=args.max_requests,
                                              page_size=args.page_size, delay=args.delay)
            if args.archive_only:
                print(encode_json({'snapshot': str(snapshot), 'status': 'archived_only'}))
                return 0
        elif args.command == 'report-live':
            archives = run_report_collector(args.source, args.report_id, args.offline)
            if args.archive_only:
                print(encode_json({'archives': [str(p) for p in archives], 'status': 'archived_only'}))
                return 0
        if args.command == 'fetch-json':
            token = os.environ.get(args.token_env) if args.token_env else None
            if args.token_env and not token:
                raise ValueError('Kaynak erişim token ortam değişkeni tanımsız')
            archive = collect_json(args.source, args.url, args.root, auth_token=token)
            print(encode_json({'archive': str(archive), 'status': 'archived_only'}))
            return 0
        if args.command == 'openalex-crawl':
            api_key = os.environ.get('OPENALEX_API_KEY')
            if args.archive_only:
                pages = crawl_openalex(args.entity_type, args.filter, args.root,
                                       per_page=args.per_page, max_pages=args.pages,
                                       api_key=api_key, delay=args.delay)
                print(encode_json({'pages': pages, 'status': 'archived_only'}))
                return 0
            conf = read_env_values(args.env_file) if args.env_file else {}
            base = os.environ.get('DATA_API_BASE_URL') or conf.get('DATA_API_BASE_URL')
            key = os.environ.get('DB_WRITE_API_KEY') or conf.get('DB_WRITE_API_KEY')
            ledger = Ledger(args.ledger)
            client = RawWriteClient(base_url=base, api_key=key)
            try:
                def publish_page(folder, entity_type):
                    return publish_capture(folder, ledger, client,
                                           openalex_entity_type=entity_type)
                pages = crawl_openalex(args.entity_type, args.filter, args.root,
                                       per_page=args.per_page, max_pages=args.pages,
                                       api_key=api_key, delay=args.delay,
                                       publish=publish_page)
                print(encode_json({'pages': pages, 'checkpoint': ledger.stats(),
                                   'status': 'raw_write_requests_completed'}))
                return 0
            finally:
                client.close()
                ledger.close()
        if args.command == 'yokatlas' and args.verify_only:
            _, pages = prepare_yokatlas(args.snapshot)
            print(encode_json({'status': 'verified_no_writes', 'pages': len(pages)}))
            return 0
        ledger = Ledger(args.ledger)
        try:
            if args.command == 'status':
                result = ledger.get(args.operation_id) if args.operation_id else ledger.stats()
                print(encode_json({'checkpoint': result}))
                return 0
            if args.command == 'reconcile':
                if not args.verified_by_db:
                    raise ValueError('Independent DB verification is required')
                if args.not_committed:
                    ledger.reconcile(args.operation_id, not_committed=True)
                else:
                    key = json.loads(args.committed_key)
                    if not isinstance(key, dict) or not key or any(type(v) not in (str, int) for v in key.values()):
                        raise ValueError('Committed key must be a nonempty PK object')
                    ledger.reconcile(args.operation_id, committed_key=key)
                print(encode_json({'status': 'reconciled', 'operation_id': args.operation_id}))
                return 0
            conf = read_env_values(args.env_file) if args.env_file else {}
            # Actual environment overrides the file. No source or admin secrets are required here.
            base = os.environ.get('DATA_API_BASE_URL') or conf.get('DATA_API_BASE_URL')
            key = os.environ.get('DB_WRITE_API_KEY') or conf.get('DB_WRITE_API_KEY')
            client = RawWriteClient(base_url=base, api_key=key)
            try:
                if args.command == 'yokatlas':
                    result = publish_yokatlas(args.snapshot, ledger, client)
                elif args.command == 'yokatlas-live':
                    result = publish_yokatlas(snapshot, ledger, client)
                elif args.command == 'report':
                    result = publish_report(args.archive, ledger, client)
                elif args.command == 'report-live':
                    results = [publish_report(p, ledger, client) for p in archives]
                    result = {'source': args.source, 'reports': results}
                else:
                    if args.records_key and not args.tuik_legacy:
                        raise ValueError('--records-key requires --tuik-legacy')
                    result = publish_capture(args.directory, ledger, client,
                                             source_entity='tuik_df_adnks_t16' if args.tuik_legacy else None,
                                             records_key=args.records_key,
                                             openalex_entity_type=args.openalex_type)
            finally:
                client.close()
            print(encode_json({**result, 'checkpoint': ledger.stats()}))
            return 0
        finally:
            ledger.close()
    except Exception as exc:
        print(f'ERROR: {type(exc).__name__}: {exc if isinstance(exc, (ValueError, ReconciliationRequired, RejectedWrite, UncertainWrite)) else "Kontrol gerektiren hata; ayrıntılar için yerel loglara bakın"}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
