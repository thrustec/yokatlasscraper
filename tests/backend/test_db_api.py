"""Data API boundary checks that do not need PostgreSQL."""
import json
import unittest
from decimal import Decimal
from unittest.mock import patch

import psycopg
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import db
from backend.main import app


class DataAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        config = patch.dict(db.CONFIG, {"DB_WRITE_API_KEY": "write-test-key",
            "ATLAS_RAW_WRITER_PASSWORD": "writer", "ATLAS_ANALYTICS_READER_PASSWORD": "reader"})
        config.start()
        self.addCleanup(config.stop)
        self.headers = {"X-API-Key": "write-test-key", "Content-Type": "application/json"}

    def test_write_requires_key_and_exact_request_shape(self):
        with patch.object(db, "insert_row") as insert:
            for headers in ({}, {"X-API-Key": "wrong"}):
                self.assertEqual(self.client.post('/api/db/write', headers=headers,
                    json={"table": "ingestion_runs", "data": {}}).status_code, 401)
            for body in ({"table": "raw.ingestion_runs", "data": {}},
                         {"table": "ingestion_runs", "data": []},
                         {"table": "ingestion_runs", "data": {}, "schema": "core"},
                         {"table": "ingestion_runs"}):
                self.assertEqual(self.client.post('/api/db/write', json=body, headers=self.headers).status_code, 422)
            insert.assert_not_called()

    def test_write_returns_key_and_keeps_decimal_tokens_exact(self):
        with patch.object(db, "insert_row", return_value={"id": 7}) as insert:
            response = self.client.post('/api/db/write', headers=self.headers,
                content='{"table":"example","data":{"score":1234567890.123456789,"payload":{"n":1.000000000000001}}}')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"table": "example", "key": {"id": 7}})
        values = insert.call_args.args[1]
        self.assertEqual(values['score'], Decimal('1234567890.123456789'))
        self.assertEqual(values['payload']['n'], Decimal('1.000000000000001'))

    def test_nonfinite_json_is_rejected(self):
        for token in ('NaN', 'Infinity', '-Infinity', '1e999999999999999999999999999999'):
            with self.subTest(token=token), patch.object(db, 'insert_row') as insert:
                response = self.client.post('/api/db/write', headers=self.headers,
                    content='{"table":"example","data":{"score":' + token + '}}')
                self.assertEqual(response.status_code, 422)
                insert.assert_not_called()

    def test_invalid_envelope_does_not_echo_payload_or_return_500(self):
        for content in ('{"table":NaN,"data":{"secret":"do-not-echo"}}',
                        '{"data":{"secret":"do-not-echo"}}',
                        '{"table":"example","data":{},"unexpected":NaN}'):
            with self.subTest(content=content), patch.object(db, 'insert_row') as insert:
                response = self.client.post('/api/db/write', headers=self.headers, content=content)
                self.assertEqual(response.status_code, 422)
                self.assertNotIn('do-not-echo', response.text)
                insert.assert_not_called()

    def test_read_is_public_and_passes_typed_filters_and_multiple_sort_columns(self):
        with patch.object(db, 'read_rows', return_value=[{'score': Decimal('4.419')}]) as read:
            response = self.client.get('/api/db/read', params=[('table', 'scores'),
                ('order_by', 'year'), ('order_by', 'id'), ('filters', '{"year":2026,"score":4.419}'),
                ('search_column', 'name'), ('q', "' OR 1=1 --"), ('direction', 'desc')])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'table': 'scores', 'data': [{'score': 4.419}], 'limit': 50, 'offset': 0})
        self.assertEqual(read.call_args.args, ('scores', {'year': 2026, 'score': Decimal('4.419')},
            ['year', 'id'], 'desc', 'name', "' OR 1=1 --", 50, 0))

    def test_invalid_read_parameters_stop_before_database(self):
        for extra in ({'order_by': ''}, {'limit': 101}, {'offset': -1},
                      {'direction': 'asc; DROP TABLE raw.api_responses'},
                      {'order_by': 'id;select'}, {'table': 'raw.api_responses'},
                      {'filters': '[]'}, {'filters': '{bad'}, {'filters': '{"x":NaN}'},
                      {'search_column': 'name'}, {'q': 'test'}):
            with self.subTest(extra=extra), patch.object(db, 'read_rows') as read:
                response = self.client.get('/api/db/read', params={'table': 'scores', 'order_by': 'id', **extra})
                self.assertEqual(response.status_code, 422, response.text)
                read.assert_not_called()
        self.assertEqual(self.client.get('/api/db/read', params={'table': 'scores'}).status_code, 422)

    def test_database_failure_does_not_expose_details(self):
        with patch.object(db.psycopg, 'connect', side_effect=psycopg.OperationalError('secret detail')):
            response = self.client.get('/status')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('secret detail', response.text)
        with patch.dict(db.CONFIG, {'DB_WRITE_API_KEY': ''}):
            self.assertEqual(self.client.post('/api/db/write', json={'table': 'x', 'data': {}}).status_code, 503)

    def test_old_data_routes_are_removed_and_bot_routes_stay_registered(self):
        for path in ('/api/veri-kapsami', '/api/universiteler', '/api/programlar',
                     '/api/net-sonuclari', '/api/sege', '/api/urap', '/api/rapor-yayinlari'):
            self.assertEqual(self.client.get(path).status_code, 404)
            self.assertEqual(self.client.post(path, json={}).status_code, 404)
        from backend.tuik_admin import router, bots
        paths = set(app.openapi()['paths'])
        self.assertTrue({route.path for route in router.routes if route.include_in_schema} <= paths)
        inventory = {row['bot_id']: row for row in bots()}
        self.assertEqual(inventory['sege']['command'], 'python -m scraper.panel_sege')
        self.assertFalse(inventory['urap']['manual_runs'])
        self.assertEqual(self.client.get('/admin/tuik/').status_code, 200)
        self.assertEqual(self.client.get('/admin/tuik/assets/admin.js').status_code, 200)

    def test_swagger_exposes_only_two_data_operations(self):
        schema = self.client.get('/openapi.json').json()
        self.assertEqual({path for path in schema['paths'] if path.startswith('/api/')},
            {'/api/db/write', '/api/db/read'})
        self.assertIn('security', schema['paths']['/api/db/write']['post'])
        self.assertNotIn('security', schema['paths']['/api/db/read']['get'])
        self.assertIn('requestBody', schema['paths']['/api/db/write']['post'])


