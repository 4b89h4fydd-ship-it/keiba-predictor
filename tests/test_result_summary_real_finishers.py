"""Canonical result summaries use actual recorded finishers, not dummy ranks."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class RealResultSummaries(unittest.TestCase):
    def test_nar_summary_contains_real_podium_from_same_entries_db(self):
        import app
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"nar.sqlite"
            db=sqlite3.connect(path)
            db.execute("""CREATE TABLE races(track TEXT,date TEXT,race_no INTEGER,field_size INTEGER,
                title TEXT,distance INTEGER,condition TEXT,weather TEXT,prize1 INTEGER,
                start_time TEXT,scheduled_start_time TEXT)""")
            db.execute("""CREATE TABLE entries(track TEXT,date TEXT,race_no INTEGER,horse_no INTEGER,
                frame_no INTEGER,name TEXT,finish INTEGER,time_seconds REAL,corner_positions_json TEXT)""")
            db.execute("INSERT INTO races VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                ("大井","2026-10-12",1,3,"テスト結果",1200,"良","晴",100,"10:05","10:05"))
            for no,finish in [(3,1),(1,2),(2,3)]:
                db.execute("INSERT INTO entries VALUES(?,?,?,?,?,?,?,?,?)",
                    ("大井","2026-10-12",1,no,no,"馬"+str(no),finish,72.1,"[1,2,3]"))
            db.commit();db.close()
            with patch.object(app,"DB_PATH",path):
                summary=app.nar_race_summaries("2026-10-12")
        self.assertEqual(len(summary),1)
        self.assertEqual(summary[0]["result"]["status"],"確定")
        self.assertEqual([(x["finish"],x["horseNumber"]) for x in summary[0]["result"]["finishers"]],
                         [(1,3),(2,1),(3,2)])
        self.assertEqual(summary[0]["result"]["finishers"][0]["name"],"馬3")

    def test_no_synthetic_podium_in_jra_summary(self):
        text=Path("app.py").read_text(encoding="utf-8")
        self.assertNotIn('[{"finish":1}]',text)


if __name__=="__main__":
    unittest.main()
