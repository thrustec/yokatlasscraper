"""Prepare the optional local CRUD demo; no existing records are changed."""
import secrets
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql


def main():
    repo = Path(__file__).resolve().parents[1]
    config = dotenv_values(repo / ".env")
    env_path = repo / ".env.demo"
    demo = dotenv_values(env_path)
    changed = False
    for name in ("ATLAS_DEMO_WRITE_PASSWORD", "DEMO_API_KEY"):
        if not demo.get(name):
            demo[name] = secrets.token_urlsafe(32)
            changed = True
    if changed:
        env_path.write_text(
            "# Local demo credentials. Do not commit.\n"
            + "".join(f"{name}={value}\n" for name, value in demo.items()),
            encoding="utf-8",
        )
    with psycopg.connect(
        host="127.0.0.1", port=int(config.get("POSTGRES_PORT") or 5433),
        dbname="yokatlas_intelligence", user="atlas_owner",
        password=config.get("POSTGRES_ADMIN_PASSWORD"), connect_timeout=5,
    ) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = 'atlas_demo_writer'"
        ).fetchone()
        action = "ALTER" if exists else "CREATE"
        conn.execute(sql.SQL(action + " ROLE atlas_demo_writer LOGIN PASSWORD {}").format(
            sql.Literal(demo["ATLAS_DEMO_WRITE_PASSWORD"])
        ))
        conn.execute((repo / "backend/demo-write.sql").read_text(encoding="utf-8"))
    print("Demo CRUD ready. Use DEMO_API_KEY from .env.demo in Swagger Authorize.")


if __name__ == "__main__":
    main()