class ValueTests(unittest.TestCase):
    def column(self, kind, **overrides):
        return {'name': 'value', 'type': kind, 'sql_type': kind, 'builtin': True,
                'required': True, 'modifier': -1, **overrides}

    def test_integer_ranges_and_no_coercion(self):
        for kind, bits in db.INTEGER_BITS.items():
            column = self.column(kind)
            for value in (-(2**(bits-1)), 2**(bits-1)-1):
                self.assertEqual(db.validate_value(column, value), value)
            for value in ('123', True, 1.0, Decimal('1'), -(2**(bits-1))-1, 2**(bits-1)):
                with self.subTest(kind=kind, value=value), self.assertRaises(HTTPException):
                    db.validate_value(column, value)

    def test_numeric_precision_scale_and_no_context_rounding(self):
        for sql_type, valid, invalid in (
            ('numeric(5,2)', '999.99', ('1000', '1.001')),
            ('numeric(2,-3)', '99000', ('100000', '99001')),
            ('numeric(3,5)', '.00999', ('.01', '.000001')),
            ('numeric(40,5)', '99999999999999999999999999999999999.99999', ('1e35',)),
        ):
            column = self.column('numeric', sql_type=sql_type)
            self.assertEqual(db.validate_value(column, Decimal(valid)), Decimal(valid))
            for value in invalid:
                with self.subTest(sql_type=sql_type, value=value), self.assertRaises(HTTPException):
                    db.validate_value(column, Decimal(value))
        for value in ('1.2', True, Decimal('NaN'), Decimal('Infinity')):
            with self.assertRaises(HTTPException):
                db.validate_value(self.column('numeric'), value)

    def test_text_boolean_null_and_unsupported_types(self):
        self.assertEqual(db.validate_value(self.column('varchar', modifier=7), 'İÜÖ'), 'İÜÖ')
        self.assertIsNone(db.validate_value(self.column('text', required=False), None))
        for column, value in ((self.column('varchar', modifier=7), 'long'),
                              (self.column('text'), '\x00'), (self.column('text'), '\ud800'),
                              (self.column('bool'), 1), (self.column('text'), None),
                              (self.column('uuid'), 'x'), (self.column('text', builtin=False), 'x')):
            with self.subTest(column=column, value=repr(value)), self.assertRaises(HTTPException):
                db.validate_value(column, value)

    def test_temporal_values_do_not_silently_round_or_drop_timezone(self):
        for kind, value in (('date', '2026-10-22'), ('timestamp', '2026-10-22T13:30:00'),
                            ('timestamptz', '2026-10-22T13:30:00+03:00'), ('time', '13:30:00'),
                            ('timetz', '13:30:00Z')):
            self.assertIsNotNone(db.validate_value(self.column(kind), value))
        for column, value in ((self.column('date'), '2026-02-30'),
                              (self.column('timestamp'), '2026-10-22T00:00:00Z'),
                              (self.column('timestamptz'), '2026-10-22T00:00:00'),
                              (self.column('timestamp', modifier=3), '2026-10-22T00:00:00.0001'),
                              (self.column('timestamp'), '2026-10-22T00:00:00.0000001')):
            with self.subTest(value=value), self.assertRaises(HTTPException):
                db.validate_value(column, value)

    def test_json_numbers_stay_numbers_and_keep_precision(self):
        value = {'text': 'İstanbul', 'items': [Decimal('1.0000000000000001'), True, None]}
        self.assertEqual(json.loads(db.json_text(value), parse_float=Decimal), value)


if __name__ == '__main__':
    unittest.main()
