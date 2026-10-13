"""Read-only integration checks. PostgreSQL and the demo sample must be loaded."""
import unittest
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient

from backend.main import app


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_database_and_loaded_data(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"], "connected")
        counts = self.client.get("/api/coverage").json()
        for entity in ("universities", "program_versions", "net_results"):
            self.assertGreater(counts[entity], 0)

    def test_program_filters_and_detail(self):
        response = self.client.get("/api/programs", params={"puan_turu": "SAY", "limit": 2})
        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertTrue(rows)
        self.assertLessEqual(len(rows), 2)
        self.assertTrue(all(row["puan_turu"] == "SAY" for row in rows))
        first = rows[0]
        response = self.client.get(
            f"/api/programs/{first['kilavuz_kodu']}", params={"yil": first["yil"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), first)
        filtered = self.client.get(
            "/api/programs", params={"universite_id": first["universite_id"], "yil": first["yil"]}
        ).json()
        self.assertTrue(filtered)
        self.assertTrue(all(row["universite_id"] == first["universite_id"] for row in filtered))
        self.assertEqual(self.client.get("/api/programs/1").status_code, 404)

    def test_search_pagination_and_net_filters(self):
        first = self.client.get("/api/universities", params={"limit": 1}).json()[0]
        second = self.client.get("/api/universities", params={"limit": 1, "offset": 1}).json()[0]
        self.assertNotEqual(first["universite_id"], second["universite_id"])
        matches = self.client.get("/api/universities", params={"q": first["universite_adi"]}).json()
        self.assertIn(first, matches)
        # Quotes remain a bound search value, never SQL.
        self.assertEqual(self.client.get("/api/universities", params={"q": "' OR 1=1 --"}).json(), [])
        net = self.client.get("/api/net-results", params={"limit": 1}).json()[0]
        matches = self.client.get(
            "/api/net-results", params={"yil": net["yil"], "puan_turu": net["puan_turu"],
                                        "kilavuz_kodu": net["kilavuz_kodu"]}
        ).json()
        self.assertEqual(matches, [net])

    def test_invalid_inputs_and_database_failure(self):
        for params in ({"limit": 101}, {"offset": -1}, {"puan_turu": "INVALID"}):
            self.assertEqual(self.client.get("/api/programs", params=params).status_code, 422)
        with patch("backend.main.psycopg.connect", side_effect=psycopg.OperationalError("secret detail")):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret detail", response.text)


if __name__ == "__main__":
    unittest.main()
