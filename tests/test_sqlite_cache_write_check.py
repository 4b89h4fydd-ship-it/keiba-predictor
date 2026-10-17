"""A readable SQLite cache must also permit a write transaction."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from scripts.arvexq_sqlite_health import _quick_check, sanitize


class SQLiteWritableCacheTests(unittest.TestCase):
    def test_healthy_cache_can_write(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "race.sqlite"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY)")
            self.assertEqual(_quick_check(db), (True, "ok"))
            checked, removed, _ = sanitize(Path(folder))
            self.assertEqual((checked, removed), (1, 0))
            self.assertTrue(db.exists())

    def test_readable_but_locked_cache_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "race.sqlite"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY)")
            locker = sqlite3.connect(db, timeout=0.1)
            try:
                locker.execute("BEGIN IMMEDIATE")
                ok, reason = _quick_check(db)
                self.assertFalse(ok)
                self.assertIn("locked", reason)
            finally:
                locker.rollback()
                locker.close()


if __name__ == "__main__":
    unittest.main()
