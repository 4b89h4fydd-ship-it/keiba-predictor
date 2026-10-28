"""Append-only originals, exact-byte hashes and independently reopened backups.

Separate SQLite file: never writes existing application/history tables.
"""
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from .contracts import aware


SCHEMA = '''
CREATE TABLE IF NOT EXISTS originals(
 race_id TEXT NOT NULL, generated_at TEXT NOT NULL, starts_at TEXT NOT NULL,
 payload BLOB NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(race_id));
CREATE TRIGGER IF NOT EXISTS originals_no_update BEFORE UPDATE ON originals
BEGIN SELECT RAISE(ABORT, 'immutable original'); END;
CREATE TRIGGER IF NOT EXISTS originals_no_delete BEFORE DELETE ON originals
BEGIN SELECT RAISE(ABORT, 'immutable original'); END;
'''


class Ledger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.executescript(SCHEMA)

    def close(self):
        self.connection.close()

    def seal(self, race_id: str, generated_at: datetime, starts_at: datetime,
             payload: dict) -> str:
        aware(generated_at)
        aware(starts_at)
        if generated_at >= starts_at:
            raise ValueError('cannot seal after start')
        if not race_id.strip() or payload.get('race_id') != race_id:
            raise ValueError('race identity mismatch')
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False).encode()
        digest = hashlib.sha256(raw).hexdigest()
        with self.connection:
            # INSERT OR REPLACE is forbidden: the first original always wins.
            self.connection.execute('INSERT INTO originals VALUES(?,?,?,?,?)',
                                    (race_id, generated_at.isoformat(), starts_at.isoformat(), raw, digest))
        return digest

    def read(self, race_id: str) -> dict:
        row = self.connection.execute('SELECT payload,sha256 FROM originals WHERE race_id=?',
                                      (race_id,)).fetchone()
        if row is None:
            raise KeyError(race_id)
        if hashlib.sha256(row[0]).hexdigest() != row[1]:
            raise ValueError('original hash mismatch')
        return json.loads(row[0])

    def backup(self, destination: str | Path) -> dict:
        if self.connection.in_transaction:
            raise ValueError('backup requires committed transaction')
        destination = Path(destination)
        # Reserve destination exclusively; never overwrite a previous backup.
        with destination.open('xb'):
            pass
        target = sqlite3.connect(destination)
        try:
            self.connection.backup(target)
        finally:
            target.close()
        with sqlite3.connect(f'file:{destination.resolve()}?mode=ro', uri=True) as restored:
            if restored.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('backup integrity failed')
            rows = restored.execute('SELECT * FROM originals ORDER BY race_id').fetchall()
            expected = self.connection.execute('SELECT * FROM originals ORDER BY race_id').fetchall()
            if rows != expected:
                raise ValueError('backup restore mismatch')
            for row in rows:
                if hashlib.sha256(row[3]).hexdigest() != row[4]:
                    raise ValueError('backup payload hash mismatch')
        return {'rows': len(rows), 'restore_verified': True,
                'file_sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}
