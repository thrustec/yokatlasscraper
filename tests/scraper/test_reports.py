"""PDF layout, archive integrity, cancellation and isolated PostgreSQL checks."""
import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

from scraper import report_bot as bot
from scraper import report_parsers as parsers


ROOT = Path(__file__).resolve().parents[2]


def urap_data():
    rows = []
    for rank in range(1, 199):
        total = 1200 - rank
        rows.append({'universite_adi': f'Test Üniversitesi {rank}', 'il_adi': 'Ankara',
                     'sira': rank, 'toplam_puan': total,
                     'puanlar': {key: total / 8 for key in parsers.INDICATORS},
                     'source_page': 18, 'source_table': 'Tablo 10'})
    return {'report_id': 'urap-tr-2025-2026', 'source_system': 'urap', 'edition': '2025-2026',
            'parser_version': parsers.PARSER_VERSION, 'counts': {'universite': 198}, 'records': rows}


def sege_data():
    rows = []
    names = ['Ankara' if rank == 6 else f'İl {rank}' for rank in range(1, 82)]
    for rank, name in enumerate(names, 1):
        rows.append({'yerlesim_duzeyi': 'il', 'yerlesim_adi': name, 'il_adi': name,
                     'sira': rank, 'skor': 100 - rank, 'kademe': 1,
                     'alt_boyut_siralari': {key: rank for key in parsers.DIMENSIONS},
                     'source_page': 47, 'source_table': 'Tablo 12'})
    for rank in range(1, 27):
        members = names[(rank - 1) * 3:rank * 3] if rank < 26 else names[75:]
        rows.append({'yerlesim_duzeyi': 'bolge', 'yerlesim_adi': f'TR{rank:02}', 'bolge_kodu': f'TR{rank:02}',
                     'bolge_illeri': members, 'sira': rank, 'skor': 200 - rank, 'kademe': 1,
                     'source_page': 89, 'source_table': 'Tablo 21'})
    return {'report_id': 'sege-il-2025', 'source_system': 'sege', 'edition': '2025',
            'parser_version': parsers.PARSER_VERSION, 'counts': {'il': 81, 'bolge': 26}, 'records': rows}


def make_archive(root, data, suffix=b''):
    source = root / ('input' + str(len(list(root.glob('input*')))) + '.pdf')
    source.write_bytes(b'%PDF-1.7\nunit-test-source' + suffix)
    with patch.object(bot, 'parse_report', return_value=copy.deepcopy(data)):
        return bot.archive_report(root / 'archive', data['report_id'], pdf_path=source)


def monitor(settings=None):
    obj = Mock(settings=settings or {}, retry_requests=[])
    obj.should_stop.return_value = False
    return obj


