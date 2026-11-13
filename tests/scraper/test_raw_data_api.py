"""No network, no live DB, no production inserts. Run: python -m unittest discover -s tests/scraper -p 'test_raw_data_api.py' -v"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
from urllib.parse import parse_qs, urlsplit
import unittest
from unittest.mock import patch

from scraper.data_api.client import RawWriteClient, RejectedWrite, UncertainWrite, decode_json, encode_json
from scraper.data_api.ledger import Ledger, ReconciliationRequired
from scraper.data_api.publish import publish_capture, publish_report, publish_yokatlas, prepare_yokatlas
from scraper.data_api.collect import collect_json, crawl_openalex


class MemoryWriter:
    """Model INSERT with generated DB keys; works without a running server."""
    def __init__(self):
        self.calls = []
        self.error = None

    def insert(self, table, data):
        self.calls.append((table, data))
        if self.error:
            raise self.error
        column = {'ingestion_runs': 'ingestion_run_id', 'api_responses': 'api_response_id',
                  'source_records': 'source_record_id', 'report_documents': 'document_id',
                  'openalex_object_snapshots': 'snapshot_id'}[table]
        return {column: len(self.calls) + 100}


class FakeResponse:
    def __init__(self, status=201, payload=None):
        self.status_code = status
        self.payload = payload

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class ClientTests(unittest.TestCase):
    def test_exact_decimal_preserved(self):
        value = decode_json(b'{"value":0.123456789123456789123456789}')
        self.assertIsInstance(value['value'], Decimal)
        self.assertIn('0.123456789123456789123456789', encode_json(value))
        self.assertEqual(encode_json({'a': 12, 'b': None}), '{"a":12,"b":null}')

    def test_single_row_and_auth_headers(self):
        sess = FakeSession(FakeResponse(201, {'table': 'ingestion_runs', 'key': {'ingestion_run_id': 4}}))
        client = RawWriteClient('https://api.example.org', 'private-key', session=sess)
        self.assertEqual(client.insert('ingestion_runs', {'source_system': 'yokatlas'}), {'ingestion_run_id': 4})
        self.assertEqual(sess.calls[0][0], 'https://api.example.org/api/db/write')
        self.assertEqual(sess.calls[0][1]['headers']['X-API-Key'], 'private-key')
        self.assertNotIn('Bearer', sess.calls[0][1]['headers']['X-API-Key'])
        self.assertNotIn('raw.', sess.calls[0][1]['data'].decode())

    def test_bad_reply_is_uncertain(self):
        sess = FakeSession(FakeResponse(201, {'table': 'ingestion_runs', 'key': []}))
        client = RawWriteClient('https://api.example.org', 'private-key', session=sess)
        with self.assertRaises(UncertainWrite):
            client.insert('ingestion_runs', {})

    def test_duplicate_409_is_not_success(self):
        sess = FakeSession(FakeResponse(409))
        client = RawWriteClient('https://api.example.org', 'private-key', session=sess)
        with self.assertRaises(RejectedWrite) as caught:
            client.insert('ingestion_runs', {})
        self.assertEqual(caught.exception.status, 409)

    def test_tls_enforced(self):
        with self.assertRaises(ValueError):
            RawWriteClient('http://external.example', 'some-key')

    def test_private_docker_api_http_allowed(self):
        sess = FakeSession(FakeResponse(201, {'table': 'ingestion_runs', 'key': {'ingestion_run_id': 4}}))
        client = RawWriteClient('http://yokatlas-data-api:8000', 'private-key', session=sess)
        self.assertEqual(client.insert('ingestion_runs', {'source_system': 'yokatlas'}), {'ingestion_run_id': 4})
        self.assertEqual(sess.calls[0][0], 'http://yokatlas-data-api:8000/api/db/write')

    def test_other_internal_http_rejected(self):
        for url in ('http://postgres:5432', 'http://yokatlas-data-api:8001',
                    'http://yokatlas-data-api:8000/unexpected', 'http://evil.example'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                RawWriteClient(url, 'private-key')


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'progress.sqlite3'

    def test_persisted_replay_skips_insert(self):
        writer = MemoryWriter()
        ledger = Ledger(self.path)
        self.assertEqual(ledger.execute('x/run', 'ingestion_runs', {}, writer), {'ingestion_run_id': 101})
        ledger.close()
        ledger = Ledger(self.path)
        self.assertEqual(ledger.execute('x/run', 'ingestion_runs', {}, writer), {'ingestion_run_id': 101})
        self.assertEqual(len(writer.calls), 1)
        ledger.close()

    def test_timeout_is_parked_without_retry(self):
        writer = MemoryWriter()
        writer.error = UncertainWrite('timeout')
        ledger = Ledger(self.path)
        with self.assertRaises(UncertainWrite):
            ledger.execute('x/run', 'ingestion_runs', {}, writer)
        self.assertEqual(ledger.get('x/run')['state'], 'uncertain')
        writer.error = None
        with self.assertRaises(ReconciliationRequired):
            ledger.execute('x/run', 'ingestion_runs', {}, writer)
        self.assertEqual(len(writer.calls), 1)
        ledger.close()

    def test_409_remains_rejected_until_operator(self):
        writer = MemoryWriter()
        writer.error = RejectedWrite(409)
        ledger = Ledger(self.path)
        with self.assertRaises(RejectedWrite):
            ledger.execute('x/run', 'ingestion_runs', {}, writer)
        self.assertEqual(ledger.get('x/run')['state'], 'rejected')
        with self.assertRaises(ReconciliationRequired):
            ledger.execute('x/run', 'ingestion_runs', {}, writer)
        ledger.reconcile('x/run', committed_key={'ingestion_run_id': 444})
        self.assertEqual(ledger.execute('x/run', 'ingestion_runs', {}, writer), {'ingestion_run_id': 444})
        ledger.close()

    def test_different_payload_same_operation_fails(self):
        writer = MemoryWriter()
        ledger = Ledger(self.path)
        ledger.execute('x/run', 'ingestion_runs', {'source_system':'yokatlas'}, writer)
        with self.assertRaises(ReconciliationRequired):
            ledger.execute('x/run', 'ingestion_runs', {'source_system':'urap'}, writer)
        ledger.close()


class PublishingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = Ledger(self.root / 'ledger.sqlite3')
        self.addCleanup(self.ledger.close)
        self.writer = MemoryWriter()

    def capture(self, source, payload, *, url):
        folder = self.root / 'capture'
        folder.mkdir(exist_ok=True)
        raw = encode_json(payload).encode('utf-8')
        (folder / 'body.json').write_bytes(raw)
        (folder / 'receipt.json').write_text(encode_json({
            'source_system': source, 'url': url, 'method': 'GET',
            'captured_at': '2026-10-25T10:00:00Z', 'http_status': 200,
            'sha256': hashlib.sha256(raw).hexdigest(),
        }), encoding='utf-8')
        return folder

    def test_openalex_snapshots_parent_first_and_replay(self):
        folder = self.capture('openalex', {'results': [
            {'id': 'https://openalex.org/W100', 'title': 'A'},
            {'id': 'https://openalex.org/W101', 'title': 'B'},
        ]}, url='https://api.openalex.org/works?per_page=2')
        r = publish_capture(folder, self.ledger, self.writer, openalex_entity_type='works')
        self.assertEqual(r['child_records'], 2)
        self.assertEqual([x[0] for x in self.writer.calls], [
            'ingestion_runs', 'api_responses', 'openalex_object_snapshots', 'openalex_object_snapshots'])
        self.assertEqual(self.writer.calls[0][1]['scraper_version'], 'raw-api-bots-v1')
        self.assertEqual(self.writer.calls[-1][1]['source_array_index'], 1)
        publish_capture(folder, self.ledger, self.writer, openalex_entity_type='works')
        self.assertEqual(len(self.writer.calls), 4)

        with self.ledger.transaction() as db:
            db.execute("UPDATE operations SET payload_sha256=? WHERE table_name='ingestion_runs'",
                       ('f67f28238178fc03aab4c89968272c1c5d758bbe51b4ba561028af5b97240fab',))
        resumed = publish_capture(folder, self.ledger, self.writer, openalex_entity_type='works')
        self.assertEqual(resumed['run_id'], r['run_id'])
        self.assertEqual(len(self.writer.calls), 4)

    def test_openalex_invalid_snapshot_rejected_before_write(self):
        folder = self.capture('openalex', {'results': [
            {'id': 'https://openalex.org/W123'}, {'id': 'https://other.example/invalid'}
        ]}, url='https://api.openalex.org/works')
        with self.assertRaises(ValueError):
            publish_capture(folder, self.ledger, self.writer, openalex_entity_type='works')
        self.assertEqual(self.writer.calls, [])

    def test_tuik_legacy_keeps_full_source(self):
        record = {'DATAFLOW': 'TR:DF_ADNKS_T16(1.0)', 'TIME_PERIOD': '2025',
                  'REF_AREA': '34', 'OBS_VALUE': '120', 'DIMENSION_X': 'M'}
        folder = self.capture('tuik', [record], url='https://nsiws.tuik.gov.tr/rest/data/whatever')
        res = publish_capture(folder, self.ledger, self.writer, source_entity='tuik_df_adnks_t16')
        self.assertEqual(res['child_records'], 1)
        self.assertEqual(self.writer.calls[-1][1]['record'], record)

    def test_forged_nonofficial_capture_rejected_before_write(self):
        folder = self.capture('openalex', {'id': 'https://openalex.org/W12'},
                              url='https://example.org/not-openalex')
        with self.assertRaises(ValueError):
            publish_capture(folder, self.ledger, self.writer)
        self.assertEqual(self.writer.calls, [])

    def test_report_document_uses_existing_real_parser_result(self):
        sha = 'a' * 64
        archive = self.root / 'report'
        archive.mkdir()
        (archive / 'manifest.json').write_text(json.dumps({'report_id':'sege-il-2025'}))
        meta = {'source_sha256':sha, 'parser_version':'reports-pdf-1',
                'source_url':'https://www.kalkinmakutuphanesi.gov.tr/real.pdf',
                'captured_at':'2026-10-25T10:00:00Z', 'extracted_sha256':'b'*64}
        reports = types.ModuleType('scraper.report_parsers')
        reports.REPORTS = {'sege-il-2025': {'bot':'sege', 'edition':'2025'}}
        report_bot = types.ModuleType('scraper.report_bot')
        report_bot.read_archive = lambda folder, report_id: (meta, {'records':[{'sira':1}], 'counts':{}})
        with patch.dict(sys.modules, {'scraper.report_parsers':reports, 'scraper.report_bot':report_bot}):
            result = publish_report(archive, self.ledger, self.writer)
            self.assertEqual(result['source'], 'sege')
            self.assertEqual([c[0] for c in self.writer.calls], ['ingestion_runs','report_documents'])
            self.assertEqual(self.writer.calls[1][1]['payload']['records'][0]['sira'], 1)
            publish_report(archive, self.ledger, self.writer)
            self.assertEqual(len(self.writer.calls), 2)

    def test_tuik_wrong_entity_does_not_write(self):
        folder = self.capture('tuik', [{'DATAFLOW': 'something'}],
                              url='https://nsiws.tuik.gov.tr/rest/data/example')
        with self.assertRaises(ValueError):
            publish_capture(folder, self.ledger, self.writer, source_entity='tuik_df_adnks_t16')
        self.assertEqual(self.writer.calls, [])

    def test_corrupt_capture_checksum_stops_before_write(self):
        folder = self.capture('openalex', {'id': 'https://openalex.org/W1'},
                              url='https://api.openalex.org/works/W1')
        (folder / 'body.json').write_text('{}')
        with self.assertRaises(ValueError):
            publish_capture(folder, self.ledger, self.writer)
        self.assertEqual(self.writer.calls, [])

    def test_yok_archive_parent_child_and_replay(self):
        ENTITIES = ('universities','program_groups','cities','programs','net_results')
        PATHS = {'universities': ('GET','/api/tercih-kilavuz/universiteler'),
                 'program_groups': ('GET','/api/tercih-kilavuz/universite-programlar'),
                 'cities': ('GET','/api/tercih-kilavuz/universite-iller'),
                 'programs': ('POST','/api/tercih-kilavuz/search'),
                 'net_results': ('POST','/api/netler/search')}
        source = types.ModuleType('scripts.database.load_archive')
        source.ENTITIES, source.PATHS = ENTITIES, PATHS
        base = self.root / 'snapshot'
        (base / 'complete_data').mkdir(parents=True)
        manifest = {'phase': 'archived', 'snapshot_id': 'test-1', 'partitions': {}}
        archive_entries = [
            ('universities', None, None, [{'universiteId': 42}]),
            ('program_groups', None, None, [{'programGrubuId': 1}]),
            ('cities', None, None, [{'ilKodu': 34}]),
            ('programs', 'SAY', 0, {'content': [{'kilavuzKodu': 12}]}),
            ('net_results', 'SAY', 0, {'content': [{'kilavuzKodu': 12}]}),
        ]
        for entity, score, page, obj in archive_entries:
            path = base / 'complete_data' / entity / (score or 'all') / ('page_000000.json' if score else 'all.json')
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = encode_json(obj).encode('utf-8')
            path.write_bytes(raw)
            receipt = {'sha256': hashlib.sha256(raw).hexdigest(), 'method': PATHS[entity][0],
                       'endpoint': PATHS[entity][1], 'http_status': 200, 'captured_at': '2026-10-25T10:00:00Z',
                       'records': len(obj if isinstance(obj,list) else obj['content']),
                       'request': {'page':page,'filters':{'puanTuru':score}} if score else None}
            path.with_suffix('.meta.json').write_text(encode_json(receipt))
            key = entity if score is None else entity + '/' + score
            manifest['partitions'][key] = {'rows': 1, 'pages': 1}
        (base / 'manifest.json').write_text(encode_json(manifest))
        def iterfiles(root):
            for entity, score, page, _ in archive_entries:
                path = root / 'complete_data' / entity / (score or 'all') / ('page_000000.json' if score else 'all.json')
                yield entity, score, page, path
        source.source_files = iterfiles
        # The actual checked-out repository supplies the original loader.
        with patch.dict(sys.modules, {'scripts.database.load_archive': source}):
            _, pages = prepare_yokatlas(base)
            self.assertEqual(len(pages), 5)
            res = publish_yokatlas(base, self.ledger, self.writer)
            self.assertEqual(res['responses'], 5)
            self.assertEqual(res['records'], 5)
            self.assertEqual(len(self.writer.calls), 11)
            publish_yokatlas(base, self.ledger, self.writer)
            self.assertEqual(len(self.writer.calls), 11)


class LiveOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_yok_live_uses_archive_only_and_never_calls_direct_db(self):
        from scraper.data_api.cli import run_yokatlas_collector
        snapshot_id = '20261025T100000Z-abc123'
        (self.root / 'state.json').write_text(json.dumps({'last_snapshot': snapshot_id}))
        with patch('scraper.data_api.cli.subprocess.run', return_value=types.SimpleNamespace(returncode=0)) as runner:
            archive = run_yokatlas_collector(self.root, max_requests=10, page_size=20, delay=2)
        self.assertEqual(archive, self.root / 'snapshots' / snapshot_id)
        command = runner.call_args.args[0]
        self.assertIn('--archive-only', command)
        self.assertEqual(command[command.index('--max-requests')+1], '10')
        self.assertNotIn('--env-file', command)

    def test_yok_incomplete_collection_does_not_publish(self):
        from scraper.data_api.cli import run_yokatlas_collector
        with patch('scraper.data_api.cli.subprocess.run', return_value=types.SimpleNamespace(returncode=2)):
            with self.assertRaisesRegex(ValueError, 'not finished'):
                run_yokatlas_collector(self.root, max_requests=1, page_size=20, delay=2)

    def test_bounded_openalex_cursor_fetch_with_bearer_header(self):
        responses = [
            {'results': [{'id': 'https://openalex.org/I42'}], 'meta': {'next_cursor': 'abc=='}},
            {'results': [{'id': 'https://openalex.org/I55'}], 'meta': {'next_cursor': None}},
        ]
        calls, published = [], []
        def mocked_collect(source, url, root, *, auth_token=None):
            idx = len(calls)
            calls.append((source, url, auth_token))
            folder = self.root / str(idx)
            folder.mkdir()
            (folder / 'body.json').write_text(json.dumps(responses[idx]))
            return folder
        with patch('scraper.data_api.collect.collect_json', side_effect=mocked_collect):
            result = crawl_openalex('institutions', 'country_code:TR', self.root,
                                    max_pages=3, api_key='test-token', delay=0,
                                    publish=lambda folder, entity: published.append((folder, entity)))
        self.assertEqual(len(result), 2)
        self.assertEqual(len(published), 2)
        self.assertEqual([urlsplit(call[1]).hostname for call in calls], ['api.openalex.org']*2)
        self.assertEqual(parse_qs(urlsplit(calls[1][1]).query)['cursor'], ['abc=='])
        self.assertTrue(all(c[2]=='test-token' for c in calls))
        self.assertNotIn('test-token', calls[1][1])

    def test_cursor_after_first_page_requires_api_key(self):
        with self.assertRaisesRegex(ValueError, 'OPENALEX_API_KEY'):
            crawl_openalex('institutions', 'country_code:TR', self.root, max_pages=2)


if __name__ == '__main__':
    unittest.main()
