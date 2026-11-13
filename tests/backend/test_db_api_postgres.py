"""Opt-in PostgreSQL 17 checks: DATA_API_TEST_DSN must name an isolated test database."""
import os
import secrets
import unittest
from pathlib import Path
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient
from psycopg import sql

from backend import db
from backend.main import app


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / 'database/migrations'


@unittest.skipUnless(os.environ.get('DATA_API_TEST_DSN'), 'Set DATA_API_TEST_DSN to an isolated test database')
class PostgreSQLDataAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = psycopg.connect(os.environ['DATA_API_TEST_DSN'], autocommit=True)
        cls.addClassCleanup(cls.admin.close)
        if not cls.admin.info.dbname.startswith('test_yokatlas_'):
            raise ValueError('Refusing to modify a database without the test_yokatlas_ prefix')
        if not cls.admin.execute("SELECT 1 FROM pg_roles WHERE rolname='atlas_ingest'").fetchone():
            source = (MIGRATIONS / '000_roles.sql').read_text()
            source = source.replace('yokatlas_intelligence', sql.Identifier(cls.admin.info.dbname).as_string(cls.admin))
            for name in ('ingest_password', 'api_password', 'analytics_password'):
                source = source.replace(":'" + name + "'", sql.Literal(secrets.token_urlsafe(24)).as_string(cls.admin))
            cls.admin.execute(source)
        for path in sorted(MIGRATIONS.glob('00[1-7]_*.sql')):
            cls.admin.execute(path.read_text())
        cls.legacy_permissions = cls.permissions()
        cls.admin.execute('''CREATE TABLE raw.api_test_types (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            natural_key text NOT NULL UNIQUE,
            score numeric(40,5) NOT NULL CHECK (score>=0),
            amount numeric(5,2), short_name varchar(3), fixed_name char(3),
            small smallint, real_value real, double_value double precision,
            enabled boolean NOT NULL DEFAULT true,
            event_day date, captured_at timestamptz NOT NULL DEFAULT now(),
            local_time timestamp(3), time_of_day time(3), zoned_time timetz(3),
            payload jsonb NOT NULL DEFAULT '{}', plain_json json,
            generated_score numeric GENERATED ALWAYS AS (score+1) STORED,
            unsupported uuid
        );
        CREATE TABLE raw.api_test_composite (left_id bigint, right_id bigint, note text,
            PRIMARY KEY(left_id,right_id) INCLUDE (note));
        CREATE TABLE analytics.api_test_catalog (id bigint PRIMARY KEY, name text, year integer,
            score numeric(12,3), missing text, payload jsonb, plain_json json);
        INSERT INTO analytics.api_test_catalog VALUES
            (1,'Ankara',2026,4.419,NULL,'{"flag":true}','{"flag":true}'),
            (2,'İstanbul',2026,3.300,'present','{}','{}'),
            (3,'ankara %_\\',2025,2.200,NULL,'{}','{}');
        CREATE VIEW analytics.api_test_view AS SELECT * FROM analytics.api_test_catalog;
        CREATE MATERIALIZED VIEW analytics.api_test_materialized AS SELECT * FROM analytics.api_test_catalog;
        CREATE TABLE analytics.api_test_empty (id integer);''')
        cls.admin.execute((MIGRATIONS / '008_data_api_roles.sql').read_text())
        cls.passwords = {role: secrets.token_urlsafe(24) for role in ('atlas_raw_writer', 'atlas_analytics_reader')}
        for role, password in cls.passwords.items():
            cls.admin.execute(sql.SQL('ALTER ROLE {} PASSWORD {}').format(sql.Identifier(role), sql.Literal(password)))
        cls.config = {
            'PGHOST': cls.admin.info.host, 'PGPORT': str(cls.admin.info.port),
            'PGDATABASE': cls.admin.info.dbname, 'DB_WRITE_API_KEY': 'integration-write-key',
            'ATLAS_RAW_WRITER_PASSWORD': cls.passwords['atlas_raw_writer'],
            'ATLAS_ANALYTICS_READER_PASSWORD': cls.passwords['atlas_analytics_reader'],
        }
        cls.client = TestClient(app)
        cls.addClassCleanup(cls.client.close)
        cls.headers = {'X-API-Key': 'integration-write-key', 'Content-Type': 'application/json'}

    @classmethod
    def tearDownClass(cls):
        cls.admin.execute('''DROP VIEW analytics.api_test_view;
            DROP MATERIALIZED VIEW analytics.api_test_materialized;
            DROP TABLE analytics.api_test_catalog, analytics.api_test_empty,
                       raw.api_test_types, raw.api_test_composite;''')

    @classmethod
    def permissions(cls):
        tables = cls.admin.execute('''SELECT r.rolname,n.nspname,c.relname,p.permission,
                   has_table_privilege(r.oid,c.oid,p.permission)
            FROM pg_roles r CROSS JOIN pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE')) p(permission)
            WHERE r.rolname IN ('atlas_ingest','atlas_api','atlas_analytics')
              AND n.nspname IN ('raw','staging','core','quality','api','analytics')
              AND c.relkind IN ('r','p','v','m') AND c.relname NOT LIKE 'api_test_%'
            ORDER BY 1,2,3,4''').fetchall()
        schemas = cls.admin.execute('''SELECT r.rolname,n.nspname,p.permission,
                has_schema_privilege(r.oid,n.oid,p.permission)
            FROM pg_roles r CROSS JOIN pg_namespace n CROSS JOIN (VALUES ('USAGE'),('CREATE')) p(permission)
            WHERE r.rolname IN ('atlas_ingest','atlas_api','atlas_analytics')
              AND n.nspname IN ('raw','staging','core','quality','api','analytics')
            ORDER BY 1,2,3''').fetchall()
        sequences = cls.admin.execute('''SELECT r.rolname,n.nspname,c.relname,p.permission,
                has_sequence_privilege(r.oid,c.oid,p.permission)
            FROM pg_roles r CROSS JOIN pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            CROSS JOIN (VALUES ('USAGE'),('SELECT'),('UPDATE')) p(permission)
            WHERE r.rolname IN ('atlas_ingest','atlas_api','atlas_analytics')
              AND n.nspname IN ('raw','staging','core','quality','api','analytics')
              AND c.relkind='S' AND c.relname NOT LIKE 'api_test_%'
            ORDER BY 1,2,3,4''').fetchall()
        defaults = cls.admin.execute('''SELECT d.defaclrole,n.nspname,d.defaclobjtype,
                a.grantor,a.grantee,a.privilege_type,a.is_grantable
            FROM pg_default_acl d LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace
            CROSS JOIN LATERAL aclexplode(d.defaclacl) a JOIN pg_roles r ON r.oid=a.grantee
            WHERE r.rolname IN ('atlas_ingest','atlas_api','atlas_analytics')
            ORDER BY 1,2,3,4,5,6''').fetchall()
        return tables, schemas, sequences, defaults

    def setUp(self):
        config = patch.dict(db.CONFIG, self.config)
        config.start()
        self.addCleanup(config.stop)

    def insert(self, table='api_test_types', **data):
        return self.client.post('/api/db/write', headers=self.headers,
            json={'table': table, 'data': data})

    def sample(self, **overrides):
        return {'natural_key': secrets.token_hex(8), 'score': 4.419, **overrides}

    def read(self, table='api_test_catalog', **params):
        return self.client.get('/api/db/read', params={'table': table, 'order_by': 'id', **params})

    def role_connection(self, role):
        conn = psycopg.connect(host=self.admin.info.host, port=self.admin.info.port,
            dbname=self.admin.info.dbname, user=role, password=self.passwords[role], autocommit=True)
        self.addCleanup(conn.close)
        return conn

    def test_defaults_generated_key_and_commit(self):
        data = self.sample()
        response = self.insert(**data)
        self.assertEqual(response.status_code, 201, response.text)
        key = response.json()['key']
        self.assertEqual(list(key), ['id'])
        row = self.admin.execute('SELECT natural_key, enabled, payload, generated_score FROM raw.api_test_types WHERE id=%s',
            (key['id'],)).fetchone()
        self.assertEqual(row[:3], (data['natural_key'], True, {}))
        self.assertEqual(str(row[3]), '5.41900')
        run = self.insert('ingestion_runs')
        self.assertEqual(run.status_code, 201, run.text)
        run_id = run.json()['key']['ingestion_run_id']
        self.assertEqual(self.admin.execute('SELECT source_system FROM raw.ingestion_runs WHERE ingestion_run_id=%s',
            (run_id,)).fetchone()[0], 'yokatlas')
        self.admin.execute('DELETE FROM raw.ingestion_runs WHERE ingestion_run_id=%s', (run_id,))

    def test_parent_child_inserts_unique_and_foreign_key_errors(self):
        run = self.insert('ingestion_runs').json()['key']['ingestion_run_id']
        data = {'ingestion_run_id': run, 'endpoint': '/api/test', 'method': 'GET',
                'source_hash_sha256': 'a'*64, 'payload': {'data': [1]}}
        try:
            response = self.insert('api_responses', **data)
            self.assertEqual(response.status_code, 201, response.text)
            response_id = response.json()['key']['api_response_id']
            child = self.insert('source_records', api_response_id=response_id,
                source_entity='test', source_array_index=0, record={'value': 1})
            self.assertEqual(child.status_code, 201, child.text)
            self.assertEqual(self.insert('api_responses', **data).status_code, 409)
            self.assertEqual(self.insert('api_responses', **{**data, 'ingestion_run_id': 9223372036854775807}).status_code, 409)
        finally:
            self.admin.execute('DELETE FROM raw.source_records WHERE api_response_id IN (SELECT api_response_id FROM raw.api_responses WHERE ingestion_run_id=%s)', (run,))
            self.admin.execute('DELETE FROM raw.api_responses WHERE ingestion_run_id=%s', (run,))
            self.admin.execute('DELETE FROM raw.ingestion_runs WHERE ingestion_run_id=%s', (run,))

    def test_invalid_writes_leave_no_row(self):
        cases = [self.sample(extra=1), {'score': 1}, self.sample(score='1'),
            self.sample(score=True), self.sample(score=-1), self.sample(id=7),
            self.sample(generated_score=1), self.sample(score=None), self.sample(small=32768),
            self.sample(small=True), self.sample(short_name='four'), self.sample(fixed_name='four'),
            self.sample(amount=1.001), self.sample(amount=1000), self.sample(enabled='true'),
            self.sample(event_day='2026-02-30'), self.sample(captured_at='2026-10-22T00:00:00'),
            self.sample(local_time='2026-10-22T00:00:00.0001'),
            self.sample(time_of_day='12:30:00.0001'), self.sample(unsupported='invalid')]
        before = self.admin.execute('SELECT count(*) FROM raw.api_test_types').fetchone()[0]
        for data in cases:
            with self.subTest(data=data):
                response = self.insert(**data)
                self.assertEqual(response.status_code, 422, response.text)
        after = self.admin.execute('SELECT count(*) FROM raw.api_test_types').fetchone()[0]
        self.assertEqual(after, before)

    def test_duplicate_is_error_and_does_not_update(self):
        data = self.sample()
        self.assertEqual(self.insert(**data).status_code, 201)
        self.assertEqual(self.insert(**{**data, 'score': 99}).status_code, 409)
        score = self.admin.execute('SELECT score FROM raw.api_test_types WHERE natural_key=%s', (data['natural_key'],)).fetchone()[0]
        self.assertEqual(str(score), '4.41900')

    def test_decimal_and_nested_json_precision_survive_http_and_database(self):
        response = self.client.post('/api/db/write', headers=self.headers, content='''{
            "table":"api_test_types","data":{"natural_key":"exact-decimals",
            "score":123456789012345678901234567890.12345,
            "payload":{"number":1.12345678901234567890123456789},"plain_json":[1.00000000000000001]}}''')
        self.assertEqual(response.status_code, 201, response.text)
        row = self.admin.execute("SELECT score::text,payload->>'number',plain_json->>0 FROM raw.api_test_types WHERE natural_key='exact-decimals'").fetchone()
        self.assertEqual(row, ('123456789012345678901234567890.12345', '1.12345678901234567890123456789', '1.00000000000000001'))

    def test_composite_primary_key_excludes_include_columns(self):
        response = self.insert('api_test_composite', left_id=1, right_id=2, note='private')
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['key'], {'left_id': 1, 'right_id': 2})

    def test_live_catalog_changes_and_supported_temporal_and_float_values(self):
        self.admin.execute('ALTER TABLE raw.api_test_types ADD COLUMN fresh_column text')
        try:
            response = self.insert(**self.sample(fresh_column='new', event_day='2026-10-22',
                captured_at='2026-10-22T13:30:00+03:00', local_time='2026-10-22T13:30:00.123',
                time_of_day='13:30:00.123', zoned_time='13:30:00.123+03:00',
                real_value=1.25, double_value=2.5))
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(self.admin.execute('SELECT fresh_column FROM raw.api_test_types WHERE id=%s',
                (response.json()['key']['id'],)).fetchone()[0], 'new')
        finally:
            self.admin.execute('ALTER TABLE raw.api_test_types DROP COLUMN fresh_column')

    def test_reads_table_view_materialized_view_and_empty_table(self):
        for table in ('api_test_catalog', 'api_test_view', 'api_test_materialized'):
            with self.subTest(table=table):
                response = self.read(table)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual([row['id'] for row in response.json()['data']], [1,2,3])
        self.assertEqual(self.read('api_test_empty').json()['data'], [])
        self.assertEqual(self.read('does_not_exist').status_code, 404)
        self.assertEqual(self.read('program_catalog').status_code, 404)
        self.assertEqual(self.read('api_responses').status_code, 404)
        self.assertEqual(self.insert('universities').status_code, 404)

    def test_filters_search_sort_and_pagination(self):
        self.assertEqual([row['id'] for row in self.read(filters='{"year":2026,"missing":null}').json()['data']], [1])
        self.assertEqual([row['id'] for row in self.read(filters='{"payload":{"flag":true}}').json()['data']], [1])
        self.assertEqual([row['id'] for row in self.read(filters='{"plain_json":{"flag":true}}').json()['data']], [1])
        result = self.read(search_column='name', q='ANKARA', direction='desc', limit=1, offset=1)
        self.assertEqual([row['id'] for row in result.json()['data']], [1])
        self.assertEqual(self.read(search_column='name', q="' OR 1=1 --").json()['data'], [])
        self.assertEqual([row['id'] for row in self.read(search_column='name', q='%_\\').json()['data']], [3])
        for params in ({'filters': '{"year":"2026"}'}, {'filters': '{"unknown":1}'},
                       {'filters': '{"id; DROP TABLE raw.api_responses":1}'},
                       {'search_column': 'id', 'q': '1'}, {'order_by': 'missing_column'}):
            self.assertEqual(self.read(**params).status_code, 422)

    def test_roles_cannot_cross_schemas_or_change_existing_data(self):
        writer = self.role_connection('atlas_raw_writer')
        reader = self.role_connection('atlas_analytics_reader')
        self.assertEqual(reader.execute('SHOW default_transaction_read_only').fetchone()[0], 'on')
        for conn, statement in (
            (writer, 'SELECT payload FROM raw.api_responses'),
            (writer, "UPDATE raw.ingestion_runs SET status='failed'"),
            (writer, 'DELETE FROM raw.ingestion_runs'),
            (writer, 'SELECT * FROM analytics.api_test_catalog'),
            (writer, "INSERT INTO core.universities(universite_id,universite_adi) VALUES (1,'x')"),
            (reader, 'SELECT * FROM raw.api_responses'),
            (reader, 'SELECT * FROM staging.universities'),
            (reader, 'SELECT * FROM core.universities'),
            (reader, 'SELECT * FROM api.universities'),
            (reader, 'SELECT * FROM quality.quarantined_records'),
            (reader, "INSERT INTO analytics.api_test_catalog(id) VALUES (99)"),
        ):
            with self.subTest(statement=statement), self.assertRaises(psycopg.Error):
                conn.execute(statement)
        reader.execute('SET default_transaction_read_only=off')
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            reader.execute('INSERT INTO analytics.api_test_catalog(id) VALUES (99)')
        self.assertEqual(self.admin.execute('''SELECT count(*) FROM pg_auth_members
            WHERE member IN ('atlas_raw_writer'::regrole,'atlas_analytics_reader'::regrole)''').fetchone()[0], 0)

    def test_reapplying_migration_preserves_bot_grants_and_future_analytics_access(self):
        self.admin.execute((MIGRATIONS / '008_data_api_roles.sql').read_text())
        self.assertEqual(self.permissions(), self.legacy_permissions)
        for owner in ('atlas_owner', 'atlas_analytics'):
            with self.admin.transaction():
                self.admin.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(owner)))
                self.admin.execute('CREATE TABLE analytics.api_test_future(id integer)')
            try:
                self.assertEqual(self.read('api_test_future').status_code, 200)
            finally:
                self.admin.execute('DROP TABLE analytics.api_test_future')


if __name__ == '__main__':
    unittest.main()
