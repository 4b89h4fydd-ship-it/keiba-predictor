"""Regression tests for non-destructive NAR metadata preservation."""
import sqlite3
import unittest
from arvexq.ingest.nar_official_metadata import (
    official_race_metadata, migrate_race_metadata, update_race_metadata,
)


class NarOfficialMetadataTests(unittest.TestCase):
    def test_existing_rows_survive_migration_and_missing_csv_values(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE races(track TEXT,date TEXT,race_no INTEGER,title TEXT)")
        conn.execute("INSERT INTO races VALUES ('金沢','2026-10-12',1,'原本')")
        migrate_race_metadata(conn)
        migrate_race_metadata(conn)
        fields = [row[1] for row in conn.execute("PRAGMA table_info(races)")]
        self.assertEqual(len(fields), len(set(fields)))
        parsed = official_race_metadata(
            ["金沢", "ダート", "右", "C2"], {"surface": 1, "direction": 2, "class_condition": 3})
        self.assertTrue(update_race_metadata(conn, ("金沢", "2026-10-12", 1), parsed))
        self.assertFalse(update_race_metadata(conn, ("金沢", "2026-10-12", 1), {
            "surface": "", "direction": "", "class_condition": ""}))
        row = conn.execute("SELECT title,surface,direction,class_condition FROM races").fetchone()
        self.assertEqual(row, ("原本", "ダート", "右", "C2"))
        self.assertEqual(official_race_metadata(["金沢"], {"surface": 21}), {
            "surface": "", "direction": "", "class_condition": ""})


if __name__ == "__main__":
    unittest.main()
