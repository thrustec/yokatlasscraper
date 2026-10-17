"""Admin paneli web sunucusu: JSON API + panel arayüzü.

Çalıştırma:  uvicorn adminpanel.web:app --host 127.0.0.1 --port 8090
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from croniter import croniter
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg import errors as pg_errors
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, field_validator

from . import alerts, config, db, health, mailer, security
from .runner import TZ

COOKIE = "unirota_session"
app = FastAPI(title="ÜniRota admin paneli", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


@app.on_event("startup")
def _migrate_on_startup():
    # ops şeması yoksa kurar; varsa dokunmaz (bütün komutlar IF NOT EXISTS).
    db.migrate()


# ---------------------------------------------------------------- güvenlik
@app.middleware("http")
async def csrf_and_headers(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.headers.get("x-requested-with") != "unirota":
            return JSONResponse({"detail": "Geçersiz istek"}, status_code=403)
    resp = await call_next(request)
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


def current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Giriş yapın")
    u = db.one(
        "SELECT u.user_id, u.username, u.full_name, u.email, u.receive_alerts FROM ops.sessions s "
        "JOIN ops.users u USING (user_id) WHERE s.token_hash=%s AND s.expires_at > now() AND u.is_active",
        (security.token_hash(token),))
    if not u:
        raise HTTPException(401, "Oturum süresi doldu, tekrar giriş yapın")
    return u


User = Depends(current_user)


def _set_session(resp: Response, user_id: int):
    token, th = security.new_session_token()
    db.run("INSERT INTO ops.sessions(token_hash, user_id, expires_at) VALUES (%s,%s, now() + make_interval(days => %s))",
           (th, user_id, config.SESSION_DAYS))
    db.run("DELETE FROM ops.sessions WHERE expires_at < now()")
    resp.set_cookie(COOKIE, token, httponly=True, samesite="strict", secure=config.COOKIE_SECURE,
                    max_age=config.SESSION_DAYS * 86400, path="/")


# ---------------------------------------------------------------- giriş
class LoginIn(BaseModel):
    username: str
    password: str


class SetupIn(BaseModel):
    username: str = Field(pattern=r"^[a-z0-9._-]{2,40}$")
    full_name: str = Field(min_length=2, max_length=80)
    email: str | None = None
    password: str = Field(min_length=10, max_length=200)


@app.get("/api/auth/state")
def auth_state():
    n = db.one("SELECT count(*) AS n FROM ops.users")["n"]
    return {"needs_setup": n == 0}


@app.post("/api/auth/setup")
def auth_setup(body: SetupIn, response: Response):
    """Hiç kullanıcı yokken ilk yöneticiyi oluşturur."""
    with db.conn() as c, c.transaction():
        c.execute("LOCK TABLE ops.users IN EXCLUSIVE MODE")
        if c.execute("SELECT count(*) AS n FROM ops.users").fetchone()["n"] > 0:
            raise HTTPException(409, "İlk kurulum zaten yapılmış")
        uid = c.execute(
            "INSERT INTO ops.users(username, full_name, email, password_hash) VALUES (%s,%s,%s,%s) RETURNING user_id",
            (body.username, body.full_name, body.email or None, security.hash_password(body.password))
        ).fetchone()["user_id"]
    db.audit(uid, "İlk kurulum: yönetici oluşturuldu", details={"username": body.username})
    _set_session(response, uid)
    return {"ok": True}


@app.post("/api/auth/login")
def login(body: LoginIn, response: Response):
    u = db.one("SELECT user_id, password_hash FROM ops.users WHERE username=%s AND is_active",
               (body.username.strip().lower(),))
    if not u or not security.verify_password(body.password, u["password_hash"]):
        raise HTTPException(401, "Kullanıcı adı ya da parola yanlış")
    db.run("UPDATE ops.users SET last_login_at=now() WHERE user_id=%s", (u["user_id"],))
    _set_session(response, u["user_id"])
    return {"ok": True}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        db.run("DELETE FROM ops.sessions WHERE token_hash=%s", (security.token_hash(token),))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@app.get("/api/me")
def me(user=User):
    return user


# ---------------------------------------------------------------- yardımcılar
def next_fire(cron: str | None) -> str | None:
    if not cron:
        return None
    try:
        return croniter(cron, datetime.now(TZ)).get_next(datetime).isoformat()
    except Exception:
        return None


BOT_SELECT = """
SELECT b.*, u.full_name AS owner_name, u.username AS owner_username,
       a.run_id AS active_run_id, a.status AS active_status, a.trigger AS active_trigger,
       a.started_at AS active_started_at, a.queued_at AS active_queued_at, a.heartbeat_at AS active_heartbeat_at,
       a.progress_current, a.progress_total, a.progress_label, a.records_written AS active_records,
       a.stop_requested AS active_stop_requested,
       l.run_id AS last_run_id, l.status AS last_status, l.started_at AS last_started_at,
       l.finished_at AS last_finished_at, l.records_written AS last_records, l.error_message AS last_error,
       l.pages_failed AS last_pages_failed,
       (SELECT max(finished_at) FROM ops.runs s WHERE s.bot_id=b.bot_id AND s.status='succeeded') AS last_success_at,
       (SELECT count(*) FROM ops.failed_requests f WHERE f.bot_id=b.bot_id AND f.resolved_at IS NULL) AS open_failed,
       (SELECT coalesce(json_agg(x ORDER BY x.run_id), '[]') FROM (
            SELECT run_id, status, records_written, extract(epoch FROM finished_at-started_at)::int AS seconds
            FROM ops.runs s WHERE s.bot_id=b.bot_id AND s.finished_at IS NOT NULL
            ORDER BY run_id DESC LIMIT 12) x) AS recent
