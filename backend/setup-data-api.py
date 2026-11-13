"""Provision only the data API roles; preserve existing bot credentials and grants."""
import os
import secrets
from pathlib import Path

import psycopg
from dotenv import dotenv_values, set_key
from psycopg import sql


def main():
    repo = Path(__file__).resolve().parents[1]
    env_path = repo / ".env"
    if not env_path.is_file():
        raise SystemExit("Önce .env ve PostgreSQL kurulumunu tamamlayın.")
    config = {**dotenv_values(env_path), **os.environ}
    for name in ("ATLAS_RAW_WRITER_PASSWORD", "ATLAS_ANALYTICS_READER_PASSWORD", "DB_WRITE_API_KEY"):
        if not config.get(name) or config[name].startswith("REPLACE_"):
            config[name] = secrets.token_urlsafe(32)
            set_key(env_path, name, config[name], quote_mode="always")
    if os.name != "nt":
        env_path.chmod(0o600)
    with psycopg.connect(
        host=config.get("PGHOST") or "127.0.0.1",
        port=int(config.get("PGPORT") or config.get("POSTGRES_PORT") or 5433),
        dbname=config.get("PGDATABASE") or "yokatlas_intelligence", user="atlas_owner",
        password=config.get("POSTGRES_ADMIN_PASSWORD"), connect_timeout=5,
    ) as conn:
        conn.execute((repo / "database/migrations/008_data_api_roles.sql").read_text(encoding="utf-8"))
        for role, key in (("atlas_raw_writer", "ATLAS_RAW_WRITER_PASSWORD"),
                          ("atlas_analytics_reader", "ATLAS_ANALYTICS_READER_PASSWORD")):
            conn.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                sql.Identifier(role), sql.Literal(config[key]),
            ))
    print("Veri API hazır. Swagger Authorize için .env içindeki DB_WRITE_API_KEY kullanılır.")


if __name__ == "__main__":
    main()
