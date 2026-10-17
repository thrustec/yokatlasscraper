"""botkit: botların admin paneliyle konuşması için küçük yardımcı.

Kullanım (bir botun içinde):

    from botkit import Bot

    with Bot.from_env() as bot:
        delay = bot.settings.get("delay_seconds", 1.5)
        sayfalar = list(range(1, 286))
        for i, sayfa in enumerate(sayfalar, 1):
            if bot.should_stop():
                break
            bot.progress(i, len(sayfalar), "TYT sayfaları")
            try:
                veri = indir(sayfa)
                bot.request_ok()
                bot.records(kaydet(veri))
            except Exception as e:
                bot.request_failed(f"tyt:{sayfa}", url=..., error=str(e))
            bot.sleep(delay)

Panel çalıştırırken ADMIN_RUN_ID ve ADMIN_DATABASE_URL ortam değişkenleri gelir.
Bot elle (terminalden) çalıştırılırsa bu değişkenler yoktur; botkit o zaman
sadece ekrana yazar, veritabanına bir şey yazmaz. Böylece bot panel olmadan da denenebilir.

Loglar: bot.log / bot.warning / bot.error ya da düz print() kullanın. Çalıştırıcı
botun çıktısını satır satır panele aktarır. Satır "WARNING:" / "ERROR:" ile başlarsa
o seviyede görünür.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from typing import Any

__all__ = ["Bot"]

HEARTBEAT_SECONDS = 5


class Bot:
    def __init__(self, run_id: int | None, database_url: str | None, slug: str, settings: dict):
        self.run_id = run_id
        self.slug = slug
        self.settings: dict[str, Any] = settings
        self.ingestion_run_id: int | None = None
        self.retry_requests: list[dict] = []
        self._db_url = database_url if run_id else None
        self._conn = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._done = threading.Event()
        self._dirty = False
        self._progress: tuple[int | None, int | None, str | None] = (None, None, None)
        self._c = dict(pages_requested=0, pages_ok=0, pages_failed=0,
                       records_written=0, warnings=0, errors=0)
        self._summary: dict[str, Any] = {}
        self._hb: threading.Thread | None = None

    # ------------------------------------------------------------------ kurulum
    @classmethod
    def from_env(cls) -> "Bot":
        run_id = os.environ.get("ADMIN_RUN_ID")
        settings = {}
        if os.environ.get("BOT_SETTINGS"):
            try:
                settings = json.loads(os.environ["BOT_SETTINGS"])
            except json.JSONDecodeError:
                print("WARNING: BOT_SETTINGS okunamadı, varsayılan ayarlar kullanılıyor", flush=True)
        return cls(
            int(run_id) if run_id else None,
            os.environ.get("ADMIN_DATABASE_URL") or os.environ.get("DATABASE_URL"),
            os.environ.get("BOT_SLUG", os.path.basename(sys.argv[0]).removesuffix(".py")),
            settings,
        )

    @property
    def connected(self) -> bool:
        return self._conn is not None

    def __enter__(self) -> "Bot":
        try:
            signal.signal(signal.SIGTERM, self._on_sigterm)
        except ValueError:  # ana iş parçacığı değilse
            pass
        if self.run_id and self._db_url:
            import psycopg
            from psycopg.rows import dict_row

            self._conn = psycopg.connect(self._db_url, autocommit=True, row_factory=dict_row)
            self._open_ingestion_run()
            self._load_retry_requests()
            self._hb = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._hb.start()
        self.log(f"Bot başladı: {self.slug}" + (f" (çalışma #{self.run_id})" if self.run_id else " (panel dışı)"))
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc is not None and not isinstance(exc, (KeyboardInterrupt, SystemExit)):
            self.error(f"Beklenmeyen hata: {exc_type.__name__}: {exc}")
        stopped = self._stop.is_set()
        ok = exc is None and not stopped
        status = "completed" if ok else ("stopped" if stopped else "failed")
        self.log(f"Bot bitti: {status}. Kayıt: {self._c['records_written']}, "
                 f"başarılı istek: {self._c['pages_ok']}, başarısız: {self._c['pages_failed']}")
        self._done.set()
        if self._hb:
            self._hb.join(timeout=HEARTBEAT_SECONDS + 2)
        if self._conn:
            self._flush()
            self._close_ingestion_run(status)
            self._conn.close()
        return False  # hata varsa yukarı fırlasın; çıkış kodu 1 olsun

    # ------------------------------------------------------------------ loglar
    def _print(self, level: str, msg: str) -> None:
        prefix = "" if level == "INFO" else level + ": "
        print(prefix + str(msg), flush=True)

    def log(self, msg: str) -> None:
        self._print("INFO", msg)

    def debug(self, msg: str) -> None:
        self._print("DEBUG", msg)

    def warning(self, msg: str) -> None:
        with self._lock:
            self._c["warnings"] += 1
            self._dirty = True
        self._print("WARNING", msg)

    def error(self, msg: str) -> None:
        with self._lock:
            self._c["errors"] += 1
            self._dirty = True
        self._print("ERROR", msg)

    # ------------------------------------------------------------------ sayaçlar
    def progress(self, current: int, total: int | None = None, label: str | None = None) -> None:
        with self._lock:
            self._progress = (current, total, label)
            self._dirty = True

    def request_ok(self, failed_id: int | None = None) -> None:
        """Bir istek başarılı. Yeniden deneme çalışmasında failed_id verilirse o hata kapanır."""
        with self._lock:
            self._c["pages_requested"] += 1
            self._c["pages_ok"] += 1
            self._dirty = True
        if failed_id and self._conn:
            self._exec("UPDATE ops.failed_requests SET resolved_at=now(), resolved_by_run_id=%s "
                       "WHERE failed_id=%s", (self.run_id, failed_id))

    def request_failed(self, request_key: str, *, url: str | None = None, params: dict | None = None,
                       http_status: int | None = None, error: str | None = None,
                       failed_id: int | None = None) -> None:
        """Bir istek başarısız. request_key, botun daha sonra yeniden denemek için anlayacağı
        bir anahtardır (ör. "netler:SAY:12")."""
        with self._lock:
            self._c["pages_requested"] += 1
            self._c["pages_failed"] += 1
            self._dirty = True
        self._print("WARNING", f"İstek başarısız: {request_key} "
                    f"{'HTTP ' + str(http_status) if http_status else ''} {error or ''}".rstrip())
        if not self._conn:
            return
        from psycopg.types.json import Jsonb

        if failed_id:
            self._exec("UPDATE ops.failed_requests SET attempts=attempts+1, http_status=%s, error=%s "
                       "WHERE failed_id=%s", (http_status, error, failed_id))
        else:
            self._exec(
                "INSERT INTO ops.failed_requests(run_id, bot_id, request_key, url, params, http_status, error) "
                "SELECT %s, bot_id, %s, %s, %s, %s, %s FROM ops.runs WHERE run_id=%s",
                (self.run_id, request_key, url, Jsonb(params or {}), http_status, error, self.run_id))

    def records(self, n: int = 1) -> None:
        with self._lock:
            self._c["records_written"] += int(n)
            self._dirty = True

    def summary(self, **values) -> None:
        """Çalışma özetine serbest bilgi ekler (panelde çalışma ayrıntısında görünür)."""
        with self._lock:
            self._summary.update(values)
            self._dirty = True

    # ------------------------------------------------------------------ kalite
    def check(self, name: str, passed: bool | str, observed: Any = None) -> None:
        """quality.data_quality_checks tablosuna bir kontrol sonucu yazar.
        passed: True/False ya da 'pass' / 'warn' / 'fail'."""
        status = passed if isinstance(passed, str) else ("pass" if passed else "fail")
        level = {"pass": "INFO", "warn": "WARNING", "fail": "ERROR"}.get(status, "INFO")
        self._print(level, f"Kalite kontrolü [{status}] {name}: {observed}")
        if status == "warn":
            with self._lock:
                self._c["warnings"] += 1
        if self._conn:
            from psycopg.types.json import Jsonb

            self._exec("INSERT INTO quality.data_quality_checks(ingestion_run_id, check_name, status, observed_value) "
                       "VALUES (%s,%s,%s,%s)", (self.ingestion_run_id, name, status, Jsonb(observed)))

    def quarantine(self, entity: str, reason: str, natural_key: Any = None,
                   candidate_payloads: list | None = None) -> None:
        self._print("WARNING", f"Karantina: {entity} — {reason}")
        if self._conn:
            from psycopg.types.json import Jsonb

            self._exec("INSERT INTO quality.quarantined_records(ingestion_run_id, entity, reason, natural_key, "
                       "candidate_payloads) VALUES (%s,%s,%s,%s,%s)",
                       (self.ingestion_run_id, entity, reason, Jsonb(natural_key),
                        Jsonb(candidate_payloads or [])))

    # ------------------------------------------------------------------ durdurma
    def should_stop(self) -> bool:
        return self._stop.is_set()

    def sleep(self, seconds: float) -> None:
        """Durdurma isteği gelirse hemen uyanan bekleme."""
        self._stop.wait(max(0.0, float(seconds)))

    def _on_sigterm(self, signum, frame):
        if not self._stop.is_set():
            self._print("WARNING", "Durdurma isteği alındı, bot güvenli şekilde duruyor")
        self._stop.set()

    # ------------------------------------------------------------------ veritabanı
    def _exec(self, sql, params=None):
        with self._lock:
            return self._conn.execute(sql, params)

    def _open_ingestion_run(self):
        from psycopg.types.json import Jsonb

        row = self._exec(
            "INSERT INTO raw.ingestion_runs(source_system, status, scraper_version, details) "
            "VALUES (%s,'running',%s,%s) RETURNING ingestion_run_id",
            (self.slug, os.environ.get("BOT_VERSION") or self.settings.get("version"),
             Jsonb({"admin_run_id": self.run_id}))).fetchone()
        self.ingestion_run_id = row["ingestion_run_id"]
        self._exec("UPDATE ops.runs SET ingestion_run_id=%s WHERE run_id=%s", (self.ingestion_run_id, self.run_id))

    def _close_ingestion_run(self, status):
        from psycopg.types.json import Jsonb

        details = {"admin_run_id": self.run_id, **self._c, **self._summary}
        self._exec("UPDATE raw.ingestion_runs SET completed_at=now(), status=%s, details=%s "
                   "WHERE ingestion_run_id=%s", (status, Jsonb(details), self.ingestion_run_id))

    def _load_retry_requests(self):
        rows = self._exec(
            "SELECT f.failed_id, f.request_key, f.url, f.params, f.attempts FROM ops.failed_requests f "
            "JOIN ops.runs r ON r.run_id=%s "
            "WHERE r.trigger='retry' AND f.bot_id=r.bot_id AND f.resolved_at IS NULL "
            "ORDER BY f.failed_id", (self.run_id,)).fetchall()
        self.retry_requests = rows
        if rows:
            self.log(f"Yeniden denenecek {len(rows)} başarısız istek var")

    def _flush(self):
        from psycopg.types.json import Jsonb

        with self._lock:
            c = dict(self._c)
            cur, tot, label = self._progress
            summary = dict(self._summary)
            self._dirty = False
        self._exec(
            "UPDATE ops.runs SET heartbeat_at=now(), progress_current=%s, progress_total=%s, progress_label=%s, "
            "pages_requested=%s, pages_ok=%s, pages_failed=%s, records_written=%s, warnings=%s, errors=%s, "
            "summary=summary || %s WHERE run_id=%s",
            (cur, tot, label, c["pages_requested"], c["pages_ok"], c["pages_failed"], c["records_written"],
             c["warnings"], c["errors"], Jsonb(summary), self.run_id))

    def _heartbeat_loop(self):
        while not self._done.wait(HEARTBEAT_SECONDS):
            try:
                self._flush()
                row = self._exec("SELECT stop_requested FROM ops.runs WHERE run_id=%s", (self.run_id,)).fetchone()
                if row and row["stop_requested"] and not self._stop.is_set():
                    self._print("WARNING", "Panelden durdurma isteği geldi")
                    self._stop.set()
            except Exception as e:  # bağlantı koparsa botu öldürmeyelim
                print(f"WARNING: panel bağlantısı hatası: {e}", flush=True)