FROM ops.bots b
LEFT JOIN ops.users u ON u.user_id=b.owner_user_id
LEFT JOIN LATERAL (SELECT * FROM ops.runs r WHERE r.bot_id=b.bot_id AND r.status IN ('queued','running')
                   ORDER BY run_id DESC LIMIT 1) a ON true
LEFT JOIN LATERAL (SELECT * FROM ops.runs r WHERE r.bot_id=b.bot_id AND r.finished_at IS NOT NULL
                   ORDER BY run_id DESC LIMIT 1) l ON true
"""


def bot_state(b: dict) -> str:
    if b["active_status"] == "running":
        return "running"
    if b["active_status"] == "queued":
        return "queued"
    if not b["enabled"]:
        return "off"
    if b["last_status"] in ("failed", "timed_out"):
        return "error"
    return "idle"


def decorate(b: dict) -> dict:
    b["state"] = bot_state(b)
    b["next_run_at"] = next_fire(b["schedule_cron"]) if b["enabled"] else None
    return b


def get_bot(bot_id: int) -> dict:
    b = db.one(BOT_SELECT + " WHERE b.bot_id=%s", (bot_id,))
    if not b:
        raise HTTPException(404, "Bot bulunamadı")
    return decorate(b)


# ---------------------------------------------------------------- genel bakış
@app.get("/api/overview")
def overview(user=User):
    bots = [decorate(b) for b in db.all(BOT_SELECT + " ORDER BY b.name")]
    events = db.all("""
        SELECT r.run_id, r.status, r.trigger, r.queued_at, r.started_at, r.finished_at, r.records_written,
               r.error_message, b.bot_id, b.name AS bot_name, u.full_name AS by_name,
               coalesce(r.finished_at, r.started_at, r.queued_at) AS ts
        FROM ops.runs r JOIN ops.bots b USING (bot_id) LEFT JOIN ops.users u ON u.user_id=r.triggered_by
        ORDER BY ts DESC LIMIT 12""")
    counts = db.one("""
        SELECT count(*) FILTER (WHERE status='running') AS running,
               count(*) FILTER (WHERE status IN ('failed','timed_out') AND finished_at > now()-interval '1 day') AS failed_24h,
               count(*) FILTER (WHERE status='succeeded' AND finished_at > now()-interval '1 day') AS ok_24h,
               coalesce(sum(records_written) FILTER (WHERE finished_at > now()-interval '1 day'),0) AS records_24h
        FROM ops.runs""")
    return {"bots": bots, "events": events, "counts": counts, "health": health.server()}


@app.get("/api/health")
def server_health(user=User):
    return health.server()


# ---------------------------------------------------------------- botlar
class BotIn(BaseModel):
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{1,40}$")
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    source_url: str | None = Field(default=None, max_length=500)
    owner_user_id: int | None = None
    command: str | None = Field(default=None, min_length=1, max_length=500)
    working_dir: str | None = Field(default=None, max_length=300)
    enabled: bool | None = None
    schedule_cron: str | None = None
    timeout_minutes: int | None = Field(default=None, ge=1, le=2880)
    settings: dict[str, Any] | None = None
    expected_min_records: int | None = Field(default=None, ge=0)

    @field_validator("schedule_cron")
    @classmethod
    def _cron(cls, v):
        if v is None or v.strip() == "":
            return ""
        v = " ".join(v.split())
        if not croniter.is_valid(v) or len(v.split()) != 5:
            raise ValueError("Zamanlama geçersiz. Örnek: '0 3 * * *' (her gece 03:00)")
        return v

    @field_validator("working_dir")
    @classmethod
    def _wd(cls, v):
        if v is None:
            return v
        v = v.strip() or "."
        if v.startswith("/") or ".." in v.split("/"):
            raise ValueError("Klasör repo içinde olmalı (ör. scraper)")
        return v


@app.get("/api/bots")
def list_bots(user=User):
    return [decorate(b) for b in db.all(BOT_SELECT + " ORDER BY b.name")]


@app.get("/api/bots/{bot_id}")
def bot_detail(bot_id: int, user=User):
    b = get_bot(bot_id)
    b["stats"] = db.one("""
        SELECT count(*) AS runs,
               count(*) FILTER (WHERE status='succeeded') AS ok,
               count(*) FILTER (WHERE status IN ('failed','timed_out')) AS failed,
               avg(extract(epoch FROM finished_at-started_at)) FILTER (WHERE status='succeeded') AS avg_seconds,
               coalesce(sum(records_written),0) AS records
        FROM ops.runs WHERE bot_id=%s""", (bot_id,))
    return b


@app.post("/api/bots")
def create_bot(body: BotIn, user=User):
    if not body.slug or not body.name or not body.command:
        raise HTTPException(422, "Kısa ad, bot adı ve çalıştırma komutu zorunlu")
    try:
        row = db.one(
            "INSERT INTO ops.bots(slug, name, description, source_url, owner_user_id, command, working_dir, enabled, "
            "schedule_cron, timeout_minutes, settings, expected_min_records) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING bot_id",
            (body.slug, body.name, body.description or "", body.source_url or None, body.owner_user_id,
             body.command, body.working_dir or ".", True if body.enabled is None else body.enabled,
             body.schedule_cron or None, body.timeout_minutes or 180, Jsonb(body.settings or {}),
             body.expected_min_records))
    except pg_errors.UniqueViolation:
        raise HTTPException(409, f"'{body.slug}' kısa adıyla bir bot zaten var")
    db.audit(user["user_id"], "Yeni bot ekledi", row["bot_id"], {"slug": body.slug, "command": body.command})
    return get_bot(row["bot_id"])


@app.patch("/api/bots/{bot_id}")
def update_bot(bot_id: int, body: BotIn, user=User):
    before = get_bot(bot_id)
    data = body.model_dump(exclude_unset=True)
    data.pop("slug", None)
    if not data:
        return before
    sets, params = [], []
    for k, v in data.items():
        if k == "settings":
            v = Jsonb(v or {})
        if k == "schedule_cron":
            v = v or None
        sets.append(f"{k}=%s")
        params.append(v)
    db.run(f"UPDATE ops.bots SET {', '.join(sets)}, updated_at=now() WHERE bot_id=%s", (*params, bot_id))
    changes = {k: {"önce": before.get(k), "sonra": data[k]} for k in data if before.get(k) != data[k]}
    if "enabled" in changes and len(changes) == 1:
        action = "Botu açtı" if data["enabled"] else "Botu kapattı"
    else:
        action = "Bot ayarlarını değiştirdi"
    if changes:
        db.audit(user["user_id"], action, bot_id, {"değişenler": changes})
    return get_bot(bot_id)


class DeleteIn(BaseModel):
    confirm_slug: str


@app.delete("/api/bots/{bot_id}")
def delete_bot(bot_id: int, body: DeleteIn, user=User):
    b = get_bot(bot_id)
    if body.confirm_slug != b["slug"]:
        raise HTTPException(400, "Onay için botun kısa adını doğru yazın")
    if b["active_run_id"]:
        raise HTTPException(409, "Bot çalışırken silinemez; önce durdurun")
    db.audit(user["user_id"], "Botu sildi", None, {"slug": b["slug"], "name": b["name"]})
    db.run("DELETE FROM ops.bots WHERE bot_id=%s", (bot_id,))
    return {"ok": True}


def _enqueue(bot_id: int, trigger: str, user: dict) -> dict:
    b = get_bot(bot_id)
    if not b["enabled"]:
        raise HTTPException(409, "Bot kapalı. Çalıştırmak için önce botu açın.")
    row = db.one(
        "INSERT INTO ops.runs(bot_id, trigger, triggered_by) VALUES (%s,%s,%s) "
        "ON CONFLICT (bot_id) WHERE status IN ('queued','running') DO NOTHING RETURNING run_id",
        (bot_id, trigger, user["user_id"]))
    if not row:
        raise HTTPException(409, "Bu bot zaten çalışıyor ya da sırada bekliyor")
    return row


@app.post("/api/bots/{bot_id}/run")
def run_bot(bot_id: int, user=User):
    row = _enqueue(bot_id, "manual", user)
    db.audit(user["user_id"], "Botu başlattı", bot_id, {"run_id": row["run_id"]})
    return {"run_id": row["run_id"]}


@app.post("/api/bots/{bot_id}/retry")
def retry_failed(bot_id: int, user=User):
    n = db.one("SELECT count(*) AS n FROM ops.failed_requests WHERE bot_id=%s AND resolved_at IS NULL", (bot_id,))["n"]
    if n == 0:
        raise HTTPException(409, "Yeniden denenecek başarısız istek yok")
    row = _enqueue(bot_id, "retry", user)
    db.audit(user["user_id"], "Başarısız istekleri yeniden denetti", bot_id, {"run_id": row["run_id"], "adet": n})
    return {"run_id": row["run_id"], "count": n}


@app.post("/api/bots/{bot_id}/stop")
def stop_bot(bot_id: int, user=User):
    row = db.one("UPDATE ops.runs SET stop_requested=true WHERE bot_id=%s AND status IN ('queued','running') "
                 "RETURNING run_id, status", (bot_id,))
    if not row:
        raise HTTPException(409, "Bot şu an çalışmıyor")
    if row["status"] == "queued":
        db.run("UPDATE ops.runs SET status='stopped', finished_at=now() WHERE run_id=%s AND status='queued'",
               (row["run_id"],))
    db.audit(user["user_id"], "Botu durdurdu", bot_id, {"run_id": row["run_id"]})
    return {"run_id": row["run_id"]}


@app.get("/api/bots/{bot_id}/runs")
def bot_runs(bot_id: int, limit: int = 50, user=User):
    return db.all("""
        SELECT r.*, u.full_name AS by_name, extract(epoch FROM coalesce(r.finished_at, now())-r.started_at)::int AS seconds
        FROM ops.runs r LEFT JOIN ops.users u ON u.user_id=r.triggered_by
        WHERE r.bot_id=%s ORDER BY r.run_id DESC LIMIT %s""", (bot_id, min(limit, 500)))


@app.get("/api/bots/{bot_id}/failed")
def bot_failed(bot_id: int, include_resolved: bool = False, user=User):
    return db.all(
        "SELECT * FROM ops.failed_requests WHERE bot_id=%s " + ("" if include_resolved else "AND resolved_at IS NULL ")
        + "ORDER BY failed_id DESC LIMIT 500", (bot_id,))


@app.post("/api/failed/{failed_id}/dismiss")
def dismiss_failed(failed_id: int, user=User):
    row = db.one("UPDATE ops.failed_requests SET resolved_at=now() WHERE failed_id=%s AND resolved_at IS NULL "
                 "RETURNING bot_id, request_key", (failed_id,))
    if not row:
        raise HTTPException(404, "Kayıt bulunamadı ya da zaten kapalı")
    db.audit(user["user_id"], "Başarısız isteği yok saydı", row["bot_id"], {"istek": row["request_key"]})
    return {"ok": True}


@app.get("/api/runs/{run_id}")
def run_detail(run_id: int, user=User):
    r = db.one("""SELECT r.*, b.name AS bot_name, u.full_name AS by_name,
                  extract(epoch FROM coalesce(r.finished_at, now())-r.started_at)::int AS seconds
                  FROM ops.runs r JOIN ops.bots b USING (bot_id) LEFT JOIN ops.users u ON u.user_id=r.triggered_by
                  WHERE r.run_id=%s""", (run_id,))
    if not r:
        raise HTTPException(404, "Çalışma bulunamadı")
    r["log_counts"] = db.one("""SELECT count(*) FILTER (WHERE level='warning') AS warning,
                                count(*) FILTER (WHERE level='error') AS error, count(*) AS total
                                FROM ops.run_logs WHERE run_id=%s""", (run_id,))
    return r


@app.get("/api/runs/{run_id}/logs")
def run_logs(run_id: int, after_id: int = 0, level: str | None = None, q: str | None = None,
             limit: int = 500, user=User):
    where, params = ["run_id=%s", "log_id>%s"], [run_id, after_id]
    if level in ("warning", "error"):
        where.append("level = ANY(%s)")
        params.append(["warning", "error"] if level == "warning" else ["error"])
    if q:
        where.append("message ILIKE %s")
        params.append("%" + q.replace("%", r"\%") + "%")
    params.append(min(limit, 2000))
    if after_id == 0:  # ilk yükleme: son N satır
        rows = db.all(f"SELECT * FROM (SELECT * FROM ops.run_logs WHERE {' AND '.join(where)} "
                      f"ORDER BY log_id DESC LIMIT %s) x ORDER BY log_id", params)
    else:
        rows = db.all(f"SELECT * FROM ops.run_logs WHERE {' AND '.join(where)} ORDER BY log_id LIMIT %s", params)
    return rows


# ---------------------------------------------------------------- veri kalitesi
@app.get("/api/quality/checks")
def quality_checks(status: str | None = None, limit: int = 200, user=User):
    where, params = [], []
    if status in ("pass", "warn", "fail"):
        where.append("c.status=%s")
        params.append(status)
    params.append(min(limit, 1000))
    return db.all(f"""
        SELECT c.*, i.source_system, r.run_id, b.bot_id, b.name AS bot_name
        FROM quality.data_quality_checks c
        LEFT JOIN raw.ingestion_runs i ON i.ingestion_run_id=c.ingestion_run_id
        LEFT JOIN ops.runs r ON r.ingestion_run_id=c.ingestion_run_id
        LEFT JOIN ops.bots b ON b.bot_id=r.bot_id
        {'WHERE ' + ' AND '.join(where) if where else ''}
        ORDER BY c.executed_at DESC LIMIT %s""", params)


@app.get("/api/quality/summary")
def quality_summary(user=User):
    return db.one("""
        SELECT (SELECT count(*) FROM quality.data_quality_checks WHERE executed_at > now()-interval '7 days') AS checks_7d,
               (SELECT count(*) FROM quality.data_quality_checks WHERE status='fail' AND executed_at > now()-interval '7 days') AS fail_7d,
               (SELECT count(*) FROM quality.data_quality_checks WHERE status='warn' AND executed_at > now()-interval '7 days') AS warn_7d,
               (SELECT count(*) FROM quality.quarantined_records WHERE resolved_at IS NULL) AS quarantine_open""")


@app.get("/api/quality/quarantine")
def quarantine(open_only: bool = True, user=User):
    return db.all(f"""
        SELECT q.*, i.source_system FROM quality.quarantined_records q
        LEFT JOIN raw.ingestion_runs i ON i.ingestion_run_id=q.ingestion_run_id
        {'WHERE q.resolved_at IS NULL' if open_only else ''}
        ORDER BY q.quarantine_id DESC LIMIT 300""")


class ResolveIn(BaseModel):
    resolution: str = Field(min_length=2, max_length=1000)


@app.post("/api/quality/quarantine/{qid}/resolve")
def resolve_quarantine(qid: int, body: ResolveIn, user=User):
    note = f"{body.resolution} ({user['full_name']})"
    row = db.one("UPDATE quality.quarantined_records SET resolved_at=now(), resolution=%s "
                 "WHERE quarantine_id=%s AND resolved_at IS NULL RETURNING entity", (note, qid))
    if not row:
        raise HTTPException(404, "Kayıt bulunamadı ya da zaten çözülmüş")
    db.audit(user["user_id"], "Karantina kaydını çözdü", None, {"quarantine_id": qid, "not": body.resolution})
    return {"ok": True}


# ---------------------------------------------------------------- veri kapsamı
COVERAGE = [
    ("YÖK Atlas", "Üniversiteler", "core.universities", None),
    ("YÖK Atlas", "İller", "core.cities", None),
    ("YÖK Atlas", "Program grupları", "core.program_groups", None),
    ("YÖK Atlas", "Programlar", "core.program_versions", None),
    ("YÖK Atlas", "Net sonuçları", "core.net_results", None),
    ("YÖK Atlas", "Ham API cevapları", "raw.api_responses", "captured_at"),
    ("YÖK Atlas", "Ham kayıtlar", "raw.source_records", None),
    ("SEGE", "Sıralama satırları", "raw.sege_ranking_rows", None),
    ("SEGE", "Yayın (PDF) kaydı", "raw.sege_artifacts", "captured_at"),
    ("URAP", "Sıralama satırları", "raw.urap_ranking_rows", None),
    ("URAP", "Ölçüt puanları", "raw.urap_metric_scores", None),
    ("URAP", "Yayın (PDF) kaydı", "raw.urap_artifacts", "captured_at"),
]
_IDENT = re.compile(r"^[a-z_]+\.[a-z_]+$")


@app.get("/api/coverage")
def coverage(user=User):
    out = []
    with db.conn() as c:
        for source, label, table, ts_col in COVERAGE:
            if not _IDENT.match(table) or not c.execute("SELECT to_regclass(%s) AS t", (table,)).fetchone()["t"]:
                continue
            sql = f"SELECT count(*) AS n" + (f", max({ts_col}) AS last" if ts_col else "") + f" FROM {table}"
            r = c.execute(sql).fetchone()
            out.append({"source": source, "label": label, "table": table, "rows": r["n"], "last": r.get("last")})
        sources = c.execute("""
            SELECT source_system, count(*) AS runs, max(completed_at) AS last_completed,
                   (array_agg(status ORDER BY started_at DESC))[1] AS last_status,
                   (array_agg(scraper_version ORDER BY started_at DESC))[1] AS last_version
            FROM raw.ingestion_runs GROUP BY source_system ORDER BY source_system""").fetchall()
    return {"tables": out, "sources": sources}


# ---------------------------------------------------------------- bildirimler
class RuleIn(BaseModel):
    enabled: bool | None = None
    threshold: float | None = None


@app.get("/api/alerts")
def alert_info(user=User):
    return {
        "smtp_configured": mailer.configured(),
        "smtp_from": config.SMTP_FROM if mailer.configured() else None,
        "rules": db.all("SELECT * FROM ops.alert_rules ORDER BY rule_key"),
        "recipients": db.all("SELECT user_id, full_name, email, receive_alerts FROM ops.users WHERE is_active ORDER BY user_id"),
        "sent": db.all("""SELECT a.*, b.name AS bot_name FROM ops.alerts_sent a LEFT JOIN ops.bots b USING (bot_id)
                          ORDER BY a.alert_id DESC LIMIT 50"""),
    }


@app.put("/api/alerts/rules/{key}")
def update_rule(key: str, body: RuleIn, user=User):
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(422, "Değişiklik yok")
    sets = ", ".join(f"{k}=%s" for k in data)
    n = db.run(f"UPDATE ops.alert_rules SET {sets} WHERE rule_key=%s", (*data.values(), key))
    if not n:
        raise HTTPException(404, "Kural bulunamadı")
    db.audit(user["user_id"], "Bildirim kuralını değiştirdi", None, {"kural": key, **data})
    return {"ok": True}


@app.post("/api/alerts/test")
def test_alert(user=User):
    res = alerts.notify("test", f"test:{datetime.now().timestamp()}", "Deneme bildirimi",
                        f"Bu bir deneme e-postasıdır. {user['full_name']} panelden gönderdi.\n"
                        f"Bu e-postayı aldıysanız bildirimler çalışıyor.", force=True)
    db.audit(user["user_id"], "Deneme e-postası gönderdi", None, res)
    if not res.get("delivered"):
        raise HTTPException(502, f"E-posta gönderilemedi: {res.get('error')}")
    return res


# ---------------------------------------------------------------- ekip
class UserIn(BaseModel):
    username: str | None = Field(default=None, pattern=r"^[a-z0-9._-]{2,40}$")
    full_name: str | None = Field(default=None, min_length=2, max_length=80)
    email: str | None = Field(default=None, max_length=200)
    password: str | None = Field(default=None, min_length=10, max_length=200)
    receive_alerts: bool | None = None
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        if v in (None, ""):
            return v
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("E-posta adresi geçersiz")
        return v.strip()


@app.get("/api/users")
def users(user=User):
    return db.all("SELECT user_id, username, full_name, email, receive_alerts, is_active, created_at, last_login_at "
                  "FROM ops.users ORDER BY user_id")


@app.post("/api/users")
def create_user(body: UserIn, user=User):
    if not (body.username and body.full_name and body.password):
        raise HTTPException(422, "Kullanıcı adı, ad soyad ve en az 10 karakterlik parola gerekli")
    try:
        row = db.one("INSERT INTO ops.users(username, full_name, email, password_hash, receive_alerts) "
                     "VALUES (%s,%s,%s,%s,%s) RETURNING user_id",
                     (body.username, body.full_name, body.email or None, security.hash_password(body.password),
                      True if body.receive_alerts is None else body.receive_alerts))
    except pg_errors.UniqueViolation:
        raise HTTPException(409, "Bu kullanıcı adı alınmış")
    db.audit(user["user_id"], "Ekip üyesi ekledi", None, {"username": body.username})
    return {"user_id": row["user_id"]}


@app.patch("/api/users/{user_id}")
def update_user(user_id: int, body: UserIn, user=User):
    data = body.model_dump(exclude_unset=True)
    data.pop("username", None)
    if data.get("is_active") is False and user_id == user["user_id"]:
        raise HTTPException(409, "Kendi hesabınızı kapatamazsınız")
    if "password" in data:
        pw = data.pop("password")
        if pw:
            data["password_hash"] = security.hash_password(pw)
    if "email" in data:
        data["email"] = data["email"] or None
    if not data:
        raise HTTPException(422, "Değişiklik yok")
    sets = ", ".join(f"{k}=%s" for k in data)
    if not db.run(f"UPDATE ops.users SET {sets} WHERE user_id=%s", (*data.values(), user_id)):
        raise HTTPException(404, "Kullanıcı bulunamadı")
    if "password_hash" in data:
        db.run("DELETE FROM ops.sessions WHERE user_id=%s AND user_id<>%s", (user_id, user["user_id"]))
    shown = {k: v for k, v in data.items() if k != "password_hash"}
    if "password_hash" in data:
        shown["parola"] = "değiştirildi"
    db.audit(user["user_id"], "Ekip üyesini güncelledi", None, {"user_id": user_id, **shown})
    return {"ok": True}


@app.get("/api/audit")
def audit_log(limit: int = 100, bot_id: int | None = None, user=User):
    where = "WHERE a.bot_id=%s" if bot_id else ""
    params = ([bot_id] if bot_id else []) + [min(limit, 500)]
    return db.all(f"""SELECT a.*, u.full_name AS user_name, b.name AS bot_name FROM ops.audit_log a
                      LEFT JOIN ops.users u USING (user_id) LEFT JOIN ops.bots b ON b.bot_id=a.bot_id
                      {where} ORDER BY a.audit_id DESC LIMIT %s""", params)


# ---------------------------------------------------------------- arayüz
@app.get("/")
def index():
    return FileResponse(config.STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/healthz")
def healthz():
    db.one("SELECT 1")
    return {"ok": True}
