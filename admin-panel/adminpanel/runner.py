"""Çalıştırıcı (runner): sunucuda sürekli açık durur.

- Zamanı gelen botlar için çalışma kuyruğa ekler (cron).
- Kuyruktaki çalışmaları başlatır (aynı anda en fazla ADMIN_MAX_PARALLEL_RUNS).
- Botun çıktısını satır satır ops.run_logs tablosuna yazar.
- Panelden gelen durdurma isteklerini ve zaman aşımlarını uygular.
- E-posta bildirim kurallarını kontrol eder.

Çalıştırma:  python -m adminpanel.runner
"""
from __future__ import annotations

import json
import logging
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from croniter import croniter

from . import alerts, config, db

log = logging.getLogger("runner")
VERSION = "1.0"
TZ = ZoneInfo(os.environ.get("ADMIN_TIMEZONE", "Europe/Istanbul"))
STOP_GRACE_SECONDS = 30
LEVEL_RE = re.compile(r"^\s*(?:\[?)(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)(?:\]?)\s*[:\-]?\s*", re.I)
LEVEL_MAP = {"debug": "debug", "info": "info", "warning": "warning", "warn": "warning",
             "error": "error", "critical": "error"}
PANEL_DIR = Path(__file__).resolve().parents[1]  # botkit buradan import edilir


@dataclass
class Proc:
    run_id: int
    bot_id: int
    popen: subprocess.Popen
    timeout_at: float
    readers: list = field(default_factory=list)
    term_sent_at: float | None = None
    reason: str | None = None  # 'stopped' | 'timed_out'
    last_error: str | None = None


