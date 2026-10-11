"""racedb/odds.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
import json
import sqlite3
import time
from arvexq.storage.policies.market import retain_odds


class Odds:
    def save_odds(self, race_id: str, rows: list[dict], source: str = "", captured_at: int | None = None) -> int:
        if not rows:return 0
        rows=retain_odds(self.path,race_id,rows)
        # Round to 15 seconds so a polling burst cannot create pointless duplicates.
        ts=int(captured_at or time.time());ts=ts-(ts%15)
        conn=sqlite3.connect(self.path,timeout=3);count=0
        try:
            for z in rows:
                z=self._ports._strip_excluded(z)
                try:no=int(z.get("horseNumber") or 0)
                except Exception:no=0
                if no<=0:continue
                try:wo=float(z.get("winOdds")) if z.get("winOdds") not in (None,"") else None
                except Exception:wo=None
                try:pop=int(z.get("popularity")) if z.get("popularity") not in (None,"") else None
                except Exception:pop=None
                conn.execute("INSERT OR REPLACE INTO odds_history(race_id,horse_no,captured_at,win_odds,popularity,source,raw_json) VALUES(?,?,?,?,?,?,?)",
                             (race_id,no,ts,wo,pop,str(source or z.get("oddsSource") or ""),json.dumps(z,ensure_ascii=False,separators=(",",":"),default=str)))
                count+=1
            conn.commit();return count
        finally:conn.close()


    def odds_latest(self, race_id: str) -> list[dict]:
        conn=sqlite3.connect(self.path,timeout=2);conn.row_factory=sqlite3.Row
        try:
            rows=conn.execute("""SELECT o.* FROM odds_history o JOIN (SELECT horse_no,MAX(captured_at) t FROM odds_history WHERE race_id=? GROUP BY horse_no) x
                                 ON o.horse_no=x.horse_no AND o.captured_at=x.t WHERE o.race_id=? ORDER BY o.horse_no""",(race_id,race_id)).fetchall()
            return [{"horseNumber":int(r["horse_no"]),"winOdds":r["win_odds"],"popularity":r["popularity"],"oddsSource":r["source"],"capturedAt":int(r["captured_at"])} for r in rows]
        finally:conn.close()

