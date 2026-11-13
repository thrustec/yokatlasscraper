"""TÜİK SDMX catalog and manual ingestion jobs for the local admin API."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from scripts.database.load_archive import read_env


ROOT = Path(__file__).resolve().parents[1]
CONFIG = read_env(ROOT / ".env")
TOKEN_URL = "https://giris.tuik.gov.tr/realms/web/protocol/openid-connect/token"
SDMX_URL = "https://nsiws.tuik.gov.tr/rest"
MAX_METADATA_BYTES = 25 * 1024 * 1024
MAX_DATA_BYTES = 25 * 1024 * 1024
POPULATION_FLOW = "DF_ADNKS_T16"
POPULATION_VERSION = "1.0"
BOT_ID = "tuik-sdmx"
_catalog_cache: tuple[float, list[dict]] | None = None


class TuikError(RuntimeError):
    """Safe operational error; never includes credentials or response bodies."""


def _db_connect() -> psycopg.Connection:
    config = {**CONFIG, **os.environ}
    password = config.get("ATLAS_INGEST_PASSWORD")
    if not password:
        raise TuikError("Veritabanı yazma yapılandırması eksik.")
    return psycopg.connect(
        host=config.get("PGHOST", "127.0.0.1"),
        port=int(config.get("PGPORT") or config.get("POSTGRES_PORT") or 5433),
        dbname=config.get("PGDATABASE", "yokatlas_intelligence"),
        user="atlas_ingest",
        password=password,
        connect_timeout=5,
        options="-c statement_timeout=60000 -c lock_timeout=10000",
    )


def _tuik_key() -> str:
    key = os.environ.get("TUIK_API_KEY") or CONFIG.get("TUIK_API_KEY")
    if not key:
        raise TuikError("Sunucu yapılandırmasında TUIK_API_KEY bulunamadı.")
    return key


def _download(url: str, *, token: str | None = None, form: dict | None = None,
          limit: int = MAX_METADATA_BYTES) -> bytes:
    body = urllib.parse.urlencode(form).encode() if form is not None else None
    headers = {"Accept-Encoding": "identity", "User-Agent": "YOKAtlas-TUIK-Bot/1.0"}
    if urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("format") == ["SDMX-CSV"]:
        headers["Accept"] = "text/csv"
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise TuikError(f"TÜİK isteği HTTP {response.status} döndürdü.")
            raw = response.read(limit + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise TuikError("TÜİK erişimi reddetti; API anahtarını ve yetkiyi kontrol edin.") from None
        if exc.code == 429:
            raise TuikError("TÜİK istek sınırına ulaşıldı; daha sonra yeniden deneyin.") from None
        raise TuikError(f"TÜİK isteği HTTP {exc.code} döndürdü.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise TuikError("TÜİK servisine bağlanılamadı.") from None
    if len(raw) > limit:
        raise TuikError("TÜİK yanıtı izin verilen boyutu aştı.")
    return raw


def _read(url: str, *, token: str | None = None, form: dict | None = None,
          limit: int = MAX_METADATA_BYTES, monitor=None) -> bytes:
    if monitor and monitor.should_stop():
        raise KeyboardInterrupt
    failed_id = next((r["failed_id"] for r in monitor.retry_requests
                      if r["request_key"] == url), None) if monitor else None
    try:
        raw = _download(url, token=token, form=form, limit=limit)
    except TuikError as exc:
        if monitor:
            # Authentication form and bearer token never enter retry parameters or logs.
            monitor.request_failed(url, url=url, error=str(exc), failed_id=failed_id)
        raise
    if monitor:
        monitor.request_ok(failed_id=failed_id)
        if monitor.should_stop():
            raise KeyboardInterrupt
    return raw


def _token(monitor=None) -> str:
    raw = _read(TOKEN_URL, form={
        "grant_type": "password",
        "client_id": "nsi-ws-consumer",
        "api_key": _tuik_key(),
    }, monitor=monitor)
    try:
        token = json.loads(raw).get("access_token")
    except (ValueError, AttributeError):
        token = None
    if not isinstance(token, str) or not token:
        raise TuikError("TÜİK erişim anahtarıyla token alınamadı.")
    return token


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _classify(title: str) -> tuple[str, str]:
    value = _normalize(title)
    categories = (
        ("migration", "Göç", ("goc", "migration")),
        ("demography", "Nüfus ve demografi", ("nufus", "adnks", "demografi", "population", "dogum", "olum")),
        ("prices", "Fiyatlar ve enflasyon", ("fiyat", "tu fe", "tufe", "u fe", "ufe", "cpi", "price", "enflasyon")),
        ("labor", "İşgücü ve ücretler", ("isgucu", "istihdam", "issizlik", "ucret", "labour", "labor", "employment", "wage")),
        ("education", "Eğitim", ("egitim", "education", "ogretim")),
        ("housing", "Konut ve inşaat", ("konut", "housing", "yapi ruhsat", "construction")),
        ("tourism", "Turizm", ("turizm", "tourism")),
        ("agriculture", "Tarım", ("tarim", "agriculture", "crop", "livestock")),
        ("health", "Sağlık", ("saglik", "health")),
        ("trade", "Dış ticaret", ("dis ticaret", "foreign trade", "export", "import")),
        ("economy", "Ekonomi ve milli hesaplar", ("gayrisafi", "gdp", "milli gelir", "national account", "ekonomik", "ekonomi")),
    )
    for slug, label, needles in categories:
        if any(needle in value for needle in needles):
            return slug, label
    return "other", "Diğer TÜİK verileri"


def _normalize(value: str) -> str:
    value = value.translate(str.maketrans({"ı": "i", "İ": "I"}))
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def list_datasets(*, refresh: bool = False, monitor=None) -> list[dict]:
    global _catalog_cache
    if _catalog_cache and not refresh and time.monotonic() - _catalog_cache[0] < 1800:
        return _catalog_cache[1]
    raw = _read(f"{SDMX_URL}/dataflow/TR/all/latest?detail=full", token=_token(monitor), monitor=monitor)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise TuikError("TÜİK veri kataloğu beklenen XML biçiminde değil.") from None
    datasets = []
    for node in root.iter():
        if _local_name(node.tag) != "Dataflow":
            continue
        dataflow_id, version = node.attrib.get("id"), node.attrib.get("version")
        if not dataflow_id or not version or not re.fullmatch(r"[A-Z0-9_]+", dataflow_id):
            continue
        names = []
        for child in node.iter():
            if _local_name(child.tag) == "Name" and (child.text or "").strip():
                lang = child.attrib.get("{http://www.w3.org/XML/1998/namespace}lang", "")
                names.append((lang.lower(), child.text.strip()))
        title = next((name for lang, name in names if lang.startswith("tr")), None)
        title = title or next((name for lang, name in names if lang.startswith("en")), None)
        title = title or dataflow_id
        category_id, category = _classify(title)
        datasets.append({
            "id": dataflow_id,
            "version": version,
            "title": title,
            "category_id": category_id,
            "category": category,
            "normalization": "typed" if dataflow_id == POPULATION_FLOW and version == POPULATION_VERSION else "raw_only",
        })
    if not datasets:
        raise TuikError("TÜİK kataloğunda veri akışı bulunamadı.")
    datasets.sort(key=lambda d: (d["category"], d["title"].casefold(), d["id"]))
    _catalog_cache = (time.monotonic(), datasets)
    return datasets


def create_run(dataflow: dict, year: int) -> int:
    details = {
        "bot_id": BOT_ID,
        "dataflow_id": dataflow["id"],
        "dataflow_version": dataflow["version"],
        "dataflow_title": dataflow["title"],
        "category_id": dataflow["category_id"],
        "year": year,
    }
    with _db_connect() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO raw.ingestion_runs (source_system, scraper_version, status, details)
               VALUES ('tuik_sdmx', 'tuik-sdmx-1', 'queued', %s) RETURNING ingestion_run_id""",
            (Jsonb(details),),
        )
        return cur.fetchone()[0]


