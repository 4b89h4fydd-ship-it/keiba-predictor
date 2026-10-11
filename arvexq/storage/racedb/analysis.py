"""racedb/analysis.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
import json
import sqlite3
import time
from arvexq.storage.policies.market import retain_analysis


class Analysis:
    def save_analysis(self, race_id: str, payload: dict) -> None:
        if not race_id or not isinstance(payload,dict):return
        payload=retain_analysis(self.path,race_id,payload)
        payload=self._ports._strip_excluded(payload)
        scenarios=payload.get("scenarios") or {}
        horses=payload.get("horses") or []
        now=int(time.time())
        conn=sqlite3.connect(self.path,timeout=3)
        try:
            conn.execute("INSERT INTO race_analysis(race_id,updated_at,scenario_json,horse_diagnosis_json,raw_json) VALUES(?,?,?,?,?) ON CONFLICT(race_id) DO UPDATE SET updated_at=excluded.updated_at,scenario_json=excluded.scenario_json,horse_diagnosis_json=excluded.horse_diagnosis_json,raw_json=excluded.raw_json",
                         (race_id,now,json.dumps(scenarios,ensure_ascii=False,separators=(",",":"),default=str),json.dumps(horses,ensure_ascii=False,separators=(",",":"),default=str),json.dumps(payload,ensure_ascii=False,separators=(",",":"),default=str)))
            conn.commit()
        finally:conn.close()


    def get_analysis(self, race_id: str) -> dict | None:
        conn=sqlite3.connect(self.path,timeout=2);conn.row_factory=sqlite3.Row
        try:
            row=conn.execute("SELECT raw_json FROM race_analysis WHERE race_id=?",(race_id,)).fetchone()
            return json.loads(row["raw_json"]) if row else None
        except Exception:return None
        finally:conn.close()

