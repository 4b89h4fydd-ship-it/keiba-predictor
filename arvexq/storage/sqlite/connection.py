"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _new_conn(path: Path, *, sqlite3):
    conn = sqlite3.connect(path, timeout=1.5)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA query_only=ON')
        conn.execute('PRAGMA busy_timeout=1200')
    except Exception:
        pass
    return conn
