"""Report read endpoints use curated views and bound filters; no database needed."""
import unittest
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.main import app


class ReportAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_sege_defaults_latest_year_per_geography_and_binds_search(self):
        with patch('backend.main.query', return_value=[]) as query:
            response = self.client.get('/api/sege', params={'duzey': 'ilce', 'il_kodu': 34, 'q': "' OR 1=1 --"})
        self.assertEqual(response.status_code, 200)
        statement, params = query.call_args.args
        self.assertIn('api.sege_results', statement)
        self.assertIn('max(yil)', statement)
        self.assertNotIn("' OR 1=1 --", statement)
        self.assertEqual(params['duzey'], 'ilce')
        self.assertEqual(params['il_kodu'], 34)
        self.assertEqual(params['q'], "%' OR 1=1 --%")

    def test_urap_filters_and_source_fields_are_returned(self):
        rows = [{'universite_id': 42, 'sira': 1, 'donem': '2025-2026', 'puanlar': {'makale': 189.43}, 'source_page': 18}]
        with patch('backend.main.query', return_value=rows) as query:
            response = self.client.get('/api/urap', params={'donem': '2025-2026', 'universite_id': 42, 'limit': 1, 'offset': 1})
        self.assertEqual(response.json(), rows)
        self.assertEqual(query.call_args.args[1]['universite_id'], 42)
        self.assertEqual(query.call_args.args[1]['offset'], 1)

    def test_invalid_filters_do_not_reach_database(self):
        cases = [('/api/sege', {'duzey': 'unknown'}), ('/api/sege', {'il_kodu': 82}),
                 ('/api/sege', {'limit': 1000}), ('/api/urap', {'offset': -1}),
                 ('/api/urap', {'donem': '2026-2025'}), ('/api/urap', {'donem': '2026'})]
        for url, params in cases:
            with self.subTest(params=params), patch('backend.main.query') as query:
                self.assertEqual(self.client.get(url, params=params).status_code, 422)
                query.assert_not_called()

    def test_postgres_decimal_scores_are_json_numbers(self):
        for url, field, value in [('/api/sege', 'skor', '4.419'), ('/api/urap', 'toplam_puan', '1152.91')]:
            with self.subTest(url=url), patch('backend.main.query', return_value=[{field: Decimal(value)}]):
                result = self.client.get(url).json()[0][field]
                self.assertIsInstance(result, float)
                self.assertEqual(result, float(value))

    def test_publication_list_and_ops_inventory(self):
        with patch('backend.main.query', return_value=[]) as query:
            self.assertEqual(self.client.get('/api/rapor-yayinlari').status_code, 200)
        self.assertIn('api.report_publications', query.call_args.args[0])
        from backend.tuik_admin import bots
        inventory = {row['bot_id']: row for row in bots()}
        self.assertEqual(inventory['sege']['command'], 'python -m scraper.panel_sege')
        self.assertFalse(inventory['urap']['manual_runs'])


if __name__ == '__main__':
    unittest.main()
