"""Real SQLite WAL preservation and fail-closed cache health contracts."""
import sqlite3
from pathlib import Path

import pytest

from scripts.arvexq_sqlite_health import sanitize


def test_committed_uncheckpointed_wal_survives_audit(tmp_path):
    path = tmp_path / "facts.sqlite"
    writer = sqlite3.connect(str(path))
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE history(horse TEXT NOT NULL)")
        writer.commit()
        writer.execute("INSERT INTO history VALUES ('persistent past race')")
        writer.commit()
        wal = Path(str(path) + "-wal")
        assert wal.exists() and wal.stat().st_size > 0
        before = wal.read_bytes()
        checked, removed, paths = sanitize(tmp_path)
        assert checked == 1 and removed == 0 and paths == []
        assert wal.exists()
        assert wal.read_bytes() == before
        assert writer.execute("SELECT horse FROM history").fetchone()[0] == "persistent past race"
    finally:
        writer.close()


def test_corrupt_database_is_never_deleted(tmp_path):
    path = tmp_path / "damaged.sqlite"
    # Valid SQLite header but unrecoverable content: should remain untouched.
    payload = b"SQLite format 3\x00" + b"\xff" * 2048
    path.write_bytes(payload)
    with pytest.raises(RuntimeError, match="preserved"):
        sanitize(tmp_path)
    assert path.read_bytes() == payload


def test_locked_database_keeps_original_bytes(tmp_path):
    path = tmp_path / "busy.sqlite"
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("CREATE TABLE t(x INT)")
        conn.commit()
        conn.execute("BEGIN EXCLUSIVE")
        before = path.read_bytes()
        with pytest.raises(RuntimeError, match="preserved"):
            sanitize(tmp_path)
        assert path.read_bytes() == before
    finally:
        conn.rollback()
        conn.close()
