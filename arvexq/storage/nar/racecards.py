"""nar/racecards.py: SQL, payload and preservation rules inherited from 19b76d3."""
from __future__ import annotations
import json
from arvexq.normalize.scalars import _stable_id


class NarRacecards:
    def races_json(self, iso_date: str) -> list[dict]:
        race_rows = self.conn.execute(
            "SELECT * FROM races WHERE date=? ORDER BY track, race_no", (iso_date,)
        ).fetchall()
        result: list[dict] = []
        for race in race_rows:
            entries = self.conn.execute(
                "SELECT * FROM entries WHERE track=? AND date=? AND race_no=? ORDER BY horse_no",
                (race["track"], iso_date, race["race_no"]),
            ).fetchall()
            if not entries:
                continue
            horses = []
            for e in entries:
                horses.append(
                    {
                        "id": _stable_id(iso_date, race["track"], race["race_no"], e["horse_no"], e["name"]),
                        "horseNumber": int(e["horse_no"]),
                        "frameNumber": int(e["frame_no"] or 0),
                        "name": e["name"],
                        "age": int(e["age"] or 0),
                        "sex": e["sex"] or "牡",
                        "carriedWeight": float(e["carried_weight"] or 0),
                        "jockey": e["jockey"] or "",
                        "trainer": e["trainer"] or "",
                        "jockeyStats": self.stats("jockey", e["jockey"], iso_date),
                        "trainerStats": self.stats("trainer", e["trainer"], iso_date),
                        "jockeyProfile": self.role_profile("jockey", e["jockey"], iso_date, race["track"], int(race["distance"] or 0), race["condition"] or "不明"),
                        "trainerProfile": self.role_profile("trainer", e["trainer"], iso_date, race["track"], int(race["distance"] or 0), race["condition"] or "不明"),
                        "prizeMoneyAtRace": self.prize_before(e["name"], iso_date),
                        "recentRaces": self.recent_races(e["name"], iso_date, 5),
                    }
                )
            finishers = []
            for e in entries:
                fin = int(e["finish"] or 0)
                if fin > 0:
                    finishers.append({
                        "finish": fin,
                        "horseNumber": int(e["horse_no"]),
                        "frameNumber": int(e["frame_no"] or 0),
                        "name": e["name"],
                        "timeSeconds": float(e["time_seconds"] or 0),
                        "cornerPositions": json.loads(e["corner_positions_json"] or "[]"),
                    })
            finishers.sort(key=lambda x: (x["finish"], x["horseNumber"]))
            need = min(3, len(entries))
            ranks = {x["finish"] for x in finishers}
            finalized = need > 0 and all(i in ranks for i in range(1, need + 1))
            result_obj = {"status": "確定", "finishers": finishers} if finalized else None
            result.append(
                {
                    "id": f"nar-{iso_date}-{race['track']}-{int(race['race_no']):02d}",
                    "circuit": "地方",
                    "date": iso_date,
                    "track": race["track"],
                    "raceNumber": int(race["race_no"]),
                    "title": race["title"] or f"{int(race['race_no'])}R",
                    "distance": int(race["distance"] or 0),
                    "condition": race["condition"] or "不明",
                    "weather": race["weather"] or "不明",
                    "fieldSize": int(race["field_size"] or len(entries)),
                    "racePrize1": int(race["prize1"] or 0),
                    "surface": "",
                    "startTime": race["start_time"] or "",
                    "scheduledStartTime": race["scheduled_start_time"] or race["start_time"] or "",
                    "startTimeChanged": bool((race["scheduled_start_time"] or "") and (race["start_time"] or "") and race["scheduled_start_time"] != race["start_time"]),
                    "horses": horses,
                    "result": result_obj,
                    "source": "NAR公式",
                }
            )
        return result


    def coverage(self) -> dict:
        row = self.conn.execute("SELECT MIN(date) min_date, MAX(date) max_date FROM races").fetchone()
        return {"minDate": row["min_date"], "maxDate": row["max_date"]}

