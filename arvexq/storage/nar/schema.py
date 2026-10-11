"""nar/schema.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
import sqlite3
from arvexq.storage.config import DB_PATH
from pathlib import Path

class NarSchema:
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._migrate()


    def _migrate(self) -> None:
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS races (
                track TEXT NOT NULL,
                date TEXT NOT NULL,
                race_no INTEGER NOT NULL,
                start_time TEXT NOT NULL DEFAULT '',
                scheduled_start_time TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                distance INTEGER NOT NULL DEFAULT 0,
                weather TEXT NOT NULL DEFAULT '不明',
                condition TEXT NOT NULL DEFAULT '不明',
                field_size INTEGER NOT NULL DEFAULT 0,
                prize1 INTEGER NOT NULL DEFAULT 0,
                prize2 INTEGER NOT NULL DEFAULT 0,
                prize3 INTEGER NOT NULL DEFAULT 0,
                prize4 INTEGER NOT NULL DEFAULT 0,
                prize5 INTEGER NOT NULL DEFAULT 0,
                corners_json TEXT NOT NULL DEFAULT '[]',
                PRIMARY KEY(track, date, race_no)
            );
            CREATE TABLE IF NOT EXISTS entries (
                track TEXT NOT NULL,
                date TEXT NOT NULL,
                race_no INTEGER NOT NULL,
                frame_no INTEGER NOT NULL DEFAULT 0,
                horse_no INTEGER NOT NULL,
                name TEXT NOT NULL,
                sex TEXT NOT NULL DEFAULT '牡',
                age INTEGER NOT NULL DEFAULT 0,
                carried_weight REAL NOT NULL DEFAULT 0,
                jockey TEXT NOT NULL DEFAULT '',
                trainer TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT '',
                finish INTEGER NOT NULL DEFAULT 0,
                time_seconds REAL NOT NULL DEFAULT 0,
                corner_positions_json TEXT NOT NULL DEFAULT '[]',
                PRIMARY KEY(track, date, race_no, horse_no)
            );
            CREATE INDEX IF NOT EXISTS idx_entries_name_date ON entries(name, date);
            CREATE INDEX IF NOT EXISTS idx_entries_jockey_date ON entries(jockey, date);
            CREATE INDEX IF NOT EXISTS idx_entries_trainer_date ON entries(trainer, date);
            CREATE TABLE IF NOT EXISTS sync_log (
                cache_key TEXT PRIMARY KEY,
                synced_at INTEGER NOT NULL,
                archive_path TEXT NOT NULL DEFAULT ''
            );
            """
        )
        race_cols = {row[1] for row in self.conn.execute("PRAGMA table_info(races)").fetchall()}
        if "scheduled_start_time" not in race_cols:
            self.conn.execute("ALTER TABLE races ADD COLUMN scheduled_start_time TEXT NOT NULL DEFAULT ''")
        entry_cols = {row[1] for row in self.conn.execute("PRAGMA table_info(entries)").fetchall()}
        if "status" not in entry_cols:
            self.conn.execute("ALTER TABLE entries ADD COLUMN status TEXT NOT NULL DEFAULT ''")
        self.conn.execute("UPDATE races SET scheduled_start_time=start_time WHERE scheduled_start_time=''")
        self.conn.commit()

