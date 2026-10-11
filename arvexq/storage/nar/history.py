"""nar/history.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
import json
from arvexq.normalize.scalars import _int


class NarHistory:
    def stats(self, role: str, name: str, cutoff: str) -> dict[str, int]:
        if role not in {"jockey", "trainer"} or not name:
            return {"starts": 0, "wins": 0, "seconds": 0, "thirds": 0}
        row = self.conn.execute(
            f"""
            SELECT COUNT(*) starts,
                   SUM(CASE WHEN finish=1 THEN 1 ELSE 0 END) wins,
                   SUM(CASE WHEN finish=2 THEN 1 ELSE 0 END) seconds,
                   SUM(CASE WHEN finish=3 THEN 1 ELSE 0 END) thirds
            FROM entries WHERE {role}=? AND date<? AND finish>0
            """,
            (name, cutoff),
        ).fetchone()
        return {k: int(row[k] or 0) for k in ("starts", "wins", "seconds", "thirds")}


    def role_profile(self, role: str, name: str, cutoff: str, track: str, distance: int, condition: str) -> dict:
        """Condition-aware jockey/trainer record available strictly before the target race."""
        if role not in {"jockey", "trainer"} or not name:
            return {"overall": 0.5, "track": 0.5, "distance": 0.5, "condition": 0.5,
                    "leaderRate": 0.0, "early3Rate": 0.0, "starts": 0}
        rows = self.conn.execute(
            f"""
            SELECT e.finish, e.corner_positions_json, r.track, r.distance, r.condition
            FROM entries e
            JOIN races r ON r.track=e.track AND r.date=e.date AND r.race_no=e.race_no
            WHERE e.{role}=? AND e.date<? AND e.finish>0
            ORDER BY e.date DESC, e.race_no DESC
            LIMIT 400
            """,
            (name, cutoff),
        ).fetchall()

        def rate(subset):
            if not subset:
                return 0.5
            top3 = sum(1 for x in subset if 0 < int(x["finish"] or 0) <= 3)
            return top3 / len(subset)

        track_rows = [x for x in rows if (x["track"] or "") == track]
        dist_rows = [x for x in rows if abs(int(x["distance"] or 0) - int(distance or 0)) <= 200]
        cond_rows = [x for x in rows if condition and condition != "不明" and (x["condition"] or "") == condition]
        lead = early3 = valid = 0
        for x in rows[:120]:
            try:
                pos = json.loads(x["corner_positions_json"] or "[]")
            except Exception:
                pos = []
            if not pos:
                continue
            first = _int(str(pos[0]))
            if first <= 0:
                continue
            valid += 1
            if first == 1:
                lead += 1
            if first <= 3:
                early3 += 1
        return {
            "overall": rate(rows),
            "track": rate(track_rows),
            "distance": rate(dist_rows),
            "condition": rate(cond_rows),
            "leaderRate": (lead / valid) if valid else 0.0,
            "early3Rate": (early3 / valid) if valid else 0.0,
            "starts": len(rows),
        }


    def prize_before(self, horse_name: str, cutoff: str) -> int:
        row = self.conn.execute(
            """
            SELECT COALESCE(SUM(CASE e.finish
                WHEN 1 THEN r.prize1 WHEN 2 THEN r.prize2 WHEN 3 THEN r.prize3
                WHEN 4 THEN r.prize4 WHEN 5 THEN r.prize5 ELSE 0 END), 0) AS prize
            FROM entries e
            JOIN races r ON r.track=e.track AND r.date=e.date AND r.race_no=e.race_no
WHERE e.name=? AND e.date<? AND e.finish>0
            """,
            (horse_name, cutoff),
        ).fetchone()
        return int(row["prize"] or 0)


    def recent_races(self, horse_name: str, cutoff: str, limit: int = 5) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT e.*, r.title, r.distance, r.weather, r.condition, r.field_size, r.prize1
            FROM entries e
            JOIN races r ON r.track=e.track AND r.date=e.date AND r.race_no=e.race_no
            WHERE e.name=? AND e.date<? AND e.finish>0
            ORDER BY e.date DESC, e.race_no DESC
            LIMIT ?
            """,
            (horse_name, cutoff, limit),
        ).fetchall()
        return [
            {
                "date": row["date"],
                "track": row["track"],
                "raceNumber": int(row["race_no"] or 0),
                "raceId": f"nar-{row['date']}-{row['track']}-{int(row['race_no'] or 0):02d}",
                "title": row["title"] or f"{int(row['race_no'] or 0)}R",
                "distance": int(row["distance"] or 0),
                "condition": row["condition"] or "不明",
                "weather": row["weather"] or "不明",
                "finish": int(row["finish"] or 0),
                "timeSeconds": float(row["time_seconds"] or 0),
                "cornerPositions": json.loads(row["corner_positions_json"] or "[]"),
                "fieldSize": int(row["field_size"] or 0),
                "racePrize1": int(row["prize1"] or 0),
                "carriedWeight": float(row["carried_weight"] or 0),
                "jockey": row["jockey"] or "",
                "trainer": row["trainer"] or "",
            }
            for row in rows
        ]