def list_runs(limit: int = 20) -> list[dict]:
    with _db_connect() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT ingestion_run_id::text AS run_id, status, started_at, completed_at,
                      details->>'dataflow_id' AS dataflow_id,
                      details->>'dataflow_title' AS dataflow_title,
                      details->>'category_id' AS category_id,
                      nullif(details->>'year','')::integer AS year,
                      nullif(details->>'records','')::integer AS records,
                      nullif(details->>'staged_records','')::integer AS staged_records,
                      details->>'normalization' AS normalization,
                      details->>'message' AS message
               FROM raw.ingestion_runs
               WHERE source_system='tuik_sdmx'
               ORDER BY ingestion_run_id DESC LIMIT %s""",
            (limit,),
        )
        return cur.fetchall()


def get_run(run_id: int) -> dict | None:
    with _db_connect() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT ingestion_run_id::text AS run_id, status, started_at, completed_at,
                      details->>'dataflow_id' AS dataflow_id,
                      details->>'dataflow_title' AS dataflow_title,
                      details->>'category_id' AS category_id,
                      nullif(details->>'year','')::integer AS year,
                      nullif(details->>'records','')::integer AS records,
                      nullif(details->>'staged_records','')::integer AS staged_records,
                      details->>'normalization' AS normalization,
                      details->>'message' AS message
               FROM raw.ingestion_runs
               WHERE source_system='tuik_sdmx' AND ingestion_run_id=%s""",
            (run_id,),
        )
        return cur.fetchone()