class ReportTests(unittest.TestCase):
    def test_turkish_names_and_split_hyphen(self):
        self.assertEqual(parsers.name_key('ELÂZIĞ'), parsers.name_key('Elazığ'))
        self.assertEqual(parsers.name_key('ŞANLIURFA'), parsers.name_key('Şanlıurfa'))
        self.assertEqual(parsers.clean('İSTANBUL ÜNİVERSİTESİ-\nCERRAHPAŞA'), 'İSTANBUL ÜNİVERSİTESİ-CERRAHPAŞA')
        self.assertEqual(parsers.number('-0,001'), -0.001)
        for text in ['NaN', '1.234,56', '', '3 4']:
            with self.subTest(text=text), self.assertRaises(parsers.ReportError):
                parsers.number(text)

    def test_incomplete_duplicate_reordered_and_bad_components_are_rejected(self):
        original = urap_data()
        parsers.validate_extraction(original, original['report_id'])
        mutations = [
            lambda d: d['records'].pop(),
            lambda d: d['records'][1].update(sira=1),
            lambda d: d['records'][0].update(universite_adi=d['records'][1]['universite_adi']),
            lambda d: d['records'][0].update(universite_adi=d['records'][1]['universite_adi'], il_adi='İstanbul'),
            lambda d: d['records'][0].update(toplam_puan=float('nan')),
            lambda d: d['records'][0]['puanlar'].pop('makale'),
            lambda d: d['records'][0]['puanlar'].update(makale=0),
            lambda d: d['records'][0].update(source_page=999),
            lambda d: d.update(edition='2026-2027'),
        ]
        for mutate in mutations:
            data = copy.deepcopy(original)
            mutate(data)
            with self.subTest(mutate=mutate), self.assertRaises(parsers.ReportError):
                parsers.validate_extraction(data, data['report_id'])

    def test_rotated_urap_header_and_continuation_rows(self):
        values = ['1', None, 'KOÇ ÜNİVERSİTESİ', '', 'İSTANBUL', *['1,00'] * 8, '8,00']
        pages = [Mock() for _ in range(31)]
        for page in pages:
            page.extract_tables.return_value = []
        pages[17].extract_tables.return_value = [[['SIRA', 'header'], values]]
        pages[25].extract_tables.return_value = [[['198', 'SON ÜNİVERSİTE', 'ANKARA', *['0,00'] * 9]]]
        rows = parsers._urap(SimpleNamespace(pages=pages), None)
        self.assertEqual([r['sira'] for r in rows], [1, 198])
        self.assertEqual(rows[0]['source_page'], 18)
        self.assertEqual(rows[1]['toplam_puan'], 0)
        self.assertEqual(len(rows[0]['puanlar']), 8)

    def test_wrong_layout_is_not_parsed(self):
        pdf = MagicMock(pages=[Mock()])
        with patch.object(parsers.pdfplumber, 'open') as opening:
            opening.return_value.__enter__.return_value = pdf
            with self.assertRaisesRegex(parsers.ReportError, 'sayfa sayısı'):
                parsers.parse_report('unused.pdf', 'sege-il-2025')

    def test_archive_cache_offline_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = make_archive(root, urap_data())
            meta, data = bot.read_archive(archive, 'urap-tr-2025-2026')
            self.assertEqual(len(data['records']), 198)
            with patch.object(bot, 'download_pdf') as download, patch.object(bot, 'parse_report') as parse:
                again = bot.archive_report(root / 'archive', 'urap-tr-2025-2026', offline=True)
            self.assertEqual(again, archive)
            self.assertEqual(bot.read_archive(again, data['report_id'])[0]['captured_at'], meta['captured_at'])
            download.assert_not_called()
            parse.assert_not_called()
            (archive / 'extraction.json').write_text('{}')
            with self.assertRaisesRegex(parsers.ReportError, 'özeti'):
                bot.read_archive(archive, data['report_id'])

    def test_source_survives_parse_error_and_can_be_retried_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(bot, 'download_pdf', return_value=b'%PDF-1.7\npartial'), \
                    patch.object(bot, 'parse_report', side_effect=parsers.ReportError('layout')):
                with self.assertRaises(parsers.ReportError):
                    bot.archive_report(root, 'urap-tr-2025-2026')
            source = next(root.glob('*/' + '*' + '/source.pdf'))
            source_receipt = json.loads(source.with_name('source.meta.json').read_text())
            with patch.object(bot, 'download_pdf') as download, patch.object(bot, 'parse_report', return_value=urap_data()):
                archive = bot.archive_report(root, 'urap-tr-2025-2026', offline=True)
            download.assert_not_called()
            self.assertEqual(bot.read_archive(archive, 'urap-tr-2025-2026')[0]['captured_at'], source_receipt['captured_at'])

    def test_http_html_rejection_and_redirect_stay_on_official_host(self):
        for status, headers, chunks in [(200, {}, [b'<html>Request Rejected</html>']),
                                        (302, {'Location': 'http://127.0.0.1/private'}, [])]:
            response = MagicMock(status_code=status, headers=headers)
            response.__enter__.return_value = response
            response.iter_content.return_value = iter(chunks)
            panel = monitor()
            with patch.object(bot.requests, 'get', return_value=response) as get:
                with self.assertRaises(parsers.ReportError):
                    bot.download_pdf('sege-il-2025', panel)
            self.assertEqual(get.call_count, 1)
            panel.request_failed.assert_called_once()
            panel.request_ok.assert_not_called()

    def test_cancelled_download_cannot_count_as_success(self):
        response = MagicMock(status_code=200, headers={})
        response.__enter__.return_value = response
        response.iter_content.return_value = iter([b'%PDF-1.7', b'chunk'])
        panel = monitor()
        panel.should_stop.side_effect = [False, False, True]
        with patch.object(bot.requests, 'get', return_value=response), self.assertRaises(KeyboardInterrupt):
            bot.download_pdf('urap-tr-2025-2026', panel)
        panel.request_ok.assert_not_called()

    def test_paths_and_settings_are_checked_before_requests(self):
        settings = [{'arsiv_dizini': '../outside'}, {'sadece_arsiv': 'false'},
                    {'rapor': 'urap-tr-2025-2026'}, {'unknown': True},
                    {'pdf_dosyasi': 'outputs/input.pdf'}]
        for value in settings:
            with self.subTest(settings=value), patch.object(bot, 'download_pdf') as get:
                with self.assertRaises(parsers.ReportError):
                    bot.run('sege', value)
                get.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(bot, 'ROOT', Path(tmp)):
                (Path(tmp) / 'escape').symlink_to(Path(tmp).parent, target_is_directory=True)
                with self.assertRaises(parsers.ReportError):
                    bot.local_path('escape/elsewhere')

    def test_retry_preserves_original_report_after_settings_change(self):
        panel = monitor({'rapor': 'sege-il-2025', 'sadece_arsiv': True})
        panel.retry_requests = [{'request_key': parsers.REPORTS['sege-ilce-2022']['url'], 'failed_id': 12}]
        with tempfile.TemporaryDirectory() as tmp, patch.object(bot, 'ROOT', Path(tmp).resolve()), \
                patch.object(bot, 'archive_report', return_value=Path(tmp)) as archive, \
                patch.object(bot, 'read_archive', return_value=({}, {'counts': {'ilce': 973}, 'records': [None] * 973})):
            result = bot.run('sege', panel.settings, panel)
        self.assertEqual(archive.call_args.args[1], 'sege-ilce-2022')
        self.assertEqual(result[0]['report_id'], 'sege-ilce-2022')

    def test_connection_uses_ingestion_role_and_tls_settings(self):
        import psycopg
        with patch.object(bot, 'read_env', return_value={}), patch.dict(os.environ, {
            'ATLAS_INGEST_PASSWORD': 'ingest-test', 'PGUSER': 'atlas_owner',
            'PGPASSWORD': 'wrong-password', 'PGSSLMODE': 'verify-full', 'PGSSLROOTCERT': '/test/ca.pem',
        }), patch.object(psycopg, 'connect') as connect:
            bot.db_connect()
        self.assertEqual(connect.call_args.kwargs['user'], 'atlas_ingest')
        self.assertEqual(connect.call_args.kwargs['password'], 'ingest-test')
        self.assertEqual(connect.call_args.kwargs['sslmode'], 'verify-full')
        self.assertEqual(connect.call_args.kwargs['sslrootcert'], '/test/ca.pem')


