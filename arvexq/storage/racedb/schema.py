"""racedb/schema.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
import sqlite3
from arvexq.storage.ports import RaceSnapshotPorts
from arvexq.storage.config import RACEDB_PATH
from pathlib import Path

class RaceSchema:
    def __init__(self, path: Path = RACEDB_PATH, *, ports: RaceSnapshotPorts):
        self._ports = ports
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=5)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS race_snapshots (
                    race_id TEXT PRIMARY KEY,
                    race_date TEXT NOT NULL DEFAULT '',
                    circuit TEXT NOT NULL DEFAULT '',
                    track TEXT NOT NULL DEFAULT '',
                    race_no INTEGER NOT NULL DEFAULT 0,
                    title TEXT NOT NULL DEFAULT '',
                    surface TEXT NOT NULL DEFAULT '',
                    distance INTEGER NOT NULL DEFAULT 0,
                    condition TEXT NOT NULL DEFAULT '',
                    weather TEXT NOT NULL DEFAULT '',
                    start_time TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_racedb_races_date ON race_snapshots(race_date,circuit,track,race_no);

                CREATE TABLE IF NOT EXISTS horse_master (
                    horse_key TEXT PRIMARY KEY,
                    name TEXT NOT NULL DEFAULT '',
                    horse_external_id TEXT NOT NULL DEFAULT '',
                    sex TEXT NOT NULL DEFAULT '',
                    age INTEGER NOT NULL DEFAULT 0,
                    birthday TEXT NOT NULL DEFAULT '',
                    sire TEXT NOT NULL DEFAULT '',
                    dam TEXT NOT NULL DEFAULT '',
                    damsire TEXT NOT NULL DEFAULT '',
                    trainer TEXT NOT NULL DEFAULT '',
                    owner TEXT NOT NULL DEFAULT '',
                    producer TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL,
                    raw_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_racedb_horse_name ON horse_master(name);

                CREATE TABLE IF NOT EXISTS horse_entries (
                    race_id TEXT NOT NULL,
                    horse_no INTEGER NOT NULL,
                    horse_key TEXT NOT NULL DEFAULT '',
                    frame_no INTEGER NOT NULL DEFAULT 0,
                    name TEXT NOT NULL DEFAULT '',
                    jockey TEXT NOT NULL DEFAULT '',
                    trainer TEXT NOT NULL DEFAULT '',
                    carried_weight REAL,
                    body_weight INTEGER,
                    body_weight_change INTEGER,
                    prize_money INTEGER NOT NULL DEFAULT 0,
                    ten1f TEXT,
                    ten TEXT,
                    agari TEXT,
                    estimated_popularity TEXT,
                    pedigree_json TEXT NOT NULL DEFAULT '{}',
                    style_json TEXT NOT NULL DEFAULT '{}',
                    fit_json TEXT NOT NULL DEFAULT '{}',
                    debut_json TEXT NOT NULL DEFAULT '{}',
                    jump_json TEXT NOT NULL DEFAULT '{}',
                    representative_json TEXT NOT NULL DEFAULT '{}',
                    opponent_level REAL,
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    sources_json TEXT NOT NULL DEFAULT '[]',
                    updated_at INTEGER NOT NULL,
                    raw_json TEXT NOT NULL DEFAULT '{}',
                    PRIMARY KEY(race_id,horse_no)
                );
                CREATE INDEX IF NOT EXISTS idx_racedb_entries_horse ON horse_entries(horse_key);

                CREATE TABLE IF NOT EXISTS past_runs (
                    horse_key TEXT NOT NULL,
                    run_key TEXT NOT NULL,
                    race_date TEXT NOT NULL DEFAULT '',
                    track TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    distance INTEGER NOT NULL DEFAULT 0,
                    surface TEXT NOT NULL DEFAULT '',
                    condition TEXT NOT NULL DEFAULT '',
                    weather TEXT NOT NULL DEFAULT '',
                    finish INTEGER NOT NULL DEFAULT 0,
                    time_seconds REAL,
                    agari3f REAL,
                    agari_rank INTEGER,
                    frame_no INTEGER NOT NULL DEFAULT 0,
                    horse_no INTEGER NOT NULL DEFAULT 0,
                    carried_weight REAL,
                    jockey TEXT NOT NULL DEFAULT '',
                    corner_json TEXT NOT NULL DEFAULT '[]',
                    opponent_level REAL,
                    representative INTEGER NOT NULL DEFAULT 0,
                    source TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL,
                    raw_json TEXT NOT NULL DEFAULT '{}',
                    PRIMARY KEY(horse_key,run_key)
                );
                CREATE INDEX IF NOT EXISTS idx_racedb_runs_date ON past_runs(horse_key,race_date DESC);
                CREATE INDEX IF NOT EXISTS idx_racedb_runs_cutoff ON past_runs(race_date,jockey);
                CREATE INDEX IF NOT EXISTS idx_racedb_runs_jockey ON past_runs(jockey,race_date);
                CREATE INDEX IF NOT EXISTS idx_racedb_horse_sire ON horse_master(sire);
                CREATE INDEX IF NOT EXISTS idx_racedb_runs_track_date ON past_runs(track,race_date);

                CREATE TABLE IF NOT EXISTS odds_history (
                    race_id TEXT NOT NULL,
                    horse_no INTEGER NOT NULL,
                    captured_at INTEGER NOT NULL,
                    win_odds REAL,
                    popularity INTEGER,
                    source TEXT NOT NULL DEFAULT '',
                    raw_json TEXT NOT NULL DEFAULT '{}',
                    PRIMARY KEY(race_id,horse_no,captured_at)
                );
                CREATE INDEX IF NOT EXISTS idx_racedb_odds_race ON odds_history(race_id,captured_at DESC);

                CREATE TABLE IF NOT EXISTS race_analysis (
                    race_id TEXT PRIMARY KEY,
                    updated_at INTEGER NOT NULL,
                    scenario_json TEXT NOT NULL DEFAULT '{}',
                    horse_diagnosis_json TEXT NOT NULL DEFAULT '[]',
                    raw_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS source_state (
                    source_key TEXT PRIMARY KEY,
                    updated_at INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS field_state (
                    race_id TEXT NOT NULL,
                    field_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'missing',
                    completeness INTEGER NOT NULL DEFAULT 0,
                    source TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL DEFAULT 0,
                    last_attempt_at INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    note TEXT NOT NULL DEFAULT '',
                    value_hash TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(race_id,field_key)
                );
                CREATE INDEX IF NOT EXISTS idx_racedb_field_status ON field_state(status,updated_at);
                CREATE INDEX IF NOT EXISTS idx_racedb_field_race ON field_state(race_id,field_key);

                CREATE TABLE IF NOT EXISTS collector_runs (
                    run_id TEXT PRIMARY KEY,
                    race_id TEXT NOT NULL,
                    started_at INTEGER NOT NULL,
                    finished_at INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT '',
                    attempted_fields TEXT NOT NULL DEFAULT '[]',
                    before_json TEXT NOT NULL DEFAULT '{}',
                    after_json TEXT NOT NULL DEFAULT '{}',
                    note TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_racedb_collector_race ON collector_runs(race_id,started_at DESC);
                """
            )
            # v86 forward-compatible migration for an existing RaceDB.
            # CR/share from v85 are intentionally no longer read or written.
            def ensure_column(table: str, column: str, ddl: str) -> None:
                cols={str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
                if column not in cols:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            for col,ddl in (
                ("style_json","TEXT NOT NULL DEFAULT '{}'"),("fit_json","TEXT NOT NULL DEFAULT '{}'"),
                ("debut_json","TEXT NOT NULL DEFAULT '{}'"),("jump_json","TEXT NOT NULL DEFAULT '{}'"),
                ("representative_json","TEXT NOT NULL DEFAULT '{}'"),("opponent_level","REAL")
            ): ensure_column("horse_entries",col,ddl)
            for col,ddl in (
                ("agari3f","REAL"),("agari_rank","INTEGER"),("frame_no","INTEGER NOT NULL DEFAULT 0"),
                ("horse_no","INTEGER NOT NULL DEFAULT 0"),("opponent_level","REAL"),("representative","INTEGER NOT NULL DEFAULT 0")
            ): ensure_column("past_runs",col,ddl)
            conn.commit()
        finally:
            conn.close()