class Runner:
    def __init__(self):
        self.name = os.environ.get("ADMIN_RUNNER_NAME", "main")
        self.procs: dict[int, Proc] = {}
        self.last_cron_check: dict[int, datetime] = {}
        self.last_alert_check = 0.0
        self.stopping = False

    # ------------------------------------------------------------ yaşam döngüsü
    def start(self):
        db.migrate()  # web henüz başlamadıysa ops şeması burada kurulur
        db.run(
            "INSERT INTO ops.runner_status(runner_name, heartbeat_at, started_at, hostname, version) "
            "VALUES (%s, now(), now(), %s, %s) ON CONFLICT (runner_name) DO UPDATE SET "
            "heartbeat_at=now(), started_at=now(), hostname=excluded.hostname, version=excluded.version",
            (self.name, socket.gethostname(), VERSION))
        n = db.run(
            "UPDATE ops.runs SET status='failed', finished_at=now(), "
            "error_message='Çalıştırıcı yeniden başlatıldı; çalışma yarıda kaldı' WHERE status='running'")
        if n:
            log.warning("%s yarım kalmış çalışma 'hata' olarak işaretlendi", n)
        log.info("Çalıştırıcı başladı (repo: %s, paralel: %s)", config.REPO_DIR, config.MAX_PARALLEL_RUNS)

    def loop(self):
        self.start()
        signal.signal(signal.SIGTERM, self._on_term)
        signal.signal(signal.SIGINT, self._on_term)
        while not self.stopping:
            try:
                self.tick()
            except Exception:
                log.exception("Çalıştırıcı adımında hata")
            time.sleep(config.RUNNER_TICK_SECONDS)
        self.shutdown()

    def _on_term(self, *_):
        self.stopping = True

    def shutdown(self):
        log.info("Çalıştırıcı kapanıyor; çalışan botlar durduruluyor")
        for p in self.procs.values():
            p.reason = p.reason or "stopped"
            self._signal(p, signal.SIGTERM)
        deadline = time.monotonic() + 20
        while self.procs and time.monotonic() < deadline:
            self.supervise()
            time.sleep(0.5)
        for p in list(self.procs.values()):
            self._signal(p, signal.SIGKILL)
        self.supervise()

    def tick(self):
        db.run("UPDATE ops.runner_status SET heartbeat_at=now() WHERE runner_name=%s", (self.name,))
        self.schedule()
        self.start_queued()
        self.supervise()
        if time.monotonic() - self.last_alert_check > 30:
            self.last_alert_check = time.monotonic()
            try:
                alerts.check_all()
            except Exception:
                log.exception("Bildirim kontrolünde hata")

    # ------------------------------------------------------------ zamanlama
    def schedule(self):
        now = datetime.now(TZ)
        bots = db.all("SELECT bot_id, slug, schedule_cron FROM ops.bots WHERE enabled AND schedule_cron IS NOT NULL")
        seen = set()
        for b in bots:
            seen.add(b["bot_id"])
            last = self.last_cron_check.get(b["bot_id"])
            if last is None:
                self.last_cron_check[b["bot_id"]] = now
                continue
            try:
                nxt = croniter(b["schedule_cron"], last).get_next(datetime)
            except Exception:
                continue
            if nxt <= now:
                self.last_cron_check[b["bot_id"]] = now
                row = db.one(
                    "INSERT INTO ops.runs(bot_id, trigger) VALUES (%s, 'schedule') "
                    "ON CONFLICT (bot_id) WHERE status IN ('queued','running') DO NOTHING RETURNING run_id",
                    (b["bot_id"],))
                if row:
                    log.info("Planlı çalışma kuyruğa eklendi: %s (#%s)", b["slug"], row["run_id"])
                else:
                    log.info("%s zaten çalışıyor; planlı çalışma atlandı", b["slug"])
        for k in list(self.last_cron_check):
            if k not in seen:
                del self.last_cron_check[k]

    # ------------------------------------------------------------ başlatma
    def start_queued(self):
        # Kuyruktayken durdurulanlar
        db.run("UPDATE ops.runs SET status='stopped', finished_at=now() WHERE status='queued' AND stop_requested")
        free = config.MAX_PARALLEL_RUNS - len(self.procs)
        if free <= 0:
            return
        rows = db.all(
            "SELECT r.run_id, r.trigger, b.bot_id, b.slug, b.command, b.working_dir, b.settings, b.timeout_minutes, "
            "b.enabled FROM ops.runs r JOIN ops.bots b USING (bot_id) "
            "WHERE r.status='queued' ORDER BY r.queued_at LIMIT %s", (free,))
        for r in rows:
            self._launch(r)

    def _launch(self, r: dict):
        run_id = r["run_id"]
        cwd = (config.REPO_DIR / (r["working_dir"] or ".")).resolve()
        env = dict(os.environ)
        env.update({
            "ADMIN_RUN_ID": str(run_id),
            "ADMIN_DATABASE_URL": config.DATABASE_URL,
            "BOT_SLUG": r["slug"],
            "BOT_SETTINGS": json.dumps(r["settings"] or {}, ensure_ascii=False),
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": os.pathsep.join(
                p for p in [str(PANEL_DIR), str(config.REPO_DIR), env.get("PYTHONPATH", "")] if p),
        })
        try:
            args = shlex.split(r["command"])
            if args and args[0] in ("python", "python3"):
                args[0] = sys.executable
            popen = subprocess.Popen(
                args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                start_new_session=True,
            )
        except Exception as e:
            log.error("Bot başlatılamadı (%s): %s", r["slug"], e)
            db.run("UPDATE ops.runs SET status='failed', started_at=now(), finished_at=now(), error_message=%s "
                   "WHERE run_id=%s", (f"Bot başlatılamadı: {e}", run_id))
            self._log(run_id, "error", f"Bot başlatılamadı: {e}  (komut: {r['command']}, klasör: {cwd})")
            return
        db.run("UPDATE ops.runs SET status='running', started_at=now(), heartbeat_at=now(), pid=%s WHERE run_id=%s",
               (popen.pid, run_id))
        p = Proc(run_id, r["bot_id"], popen, time.monotonic() + r["timeout_minutes"] * 60)
        trig = {"manual": "elle", "schedule": "zamanlayıcı", "retry": "yeniden deneme"}.get(r["trigger"], r["trigger"])
        self._log(run_id, "info", f"Çalıştırıcı botu başlattı ({trig}): {r['command']}  [pid {popen.pid}]")
        for stream, default in ((popen.stdout, "info"), (popen.stderr, "error")):
            t = threading.Thread(target=self._reader, args=(p, stream, default), daemon=True)
            t.start()
            p.readers.append(t)
        self.procs[run_id] = p
        log.info("Başladı: %s (#%s, pid %s)", r["slug"], run_id, popen.pid)

    def _reader(self, p: Proc, stream, default_level: str):
        last_hb = 0.0
        for line in iter(stream.readline, ""):
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            level = default_level
            m = LEVEL_RE.match(line)
            if m:
                level = LEVEL_MAP[m.group(1).lower()]
                line = line[m.end():] or line
            elif default_level == "error" and not line.startswith(("Traceback", "  ")) and "Error" not in line:
                # stderr'e yazılan ama hata olmayan satırlar (ör. ilerleme çubukları)
                level = "warning"
            if level == "error":
                p.last_error = line[:500]
            try:
                self._log(p.run_id, level, line[:4000])
                if time.monotonic() - last_hb > 5:
                    last_hb = time.monotonic()
                    db.run("UPDATE ops.runs SET heartbeat_at=now() WHERE run_id=%s AND status='running'", (p.run_id,))
            except Exception:
                log.exception("Log yazılamadı")
        stream.close()

    @staticmethod
    def _log(run_id: int, level: str, message: str):
        db.run("INSERT INTO ops.run_logs(run_id, level, message) VALUES (%s,%s,%s)", (run_id, level, message))

    # ------------------------------------------------------------ izleme
    def _signal(self, p: Proc, sig):
        try:
            os.killpg(p.popen.pid, sig)
        except ProcessLookupError:
            pass
        if sig == signal.SIGTERM and p.term_sent_at is None:
            p.term_sent_at = time.monotonic()

    def supervise(self):
        if not self.procs:
            return
        ids = list(self.procs)
        stop_rows = db.all("SELECT run_id FROM ops.runs WHERE run_id = ANY(%s) AND stop_requested", (ids,))
        for row in stop_rows:
            p = self.procs[row["run_id"]]
            if p.term_sent_at is None:
                p.reason = "stopped"
                self._log(p.run_id, "warning", "Panelden durduruldu; bota durma sinyali gönderildi")
                self._signal(p, signal.SIGTERM)
        now = time.monotonic()
        for p in list(self.procs.values()):
            if p.term_sent_at is None and now > p.timeout_at:
                p.reason = "timed_out"
                self._log(p.run_id, "error", "Zaman aşımı: bot izin verilen süreyi aştı, durduruluyor")
                self._signal(p, signal.SIGTERM)
            if p.term_sent_at is not None and now - p.term_sent_at > STOP_GRACE_SECONDS and p.popen.poll() is None:
                self._log(p.run_id, "warning", f"Bot {STOP_GRACE_SECONDS} saniyede durmadı, zorla kapatılıyor")
                self._signal(p, signal.SIGKILL)
            rc = p.popen.poll()
            if rc is None:
                continue
            for t in p.readers:
                t.join(timeout=5)
            if p.reason == "stopped":
                status, err = "stopped", None
            elif p.reason == "timed_out":
                status, err = "timed_out", "Zaman aşımı"
            elif rc == 0:
                status, err = "succeeded", None
            else:
                status, err = "failed", p.last_error or f"Bot {rc} çıkış koduyla bitti"
            db.run("UPDATE ops.runs SET status=%s, finished_at=now(), exit_code=%s, "
                   "error_message=coalesce(%s, error_message), heartbeat_at=now() WHERE run_id=%s",
                   (status, rc, err, p.run_id))
            # botkit kullanmayan botlar için ham çalışma kaydı da kapansın
            db.run("UPDATE raw.ingestion_runs SET status=%s, completed_at=coalesce(completed_at, now()) "
                   "WHERE ingestion_run_id=(SELECT ingestion_run_id FROM ops.runs WHERE run_id=%s) AND status='running'",
                   ({"succeeded": "completed"}.get(status, status), p.run_id))
            self._log(p.run_id, "info" if status == "succeeded" else "warning",
                      f"Çalışma bitti: {status} (çıkış kodu {rc})")
            log.info("Bitti: #%s %s (rc=%s)", p.run_id, status, rc)
            del self.procs[p.run_id]


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    Runner().loop()


if __name__ == "__main__":
    main()
