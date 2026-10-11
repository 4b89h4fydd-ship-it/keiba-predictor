"""racedb/career.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import time


class Career:
    @staticmethod
    def _horse_key(h: dict) -> str:
        ext=str(h.get("_jraHorseCname") or h.get("_netkeibaHorseId") or h.get("horseId") or "").strip()
        if ext:return "id:"+ext
        name=str(h.get("name") or "").strip()
        return "name:"+name if name else ""


    @staticmethod
    def _run_key(rr: dict) -> str:
        base="|".join(str(rr.get(k) or "") for k in ("raceId","date","track","title","distance","finish","timeSeconds"))
        return hashlib.sha1(base.encode("utf-8","ignore")).hexdigest()


    def upsert_past_runs(self, horse: dict, runs: list[dict]) -> int:
        if not isinstance(horse,dict) or not runs:return 0
        hk=self._horse_key(horse)
        if not hk:return 0
        now=int(time.time());count=0
        conn=sqlite3.connect(self.path,timeout=5)
        try:
            for rr in runs:
                if not isinstance(rr,dict):continue
                rr=self._ports._strip_excluded(rr)
                rk=self._run_key(rr)
                conn.execute(
                    """INSERT INTO past_runs(horse_key,run_key,race_date,track,title,distance,surface,condition,weather,finish,time_seconds,agari3f,agari_rank,frame_no,horse_no,carried_weight,jockey,corner_json,opponent_level,representative,source,updated_at,raw_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(horse_key,run_key) DO UPDATE SET updated_at=excluded.updated_at,raw_json=excluded.raw_json,
                       agari3f=COALESCE(excluded.agari3f,past_runs.agari3f),agari_rank=COALESCE(excluded.agari_rank,past_runs.agari_rank),
                       opponent_level=COALESCE(excluded.opponent_level,past_runs.opponent_level),representative=MAX(past_runs.representative,excluded.representative)""",
                    (hk,rk,str(rr.get("date") or ""),str(rr.get("track") or ""),str(rr.get("title") or ""),int(rr.get("distance") or 0),str(rr.get("surface") or ""),
                     str(rr.get("condition") or ""),str(rr.get("weather") or ""),int(rr.get("finish") or 0),rr.get("timeSeconds"),rr.get("agari3f") or rr.get("agari"),
                     rr.get("agariRank") or rr.get("agari_rank"),int(rr.get("frameNumber") or 0),int(rr.get("horseNumber") or 0),rr.get("carriedWeight"),str(rr.get("jockey") or ""),
                     json.dumps(rr.get("cornerPositions") or [],ensure_ascii=False,separators=(",",":")),rr.get("opponentLevel"),1 if rr.get("representative") else 0,
                     str(rr.get("source") or ""),now,json.dumps(rr,ensure_ascii=False,separators=(",",":"),default=str)))
                count+=1
            conn.commit();return count
        finally:conn.close()


    def source_updated(self, source_key: str) -> int:
        conn=sqlite3.connect(self.path,timeout=2);conn.row_factory=sqlite3.Row
        try:
            row=conn.execute("SELECT updated_at FROM source_state WHERE source_key=?",(source_key,)).fetchone()
            return int(row["updated_at"] or 0) if row else 0
        finally:conn.close()


    def mark_source(self, source_key: str, status: str = "done", note: str = "") -> None:
        conn=sqlite3.connect(self.path,timeout=2)
        try:
            conn.execute("INSERT INTO source_state(source_key,updated_at,status,note) VALUES(?,?,?,?) ON CONFLICT(source_key) DO UPDATE SET updated_at=excluded.updated_at,status=excluded.status,note=excluded.note",
                         (source_key,int(time.time()),status,note[:500]))
            conn.commit()
        finally:conn.close()

