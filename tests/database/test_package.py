import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

class ContractTests(unittest.TestCase):
    def test_schema_124_typed_columns(self):
        text=(ROOT/'database/migrations/001_data_contract_v1.sql').read_text()
        block = re.search(r'CREATE TABLE IF NOT EXISTS staging\.(\w+)\s*\((.*?)\);',text,re.S)
        self.assertIsNotNone(block)
        import json
        contract=json.loads((ROOT/'docs/database/data_contract_v1.json').read_text())
        self.assertEqual(sum(len(x) for x in contract['observed_field_metadata'].values()),124)
        for entity, fields in contract['observed_field_metadata'].items():
            match = re.search(r'CREATE TABLE IF NOT EXISTS staging\.'+entity+r'\s*\((.*?)\);',text,re.S)
            self.assertIsNotNone(match,entity)
            body=match.group(1)
            for f in fields:
                self.assertIn('"'+f['sql_column']+'" '+f['sql_type'],body,entity+'.'+f['sql_column'])
    def test_role_and_api_boundaries(self):
        grants=(ROOT/'database/migrations/003_privileges.sql').read_text()
        self.assertIn('GRANT SELECT ON ALL TABLES IN SCHEMA api TO atlas_api',grants)
        self.assertNotRegex(grants,r'GRANT\s+SELECT\s+ON\s+ALL\s+TABLES\s+IN\s+SCHEMA\s+core\s+TO\s+atlas_api')
        views=(ROOT/'database/migrations/002_api_views.sql').read_text()
        self.assertEqual(views.count('CREATE OR REPLACE VIEW api.'),8)
        self.assertIn('LEFT JOIN core.program_groups',views)
    def test_archive_reader(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('atlas_loader',ROOT/'scripts/database/load_archive.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'complete_data'
            (p/'universities').mkdir(parents=True)
            (p/'programs'/'SAY').mkdir(parents=True)
            (p/'universities'/'all.json').write_text('[{"universiteId":42,"universiteAdi":"Demo"}]')
            (p/'programs'/'SAY'/'page_000000.json').write_text('{"content":[{"kilavuzKodu":1,"yil":2026}],"totalPages":1}')
            inputs=list(module.source_files(Path(tmp)))
            self.assertEqual(len(inputs),2)
            self.assertEqual(sum(len(module.parse_file(row[3],row[0])[1]) for row in inputs),2)
            obj={'foo':2,'bar':1}
            self.assertEqual(module.digest(obj),module.digest({'bar':1,'foo':2}))
    def test_powershell_commands_and_compose(self):
        import yaml
        compose=yaml.safe_load((ROOT/'compose.yaml').read_text())
        self.assertIn('postgres',compose['services'])
        service=compose['services']['postgres']
        self.assertTrue(service['ports'][0].startswith('127.0.0.1:'))
        self.assertIn('healthcheck',service)
        self.assertTrue((ROOT/'scripts/database/setup.ps1').exists())
        self.assertTrue((ROOT/'scripts/database/verify.ps1').exists())

if __name__ == '__main__': unittest.main()
