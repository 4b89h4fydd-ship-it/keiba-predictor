"""prepared/store.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import time
from arvexq.storage.config import PREPARED_DB_PATH
from arvexq.infra.pure_snapshots import _racedb_snapshot_usable
from arvexq.infra.snapshot_status import _snapshot_final
from arvexq.prediction.prerace_archive import sealed_lock as _arvexq_sealed_lock
from arvexq.prediction.mass_prerace_bridge import prepare_mass_prerace_fields, apply_mass_prerace_fields, frozen_mass_fields
from arvexq.selection.race_selectability_snapshot import prepare_race_selectability_fields, apply_race_selectability_fields, frozen_selectability_fields


from pathlib import Path

class PreparedRaceStore:
    def __init__(self, path: Path = PREPARED_DB_PATH, *, ports):
        self._ports = ports
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=3)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS prepared_races (
                    race_id TEXT PRIMARY KEY,
                    race_date TEXT NOT NULL DEFAULT '',
                    circuit TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prepared_date ON prepared_races(race_date, circuit)")
            conn.execute("CREATE TABLE IF NOT EXISTS horse_snapshots(race_id TEXT,horse_no INTEGER,payload TEXT NOT NULL,PRIMARY KEY(race_id,horse_no))")
            conn.execute("CREATE VIEW IF NOT EXISTS race_snapshot AS SELECT * FROM prepared_races")
            conn.execute("CREATE VIEW IF NOT EXISTS horse_snapshot AS SELECT * FROM horse_snapshots")
            conn.commit()
        finally:
            conn.close()


    def get(self, race_id: str) -> tuple[dict | None, int]:
        conn = sqlite3.connect(self.path, timeout=2)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT updated_at,payload FROM prepared_races WHERE race_id=?", (race_id,)).fetchone()
            if not row:
                return None, 0
            try:
                return json.loads(row["payload"]), int(row["updated_at"] or 0)
            except Exception:
                return None, 0
        finally:
            conn.close()


    def put(self, detail: dict, force: bool = False) -> None:
        race_id = str(detail.get("id") or "")
        if not race_id:
            return
        if not _racedb_snapshot_usable(detail):
            return
        mass_fields=prepare_mass_prerace_fields(detail)
        selectability_fields=prepare_race_selectability_fields(detail)
        now = int(time.time())
        detail.setdefault("preparedMeta", {})
        revision_data={k:v for k,v in detail.items() if k!="preparedMeta"}
        detail["preparedMeta"]["revision"]=hashlib.sha256(json.dumps(revision_data,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()[:24]
        detail["preparedMeta"].update({
            "build": "v87",
            "prepared": True,
            "preparedAtEpoch": now,
            "metricsPrecomputed": True,
        })
        clean=self._ports._compact_display_snapshot(self._ports._strip_excluded(detail))
        detail.clear();detail.update(clean)
        if mass_fields:apply_mass_prerace_fields(detail,mass_fields)
        if selectability_fields:apply_race_selectability_fields(detail,selectability_fields)
        payload = json.dumps(detail, ensure_ascii=False, separators=(",", ":"))
        conn = sqlite3.connect(self.path, timeout=3)
        try:
            conn.execute("BEGIN IMMEDIATE")
            old=conn.execute("SELECT payload FROM prepared_races WHERE race_id=?",(race_id,)).fetchone()
            if old:
                previous=json.loads(old[0])
                if isinstance(previous.get("preRacePrediction"),dict) and (_arvexq_sealed_lock(previous) or self._ports._prediction_clock_state(detail)[0]=="started" or not isinstance(detail.get("preRacePrediction"),dict)):
                    detail["preRacePrediction"]=previous["preRacePrediction"]
                    previous_mass=frozen_mass_fields(previous)
                    if previous_mass:apply_mass_prerace_fields(detail,previous_mass)
                    previous_selectability=frozen_selectability_fields(previous)
                    if previous_selectability:apply_race_selectability_fields(detail,previous_selectability)
                    audit=self._ports._prediction_audit_from_lock(detail)
                    if audit:detail["predictionAudit"]=audit
                    payload=json.dumps(detail,ensure_ascii=False,separators=(",",":"))
                prev_meta=previous.get("preparedMeta") or {}
                prev_payouts=((previous.get("result") or {}).get("payouts") or [])
                new_payouts=((detail.get("result") or {}).get("payouts") or [])
                frozen=_snapshot_final(previous) or str(previous.get("date") or "")<self._ports._today_iso()
                can_upgrade=bool(force or prev_meta.get("fastPartial") or (not prev_payouts and new_payouts))
                if _racedb_snapshot_usable(previous) and frozen and not can_upgrade:
                    detail.clear();detail.update(previous)
                    return
            conn.execute(
                """
                INSERT INTO prepared_races(race_id,race_date,circuit,updated_at,payload)
                VALUES(?,?,?,?,?)
                ON CONFLICT(race_id) DO UPDATE SET
                    race_date=excluded.race_date,
                    circuit=excluded.circuit,
                    updated_at=excluded.updated_at,
                    payload=excluded.payload
                """,
                (race_id, str(detail.get("date") or ""), str(detail.get("circuit") or ""), now, payload),
            )
            conn.execute("DELETE FROM horse_snapshots WHERE race_id=?",(race_id,))
            conn.executemany("INSERT OR REPLACE INTO horse_snapshots(race_id,horse_no,payload) VALUES(?,?,?)",[(race_id,int(h.get("horseNumber") or 0),json.dumps(h,ensure_ascii=False)) for h in detail.get("horses",[])])
            conn.commit()
        finally:
            conn.close()


    def delete(self, race_id: str) -> None:
        conn = sqlite3.connect(self.path, timeout=2)
        try:
            conn.execute("DELETE FROM prepared_races WHERE race_id=?", (race_id,))
            conn.commit()
        finally:
            conn.close()


    def status(self, race_date: str = "", circuit: str = "") -> dict:
        conn = sqlite3.connect(self.path, timeout=2)
        conn.row_factory = sqlite3.Row
        try:
            where=[]; args=[]
            if race_date:
                where.append("race_date=?"); args.append(race_date)
            if circuit:
                where.append("circuit=?"); args.append(circuit)
            sql="SELECT COUNT(*) cnt, MAX(updated_at) last FROM prepared_races"
            if where: sql += " WHERE " + " AND ".join(where)
            row=conn.execute(sql,args).fetchone()
            return {"count":int(row["cnt"] or 0),"last":int(row["last"] or 0)}
        finally:
            conn.close()

