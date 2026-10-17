"""PostgreSQL bağlantı havuzu ve küçük yardımcılar."""
import atexit
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config

_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        if not config.DATABASE_URL:
            raise RuntimeError("ADMIN_DATABASE_URL (veya DATABASE_URL) tanımlı değil.")
        _pool = ConnectionPool(
            config.DATABASE_URL,
            min_size=1,
            max_size=8,
            kwargs={"row_factory": dict_row, "autocommit": True},
            open=True,
        )
        atexit.register(close)
    return _pool


def close():
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def conn():
    with pool().connection() as c:
        yield c


def all(sql: str, params=None) -> list[dict]:
    with conn() as c:
        return c.execute(sql, params).fetchall()


def one(sql: str, params=None) -> dict | None:
    with conn() as c:
        return c.execute(sql, params).fetchone()


def run(sql: str, params=None) -> int:
    with conn() as c:
        return c.execute(sql, params).rowcount


def audit(user_id, action: str, bot_id=None, details: dict | None = None) -> None:
    from psycopg.types.json import Jsonb

    run(
        "INSERT INTO ops.audit_log(user_id, action, bot_id, details) VALUES (%s,%s,%s,%s)",
        (user_id, action, bot_id, Jsonb(details or {})),
    )


def migrate() -> list[str]:
    """sql/ klasöründeki dosyaları sırayla uygular (hepsi tekrar çalıştırılabilir)."""
    applied = []
    with conn() as c:
        for f in sorted(config.SQL_DIR.glob("*.sql")):
            c.execute(f.read_text(encoding="utf-8"))
            applied.append(f.name)
    return applied
