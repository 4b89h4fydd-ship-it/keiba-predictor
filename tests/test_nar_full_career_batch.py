"""Local NAR diagnosis may display five runs, never erase older observed starts."""
from __future__ import annotations

import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from arvexq.ingest.career_transport import pack_horse
from arvexq.prediction.career_readiness import assess_career_readiness


def run(iso: str, source: str = "archive") -> dict:
    return {
        "date": iso, "track": "大井", "raceNumber": 1,
        "fieldSize": 12, "distance": 1200, "finish": 3,
        "timeSeconds": 73.2, "source": source,
    }


class NarFullCareerBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "nar.db"
        conn = sqlite3.connect(self.path)
        try:
            conn.executescript("""
                CREATE TABLE entries (
                    name TEXT, date TEXT, track TEXT, race_no INTEGER,
                    age INTEGER NOT NULL DEFAULT 0, sex TEXT NOT NULL DEFAULT '',
                    finish INTEGER, time_seconds REAL,
                    corner_positions_json TEXT, carried_weight REAL,
                    jockey TEXT, trainer TEXT
                );
                CREATE TABLE races (
                    track TEXT, date TEXT, race_no INTEGER,
                    title TEXT, distance INTEGER, weather TEXT,
                    condition TEXT, field_size INTEGER, prize1 INTEGER
                );
            """)
            for month in range(1, 9):
                iso=f"2026-{month:02d}-10"
                conn.execute("INSERT INTO races VALUES (?,?,?,?,?,?,?,?,?)",
                             ("大井", iso, 1, "C1", 1200, "晴", "良", 12, 100))
                conn.execute("INSERT INTO entries(name,date,track,race_no,finish,time_seconds,corner_positions_json,carried_weight,jockey,trainer) VALUES (?,?,?,?,?,?,?,?,?,?)",
                             ("全履歴馬", iso, "大井", 1, 2, 73.2, "[2,3,3,2]", 55.0, "J", "T"))
            # The race itself and future rows must never leak into the pre-off model.
            for iso in ("2026-10-11", "2026-10-12"):
                conn.execute("INSERT INTO races VALUES (?,?,?,?,?,?,?,?,?)",
                             ("大井", iso, 1, "C1", 1200, "晴", "良", 12, 100))
                conn.execute("INSERT INTO entries(name,date,track,race_no,finish,time_seconds,corner_positions_json,carried_weight,jockey,trainer) VALUES (?,?,?,?,?,?,?,?,?,?)",
                             ("全履歴馬", iso, "大井", 1, 1, 70.0, "[]", 55.0, "J", "T"))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def fixture():
        archive_rows = [run(f"2025-{month:02d}-01") for month in range(1, 8)]
        h = pack_horse({
            "horseNumber": 1, "name": "全履歴馬",
            "allPastRuns": archive_rows, "recentRaces": archive_rows[-5:],
            "_careerHistoryAudit": {
                "version": "arvexq-career-coverage-v1", "requestedAtRaceDate": "2026-10-11",
                "reportedStarts": 18, "observedRuns": 7, "complete": False,
            },
        }, "2026-10-11")
        return {
            "id": "nar-2026-10-11-大井-11",
            "date": "2026-10-11", "circuit": "地方",
            "horses": [h, {"horseNumber": 2, "name": "履歴なし", "allPastRuns": [],
                            "recentRaces": []}],
            "preRacePrediction": {"frozen": True, "raceId": "preserved"},
            "preRaceBet": {"fixedBeforePost": True, "items": [{"kind": "ワイド"}]},
        }

    def test_all_local_and_archived_runs_retained_but_recent_display_is_five(self):
        import app
        source=self.fixture()
        original=copy.deepcopy(source)
        with patch.object(app, "DB_PATH", self.path):
            detail=app._nar_attach_recent_batch(source, 5)
        horse=detail["horses"][0]
        self.assertEqual(len(horse["allPastRuns"]), 15)
        self.assertEqual(len(horse["recentRaces"]), 5)
        self.assertEqual(horse["allPastRuns"][0]["date"], "2026-08-10")
        self.assertEqual(horse["allPastRuns"][-1]["date"], "2025-01-01")
        self.assertNotIn("2026-10-11", [r["date"] for r in horse["allPastRuns"]])
        self.assertNotIn("2026-10-12", [r["date"] for r in horse["allPastRuns"]])
        self.assertEqual(horse["_careerHistoryAudit"]["complete"], False)
        self.assertEqual(detail["preRacePrediction"], original["preRacePrediction"])
        self.assertEqual(detail["preRaceBet"], original["preRaceBet"])
        self.assertEqual(detail["horses"][1]["allPastRuns"], [])
        # Fifteen observed starts are still NOT a verified full lifetime if
        # the date-bound official reported count is eighteen.
        readiness=assess_career_readiness(detail)
        self.assertFalse(readiness["ready"])
        self.assertEqual(readiness["blockedHorses"][0]["observedRuns"], 15)

    def test_same_name_other_birth_year_is_not_imported(self):
        import app
        detail=self.fixture()
        detail["horses"][0]["age"]=4  # 2023 birth year in 2026
        detail["horses"][0]["sex"]="牡"
        conn=sqlite3.connect(self.path)
        try:
            conn.execute("INSERT INTO races VALUES (?,?,?,?,?,?,?,?,?)",
                         ("大井","2026-09-10",1,"C1",1200,"晴","良",12,100))
            conn.execute("""INSERT INTO entries
                (name,date,track,race_no,age,sex,finish,time_seconds,corner_positions_json,
                 carried_weight,jockey,trainer)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("全履歴馬","2026-09-10","大井",1,2,"牡",2,73.2,"[]",55.0,"J","T"))
            conn.commit()
        finally:
            conn.close()
        with patch.object(app,"DB_PATH",self.path):
            got=app._nar_attach_recent_batch(detail,5)
        dates={r["date"] for r in got["horses"][0]["allPastRuns"]}
        self.assertNotIn("2026-09-10",dates,"different birth year must not enter career")
        self.assertIn("2026-08-10",dates,"compatible observed history must survive")

    def test_same_day_sources_deduplicate_without_losing_official_fields(self):
        import app
        d=self.fixture()
        d["horses"][0]["allPastRuns"]=[run("2026-03-10", "existing"),
                                         run("2025-12-01", "existing")]
        # Restrict this fixture to the two explicitly supplied rows: the
        # first test already exercises pre-existing five-row and ZIP archives.
        d["horses"][0]["recentRaces"] = []
        d["horses"][0].pop("careerArchive", None)
        with patch.object(app, "DB_PATH", self.path):
            app._nar_attach_recent_batch(d, 5)
        rows=d["horses"][0]["allPastRuns"]
        self.assertEqual(len(rows), 9)
        self.assertEqual(len([x for x in rows if x["date"] == "2026-03-10"]), 1)
        self.assertEqual(len(d["horses"][0]["recentRaces"]), 5)


    def test_extra_feed_does_not_erase_full_career_or_frozen_bets(self):
        import app
        before=[run(f"2025-{m:02d}-01") for m in range(1,10)]
        detail={"id":"nar-2026-10-11-大井-11","date":"2026-10-11",
                "circuit":"地方","horses":[{
                    "horseNumber":1,"name":"全履歴馬",
                    "allPastRuns":copy.deepcopy(before),
                    "recentRaces":copy.deepcopy(before[:5]),
                    "_careerHistoryAudit":{"reportedStarts":15,"complete":False}}],
                "preRacePrediction":{"fixedAt":"2026-10-11T09:30:00+09:00"},
                "preRaceBet":{"fixedAt":"2026-10-11T09:30:00+09:00",
                              "items":[{"kind":"馬連","combos":[[1,2]]}]}}
        original=copy.deepcopy(detail)
        extra=[run("2025-07-01","secondary"),run("2026-09-01","secondary"),
               run("2026-10-11","future"),run("2026-10-12","future")]
        updated=app._merge_enrichment(detail,{"extra":[
            {"source":"supplement","rows":[{
                "horseNumber":1,"name":"全履歴馬",
                "extra":{"allPastRuns":extra}}]}]})
        h=updated["horses"][0]
        self.assertEqual(len(h["allPastRuns"]),10,"one genuinely new past race")
        self.assertEqual(len(h["recentRaces"]),5)
        self.assertEqual(len([x for x in h["allPastRuns"]
                              if x["date"]=="2025-07-01"]),1)
        self.assertEqual(h["_careerHistoryAudit"],original["horses"][0]["_careerHistoryAudit"])
        self.assertTrue(all(x["date"]<"2026-10-11" for x in h["allPastRuns"]))
        self.assertEqual(updated["preRacePrediction"],original["preRacePrediction"])
        self.assertEqual(updated["preRaceBet"],original["preRaceBet"])


if __name__ == "__main__":
    unittest.main()