@unittest.skipUnless(os.environ.get('REPORT_BOT_PDF_DIR'), 'Set REPORT_BOT_PDF_DIR for official PDF layout checks')
class OfficialPDFTests(unittest.TestCase):
    def test_official_reports(self):
        path = Path(os.environ['REPORT_BOT_PDF_DIR'])
        cases = [('sege-il-2025', 'sege_2025.pdf'), ('sege-ilce-2022', 'sege_district_2022.pdf'),
                 ('urap-tr-2025-2026', 'urap_tr_2025_2026.pdf')]
        for report_id, filename in cases:
            with self.subTest(report_id=report_id):
                data = parsers.parse_report(path / filename, report_id)
                self.assertEqual(data['counts'], parsers.REPORTS[report_id]['counts'])
                rows = data['records']
                if report_id == 'sege-il-2025':
                    first = next(r for r in rows if r['yerlesim_duzeyi'] == 'il' and r['sira'] == 1)
                    self.assertEqual((first['yerlesim_adi'], first['skor'], first['kademe']), ('İstanbul', 4.419, 1))
                    self.assertEqual(first['alt_boyut_siralari']['egitim'], 12)
                elif report_id == 'sege-ilce-2022':
                    self.assertEqual((rows[0]['yerlesim_adi'], rows[0]['skor'], rows[0]['kademe']), ('Şişli', 6.959, 1))
                    self.assertEqual((rows[-1]['yerlesim_adi'], rows[-1]['skor']), ('Harran', -1.447))
                    seyhan = next(r for r in rows if r['sira'] == 42)
                    self.assertEqual((seyhan['il_adi'], seyhan['il_ici_sira']), ('Adana', 1))
                else:
                    self.assertEqual((rows[0]['universite_adi'], rows[0]['toplam_puan']), ('KOÇ ÜNİVERSİTESİ', 1152.91))
                    self.assertEqual((rows[-1]['sira'], rows[-1]['toplam_puan']), (198, 70.82))