def _city_codes(token: str, conn: psycopg.Connection, monitor=None) -> dict[str, int]:
    raw = _read(f"{SDMX_URL}/codelist/TR/CL_IBBS/1.2?detail=full", token=token, monitor=monitor)
    root = ET.fromstring(raw)
    code_names = {}
    for node in root.iter():
        if _local_name(node.tag) != "Code" or not node.attrib.get("id"):
            continue
        names = []
        for child in node.iter():
            if _local_name(child.tag) == "Name" and (child.text or "").strip():
                lang = child.attrib.get("{http://www.w3.org/XML/1998/namespace}lang", "").lower()
                names.append((lang, child.text.strip()))
        label = next((name for lang, name in names if lang.startswith("tr")), None)
        label = label or next((name for lang, name in names if lang.startswith("en")), None)
        if label:
            code_names[node.attrib["id"]] = label
    with conn.cursor() as cur:
        cur.execute("SELECT il_kodu, il_adi FROM core.cities WHERE il_kodu BETWEEN 1 AND 81")
        city_ids = {_normalize(name): code for code, name in cur.fetchall()}
    mapped = {}
    for source_code, name in code_names.items():
        name = re.sub(r"\s*[\[(].*?[\])]\s*$", "", name)
        key = _normalize(re.sub(r"\s+(province|ili|il)$", "", name, flags=re.IGNORECASE))
        if key in city_ids:
            mapped[source_code] = city_ids[key]
    return mapped


def _age_label(code: str) -> str:
    if code == "_T":
        return "Toplam"
    match = re.fullmatch(r"Y(\d+)T(\d+)", code)
    if match:
        return f"{int(match.group(1))}-{int(match.group(2))}"
    match = re.fullmatch(r"Y_GE(\d+)", code)
    if match:
        return f"{match.group(1)}+"
    return code


def _sex_label(code: str) -> str:
    return {"_T": "Toplam", "1": "Erkek", "2": "Kadın"}.get(code, code)


