"""Regression tests for non-destructive NAR metadata preservation."""
import sqlite3
import unittest
from arvexq.ingest.nar_official_metadata import (
    official_race_metadata, migrate_race_metadata, update_race_metadata, audit_official_race_metadata,
)


class NarOfficialMetadataTests(unittest.TestCase):
    def test_official_csv_completeness_audit(self):
        rows = [["金沢", "ダート", "右", "C2"], ["金沢", "", "左", ""]]
        before = [list(row) for row in rows]
        audit = audit_official_race_metadata(rows, {
            "surface": 1, "direction": 2, "class_condition": 3})
        self.assertEqual(audit["raceRows"], 2)
        self.assertEqual(audit["observed"], {
            "surface": 1, "direction": 2, "class_condition": 1})
        self.assertEqual(audit["coveragePercent"]["surface"], 50.0)
        self.assertEqual(rows, before)

    def test_read_only_archive_coverage_report(self):
        import csv
        import io
        import tempfile
        import zipfile
        from pathlib import Path
        from scripts.arvexq_nar_csv_coverage import audit
        race = [""] * 66
        for index, value in {0: "金沢", 1: "20261012", 2: "1",
                             21: "ダート", 22: "右", 27: "C2"}.items():
            race[index] = value
        horse = [""] * 35
        for index, value in {0: "金沢", 1: "20261012", 2: "1",
                             5: "1", 6: "検証馬", 16: "▲ 51.0"}.items():
            horse[index] = value
        with tempfile.TemporaryDirectory() as temp:
            archive_path = Path(temp) / "source.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name, rows in (("sample_racelist.csv", [race]),
                                   ("sample_horselist.csv", [horse])):
                    stream = io.StringIO()
                    csv.writer(stream).writerows(rows)
                    archive.writestr(name, stream.getvalue().encode("utf-8-sig"))
            original_bytes = archive_path.read_bytes()
            result = audit([archive_path])
            self.assertEqual(result["raceMetadata"]["raceRows"], 1)
            self.assertEqual(result["raceMetadata"]["observed"]["surface"], 1)
            self.assertEqual(result["horseRowsWithRace"], 1)
            self.assertEqual(result["raceRowsWithHorseEntries"], 1)
            self.assertEqual(result["raceRowsWithoutHorseEntries"], 0)
            self.assertEqual(result["horseRowsMatchingRacePercent"], 100.0)
            self.assertEqual(result["horseRowsWithCarriedWeight"], 1)
            self.assertEqual(original_bytes, archive_path.read_bytes())

    def test_overlapping_daily_monthly_archives_do_not_duplicate_runs(self):
        import csv
        import io
        import tempfile
        import zipfile
        from pathlib import Path
        from arvexq.databanks.nar_official_csv import NarOfficialArchive
        race = [""] * 66
        for index, value in {0: "金沢", 1: "20261012", 2: "1", 23: "1400"}.items():
            race[index] = value
        horse = [""] * 35
        for index, value in {0: "金沢", 1: "20261012", 2: "1", 5: "1",
                             6: "検証馬", 31: "1"}.items():
            horse[index] = value
        with tempfile.TemporaryDirectory() as folder:
            archives = []
            for name in ("daily.zip", "monthly.zip"):
                path = Path(folder) / name
                with zipfile.ZipFile(path, "w") as bundle:
                    for member, rows in (("sample_racelist.csv", [race]),
                                         ("sample_horselist.csv", [horse])):
                        stream = io.StringIO()
                        csv.writer(stream).writerows(rows)
                        bundle.writestr(member, stream.getvalue().encode("utf-8-sig"))
                archives.append(path)
            result = NarOfficialArchive(archives).horse_history(
                {"name": "検証馬"}, {"date": "2026-10-13"}, limit=30)
            self.assertEqual(len(result["allPastRuns"]), 1)
            self.assertEqual(len(result["recentRaces"]), 1)

    def test_archive_history_carries_official_context(self):
        import csv
        import io
        import tempfile
        import zipfile
        from pathlib import Path
        from arvexq.databanks.nar_official_csv import NarOfficialArchive
        race = [""] * 66
        for idx, val in {0: "金沢", 1: "20261012", 2: "1", 21: "ダート",
                         22: "右", 23: "1400", 24: "雨", 25: "重",
                         26: "2", 27: "C2"}.items():
            race[idx] = val
        horse = [""] * 35
        for idx, val in {0: "金沢", 1: "20261012", 2: "1",
                         3: "1", 5: "1", 6: "検証馬", 14: "騎手",
                         16: "▲ 51.0", 31: "1"}.items():
            horse[idx] = val
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "nar.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name, rows in (("x_racelist.csv", [race]),
                                   ("x_horselist.csv", [horse])):
                    output = io.StringIO()
                    csv.writer(output).writerows(rows)
                    archive.writestr(name, output.getvalue().encode("utf-8-sig"))
            history = NarOfficialArchive([archive_path]).horse_history(
                {"name": "検証馬"}, {"date": "2026-10-13"})
            row = history["allPastRuns"][0]
            for field, expected in (("surface", "ダート"), ("direction", "右"),
                                    ("weather", "雨"), ("condition", "重"),
                                    ("class", "C2"), ("carriedWeight", 51.0)):
                self.assertEqual(row[field], expected)

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
