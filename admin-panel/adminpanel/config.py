"""Ortam değişkenlerinden okunan ayarlar (.env.example dosyasına bakın)."""
import os
from pathlib import Path


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


DATABASE_URL = os.environ.get("ADMIN_DATABASE_URL") or os.environ.get("DATABASE_URL", "")

# Botların kodunun bulunduğu repo kökü. Bot komutları burada çalışır.
REPO_DIR = Path(os.environ.get("ADMIN_REPO_DIR", Path(__file__).resolve().parents[1])).resolve()

# Disk doluluğu bu yoldan ölçülür (sunucudaki veri diski).
DISK_PATH = os.environ.get("ADMIN_DISK_PATH", "/")

MAX_PARALLEL_RUNS = _int("ADMIN_MAX_PARALLEL_RUNS", 2)
RUNNER_TICK_SECONDS = _int("ADMIN_RUNNER_TICK_SECONDS", 3)
SESSION_DAYS = _int("ADMIN_SESSION_DAYS", 14)

# Oturum çerezi sadece HTTPS'te gönderilsin mi? SSH tüneliyle http://localhost kullanılıyorsa 0 kalabilir.
COOKIE_SECURE = os.environ.get("ADMIN_COOKIE_SECURE", "0") == "1"

# Panelin adresi, e-postalardaki bağlantılar için.
PANEL_URL = os.environ.get("ADMIN_PANEL_URL", "http://localhost:8090")

SMTP_HOST = os.environ.get("ADMIN_SMTP_HOST", "")
SMTP_PORT = _int("ADMIN_SMTP_PORT", 587)
SMTP_USER = os.environ.get("ADMIN_SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("ADMIN_SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("ADMIN_SMTP_FROM", SMTP_USER or "unirota-panel@localhost")
SMTP_STARTTLS = os.environ.get("ADMIN_SMTP_STARTTLS", "1") == "1"
SMTP_SSL = os.environ.get("ADMIN_SMTP_SSL", "0") == "1"

STATIC_DIR = Path(__file__).resolve().parent / "static"
SQL_DIR = Path(__file__).resolve().parent / "sql"
