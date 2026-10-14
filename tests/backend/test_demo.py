"""Integration checks. PostgreSQL, demo data and setup-demo-write.py are required."""
import secrets
import unittest
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient

from backend.main import CONFIG, DEMO_CONFIG, app, query


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_database_and_loaded_data(self):
        response = self.client.get("/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"], "connected")
        counts = self.client.get("/api/veri-kapsami").json()
        for entity in ("universities", "program_versions", "net_results"):
            self.assertGreater(counts[entity], 0)

    def test_program_filters_and_detail(self):
        response = self.client.get("/api/programlar", params={"puan_turu": "SAY", "limit": 2})
        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertTrue(rows)
        self.assertLessEqual(len(rows), 2)
        self.assertTrue(all(row["puan_turu"] == "SAY" for row in rows))
        first = rows[0]
        response = self.client.get(
            f"/api/programlar/{first['kilavuz_kodu']}", params={"yil": first["yil"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), first)
        filtered = self.client.get(
            "/api/programlar", params={"universite_id": first["universite_id"], "yil": first["yil"]}
        ).json()
        self.assertTrue(filtered)
        self.assertTrue(all(row["universite_id"] == first["universite_id"] for row in filtered))
        self.assertEqual(self.client.get("/api/programlar/1").status_code, 404)

    def test_search_pagination_and_net_filters(self):
        first = self.client.get("/api/universiteler", params={"limit": 1}).json()[0]
        second = self.client.get("/api/universiteler", params={"limit": 1, "offset": 1}).json()[0]
        self.assertNotEqual(first["universite_id"], second["universite_id"])
        matches = self.client.get("/api/universiteler", params={"q": first["universite_adi"]}).json()
        self.assertIn(first, matches)
        # Quotes remain a bound search value, never SQL.
        self.assertEqual(self.client.get("/api/universiteler", params={"q": "' OR 1=1 --"}).json(), [])
        net = self.client.get("/api/net-sonuclari", params={"limit": 1}).json()[0]
        matches = self.client.get(
            "/api/net-sonuclari", params={"yil": net["yil"], "puan_turu": net["puan_turu"],
                                        "kilavuz_kodu": net["kilavuz_kodu"]}
        ).json()
        self.assertEqual(matches, [net])

    def test_invalid_inputs_and_database_failure(self):
        for params in ({"limit": 101}, {"offset": -1}, {"puan_turu": "INVALID"}):
            self.assertEqual(self.client.get("/api/programlar", params=params).status_code, 422)
        with patch("backend.main.psycopg.connect", side_effect=psycopg.OperationalError("secret detail")):
            response = self.client.get("/status")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret detail", response.text)


    def test_create_read_update_delete_university(self):
        headers = {"X-API-Key": DEMO_CONFIG["DEMO_API_KEY"]}
        university_id = 8000000000 + secrets.randbelow(1000000000)
        url = f"/api/universiteler/{university_id}"
        before = self.client.get("/api/veri-kapsami").json()["universities"]
        body = {"universite_id": university_id, "universite_adi": "DEMO TEST ÜNİVERSİTESİ"}
        created = False
        try:
            response = self.client.post("/api/universiteler", json=body, headers=headers)
            self.assertEqual(response.status_code, 201, response.text)
            created = True
            self.assertEqual(response.json(), body)
            self.assertEqual(self.client.get(url).json(), body)
            self.assertEqual(self.client.get("/api/veri-kapsami").json()["universities"], before + 1)
            duplicate = self.client.post("/api/universiteler", json=body, headers=headers)
            self.assertEqual(duplicate.status_code, 409)
            updated = self.client.put(url, json={"universite_adi": "DEMO GÜNCELLENDİ"}, headers=headers)
            self.assertEqual(updated.status_code, 200, updated.text)
            self.assertEqual(self.client.get(url).json()["universite_adi"], "DEMO GÜNCELLENDİ")
            deleted = self.client.delete(url, headers=headers)
            self.assertEqual(deleted.status_code, 204, deleted.text)
            self.assertEqual(deleted.content, b"")
            created = False
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.put(url, json={"universite_adi": "DEMO"}, headers=headers).status_code, 404)
            self.assertEqual(self.client.delete(url, headers=headers).status_code, 404)
            self.assertEqual(self.client.get("/api/veri-kapsami").json()["universities"], before)
        finally:
            if created:
                self.client.delete(url, headers=headers)

    def test_mutations_require_key(self):
        body = {"universite_id": 900000001, "universite_adi": "DEMO"}
        for headers in ({}, {"X-API-Key": "incorrect"}):
            for method, url, payload in (
                ("POST", "/api/universiteler", body),
                ("PUT", "/api/universiteler/900000001", {"universite_adi": "DEMO"}),
                ("DELETE", "/api/universiteler/900000001", None),
            ):
                self.assertEqual(self.client.request(method, url, json=payload, headers=headers).status_code, 401)

    def test_source_backed_universities_are_protected(self):
        headers = {"X-API-Key": DEMO_CONFIG["DEMO_API_KEY"]}
        original = query(
            """SELECT universite_id, universite_adi FROM api.universities
               WHERE universite_id NOT IN (SELECT universite_id FROM api.demo_universities)
               ORDER BY universite_id LIMIT 1"""
        )[0]
        url = f"/api/universiteler/{original['universite_id']}"
        self.assertEqual(self.client.put(url, json={"universite_adi": "DEMO"}, headers=headers).status_code, 409)
        self.assertEqual(self.client.delete(url, headers=headers).status_code, 409)
        self.assertEqual(self.client.get(url).json(), original)

    def test_write_validation_and_failure(self):
        headers = {"X-API-Key": DEMO_CONFIG["DEMO_API_KEY"]}
        for body in (
            {"universite_id": -1, "universite_adi": "DEMO"},
            {"universite_id": 9223372036854775808, "universite_adi": "DEMO"},
            {"universite_id": 900000001, "universite_adi": "   "},
            {"universite_id": 900000001, "universite_adi": "DEMO", "source_record_id": 1},
        ):
            self.assertEqual(self.client.post("/api/universiteler", json=body, headers=headers).status_code, 422)
        with patch("backend.main.psycopg.connect", side_effect=psycopg.OperationalError("secret detail")):
            response = self.client.post(
                "/api/universiteler", headers=headers,
                json={"universite_id": 900000001, "universite_adi": "DEMO"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret detail", response.text)

    def test_writer_database_privileges(self):
        with psycopg.connect(
            host="127.0.0.1", port=int(CONFIG.get("POSTGRES_PORT") or 5433),
            dbname="yokatlas_intelligence", user="atlas_demo_writer",
            password=DEMO_CONFIG["ATLAS_DEMO_WRITE_PASSWORD"], connect_timeout=3,
        ) as conn:
            self.assertTrue(conn.execute(
                "SELECT has_table_privilege(current_user, 'api.demo_universities', 'DELETE')"
            ).fetchone()[0])
            self.assertTrue(conn.execute(
                "SELECT has_table_privilege(current_user, 'api.demo_programs', 'DELETE')"
            ).fetchone()[0])
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute("SELECT * FROM core.universities LIMIT 1")
            conn.rollback()
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute("SELECT * FROM raw.api_responses LIMIT 1")
            conn.rollback()


    def test_create_read_update_delete_program_by_year(self):
        headers = {"X-API-Key": DEMO_CONFIG["DEMO_API_KEY"]}
        code = 6000000000 + secrets.randbelow(1000000000)
        university_id = 8000000000 + secrets.randbelow(1000000000)
        url = f"/api/programlar/{code}"
        before = self.client.get("/api/veri-kapsami").json()
        university_created = False
        created_years = set()
        body = {
            "kilavuz_kodu": code, "yil": 2026, "universite_id": university_id,
            "puan_turu": "SAY", "birim_adi": "DEMO TEST PROGRAMI",
            "min_puan": 430.5, "basari_sirasi": 10000, "kontenjan": 20,
        }
        try:
            response = self.client.post(
                "/api/universiteler", headers=headers,
                json={"universite_id": university_id, "universite_adi": "DEMO PROGRAM TEST ÜNİVERSİTESİ"},
            )
            self.assertEqual(response.status_code, 201, response.text)
            university_created = True
            for year in (2025, 2026):
                response = self.client.post("/api/programlar", json={**body, "yil": year}, headers=headers)
                self.assertEqual(response.status_code, 201, response.text)
                created_years.add(year)
                self.assertEqual(response.json()["yil"], year)
                self.assertEqual(response.json()["universite_adi"], "DEMO PROGRAM TEST ÜNİVERSİTESİ")
                self.assertEqual(self.client.get(url, params={"yil": year}).json(), response.json())
            self.assertEqual(self.client.post("/api/programlar", json=body, headers=headers).status_code, 409)
            self.assertEqual(self.client.get(url).json()["yil"], 2026)
            self.assertEqual(self.client.get("/api/veri-kapsami").json()["program_versions"], before["program_versions"] + 2)
            self.assertEqual(self.client.delete(f"/api/universiteler/{university_id}", headers=headers).status_code, 409)
            update = {key: value for key, value in body.items() if key not in ("kilavuz_kodu", "yil")}
            update["birim_adi"] = "DEMO PROGRAM GÜNCELLENDİ"
            update["kontenjan"] = 10
            response = self.client.put(url, params={"yil": 2026}, json=update, headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["kontenjan"], 10)
            self.assertEqual(self.client.get(url, params={"yil": 2025}).json()["kontenjan"], 20)
            response = self.client.delete(url, params={"yil": 2026}, headers=headers)
            self.assertEqual(response.status_code, 204, response.text)
            self.assertEqual(response.content, b"")
            created_years.remove(2026)
            self.assertEqual(self.client.get(url, params={"yil": 2026}).status_code, 404)
            self.assertEqual(self.client.get(url).json()["yil"], 2025)
            self.assertEqual(self.client.put(url, params={"yil": 2026}, json=update, headers=headers).status_code, 404)
            self.assertEqual(self.client.delete(url, params={"yil": 2026}, headers=headers).status_code, 404)
            self.assertEqual(self.client.delete(url, params={"yil": 2025}, headers=headers).status_code, 204)
            created_years.remove(2025)
            self.assertEqual(self.client.delete(f"/api/universiteler/{university_id}", headers=headers).status_code, 204)
            university_created = False
            self.assertEqual(self.client.get("/api/veri-kapsami").json(), before)
        finally:
            for year in created_years:
                self.client.delete(url, params={"yil": year}, headers=headers)
            if university_created:
                self.client.delete(f"/api/universiteler/{university_id}", headers=headers)

    def test_program_auth_validation_and_foreign_keys(self):
        headers = {"X-API-Key": DEMO_CONFIG["DEMO_API_KEY"]}
        body = {
            "kilavuz_kodu": 900000002, "yil": 2026, "universite_id": 173499,
            "puan_turu": "SAY", "birim_adi": "DEMO",
        }
        update = {key: value for key, value in body.items() if key not in ("kilavuz_kodu", "yil")}
        url = "/api/programlar/900000002?yil=2026"
        for request_headers in ({}, {"X-API-Key": "incorrect"}):
            self.assertEqual(self.client.post("/api/programlar", json=body, headers=request_headers).status_code, 401)
            self.assertEqual(self.client.put(url, json=update, headers=request_headers).status_code, 401)
            self.assertEqual(self.client.delete(url, headers=request_headers).status_code, 401)
        for fields in (
            {"kontenjan": -1}, {"min_puan": -1}, {"birim_adi": "   "},
            {"puan_turu": "INVALID"}, {"yil": 1999},
            {"kilavuz_kodu": 9223372036854775808}, {"source_record_id": 1},
        ):
            self.assertEqual(self.client.post("/api/programlar", json={**body, **fields}, headers=headers).status_code, 422)
        self.assertEqual(self.client.put("/api/programlar/900000002", json=update, headers=headers).status_code, 422)
        self.assertEqual(self.client.delete("/api/programlar/900000002", headers=headers).status_code, 422)
        invalid = {**body, "kilavuz_kodu": 6000000000 + secrets.randbelow(1000000000),
                   "universite_id": 9223372036854775807}
        before = self.client.get("/api/veri-kapsami").json()
        response = self.client.post("/api/programlar", json=invalid, headers=headers)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.client.get("/api/veri-kapsami").json(), before)
        self.assertEqual(self.client.get(f"/api/programlar/{invalid['kilavuz_kodu']}", params={"yil": 2026}).status_code, 404)

    def test_source_programs_are_protected(self):
        headers = {"X-API-Key": DEMO_CONFIG["DEMO_API_KEY"]}
        original = query(
            """SELECT kilavuz_kodu, yil FROM api.program_catalog
               WHERE program_version_id NOT IN (SELECT program_version_id FROM api.demo_programs)
               ORDER BY kilavuz_kodu LIMIT 1"""
        )[0]
        url = f"/api/programlar/{original['kilavuz_kodu']}"
        params = {"yil": original["yil"]}
        before = self.client.get(url, params=params).json()
        body = {"puan_turu": before["puan_turu"], "birim_adi": "DEMO",
                "universite_id": before["universite_id"]}
        self.assertEqual(self.client.put(url, params=params, json=body, headers=headers).status_code, 409)
        self.assertEqual(self.client.delete(url, params=params, headers=headers).status_code, 409)
        self.assertEqual(self.client.get(url, params=params).json(), before)


if __name__ == "__main__":
    unittest.main()
