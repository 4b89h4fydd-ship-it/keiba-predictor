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


    def test_real_archive_ingestion_store_and_readback(self):
        """Exercise actual importer against a deterministic official-shaped ZIP."""
        import io
        import zipfile
        import tempfile
        from pathlib import Path
        from app import NarArchiveParser, NarStore, RACE_IDX, HORSE_IDX

        race = [""] * 66
        for key, value in {
            "track": "金沢", "date": "20261012", "race_no": "1",
            "start_time": "1200", "title": "公式検証",
            "surface": "ダート", "direction": "右", "distance": "1400",
            "weather": "晴", "condition": "良", "field_size": "2",
            "class_condition": "C2",
        }.items():
            race[RACE_IDX[key]] = value
        entries = []
        for num, finish in ((1, 1), (2, 2)):
            horse = [""] * 34
            for key, value in {
                "track": "金沢", "date": "20261012", "race_no": "1",
                "frame_no": str(num), "horse_no": str(num),
                "name": f"検証馬{num}", "sex": "牡", "age": "4",
                "jockey": "検証騎手", "carried_weight": "▲ 51.0",
                "trainer": "検証厩舎", "finish": str(finish),
                "time": "1300",
            }.items():
                horse[HORSE_IDX[key]] = value
            entries.append(horse)

        def csv_bytes(rows):
            import csv
            output = io.StringIO()
            csv.writer(output).writerows(rows)
            return output.getvalue().encode("utf-8-sig")

        zipped = io.BytesIO()
        with zipfile.ZipFile(zipped, "w") as archive:
            archive.writestr("audit_racelist.csv", csv_bytes([race]))
            archive.writestr("audit_horselist.csv", csv_bytes(entries))
        with tempfile.TemporaryDirectory() as temp:
            store = NarStore(Path(temp) / "nar.sqlite3")
            # Exercise the same production importer entry point.
            from app import NarSync
            sync = NarSync.__new__(NarSync)
            sync.parser = NarArchiveParser()
            sync.store = store
            sync.import_zip_bytes(zipped.getvalue(), "test-archive", Path(temp) / "source.zip")
            saved = store.conn.execute(
                "SELECT title,surface,direction,class_condition,weather,condition FROM races"
            ).fetchone()
            self.assertEqual(tuple(saved), ("公式検証", "ダート", "右", "C2", "晴", "良"))
            current = store.races_json("2026-10-12")
            self.assertEqual(current[0]["surface"], "ダート")
            self.assertEqual(current[0]["direction"], "右")
            self.assertEqual(current[0]["class"], "C2")
            later = store.recent_races("検証馬1", "2026-10-13")
            self.assertEqual(later[0]["surface"], "ダート")
            self.assertEqual(later[0]["class"], "C2")
            self.assertEqual(later[0]["carriedWeight"], 51.0)
            store.conn.close()


if __name__ == "__main__":
    unittest.main()
