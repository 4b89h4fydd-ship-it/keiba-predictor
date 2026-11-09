"""NAR race surface must be served from the stored official value.

Regression (2026-11-09 NAR misjudgement diagnosis): the official CSV
sync stores races.surface (fill-only, via
arvexq.ingest.nar_official_metadata.update_race_metadata) and past
runs carried it, but the three serving builders
(nar_race_summaries / nar_race_detail / _fast_local_race_detail)
hardcoded "surface":"" — so the target race's surface was empty for
100% of NAR races and the ability layer's surface feature (frozen
NAR weight 0.05) never fired in production forecasts.
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _build_db(path: Path, with_surface_column: bool = True) -> None:
    import app
    store = app.NarStore(path)
    try:
        conn = store.conn
        conn.execute(
            "INSERT INTO races(track,date,race_no,start_time,scheduled_start_time,"
            "title,distance,weather,condition,field_size,prize1,prize2,prize3,"
            "prize4,prize5,corners_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("園田", "2026-11-04", 1, "11:45", "11:45", "テスト", 820,
             "晴", "稍重", 3, 700000, 0, 0, 0, 0, "[]"))
        for no in (1, 2, 3):
            conn.execute(
                "INSERT INTO entries(track,date,race_no,frame_no,horse_no,name,"
                "sex,age,carried_weight,jockey,trainer,status,finish,"
                "time_seconds,corner_positions_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("園田", "2026-11-04", 1, no, no, "馬" + str(no), "牡", 4,
                 56.0, "騎手", "調教師", "", no, 50.0 + no, "[]"))
        conn.commit()
        if with_surface_column:
            from arvexq.ingest.nar_official_metadata import (
                migrate_race_metadata, update_race_metadata)
            migrate_race_metadata(conn)
            changed = update_race_metadata(
                conn, ("園田", "2026-11-04", 1),
                {"surface": "ダート", "direction": "右", "class_condition": ""})
            assert changed
            conn.commit()
    finally:
        store.conn.close()


class NarSurfaceServing(unittest.TestCase):
    def test_all_builders_serve_stored_surface(self):
        import app
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "nar.sqlite3"
            _build_db(path)
            real_store = app.NarStore
            with patch.object(app, "DB_PATH", path), \
                    patch.object(app, "NarStore",
                                 lambda *a, **k: real_store(path)):
                summaries = app.nar_race_summaries("2026-11-04")
                detail = app.nar_race_detail("nar-2026-11-04-園田-01")
                fast = app._fast_local_race_detail("nar-2026-11-04-園田-01")
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["surface"], "ダート")
        self.assertEqual(summaries[0]["condition"], "稍重")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["surface"], "ダート")
        self.assertEqual(detail["condition"], "稍重")
        self.assertIsNotNone(fast)
        self.assertEqual(fast["surface"], "ダート")

    def test_builders_tolerate_legacy_db_without_surface_column(self):
        # A races table created before the metadata migration (no
        # surface column) must still serve, with surface empty —
        # never crash, never invent a value.
        import app
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "nar.sqlite"
            db = sqlite3.connect(path)
            db.execute("""CREATE TABLE races(track TEXT,date TEXT,race_no INTEGER,field_size INTEGER,
                title TEXT,distance INTEGER,condition TEXT,weather TEXT,prize1 INTEGER,
                start_time TEXT,scheduled_start_time TEXT)""")
            db.execute("""CREATE TABLE entries(track TEXT,date TEXT,race_no INTEGER,horse_no INTEGER,
                frame_no INTEGER,name TEXT,finish INTEGER,time_seconds REAL,corner_positions_json TEXT)""")
            db.execute("INSERT INTO races VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                       ("園田", "2026-11-04", 1, 3, "テスト", 820, "良", "晴",
                        100, "11:45", "11:45"))
            for no in (1, 2, 3):
                db.execute("INSERT INTO entries VALUES(?,?,?,?,?,?,?,?,?)",
                           ("園田", "2026-11-04", 1, no, no, "馬" + str(no),
                            no, 50.0, "[]"))
            db.commit()
            db.close()
            with patch.object(app, "DB_PATH", path):
                summaries = app.nar_race_summaries("2026-11-04")
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["surface"], "")


if __name__ == "__main__":
    unittest.main()