def run_ingestion(run_id: int, dataflow: dict, year: int, monitor=None) -> None:
    conn = None
    try:
        conn = _db_connect()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(hashtext('tuik_sdmx_manual_ingestion'))")
            if not cur.fetchone()[0]:
                cur.execute("UPDATE raw.ingestion_runs SET status='failed', completed_at=now(), details=details || %s WHERE ingestion_run_id=%s",
                            (Jsonb({"message": "TÜİK botunda başka bir iş sürüyor."}), run_id))
                return
            cur.execute("UPDATE raw.ingestion_runs SET status='running' WHERE ingestion_run_id=%s", (run_id,))

        token = _token(monitor)
        endpoint = (f"{SDMX_URL}/data/TR,{dataflow['id']},{dataflow['version']}?"
                    + urllib.parse.urlencode({"startPeriod": year, "endPeriod": year, "format": "SDMX-CSV"}))
        body = _read(endpoint, token=token, limit=MAX_DATA_BYTES, monitor=monitor)
        try:
            text = body.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames or not {"TIME_PERIOD", "OBS_VALUE"}.issubset(reader.fieldnames):
                raise TuikError("TÜİK yanıtında beklenen SDMX-CSV kolonları yok.")
            rows = [
                {str(key).strip(): (value or "").strip() for key, value in row.items() if key}
                for row in reader
                if row and any(value for value in row.values())
            ]
        except (UnicodeDecodeError, csv.Error):
            raise TuikError("TÜİK yanıtı SDMX-CSV olarak okunamadı.") from None
        if not rows:
            raise TuikError(f"{year} yılı için TÜİK yanıtında gözlem bulunamadı.")
        if any(record["TIME_PERIOD"].split("-", 1)[0] != str(year) for record in rows):
            raise TuikError("TÜİK yanıtında seçilen yılın dışında gözlem var.")
        if len(rows) > 250000:
            raise TuikError("TÜİK yanıtı tek iş için izin verilen gözlem sayısını aştı.")

        city_map = {}
        warnings = []
        is_population = dataflow["id"] == POPULATION_FLOW and dataflow["version"] == POPULATION_VERSION
        if is_population:
            try:
                city_map = _city_codes(token, conn, monitor)
            except (TuikError, ET.ParseError, OSError):
                warnings.append("İl eşlemesi alınamadı; kayıtlar ham katmanda tutuldu.")

        digest = hashlib.sha256(body).hexdigest()
        captured_at = datetime.now(timezone.utc)
        staged_count = 0
        unmatched_codes = set()
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO raw.api_responses
                       (ingestion_run_id, endpoint, method, captured_at, source_hash_sha256, http_status, payload)
                       VALUES (%s,%s,'GET',%s,%s,200,%s)
                       ON CONFLICT DO NOTHING RETURNING api_response_id""",
                    (run_id, endpoint, captured_at, digest,
                     Jsonb({"format": "SDMX-CSV", "dataflow": dataflow["id"],
                            "version": dataflow["version"], "year": year, "body": text})),
                )
                inserted = cur.fetchone()
                if inserted:
                    response_id = inserted[0]
                    source_records = []
                    for index, record in enumerate(rows):
                        if monitor and index % 100 == 0:
                            if monitor.should_stop():
                                raise KeyboardInterrupt
                            monitor.progress(index, len(rows), "TÜİK: RAW kayıtları")
                        record_hash = hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False,
                                                                 separators=(",", ":")).encode()).hexdigest()
                        cur.execute(
                            """INSERT INTO raw.source_records
                               (api_response_id, source_entity, source_array_index, record, record_hash_sha256)
                               VALUES (%s,%s,%s,%s,%s) RETURNING source_record_id""",
                            (response_id, f"tuik_{dataflow['id'].lower()}", index, Jsonb(record), record_hash),
                        )
                        source_records.append((cur.fetchone()[0], record))
                else:
                    cur.execute("SELECT api_response_id FROM raw.api_responses WHERE endpoint=%s AND source_hash_sha256=%s",
                                (endpoint, digest))
                    existing = cur.fetchone()
                    if not existing:
                        raise TuikError("Aynı TÜİK yanıtı bulunamadı; RAW bütünlüğü doğrulanamadı.")
                    response_id = existing[0]
                    cur.execute("SELECT source_record_id, record FROM raw.source_records WHERE api_response_id=%s ORDER BY source_array_index",
                                (response_id,))
                    source_records = cur.fetchall()
                    if len(source_records) != len(rows):
                        raise TuikError("Önceki RAW yanıt eksik; üzerine yazma durduruldu.")

                if is_population and city_map:
                    for index, (source_record_id, record) in enumerate(source_records):
                        if monitor and index % 100 == 0:
                            if monitor.should_stop():
                                raise KeyboardInterrupt
                            monitor.progress(index, len(source_records), "TÜİK: il eşlemesi")
                        geo_code = record.get("IKAMET_YERI", "")
                        if geo_code == "_T":
                            continue
                        city_id = city_map.get(geo_code)
                        if city_id is None:
                            unmatched_codes.add(geo_code)
                            continue
                        try:
                            row_year = int(record["TIME_PERIOD"])
                            population = int(record["OBS_VALUE"])
                            age_code = record.get("YAS_GRUBU", "_T")
                            sex_code = record.get("SEX", "_T")
                        except (KeyError, ValueError, OverflowError):
                            warnings.append("Bazı gözlemler staging alanlarına dönüştürülemedi.")
                            continue
                        cur.execute(
                            """INSERT INTO staging.tuik_population_by_province
                               (source_record_id, il_kodu, yil, yas_grubu_kodu, yas_grubu,
                                cinsiyet_kodu, cinsiyet, nufus, tuik_ikamet_kodu,
                                source_dataflow, source_version, source_payload)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                               ON CONFLICT (source_record_id) DO NOTHING""",
                            (source_record_id, city_id, row_year, age_code, _age_label(age_code),
                             sex_code, _sex_label(sex_code), population, geo_code,
                             dataflow["id"], dataflow["version"], Jsonb(record)),
                        )
                        staged_count += cur.rowcount

                normalization = "typed" if is_population and city_map else "raw_only"
                if is_population and city_map:
                    cur.execute(
                        """SELECT count(*) FROM staging.tuik_population_by_province s
                           JOIN raw.source_records r USING (source_record_id)
                           WHERE r.api_response_id=%s""",
                        (response_id,),
                    )
                    staged_count = cur.fetchone()[0]
                if unmatched_codes:
                    warnings.append(f"İl eşleşmesi bulunmayan kod sayısı: {len(unmatched_codes)}.")
                    normalization = "partial"
                details = {
                    "bot_id": BOT_ID,
                    "dataflow_id": dataflow["id"],
                    "dataflow_version": dataflow["version"],
                    "dataflow_title": dataflow["title"],
                    "category_id": dataflow["category_id"],
                    "year": year,
                    "endpoint": endpoint,
                    "captured_at": captured_at.isoformat(),
                    "response_sha256": digest,
                    "response_id": response_id,
                    "records": len(rows),
                    "staged_records": staged_count,
                    "normalization": normalization,
                    "warnings": warnings,
                    "unmatched_geo_codes": sorted(unmatched_codes),
                }
                status = "completed_with_issues" if warnings or normalization == "partial" else "completed"
                cur.execute("UPDATE raw.ingestion_runs SET status=%s, completed_at=now(), details=%s WHERE ingestion_run_id=%s",
                            (status, Jsonb(details), run_id))
        if monitor:
            monitor.records(len(rows) if inserted else 0)
            monitor.progress(len(rows), len(rows), "TÜİK: tamamlandı")
            monitor.summary(ingestion_run_id=run_id, records=len(rows), staged_records=staged_count,
                            normalization=normalization, warnings=warnings)
            for warning in warnings:
                monitor.warning(warning)
    except KeyboardInterrupt:
        if conn and not conn.closed:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("UPDATE raw.ingestion_runs SET status='stopped', completed_at=now() WHERE ingestion_run_id=%s",
                            (run_id,))
        raise
    except Exception as exc:
        message = exc.args[0] if isinstance(exc, TuikError) and exc.args else "İş sırasında beklenmeyen hata."
        if conn:
            try:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute("UPDATE raw.ingestion_runs SET status='failed', completed_at=now(), details=details || %s WHERE ingestion_run_id=%s",
                                (Jsonb({"message": str(message)[:300], "error_type": type(exc).__name__}), run_id))
            except psycopg.Error:
                pass
    finally:
        if conn:
            try:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_unlock(hashtext('tuik_sdmx_manual_ingestion'))")
                conn.close()
            except psycopg.Error:
                pass