@unittest.skipUnless(os.environ.get('REPORT_BOT_TEST_DSN'), 'Set REPORT_BOT_TEST_DSN to an isolated test database')
class ReportDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from psycopg import sql
        cls.admin = psycopg.connect(os.environ['REPORT_BOT_TEST_DSN'], autocommit=True)
        if not cls.admin.info.dbname.startswith('test_yokatlas_'):
            cls.admin.close()
            raise ValueError('Refusing to modify a database without test_yokatlas_ prefix')
        for role in ['atlas_owner', 'atlas_api', 'atlas_analytics', 'atlas_ingest']:
            if not cls.admin.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,)).fetchone():
                statement = (sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(role), sql.Literal('isolated-report-tests'))
                             if role == 'atlas_ingest' else sql.SQL('CREATE ROLE {}').format(sql.Identifier(role)))
                cls.admin.execute(statement)
        for migration in ['001_data_contract_v1.sql', '002_api_views.sql', '003_privileges.sql',
                          '004_archive_idempotency.sql', '007_sege_urap_reports.sql']:
            cls.admin.execute((ROOT / 'database/migrations' / migration).read_text())

    @classmethod
    def tearDownClass(cls):
        cls.admin.close()

    def setUp(self):
        import psycopg
        self.admin.execute('TRUNCATE raw.ingestion_runs,core.cities,core.universities RESTART IDENTITY CASCADE')
        self.admin.execute("INSERT INTO core.cities (il_kodu,il_adi) VALUES (6,'Ankara')")
        self.admin.cursor().executemany('INSERT INTO core.universities (universite_id,universite_adi) VALUES (%s,%s)',
                                       [(n, f'Test Üniversitesi {n}') for n in range(1, 199)])
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = urap_data()
        self.archive = make_archive(self.root, self.data)
        patcher = patch.object(bot, 'db_connect', side_effect=lambda: psycopg.connect(
            host=self.admin.info.host, port=self.admin.info.port, dbname=self.admin.info.dbname,
            user='atlas_ingest', password='isolated-report-tests', autocommit=True))
        patcher.start()
        self.addCleanup(patcher.stop)

    def scalar(self, statement):
        return self.admin.execute(statement).fetchone()[0]

    def test_real_role_import_and_replay_are_idempotent(self):
        first = bot.import_report(self.archive, self.data['report_id'])
        self.assertTrue(first['published'])
        again = bot.import_report(self.archive, self.data['report_id'])
        self.assertEqual(again['new_records'], 0)
        self.assertEqual(first['document_id'], again['document_id'])
        self.assertEqual(self.scalar('SELECT count(*) FROM raw.report_documents'), 1)
        self.assertEqual(self.scalar('SELECT count(*) FROM staging.urap_rankings'), 198)
        self.assertEqual(self.scalar('SELECT count(*) FROM api.urap_rankings'), 198)
        self.assertEqual(self.scalar('SELECT count(*) FROM raw.ingestion_runs'), 2)

    def test_crashed_run_is_marked_interrupted_before_resuming_same_report(self):
        self.admin.execute('''INSERT INTO raw.ingestion_runs (source_system,status,details)
            VALUES ('urap','running','{"report_id":"urap-tr-2025-2026"}'),
                   ('sege','running','{"report_id":"sege-il-2025"}')''')
        bot.import_report(self.archive, self.data['report_id'])
        self.assertEqual(self.scalar('SELECT status FROM raw.ingestion_runs WHERE ingestion_run_id=1'), 'interrupted')
        self.assertEqual(self.scalar('SELECT status FROM raw.ingestion_runs WHERE ingestion_run_id=2'), 'running')

    def test_sege_year_queries_coexist_with_urap_edition_strings(self):
        bot.import_report(self.archive, self.data['report_id'])
        data = sege_data()
        self.admin.cursor().executemany('INSERT INTO core.cities (il_kodu,il_adi) VALUES (%s,%s) ON CONFLICT DO NOTHING',
                                       [(r['sira'],r['il_adi']) for r in data['records'] if r['yerlesim_duzeyi']=='il'])
        archive = make_archive(self.root, data, b'sege fixture')
        result = bot.import_report(archive, data['report_id'])
        self.assertTrue(result['published'])
        self.assertEqual(self.scalar('SELECT max(yil) FROM api.sege_results'), 2025)
        self.assertEqual(self.scalar("SELECT count(*) FROM api.sege_results WHERE yerlesim_duzeyi='il'"), 81)
        self.assertEqual(self.scalar('SELECT count(*) FROM api.urap_rankings'), 198)

    def test_unmapped_revision_stays_hidden_then_alias_publishes_it(self):
        first = bot.import_report(self.archive, self.data['report_id'])
        updated = copy.deepcopy(self.data)
        updated['records'][0]['universite_adi'] = 'Yeni Kaynak Adı'
        newer = make_archive(self.root, updated, b'revision')
        failed = bot.import_report(newer, self.data['report_id'])
        self.assertFalse(failed['published'])
        self.assertEqual(failed['status'], 'completed_with_issues')
        self.assertEqual(self.scalar('SELECT document_id FROM staging.report_publications'), first['document_id'])
        self.assertEqual(self.scalar('SELECT count(*) FROM staging.urap_rankings'), 396)
        fixed = bot.import_report(newer, self.data['report_id'], aliases={'Yeni Kaynak Adı': 1})
        self.assertTrue(fixed['published'])
        self.assertEqual(self.scalar('SELECT universite_adi FROM api.urap_rankings WHERE sira=1'), 'Yeni Kaynak Adı')
        self.assertEqual(self.scalar('SELECT count(*) FROM raw.report_documents'), 2)

    def test_bad_remapping_cannot_change_current_public_rows(self):
        bot.import_report(self.archive, self.data['report_id'])
        result = bot.import_report(self.archive, self.data['report_id'], aliases={'Test Üniversitesi 1': 2})
        self.assertFalse(result['published'])
        self.assertEqual(self.scalar('SELECT universite_id FROM api.urap_rankings WHERE sira=1'), 1)

    def test_sql_failure_rolls_back_document_and_records(self):
        import psycopg
        self.admin.execute('''CREATE OR REPLACE FUNCTION staging.report_test_fail() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.sira=2 THEN RAISE EXCEPTION 'private database detail'; END IF; RETURN NEW; END $$;
            CREATE TRIGGER report_test_fail BEFORE INSERT ON staging.urap_rankings
                FOR EACH ROW EXECUTE FUNCTION staging.report_test_fail()''')
        try:
            with self.assertRaises(psycopg.Error):
                bot.import_report(self.archive, self.data['report_id'])
            self.assertEqual(self.scalar('SELECT count(*) FROM raw.report_documents'), 0)
            self.assertEqual(self.scalar('SELECT count(*) FROM staging.urap_rankings'), 0)
            self.assertEqual(self.scalar('SELECT count(*) FROM api.urap_rankings'), 0)
            status, details = self.admin.execute('SELECT status,details FROM raw.ingestion_runs').fetchone()
            self.assertEqual(status, 'failed')
            self.assertNotIn('private database detail', str(details))
        finally:
            self.admin.execute('DROP TRIGGER report_test_fail ON staging.urap_rankings; DROP FUNCTION staging.report_test_fail()')

    def test_stop_mid_transaction_preserves_previous_publication(self):
        first = bot.import_report(self.archive, self.data['report_id'])
        newer = make_archive(self.root, self.data, b'new revision')
        panel = monitor()
        checks = 0
        def should_stop():
            nonlocal checks
            checks += 1
            return checks > 210
        panel.should_stop.side_effect = should_stop
        with self.assertRaises(KeyboardInterrupt):
            bot.import_report(newer, self.data['report_id'], monitor=panel)
        self.assertEqual(self.scalar('SELECT document_id FROM staging.report_publications'), first['document_id'])
        self.assertEqual(self.scalar('SELECT count(*) FROM staging.urap_rankings'), 198)
        self.assertEqual(self.scalar('SELECT count(*) FROM raw.report_documents'), 1)
        self.assertEqual(self.scalar('SELECT status FROM raw.ingestion_runs ORDER BY ingestion_run_id DESC LIMIT 1'), 'interrupted')

    def test_migration_replay_and_api_cannot_read_raw(self):
        import psycopg
        self.admin.execute((ROOT / 'database/migrations/007_sege_urap_reports.sql').read_text())
        bot.import_report(self.archive, self.data['report_id'])
        with self.admin.transaction():
            self.admin.execute('SET LOCAL ROLE atlas_api')
            self.assertEqual(self.scalar('SELECT count(*) FROM api.urap_rankings'), 198)
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.admin.transaction():
                self.admin.execute('SET LOCAL ROLE atlas_api')
                self.admin.execute('SELECT archive_path FROM raw.report_documents')


if __name__ == '__main__':
    unittest.main()
