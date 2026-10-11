"""bundles/store.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
import json
import sqlite3
import time


from pathlib import Path

class DayBundleStore:
    def __init__(self,path:Path):
        self.path=path
        self.path.parent.mkdir(parents=True,exist_ok=True)
        conn=sqlite3.connect(self.path,timeout=5)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS day_bundles(
                race_date TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                complete INTEGER NOT NULL DEFAULT 0,
                race_count INTEGER NOT NULL DEFAULT 0,
                detail_count INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL
            )""")
            conn.commit()
        finally:conn.close()


    def get(self,race_date:str,complete_only:bool=False)->dict|None:
        conn=sqlite3.connect(self.path,timeout=3);conn.row_factory=sqlite3.Row
        try:
            sql="SELECT * FROM day_bundles WHERE race_date=?"
            args=[race_date]
            if complete_only:sql+=" AND complete=1"
            row=conn.execute(sql,args).fetchone()
            if not row:return None
            try:p=json.loads(row["payload"])
            except Exception:return None
            p["persisted"]=True
            p["updatedAtEpoch"]=int(row["updated_at"] or 0)
            p["complete"]=bool(row["complete"])
            p["raceCount"]=int(row["race_count"] or 0)
            p["detailCount"]=int(row["detail_count"] or 0)
            return p
        finally:conn.close()


    def put(self,race_date:str,payload:dict,complete:bool)->None:
        if not race_date or not isinstance(payload,dict):return
        conn=sqlite3.connect(self.path,timeout=5)
        try:
            conn.execute("""INSERT INTO day_bundles(race_date,payload,complete,race_count,detail_count,updated_at)
                            VALUES(?,?,?,?,?,?)
                            ON CONFLICT(race_date) DO UPDATE SET
                              payload=excluded.payload,complete=excluded.complete,
                              race_count=excluded.race_count,detail_count=excluded.detail_count,
                              updated_at=excluded.updated_at""",
                         (race_date,json.dumps(payload,ensure_ascii=False,separators=(",",":"),default=str),
                          1 if complete else 0,int(payload.get("raceCount") or 0),
                          int(payload.get("detailCount") or 0),int(time.time())))
            conn.commit()
        finally:conn.close()

