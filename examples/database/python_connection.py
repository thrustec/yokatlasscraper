"""Local backend connection example (not for browser/frontend JavaScript)."""
import os
from pathlib import Path
import psycopg


def env_value(name, default=None):
    if name in os.environ:
        return os.environ[name]
    env_file = Path(__file__).resolve().parents[1] / '.env'
    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8-sig').splitlines():
            if line.startswith(name + '='):
                return line.split('=', 1)[1].strip()
    return default

with psycopg.connect(
    host=env_value('ATLAS_DB_HOST', '127.0.0.1'),
    port=int(env_value('ATLAS_DB_PORT', env_value('POSTGRES_PORT', '5433'))),
    dbname='yokatlas_intelligence',
    user='atlas_api',
    password=env_value('ATLAS_API_PASSWORD'),
) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT * FROM api.data_coverage ORDER BY entity')
        for row in cur.fetchall():
            print(row)
