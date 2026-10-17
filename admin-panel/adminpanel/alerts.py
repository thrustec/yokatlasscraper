"""E-posta bildirim kuralları. Çalıştırıcı bunu düzenli aralıklarla çağırır."""
import logging
from datetime import datetime

import psutil

from . import config, db, mailer

log = logging.getLogger("alerts")

STATUS_TR = {"failed": "hata verdi", "timed_out": "zaman aşımına uğradı"}


def recipients() -> list[str]:
    rows = db.all("SELECT email FROM ops.users WHERE is_active AND receive_alerts "
                  "AND email IS NOT NULL AND email <> '' ORDER BY user_id")
    return [r["email"] for r in rows]


def already_sent(dedupe_key: str) -> bool:
    return db.one("SELECT 1 FROM ops.alerts_sent WHERE dedupe_key=%s LIMIT 1", (dedupe_key,)) is not None


def notify(rule_key: str, dedupe_key: str, subject: str, body: str, bot_id=None, run_id=None,
           force: bool = False) -> dict:
    if not force and already_sent(dedupe_key):
        return {"skipped": True}
    to = recipients()
    delivered, error = False, None
    try:
        mailer.send(to, "[ÜniRota] " + subject, body)
        delivered = True
    except Exception as e:  # SMTP yoksa da kaydı tutalım, panelde görünsün
        error = str(e)
        log.warning("E-posta gönderilemedi: %s", e)
    db.run("INSERT INTO ops.alerts_sent(rule_key, dedupe_key, bot_id, run_id, subject, body, recipients, "
           "delivered, error) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
           (rule_key, dedupe_key, bot_id, run_id, subject, body, to, delivered, error))
    return {"delivered": delivered, "error": error, "recipients": to}


def _rules() -> dict:
    return {r["rule_key"]: r for r in db.all("SELECT * FROM ops.alert_rules")}


def check_all() -> None:
    rules = _rules()

    def on(key):
        r = rules.get(key)
        return r is not None and r["enabled"]

    def th(key, default):
        r = rules.get(key)
        return float(r["threshold"]) if r and r["threshold"] is not None else default

    if on("run_failed"):
        for r in db.all(
            "SELECT r.run_id, r.status, r.error_message, r.finished_at, r.records_written, b.bot_id, b.name "
            "FROM ops.runs r JOIN ops.bots b USING (bot_id) "
            "WHERE r.status IN ('failed','timed_out') AND r.finished_at > now() - interval '1 day'"):
            notify("run_failed", f"run_failed:{r['run_id']}",
                   f"{r['name']} {STATUS_TR[r['status']]}",
                   f"{r['name']} botunun #{r['run_id']} numaralı çalışması {STATUS_TR[r['status']]}.\n\n"
                   f"Hata: {r['error_message'] or 'ayrıntı yok'}\n"
                   f"Bitiş: {r['finished_at']:%d.%m.%Y %H:%M}\n"
                   f"Bu çalışmada yazılan kayıt: {r['records_written']}\n\n"
                   f"Loglar için panelde botun sayfasına bakın.",
                   bot_id=r["bot_id"], run_id=r["run_id"])

    if on("low_records"):
        for r in db.all(
            "SELECT r.run_id, r.records_written, b.expected_min_records, b.bot_id, b.name "
            "FROM ops.runs r JOIN ops.bots b USING (bot_id) "
            "WHERE r.status='succeeded' AND b.expected_min_records IS NOT NULL "
            "AND r.records_written < b.expected_min_records AND r.finished_at > now() - interval '1 day'"):
            notify("low_records", f"low_records:{r['run_id']}",
                   f"{r['name']}: beklenenden az kayıt geldi",
                   f"{r['name']} botu başarıyla bitti ama sadece {r['records_written']} kayıt yazdı "
                   f"(beklenen en az {r['expected_min_records']}).\n"
                   f"Kaynak sitenin yapısı değişmiş olabilir.",
                   bot_id=r["bot_id"], run_id=r["run_id"])

    if on("stalled"):
        minutes = th("stalled", 15)
        for r in db.all(
            "SELECT r.run_id, r.heartbeat_at, b.bot_id, b.name FROM ops.runs r JOIN ops.bots b USING (bot_id) "
            "WHERE r.status='running' AND coalesce(r.heartbeat_at, r.started_at) < now() - make_interval(mins => %s)",
            (int(minutes),)):
            notify("stalled", f"stalled:{r['run_id']}",
                   f"{r['name']} {int(minutes)} dakikadır ses vermiyor",
                   f"{r['name']} botu çalışıyor görünüyor ama {int(minutes)} dakikadır hiçbir çıktı ya da "
                   f"ilerleme bilgisi göndermedi. Takılmış olabilir; panelden durdurup yeniden başlatabilirsiniz.",
                   bot_id=r["bot_id"], run_id=r["run_id"])

    if on("schedule_missed"):
        hours = th("schedule_missed", 24)
        today = datetime.now().strftime("%Y-%m-%d")
        for b in db.all(
            "SELECT b.bot_id, b.name, b.schedule_cron, "
            "(SELECT max(finished_at) FROM ops.runs r WHERE r.bot_id=b.bot_id AND r.status='succeeded') AS last_ok "
            "FROM ops.bots b WHERE b.enabled AND b.schedule_cron IS NOT NULL "
            "AND b.created_at < now() - make_interval(hours => %s)", (int(hours),)):
            last = b["last_ok"]
            if last is None or (datetime.now(last.tzinfo) - last).total_seconds() > hours * 3600:
                notify("schedule_missed", f"schedule_missed:{b['bot_id']}:{today}",
                       f"{b['name']} {int(hours)} saattir başarıyla çalışmadı",
                       f"{b['name']} botu planlı ({b['schedule_cron']}) ama son {int(hours)} saatte başarılı "
                       f"bir çalışması yok. Son başarılı çalışma: "
                       f"{last.strftime('%d.%m.%Y %H:%M') if last else 'hiç yok'}.",
                       bot_id=b["bot_id"])

    if on("disk_usage"):
        limit = th("disk_usage", 80)
        try:
            d = psutil.disk_usage(config.DISK_PATH)
        except OSError:
            d = None
        if d and d.percent >= limit:
            notify("disk_usage", f"disk_usage:{datetime.now():%Y-%m-%d}",
                   f"Sunucu diski %{d.percent:.0f} dolu",
                   f"Sunucu diski %{d.percent:.0f} dolu (sınır %{limit:.0f}). "
                   f"Boş alan: {d.free / 1024**3:.1f} GB / {d.total / 1024**3:.1f} GB.")
