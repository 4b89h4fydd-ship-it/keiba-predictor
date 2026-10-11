"""central/store.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
import json
import sqlite3
import time
from arvexq.storage.policies.snapshots import retain_snapshot
from arvexq.storage.sqlite.transactions import begin_write
from arvexq.storage.config import CENTRAL_DB_PATH
from arvexq.normalize.central_feed import normalize_central_race
from pathlib import Path

class CentralStore:
    def __init__(self, path: Path = CENTRAL_DB_PATH):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS central_races(
              id TEXT PRIMARY KEY,
              date TEXT NOT NULL,
              track TEXT NOT NULL,
              race_no INTEGER NOT NULL,
              payload TEXT NOT NULL,
              updated_at INTEGER NOT NULL
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_central_date ON central_races(date,track,race_no)")
        self.conn.commit()


    def upsert(self, rows: list[dict]) -> int:
        n = 0
        with self.conn:
            begin_write(self.conn)
            for raw in rows:
                incoming = normalize_central_race(raw)
                if not incoming:
                    continue
                old_row=self.conn.execute("SELECT payload FROM central_races WHERE id=?",(incoming["id"],)).fetchone()
                if old_row:
                    try:old=json.loads(old_row["payload"])
                    except Exception:old={}
                    incoming=retain_snapshot(old,incoming)
                    merged=dict(old) if isinstance(old,dict) else {}
                    # Lightweight schedule rows must never erase a prepared card/result.
                    for k,v in incoming.items():
                        if k=="horses":
                            if isinstance(v,list) and v:merged[k]=v
                            continue
                        if k=="result":
                            if isinstance(v,dict) and v:merged[k]=v
                            continue
                        if k in {"weather","condition"}:
                            if v not in (None,"","不明"):merged[k]=v
                            elif k not in merged:merged[k]="不明"
                            continue
                        if k=="fieldSize":
                            if int(v or 0)>0:merged[k]=int(v)
                            continue
                        if v not in (None,"",0,[]):
                            merged[k]=v
                        elif k not in merged:
                            merged[k]=v
                    r=normalize_central_race(merged) or incoming
                else:
                    r=incoming
                self.conn.execute(
                    """INSERT INTO central_races(id,date,track,race_no,payload,updated_at)
                       VALUES(?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET date=excluded.date,track=excluded.track,
                         race_no=excluded.race_no,payload=excluded.payload,updated_at=excluded.updated_at""",
                    (r["id"], r["date"], r["track"], r["raceNumber"], json.dumps(r, ensure_ascii=False), int(time.time())),
                )
                n += 1
        return n


    def races_json(self, iso_date: str) -> list[dict]:
        rows = self.conn.execute("SELECT payload FROM central_races WHERE date=? ORDER BY track,race_no", (iso_date,)).fetchall()
        return [json.loads(x["payload"]) for x in rows]


    def coverage(self) -> dict:
        row = self.conn.execute("SELECT MIN(date) min_date, MAX(date) max_date, COUNT(*) cnt FROM central_races").fetchone()
        return {"minDate": row["min_date"], "maxDate": row["max_date"], "count": int(row["cnt"] or 0)}

