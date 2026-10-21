"""PDF archive -> validated report -> PostgreSQL; shared CLI and panel runner."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urljoin, urlsplit

import requests

from scraper.bot import process_lock
from scraper.report_parsers import PARSER_VERSION, REPORTS, ReportError, name_key, parse_report, stopped, validate_extraction
from scripts.database.load_archive import canonical, read_env


ROOT = Path(__file__).resolve().parents[1]
MAX_PDF_BYTES = 40 * 1024 * 1024


def local_path(value):
    if not isinstance(value, str) or not value or Path(value).is_absolute() or '..' in Path(value).parts:
        raise ReportError('Dosya ve arşiv yolları proje klasörü içinde göreli olmalı.')
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        raise ReportError('Dosya ve arşiv yolları proje klasörünün dışına çıkamaz.')
    return path


def atomic_write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temp = Path(stream.name)
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp and temp.exists():
            temp.unlink()


def write_json(path, data):
    atomic_write(path, canonical(data).encode('utf-8'))


def _pdf(body):
    if not body.startswith(b'%PDF-') or len(body) > MAX_PDF_BYTES:
        raise ReportError('Kaynak geçerli bir PDF değil veya 40 MB sınırını aşıyor.')
    return body


def read_pdf(path):
    if not path.is_file() or path.stat().st_size > MAX_PDF_BYTES:
        raise ReportError('PDF bulunamadı veya 40 MB sınırını aşıyor.')
    return _pdf(path.read_bytes())


def download_pdf(report_id, monitor=None):
    url = REPORTS[report_id]['url']
    stopped(monitor)
    failed_id = next((r['failed_id'] for r in monitor.retry_requests if r['request_key'] == url), None) if monitor else None
    try:
        target = url
        for _ in range(4):
            parts = urlsplit(target)
            if (parts.scheme != 'https' or parts.hostname != urlsplit(url).hostname
                    or parts.username or parts.password or parts.port not in (None, 443)):
                raise ReportError('PDF bağlantısı beklenen resmî kaynak dışına yönlendiriyor.')
            with requests.get(target, stream=True, allow_redirects=False, timeout=(10, 45),
                              headers={'User-Agent': 'YOKAtlas-Report-Bot/1.0', 'Accept': 'application/pdf'}) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    target = urljoin(target, response.headers.get('Location', ''))
                    continue
                if response.status_code != 200:
                    raise ReportError(f'PDF kaynağı HTTP {response.status_code} döndürdü; daha sonra yeniden deneyin.')
                chunks, size = [], 0
                for chunk in response.iter_content(65536):
                    stopped(monitor)
                    size += len(chunk)
                    if size > MAX_PDF_BYTES:
                        raise ReportError('PDF 40 MB sınırını aşıyor.')
                    chunks.append(chunk)
                body = _pdf(b''.join(chunks))
                break
        else:
            raise ReportError('PDF kaynağında çok fazla yönlendirme var.')
    except (requests.RequestException, ValueError):
        error = ReportError('PDF kaynağına güvenli bağlantı kurulamadı.')
        if monitor:
            monitor.request_failed(url, url=url, error=str(error), failed_id=failed_id)
        raise error from None
    except ReportError as error:
        if monitor:
            monitor.request_failed(url, url=url, error=str(error), failed_id=failed_id)
        raise
    if monitor:
        monitor.request_ok(failed_id=failed_id)
    stopped(monitor)
    return body


def read_archive(archive, report_id):
    try:
        meta = json.loads((archive / 'manifest.json').read_text())
        source = archive.parent / 'source.pdf'
        receipt = json.loads(source.with_name('source.meta.json').read_text())
        raw = read_pdf(source)
        body = (archive / 'extraction.json').read_bytes()
        if (meta['report_id'] != report_id or meta['parser_version'] != PARSER_VERSION
                or hashlib.sha256(_pdf(raw)).hexdigest() != meta['source_sha256']
                or hashlib.sha256(body).hexdigest() != meta['extracted_sha256']
                or meta['source_url'] != REPORTS[report_id]['url']
                or any(meta.get(key) != receipt.get(key) for key in ['source_sha256', 'source_url', 'captured_at'])):
            raise ReportError('PDF arşivinin kimliği veya dosya özeti uyuşmuyor.')
        captured = datetime.fromisoformat(meta['captured_at'])
        if captured.tzinfo is None:
            raise ReportError('PDF arşivindeki zaman bilgisi saat dilimi içermeli.')
        data = validate_extraction(json.loads(body), report_id)
        return meta, data
    except (ReportError, KeyboardInterrupt):
        raise
    except Exception:
        raise ReportError('PDF arşivi eksik veya bozuk; kaynak dosyasını ve manifesti kontrol edin.') from None


def archive_report(root, report_id, *, pdf_path=None, offline=False, monitor=None):
    stopped(monitor)
    base = root / report_id
    if offline:
        try:
            sha = json.loads((base / 'latest.json').read_text())['source_sha256']
            if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
                raise ValueError
            body = read_pdf(base / sha / 'source.pdf')
            if hashlib.sha256(body).hexdigest() != sha:
                raise ValueError
        except Exception:
            raise ReportError('Çevrimdışı arşiv bulunamadı veya PDF özeti uyuşmuyor.') from None
    elif pdf_path:
        body = read_pdf(pdf_path)
    else:
        body = download_pdf(report_id, monitor)
    sha = hashlib.sha256(body).hexdigest()
    folder = base / sha
    source = folder / 'source.pdf'
    if source.exists():
        if hashlib.sha256(read_pdf(source)).hexdigest() != sha:
            raise ReportError('Arşivdeki orijinal PDF değiştirilmiş; üzerine yazılmadı.')
    else:
        atomic_write(source, body)
    receipt_path = folder / 'source.meta.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt.get('source_sha256') != sha or receipt.get('source_url') != REPORTS[report_id]['url']:
            raise ReportError('Orijinal PDF makbuzu kaynakla uyuşmuyor.')
    else:
        receipt = {'source_sha256': sha, 'source_url': REPORTS[report_id]['url'],
                   'captured_at': datetime.now(timezone.utc).isoformat(),
                   'input': 'local_pdf' if pdf_path else 'archive' if offline else 'https'}
        write_json(receipt_path, receipt)
    archive = folder / PARSER_VERSION
    if (archive / 'manifest.json').exists() and (archive / 'extraction.json').exists():
        read_archive(archive, report_id)
    else:
        meta = {**receipt, 'report_id': report_id, 'parser_version': PARSER_VERSION, 'phase': 'downloaded'}
        write_json(archive / 'manifest.json', meta)
        # The source survives a parser failure; an offline retry needs no new HTTP request.
        write_json(base / 'latest.json', {'source_sha256': sha})
        data = parse_report(source, report_id, monitor)
        encoded = canonical(data).encode('utf-8')
        atomic_write(archive / 'extraction.json', encoded)
        meta.update(phase='parsed', extracted_sha256=hashlib.sha256(encoded).hexdigest(), counts=data['counts'])
        write_json(archive / 'manifest.json', meta)
    write_json(base / 'latest.json', {'source_sha256': sha})
    return archive


def db_connect():
    import psycopg
    env = {**read_env(ROOT / '.env'), **os.environ}
    password = env.get('ATLAS_INGEST_PASSWORD')
    if not password:
        raise ReportError('Veritabanı için ATLAS_INGEST_PASSWORD tanımlanmalı.')
    params = dict(host=env.get('PGHOST', '127.0.0.1'),
                  port=int(env.get('PGPORT') or env.get('POSTGRES_PORT') or 5433),
                  dbname=env.get('PGDATABASE', 'yokatlas_intelligence'),
                  user='atlas_ingest', password=password, connect_timeout=5, autocommit=True,
                  options='-c statement_timeout=60000 -c lock_timeout=10000')
    for name, option in [('PGSSLMODE', 'sslmode'), ('PGSSLROOTCERT', 'sslrootcert')]:
        if env.get(name):
            params[option] = env[name]
    return psycopg.connect(**params)


def _identities(pairs):
    groups = {}
    for code, name in pairs:
        groups.setdefault(name_key(name), set()).add(code)
    return {key: next(iter(codes)) for key, codes in groups.items() if len(codes) == 1}


def _aliases(aliases, universities):
    if not isinstance(aliases, dict):
        raise ReportError('Üniversite eşlemeleri ad → üniversite ID nesnesi olmalı.')
    result = {}
    known_ids = {code for code, _ in universities}
    for name, code in aliases.items():
        if (not isinstance(name, str) or not name_key(name) or type(code) is not int
                or code not in known_ids or name_key(name) in result):
            raise ReportError('Üniversite eşlemesi geçersiz veya hedef ID mevcut değil.')
        result[name_key(name)] = code
    return result


def import_report(archive, report_id, *, aliases=None, monitor=None):
    from psycopg.types.json import Jsonb
    meta, data = read_archive(archive, report_id)
    spec = REPORTS[report_id]
    stopped(monitor)
    with db_connect() as conn, conn.cursor() as cur:
        cur.execute('SELECT pg_try_advisory_lock(hashtext(%s))', ('pdf_report:' + report_id,))
        if not cur.fetchone()[0]:
            raise ReportError('Bu rapor için başka bir aktarım sürüyor.')
        cur.execute('''UPDATE raw.ingestion_runs SET status='interrupted',completed_at=now()
            WHERE source_system=%s AND details->>'report_id'=%s AND status='running' ''',
                    (spec['bot'], report_id))
        cur.execute('''INSERT INTO raw.ingestion_runs (source_system,scraper_version,status,details)
            VALUES (%s,%s,'running',%s) RETURNING ingestion_run_id''',
                    (spec['bot'], PARSER_VERSION, Jsonb({'report_id': report_id, 'source_sha256': meta['source_sha256']})))
        run_id = cur.fetchone()[0]
        try:
            with conn.transaction():
                cur.execute('''INSERT INTO raw.report_documents
                    (ingestion_run_id,report_id,source_system,edition,source_url,captured_at,source_sha256,
                     parser_version,extracted_sha256,archive_path,payload)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (report_id,source_sha256,parser_version) DO NOTHING RETURNING document_id''',
                            (run_id, report_id, spec['bot'], spec['edition'], meta['source_url'], meta['captured_at'],
                             meta['source_sha256'], PARSER_VERSION, meta['extracted_sha256'], str(archive), Jsonb(data)))
                inserted = cur.fetchone()
                cur.execute('''SELECT document_id,extracted_sha256 FROM raw.report_documents
                    WHERE report_id=%s AND source_sha256=%s AND parser_version=%s''',
                            (report_id, meta['source_sha256'], PARSER_VERSION))
                document_id, extracted_sha = cur.fetchone()
                if extracted_sha != meta['extracted_sha256']:
                    raise ReportError('Aynı PDF/sürüm için farklı ayrıştırma bulundu; ayrıştırıcı sürümünü inceleyin.')
                cur.execute('SELECT il_kodu,il_adi FROM core.cities')
                cities = _identities(cur.fetchall())
                cur.execute('SELECT universite_id,universite_adi FROM core.universities')
                universities = cur.fetchall()
                university_ids = {**_identities(universities), **_aliases(aliases if aliases is not None else {}, universities)}
                cur.execute('SELECT document_id FROM staging.report_publications WHERE report_id=%s', (report_id,))
                active = cur.fetchone()
                issues, seen_ids, mapped = set(), set(), []
                for index, row in enumerate(data['records']):
                    stopped(monitor)
                    city_id = cities.get(name_key(row.get('il_adi', '')))
                    uid = None
                    if row.get('yerlesim_duzeyi') != 'bolge' and city_id is None:
                        issues.add('İl eşleşmedi: ' + row['il_adi'])
                    if spec['bot'] == 'sege':
                        for member in row.get('bolge_illeri', []):
                            if name_key(member) not in cities:
                                issues.add('İl eşleşmedi: ' + member)
                    else:
                        uid = university_ids.get(name_key(row['universite_adi']))
                        if uid is None:
                            issues.add('Üniversite eşleşmedi: ' + row['universite_adi'])
                        elif uid in seen_ids:
                            issues.add('Üniversite eşlemesi birden çok kaynak kaydına bağlandı: ' + row['universite_adi'])
                        seen_ids.add(uid)
                    mapped.append((row, city_id, uid))
                # A bad remapping must not mutate the very document the public pointer already serves.
                to_stage = [] if issues and active and active[0] == document_id else mapped
                for index, (row, city_id, uid) in enumerate(to_stage):
                    stopped(monitor)
                    if monitor and index % 50 == 0:
                        monitor.progress(index, len(data['records']), 'PostgreSQL: rapor eşleme ve kayıt')
                    if spec['bot'] == 'sege':
                        key = name_key(row.get('il_adi', '')) + ':' + name_key(row['yerlesim_adi'])
                        cur.execute('''INSERT INTO staging.sege_results
                            (document_id,entity_key,yerlesim_duzeyi,yerlesim_adi,il_adi,il_kodu,bolge_kodu,
                             sira,skor,kademe,il_ici_sira,alt_boyut_siralari,bolge_illeri,source_page,source_table)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (document_id,yerlesim_duzeyi,entity_key) DO UPDATE SET il_kodu=EXCLUDED.il_kodu''',
                                    (document_id, key, row['yerlesim_duzeyi'], row['yerlesim_adi'], row.get('il_adi'),
                                     city_id, row.get('bolge_kodu'), row['sira'], row['skor'], row['kademe'], row.get('il_ici_sira'),
                                     Jsonb(row.get('alt_boyut_siralari', {})), Jsonb(row.get('bolge_illeri', [])),
                                     row['source_page'], row['source_table']))
                    else:
                        cur.execute('''INSERT INTO staging.urap_rankings
                            (document_id,source_key,universite_adi,universite_id,il_adi,il_kodu,sira,toplam_puan,puanlar,source_page,source_table)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (document_id,source_key) DO UPDATE SET
                                universite_id=EXCLUDED.universite_id,il_kodu=EXCLUDED.il_kodu''',
                                    (document_id, name_key(row['universite_adi']), row['universite_adi'], uid,
                                     row['il_adi'], city_id, row['sira'], row['toplam_puan'], Jsonb(row['puanlar']),
                                     row['source_page'], row['source_table']))
                stopped(monitor)
                if not issues:
                    cur.execute('''SELECT d.captured_at,p.document_id FROM staging.report_publications p
                        JOIN raw.report_documents d USING (document_id) WHERE p.report_id=%s''', (report_id,))
                    previous = cur.fetchone()
                    if previous and previous[1] != document_id and previous[0] > datetime.fromisoformat(meta['captured_at']):
                        raise ReportError('Arşiv yayımlanmış sürümden eski; mevcut yayın korunuyor.')
                    cur.execute('''INSERT INTO staging.report_publications (report_id,document_id) VALUES (%s,%s)
                        ON CONFLICT (report_id) DO UPDATE SET document_id=EXCLUDED.document_id,published_at=now()
                        WHERE report_publications.document_id<>EXCLUDED.document_id''', (report_id, document_id))
                result = {'report_id': report_id, 'ingestion_run_id': run_id, 'document_id': document_id,
                          'status': 'completed_with_issues' if issues else 'completed', 'published': not issues,
                          'records': len(data['records']), 'new_records': len(data['records']) if inserted else 0,
                          'counts': data['counts'], 'issues': sorted(issues)}
                cur.execute("UPDATE raw.ingestion_runs SET status=%s,completed_at=now(),details=details || %s WHERE ingestion_run_id=%s",
                            (result['status'], Jsonb(result), run_id))
        except BaseException as exc:
            message = str(exc) if isinstance(exc, ReportError) else 'Aktarım durduruldu.' if isinstance(exc, KeyboardInterrupt) else f'Veritabanı aktarımı başarısız ({type(exc).__name__}).'
            cur.execute("UPDATE raw.ingestion_runs SET status=%s,completed_at=now(),details=details || %s WHERE ingestion_run_id=%s",
                        ('interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed', Jsonb({'message': message}), run_id))
            raise
    if monitor:
        monitor.records(result['new_records'])
    return result


def run(bot_id, settings, monitor=None):
    allowed = {'rapor', 'arsiv_dizini', 'sadece_arsiv', 'pdf_dosyasi', 'cevrimdisi', 'universite_eslemeleri'}
    if not isinstance(settings, dict) or set(settings) - allowed:
        raise ReportError('Bilinmeyen rapor botu ayarı var.')
    for key in ['sadece_arsiv', 'cevrimdisi']:
        if type(settings.get(key, False)) is not bool:
            raise ReportError(f'{key} doğru/yanlış değeri olmalı.')
    selected = settings.get('rapor', 'tum')
    reports = [key for key, spec in REPORTS.items() if spec['bot'] == bot_id and selected in ('tum', key)]
    if not reports:
        raise ReportError('Seçilen rapor bu botta desteklenmiyor.')
    if monitor and monitor.retry_requests:
        previous = [key for key, spec in REPORTS.items() if spec['bot'] == bot_id
                    and any(r['request_key'] == spec['url'] for r in monitor.retry_requests)]
        if previous:
            reports = previous
    root = local_path(settings.get('arsiv_dizini', f'outputs/{bot_id}_bot'))
    pdf_path = local_path(settings['pdf_dosyasi']) if settings.get('pdf_dosyasi') else None
    if pdf_path and (len(reports) != 1 or settings.get('cevrimdisi')):
        raise ReportError('Yerel PDF için tek rapor seçilmeli ve çevrimdışı ayarı kapalı olmalı.')
    aliases = settings.get('universite_eslemeleri', {})
    if (not isinstance(aliases, dict) or any(not isinstance(name, str) or not name_key(name)
            or type(code) is not int or not 0 < code <= 9223372036854775807 for name, code in aliases.items())):
        raise ReportError('Üniversite eşlemeleri bir nesne olmalı.')
    results = []
    with process_lock(root):
        for report_id in reports:
            if monitor:
                monitor.log(REPORTS[report_id]['title'])
            archive = archive_report(root, report_id, pdf_path=pdf_path,
                                     offline=settings.get('cevrimdisi', False), monitor=monitor)
            if settings.get('sadece_arsiv', False):
                _, data = read_archive(archive, report_id)
                result = {'report_id': report_id, 'status': 'archived', 'counts': data['counts'],
                          'records': len(data['records']), 'published': False}
            else:
                result = import_report(archive, report_id, aliases=aliases, monitor=monitor)
            results.append(result)
            if monitor:
                monitor.summary(reports=results)
        if monitor:
            monitor.progress(len(reports), len(reports), 'Rapor işlemleri tamamlandı')
    return results


def panel_main(bot_id):
    from botkit import Bot
    try:
        with Bot.from_env() as monitor:
            os.environ.update(PGHOST='postgres', PGPORT='5432', PGDATABASE='yokatlas_intelligence')
            results = run(bot_id, monitor.settings, monitor)
            if any(r['status'] == 'completed_with_issues' for r in results):
                raise ReportError('Kimlik eşlemeleri eksik/çakışıyor; özet içindeki uyarıları düzeltin. Önceki yayın korundu.')
    except KeyboardInterrupt:
        print('WARNING: Durduruldu; PDF arşivi ve önceki yayın korundu.', flush=True)
        return 130
    except Exception as exc:
        message = str(exc) if isinstance(exc, ReportError) else f'Rapor botu durdu ({type(exc).__name__}); bağlantıyı, migration 007 ve arşivi kontrol edin.'
        print('ERROR: ' + message, flush=True)
        return 3
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bot', choices=['sege', 'urap'])
    parser.add_argument('--report', default='tum', choices=['tum', *REPORTS])
    parser.add_argument('--root', help='Proje içindeki göreli arşiv dizini')
    parser.add_argument('--pdf', help='Tek rapor için proje içindeki yerel PDF')
    parser.add_argument('--archive-only', action='store_true')
    parser.add_argument('--offline', action='store_true', help='Son yerel PDF arşivinden çalış; HTTP isteği yapma')
    parser.add_argument('--university-map', help='Proje içindeki ad → mevcut üniversite ID JSON dosyası')
    args = parser.parse_args()
    try:
        settings = {'rapor': args.report, 'sadece_arsiv': args.archive_only, 'cevrimdisi': args.offline}
        if args.root:
            settings['arsiv_dizini'] = args.root
        if args.pdf:
            settings['pdf_dosyasi'] = args.pdf
        if args.university_map:
            settings['universite_eslemeleri'] = json.loads(local_path(args.university_map).read_text())
        results = run(args.bot, settings)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 4 if any(r['status'] == 'completed_with_issues' for r in results) else 0
    except KeyboardInterrupt:
        print('Durduruldu; PDF arşivi ve önceki yayın korundu.')
        return 130
    except Exception as exc:
        print(str(exc) if isinstance(exc, ReportError) else f'Rapor botu durdu ({type(exc).__name__}); bağlantıyı, migration 007 ve arşivi kontrol edin.')
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
