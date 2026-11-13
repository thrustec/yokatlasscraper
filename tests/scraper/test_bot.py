"""Offline failure/resume tests; real PostgreSQL checks opt in via YOKATLAS_TEST_DSN."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import requests

from scraper import bot
from scripts.database import load_archive as loader

ROOT = Path(__file__).resolve().parents[2]


def options():
    return SimpleNamespace(page_size=2, delay=2, timeout=5, retries=2, max_requests=5000,
        interval=86400, archive_only=True, env_file=None)


class FakeAPI:
    """Three historical nets, three programs, nested/unknown fields, two pages."""
    def __init__(self, args):
        self.session = SimpleNamespace(close=lambda: None)
        self.calls = []
        self.fail_at = None
        self.lookups = {
            '/api/tercih-kilavuz/universiteler': [{'universiteId': 42, 'universiteAdi': 'Deneme Üniversitesi'}],
            '/api/tercih-kilavuz/universite-iller': [{'ilKodu': 999, 'ilAdi': 'KIBRIS'}],
            '/api/tercih-kilavuz/universite-programlar': [{'birimGrupId': 7, 'birimGrupAdi': 'Test', 'puanTuru': 'SAY'}],
        }
        self.programs = [dict(kilavuzKodu=code, yil=2026, universiteId=42, ilKodu=999,
            birimGrupId=7, puanTuru='SAY', birimId=code, birimAdi='Program',
            minPuan=401.25, kontenjan=2, ucret=123456, minPuan1='390.5',
            kosulList=[{'21': 'Koşul açıklaması'}], newField={'nested': [1, None, 'ı']})
            for code in (11, 12, 13)]
        self.nets = [dict(kilavuzKodu=11, yil=year, puanTuru='SAY', universiteId=42,
            birimGrupId=7, katsayi=0.12, obp=450.5, tytMatNet=35.75) for year in (2023, 2024, 2025)]

    def fetch(self, method, endpoint, payload):
        key = (endpoint, None if payload is None else payload['filters']['puanTuru'],
            None if payload is None else payload['page'])
        self.calls.append(key)
        if key == self.fail_at:
            raise bot.Paused('Simulated network interruption')
        if method == 'GET':
            if endpoint == '/api/parameters/yil':
                return str(self.programs[0]['yil'] if self.programs else 2026).encode()
            if endpoint == '/api/parameters/sonuc-aciklandi':
                return b'1'
            return json.dumps(self.lookups[endpoint], ensure_ascii=False).encode()
        score = payload['filters']['puanTuru']
        rows = self.programs if 'tercih-kilavuz' in endpoint else self.nets
        rows = [row for row in rows if row['puanTuru'] == score]
        size, page = payload['size'], payload['page']
        selected = rows[page * size:(page + 1) * size]
        pages = (len(rows) + size - 1) // size
        result = dict(content=selected, number=page, size=size, numberOfElements=len(selected),
            totalElements=len(rows), totalPages=pages, last=page >= pages - 1)
        if 'tercih-kilavuz' in endpoint:
            result['yil'] = self.programs[0]['yil'] if self.programs else 2026
        return json.dumps(result, ensure_ascii=False, indent=1).encode()


class BotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.args = options()
        self.api = FakeAPI(self.args)

    def run_cycle(self):
        with patch.object(bot, 'API', return_value=self.api):
            return bot.cycle(self.root, self.args)

    def test_resume_at_failed_page_without_downloading_completed_pages(self):
        failed = ('/api/tercih-kilavuz/search', 'SAY', 1)
        self.api.fail_at = failed
        with self.assertRaises(bot.Paused):
            self.run_cycle()
        state = bot.read_json(self.root / 'state.json')
        snapshot = self.root / 'snapshots' / state['active_snapshot']
        before = (snapshot / 'complete_data/programs/SAY/page_000000.json').read_bytes()
        self.api.calls.clear()
        self.api.fail_at = None
        result = self.run_cycle()
        self.assertEqual(result['phase'], 'archived')
        self.assertEqual(self.api.calls[0], failed)
        self.assertFalse(any(endpoint in self.api.lookups for endpoint, _, _ in self.api.calls))
        self.assertEqual(before, (snapshot / 'complete_data/programs/SAY/page_000000.json').read_bytes())
        self.assertEqual(result['partitions']['net_results/SAY']['rows'], 3)

    def test_corrupted_archive_stops_without_overwriting_it(self):
        self.api.fail_at = ('/api/tercih-kilavuz/search', 'SAY', 1)
        with self.assertRaises(bot.Paused):
            self.run_cycle()
        state = bot.read_json(self.root / 'state.json')
        body = self.root / 'snapshots' / state['active_snapshot'] / 'complete_data/universities/all.json'
        body.write_text('[]')
        self.api.fail_at = None
        self.api.calls.clear()
        with self.assertRaisesRegex(ValueError, 'receipt mismatch'):
            self.run_cycle()
        self.assertEqual(body.read_text(), '[]')
        self.assertEqual(self.api.calls, [])

    def test_database_failure_resumes_import_without_http_calls(self):
        self.args.archive_only = False
        with patch.object(bot, 'import_archive', side_effect=RuntimeError('DB unavailable')):
            with self.assertRaises(RuntimeError):
                self.run_cycle()
        self.api.calls.clear()
        with patch.object(bot, 'import_archive', return_value={'status': 'completed'}) as ingest:
            result = self.run_cycle()
        self.assertEqual(result['phase'], 'completed')
        self.assertEqual(self.api.calls, [])
        self.assertTrue(ingest.called)

    def test_snapshot_totals_change_preserves_partial_and_starts_fresh_next_time(self):
        original = self.api.fetch

        def changed(method, endpoint, payload):
            raw = original(method, endpoint, payload)
            if payload and payload['filters']['puanTuru'] == 'SAY' and payload['page'] == 1:
                data = json.loads(raw)
                data['content'].append(dict(data['content'][0], kilavuzKodu=14))
                data.update(totalElements=4, numberOfElements=2)
                return json.dumps(data).encode()
            return raw

        self.api.fetch = changed
        with self.assertRaises(bot.SnapshotChanged):
            self.run_cycle()
        state = bot.read_json(self.root / 'state.json')
        self.assertIsNone(state['active_snapshot'])
        manifest = next((self.root / 'snapshots').glob('*/manifest.json'))
        self.assertEqual(bot.read_json(manifest)['phase'], 'superseded')

    def test_process_lock_is_exclusive_and_released(self):
        with bot.process_lock(self.root):
            with self.assertRaises(RuntimeError):
                with bot.process_lock(self.root):
                    self.fail('Second lock acquired')
        with bot.process_lock(self.root):
            pass

    def test_numeric_validation_never_truncates_ids_or_quotas(self):
        for value in (True, 1.5, float('nan'), float(2**60), 2**63, [], {}):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                loader.parse_int({'id': value}, 'id')
        self.assertEqual(loader.parse_int({'id': '999'}, 'id'), 999)
        fields = [{'api_field': 'minPuan', 'sql_type': 'DOUBLE PRECISION'}]
        for value in (True, 'NaN', float('inf')):
            with self.assertRaises(ValueError):
                loader.field_values({'minPuan': value}, fields, lambda x: x)

    def test_retry_after_is_respected_without_immediate_retry(self):
        api = bot.API(self.args)
        self.addCleanup(api.session.close)
        response = SimpleNamespace(status_code=429, headers={'Retry-After': '3600'})
        with patch.object(api.session, 'request', return_value=response) as request, patch.object(bot.time, 'sleep'):
            with self.assertRaises(bot.Paused) as caught:
                api.fetch('GET', '/test', None)
        self.assertEqual(request.call_count, 1)
        self.assertGreaterEqual(caught.exception.delay, 3600)

    def test_http_block_does_not_retry(self):
        api = bot.API(self.args)
        self.addCleanup(api.session.close)
        response = SimpleNamespace(status_code=403, headers={})
        with patch.object(api.session, 'request', return_value=response) as request, patch.object(bot.time, 'sleep'):
            with self.assertRaises(bot.AccessBlocked):
                api.fetch('GET', '/test', None)
        self.assertEqual(request.call_count, 1)

    def test_transient_network_error_retries_and_then_returns_original_bytes(self):
        api = bot.API(self.args)
        self.addCleanup(api.session.close)
        raw = b'[ {"test": 1} ]'
        response = SimpleNamespace(status_code=200, headers={'Content-Type': 'application/json'}, content=raw)
        with patch.object(api.session, 'request', side_effect=[requests.Timeout(), response]) as request, patch.object(bot.time, 'sleep'):
            self.assertEqual(api.fetch('GET', '/test', None), raw)
        self.assertEqual(request.call_count, 2)

    def test_wrong_page_or_nonfinite_json_is_rejected(self):
        payload = {'filters': {'puanTuru': 'SAY'}, 'page': 0, 'size': 2}
        data = json.loads(self.api.fetch('POST', '/api/netler/search', payload))
        data['number'] = 1
        with self.assertRaises(ValueError):
            bot.validate('net_results', data, payload)
        with self.assertRaises(ValueError):
            bot.decode(b'{"obp":NaN}')
        with self.assertRaises(ValueError):
            bot.decode(b'{"obp":1e400}')

    def test_malformed_conditions_are_rejected_before_canonical_writes(self):
        fields=[{'api_field':'kosulList','sql_type':'JSONB'}]
        for value in ({'21':'text'}, [1], [{'21':{'unexpected':'object'}}], [{'':'empty code'}]):
            with self.subTest(value=value),self.assertRaises(ValueError):
                loader.field_values({'kosulList':value},fields,lambda x:x)


@unittest.skipUnless(os.environ.get('YOKATLAS_TEST_DSN'), 'Set YOKATLAS_TEST_DSN to an isolated test database')
class PostgreSQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from psycopg import sql
        cls.admin = psycopg.connect(os.environ['YOKATLAS_TEST_DSN'], autocommit=True)
        if not cls.admin.info.dbname.startswith('test_yokatlas_'):
            cls.admin.close()
            raise ValueError('Refusing to modify a database without the test_yokatlas_ prefix')
        cls.password = 'isolated-test-password'
        for role in ['atlas_owner', 'atlas_api', 'atlas_analytics']:
            cls.admin.execute(sql.SQL('CREATE ROLE {}').format(sql.Identifier(role)))
        cls.admin.execute(sql.SQL('CREATE ROLE atlas_ingest LOGIN PASSWORD {}').format(sql.Literal(cls.password)))
        for migration in ['001_data_contract_v1.sql', '002_api_views.sql', '003_privileges.sql', '004_archive_idempotency.sql', '005_bot_condition_sync.sql', '006_tuik_population_by_province.sql']:
            cls.admin.execute((ROOT / 'database/migrations' / migration).read_text())

    @classmethod
    def tearDownClass(cls):
        cls.admin.close()

    def setUp(self):
        from psycopg import sql
        names = self.admin.execute("SELECT schemaname,tablename FROM pg_tables WHERE schemaname IN ('raw','staging','core','quality')").fetchall()
        self.admin.execute(sql.SQL('TRUNCATE {} RESTART IDENTITY CASCADE').format(
            sql.SQL(',').join(sql.Identifier(*name) for name in names)))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.args = options()
        self.api = FakeAPI(self.args)
        self.env = self.root / 'test.env'
        self.env.write_text('\n'.join([f'PGHOST={self.admin.info.host}', f'PGPORT={self.admin.info.port}',
            f'PGDATABASE={self.admin.info.dbname}', 'PGUSER=atlas_ingest', f'PGPASSWORD={self.password}']))

    def snapshot(self):
        with patch.object(bot, 'API', return_value=self.api):
            manifest = bot.cycle(self.root, self.args)
        return self.root / 'snapshots' / manifest['snapshot_id']

    def scalar(self, query):
        return self.admin.execute(query).fetchone()[0]

    def test_real_import_preserves_nested_fields_years_and_replays_without_duplicates(self):
        snapshot = self.snapshot()
        result = loader.import_archive(snapshot, self.env)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(self.scalar('SELECT count(*) FROM core.program_versions'), 3)
        self.assertEqual(self.scalar('SELECT count(*) FROM core.net_results'), 3)
        self.assertEqual(self.scalar('SELECT array_agg(DISTINCT yil ORDER BY yil) FROM core.net_results'), [2023, 2024, 2025])
        self.assertEqual(self.scalar('SELECT count(*) FROM core.net_results WHERE program_version_id IS NOT NULL'), 0)
        self.assertEqual(self.scalar('SELECT count(*) FROM core.program_conditions'), 3)
        source = self.admin.execute("SELECT remaining_fields FROM core.program_versions WHERE kilavuz_kodu=11").fetchone()[0]
        self.assertEqual(source['newField'], {'nested': [1, None, 'ı']})
        body = snapshot / 'complete_data/programs/SAY/page_000000.json'
        saved = self.admin.execute("SELECT source_hash_sha256 FROM raw.api_responses WHERE endpoint='/api/tercih-kilavuz/search' AND score_type='SAY' AND page_number=0").fetchone()[0]
        self.assertEqual(saved, hashlib.sha256(body.read_bytes()).hexdigest())
        count = self.scalar('SELECT count(*) FROM raw.api_responses')
        again = loader.import_archive(snapshot, self.env)
        self.assertEqual(again['unchanged_files_skipped'], count)
        self.assertEqual(self.scalar('SELECT count(*) FROM raw.api_responses'), count)
        self.assertEqual(self.scalar('SELECT count(*) FROM staging.programs'), 3)
        self.assertEqual(self.scalar("SELECT jsonb_array_length(details->'observed_response_ids') FROM raw.ingestion_runs ORDER BY ingestion_run_id DESC LIMIT 1"), count)

    def test_page_transaction_rolls_back_and_resume_keeps_previous_tables(self):
        import psycopg
        snapshot = self.snapshot()
        self.admin.execute("""CREATE FUNCTION core.bot_test_failure() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.kilavuz_kodu=12 THEN RAISE EXCEPTION 'simulated DB failure'; END IF; RETURN NEW; END $$;
            CREATE TRIGGER bot_test_failure BEFORE INSERT ON core.program_versions
            FOR EACH ROW EXECUTE FUNCTION core.bot_test_failure();""")
        try:
            progress=[]
            with self.assertRaises(psycopg.errors.RaiseException):
                loader.import_archive(snapshot, self.env,on_progress=lambda entity,score,page,*_:progress.append((entity,score,page)))
            self.assertEqual(progress[-1],('programs','SAY',0))
            self.assertEqual(self.scalar('SELECT count(*) FROM core.universities'), 1)
            self.assertEqual(self.scalar('SELECT count(*) FROM staging.programs'), 0)
            self.assertEqual(self.scalar('SELECT count(*) FROM core.program_versions'), 0)
            self.assertEqual(self.scalar("SELECT count(*) FROM raw.api_responses WHERE endpoint='/api/tercih-kilavuz/search' AND score_type='SAY'"), 0)
            committed=self.scalar('SELECT count(*) FROM raw.api_responses')
        finally:
            self.admin.execute('DROP TRIGGER bot_test_failure ON core.program_versions; DROP FUNCTION core.bot_test_failure()')
        result = loader.import_archive(snapshot, self.env)
        self.assertEqual(result['unchanged_files_skipped'], committed)
        self.assertEqual(self.scalar('SELECT count(*) FROM core.program_versions'), 3)

    def test_invalid_typed_value_is_preserved_and_quarantined(self):
        self.api.programs[0]['kontenjan'] = 1.5
        snapshot = self.snapshot()
        result = loader.import_archive(snapshot, self.env)
        self.assertEqual(result['status'], 'completed_with_issues')
        self.assertEqual(result['quarantined_records'], 1)
        self.assertEqual(self.scalar('SELECT count(*) FROM core.program_versions'), 2)
        self.assertEqual(self.scalar("SELECT count(*) FROM raw.source_records WHERE source_entity='programs'"), 3)
        self.assertEqual(self.scalar("SELECT candidate_payloads->0->>'kontenjan' FROM quality.quarantined_records"), '1.5')

    def test_distinct_score_types_survive_and_conflicting_net_is_quarantined(self):
        duplicate = dict(self.api.nets[0])
        conflict = dict(duplicate, obp=499)
        variant = dict(duplicate, puanTuru='EA')
        self.api.nets.extend([duplicate, conflict, variant])
        result = loader.import_archive(self.snapshot(), self.env)
        self.assertEqual(result['identical_net_duplicate'], 1)
        self.assertEqual(result['conflicting_net_duplicate'], 1)
        self.assertEqual(result['status'], 'completed_with_issues')
        self.assertEqual(self.scalar("SELECT count(*) FROM raw.source_records WHERE source_entity='net_results'"), 6)
        self.assertEqual(self.scalar('SELECT count(*) FROM core.net_results'), 4)

    def test_database_lock_prevents_a_second_importer(self):
        snapshot = self.snapshot()
        self.admin.execute("SELECT pg_advisory_lock(hashtext('yokatlas_archive_loader'))")
        try:
            with self.assertRaisesRegex(RuntimeError, 'Another'):
                loader.import_archive(snapshot, self.env)
            self.assertEqual(self.scalar('SELECT count(*) FROM raw.ingestion_runs'), 0)
        finally:
            self.admin.execute("SELECT pg_advisory_unlock(hashtext('yokatlas_archive_loader'))")

    def test_missing_archived_page_cannot_be_reported_complete(self):
        snapshot=self.snapshot()
        (snapshot/'complete_data/net_results/SAY/page_000001.json').unlink()
        with self.assertRaisesRegex(ValueError,'missing archived pages'):
            loader.import_archive(snapshot,self.env)
        self.assertEqual(self.scalar('SELECT count(*) FROM raw.ingestion_runs'),0)

    def test_new_snapshot_reverting_old_values_updates_core_without_duplicate_raw(self):
        first=self.snapshot()
        loader.import_archive(first,self.env)
        self.api.programs[0]['ucret']=999
        self.api.programs[0]['kosulList']=[{'22':'Yeni koşul'}]
        second=self.snapshot()
        loader.import_archive(second,self.env)
        self.assertEqual(self.scalar("SELECT remaining_fields->>'ucret' FROM core.program_versions WHERE kilavuz_kodu=11"),'999')
        self.assertEqual(self.scalar("SELECT array_agg(condition_code) FROM core.program_conditions pc JOIN core.program_versions p USING (program_version_id) WHERE p.kilavuz_kodu=11"),['22'])
        count=self.scalar('SELECT count(*) FROM raw.api_responses')
        self.api.programs[0]['ucret']=123456
        self.api.programs[0]['kosulList']=[{'21':'Koşul açıklaması'}]
        third=self.snapshot()
        result=loader.import_archive(third,self.env)
        self.assertGreater(result['files_reapplied'],0)
        self.assertEqual(self.scalar('SELECT count(*) FROM raw.api_responses'),count)
        self.assertEqual(self.scalar("SELECT remaining_fields->>'ucret' FROM core.program_versions WHERE kilavuz_kodu=11"),'123456')
        self.assertEqual(self.scalar("SELECT array_agg(condition_code) FROM core.program_conditions pc JOIN core.program_versions p USING (program_version_id) WHERE p.kilavuz_kodu=11"),['21'])
        replay=loader.import_archive(third,self.env)
        self.assertEqual(replay.get('files_reapplied',0),0)
        self.assertGreater(replay['unchanged_files_skipped'],0)

    def test_condition_descriptions_keep_years_and_do_not_replace_newer_with_older(self):
        loader.import_archive(self.snapshot(),self.env)
        for row in self.api.programs:
            row['yil']=2027
            row['kosulList']=[{'21':'2027 koşulu'}]
        loader.import_archive(self.snapshot(),self.env)
        for row in self.api.programs:
            row['yil']=2025
            row['kosulList']=[{'21':'2025 koşulu'}]
        loader.import_archive(self.snapshot(),self.env)
        description,details=self.admin.execute("SELECT description,raw_details FROM core.conditions WHERE condition_code='21'").fetchone()
        self.assertEqual(description,'2027 koşulu')
        self.assertEqual(set(details['descriptions_by_year']),{'2025','2026','2027'})

    def test_bot_can_replace_condition_links_but_cannot_delete_raw_or_programs(self):
        self.assertTrue(self.scalar("SELECT has_table_privilege('atlas_ingest','core.program_conditions','DELETE')"))
        self.assertFalse(self.scalar("SELECT has_table_privilege('atlas_ingest','raw.api_responses','DELETE')"))
        self.assertFalse(self.scalar("SELECT has_table_privilege('atlas_ingest','core.program_versions','DELETE')"))

    def test_default_cycle_collects_and_imports_into_real_postgresql(self):
        self.args.archive_only=False
        self.args.env_file=self.env
        with patch.object(bot,'API',return_value=self.api):
            result=bot.cycle(self.root,self.args)
        self.assertEqual(result['phase'],'completed')
        state=bot.read_json(self.root/'state.json')
        self.assertIsNone(state['active_snapshot'])
        self.assertEqual(self.scalar('SELECT count(*) FROM core.program_versions'),3)
        self.assertEqual(self.scalar('SELECT status FROM quality.data_quality_checks'),'passed')

    def test_same_year_net_links_and_empty_numeric_values_are_handled(self):
        for row in self.api.programs:
            row['yil']=2025
            row['minPuan']=''
        for row in self.api.nets:
            row['obp']=''
        result=loader.import_archive(self.snapshot(),self.env)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(self.scalar('SELECT count(*) FROM core.net_results WHERE program_version_id IS NOT NULL'),1)
        self.assertEqual(self.scalar('SELECT count(*) FROM core.program_versions WHERE min_puan IS NULL'),3)
        self.assertEqual(self.scalar('SELECT count(*) FROM core.net_results WHERE obp IS NULL'),3)

    def test_missing_optional_lookup_is_visible_as_a_quality_warning(self):
        self.api.programs[0]['ilKodu']=99999
        result=loader.import_archive(self.snapshot(),self.env)
        self.assertEqual(result['status'],'completed_with_issues')
        self.assertEqual(result['unresolved_city'],1)
        self.assertEqual(self.scalar('SELECT status FROM quality.data_quality_checks'),'warning')


if __name__ == '__main__':
    unittest.main()
