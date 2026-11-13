"""Durable write-ahead checkpoint; deliberately no blind retries."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from .client import RejectedWrite, UncertainWrite, encode_json


class ReconciliationRequired(RuntimeError):
    pass


SCHEMA = """
CREATE TABLE IF NOT EXISTS operations (
  operation_id TEXT PRIMARY KEY,
  table_name TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('pending','committed','uncertain','rejected')),
  key_json TEXT,
  error_code TEXT,
  changed_at TEXT NOT NULL
);
"""


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        with self.db:
            yield self.db

    def get(self, operation_id: str):
        row = self.db.execute('SELECT table_name,payload_sha256,state,key_json,error_code FROM operations WHERE operation_id=?',
                              (operation_id,)).fetchone()
        if row is None:
            return None
        return {'table': row[0], 'sha': row[1], 'state': row[2],
                'key': json.loads(row[3]) if row[3] is not None else None, 'error': row[4]}

    def execute(self, operation_id: str, table: str, data: dict, client) -> dict:
        """Reserve intent on disk BEFORE the request, then persist its returned PK."""
        content_hash = hashlib.sha256(encode_json({'table': table, 'data': data}).encode('utf-8')).hexdigest()
        row = self.get(operation_id)
        if row:
            if row['table'] != table or row['sha'] != content_hash:
                raise ReconciliationRequired(f'{operation_id}: same operation ID with different contents')
            if row['state'] == 'committed':
                return row['key']
            raise ReconciliationRequired(f'{operation_id}: state={row["state"]}; manual reconciliation required')
        with self.transaction() as db:
            db.execute('INSERT INTO operations VALUES(?,?,?,?,?,?,?)',
                       (operation_id, table, content_hash, 'pending', None, None,
                        datetime.now(timezone.utc).isoformat()))
        try:
            key = client.insert(table, data)
        except RejectedWrite as exc:
            self._state(operation_id, 'rejected', str(exc.status))
            raise
        except (UncertainWrite, Exception) as exc:
            # Unexpected client errors may have occurred after the network write.
            # Fails closed and preserves the pre-request durable intent.
            self._state(operation_id, 'uncertain', type(exc).__name__)
            raise
        self._state(operation_id, 'committed', None, key)
        return key

    def _state(self, operation_id, state, error, key=None):
        with self.transaction() as db:
            db.execute('''UPDATE operations SET state=?,key_json=?,error_code=?,changed_at=?
                       WHERE operation_id=?''', (state, encode_json(key) if key is not None else None,
                       error, datetime.now(timezone.utc).isoformat(), operation_id))

    def stats(self):
        return dict(self.db.execute('SELECT state,count(*) FROM operations GROUP BY state').fetchall())

    def reconcile(self, operation_id: str, *, committed_key: dict | None = None, not_committed=False):
        """Operator-only action after independent DB verification; not an automatic retry."""
        row = self.get(operation_id)
        if not row or row['state'] == 'committed':
            raise ValueError('Operation not found or already committed')
        if not_committed:
            with self.transaction() as db:
                db.execute('DELETE FROM operations WHERE operation_id=?', (operation_id,))
        elif isinstance(committed_key, dict):
            self._state(operation_id, 'committed', None, committed_key)
        else:
            raise ValueError('Provide a verified key or an explicit non-commit decision')
