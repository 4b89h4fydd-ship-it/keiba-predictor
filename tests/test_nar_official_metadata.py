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
            as_of = audit([archive_path], target_date="2026-10-12")
            self.assertEqual(as_of["targetHorsesWithRaceRows"], 1)
            self.assertEqual(as_of["targetHorsesWithNoEarlierArchiveRuns"], 1)
            self.assertEqual(as_of["targetHorsesWithEarlierArchiveRuns"], 0)
            self.assertEqual(result["raceRowsWithHorseEntries"], 1)
            self.assertEqual(result["raceRowsWithoutHorseEntries"], 0)
            self.assertEqual(result["raceKeysWithoutHorseEntries"], [])
            self.assertEqual(result["unmatchedHorseRowsByTrack"], {})
            self.assertEqual(result["unmatchedHorseRaceKeys"], [])
            self.assertEqual(result["horseRowsMatchingRacePercent"], 100.0)
            self.assertEqual(result["horseRowsWithCarriedWeight"], 1)
            self.assertEqual(original_bytes, archive_path.read_bytes())

    def test_same_name_different_birthdates_require_identity(self):
        import csv
        import io
        import tempfile
        import zipfile
        from pathlib import Path
        from arvexq.databanks.nar_official_csv import NarOfficialArchive
        races, horses = [], []
        for date, born in (("20261010", "20200101"), ("20261011", "20210101")):
            race = [""] * 66
            horse = [""] * 35
            for row in (race, horse):
                row[0], row[1], row[2] = "金沢", date, "1"
            horse[5], horse[6], horse[10], horse[31] = "1", "同名検証馬", born, "1"
            races.append(race)
            horses.append(horse)
        with tempfile.TemporaryDirectory() as folder:
            archive_path = Path(folder) / "official.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for filename, rows in (("sample_racelist.csv", races),
                                       ("sample_horselist.csv", horses)):
                    stream = io.StringIO()
                    csv.writer(stream).writerows(rows)
                    archive.writestr(filename, stream.getvalue().encode("utf-8-sig"))
            source = NarOfficialArchive([archive_path])
            race = {"date": "2026-10-12"}
            self.assertEqual(source.horse_history({"name": "同名検証馬"}, race), {})
            identified = source.horse_history(
                {"name": "同名検証馬", "birthDate": "2020-01-01"}, race)
            self.assertEqual(len(identified["allPastRuns"]), 1)
            self.assertEqual(identified["allPastRuns"][0]["date"], "2026-10-10")

    def test_history_excludes_target_day_and_future_results(self):
        import csv
        import io
        import tempfile
        import zipfile
        from pathlib import Path
        from arvexq.databanks.nar_official_csv import NarOfficialArchive
        race_rows, horse_rows = [], []
        for day in (10, 12, 14):
            date = f"202610{day:02d}"
            race = [""] * 66
            horse = [""] * 35
            for row in (race, horse):
                row[0], row[1], row[2] = "金沢", date, "1"
            horse[5], horse[6], horse[31] = "1", "検証馬", "1"
            race_rows.append(race)
            horse_rows.append(horse)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.zip"
            with zipfile.ZipFile(path, "w") as bundle:
                for name, rows in (("r_racelist.csv", race_rows),
                                   ("h_horselist.csv", horse_rows)):
                    stream = io.StringIO()
                    csv.writer(stream).writerows(rows)
                    bundle.writestr(name, stream.getvalue().encode("utf-8-sig"))
            runs = NarOfficialArchive([path]).horse_history(
                {"name": "検証馬"}, {"date": "2026-10-12"})["allPastRuns"]
            self.assertEqual([row["date"] for row in runs], ["2026-10-10"])

    def test_default_official_history_retains_more_than_five_runs(self):
        import csv
        import io
        import tempfile
        import zipfile
        from pathlib import Path
        from arvexq.databanks.nar_official_csv import NarOfficialArchive
        races, horses = [], []
        for day in range(1, 9):
            date = f"202610{day:02d}"
            race = [""] * 66
            horse = [""] * 35
            for row in (race, horse):
                row[0], row[1], row[2] = "金沢", date, "1"
            race[23] = "1400"
            horse[5], horse[6], horse[31] = "1", "検証馬", "1"
            races.append(race)
            horses.append(horse)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.zip"
            with zipfile.ZipFile(path, "w") as archive:
                for filename, rows in (("x_racelist.csv", races), ("x_horselist.csv", horses)):
                    stream = io.StringIO()
                    csv.writer(stream).writerows(rows)
                    archive.writestr(filename, stream.getvalue().encode("utf-8-sig"))
            source = NarOfficialArchive([path])
            complete = source.horse_history({"name": "検証馬"}, {"date": "2026-10-09"})
            self.assertEqual(len(complete["recentRaces"]), 5)
            self.assertEqual(len(complete["allPastRuns"]), 8)
            limited = source.horse_history({"name": "検証馬"}, {"date": "2026-10-09"}, limit=3)
            self.assertEqual(len(limited["allPastRuns"]), 3)

    def test_overlapping_race_rows_keep_course_and_going_observations(self):
        import csv
        import io
        import tempfile
        import zipfile
        from pathlib import Path
        from arvexq.databanks.nar_official_csv import NarOfficialArchive
        first = [""] * 66
        first[0], first[1], first[2], first[21], first[23] = "金沢", "20261012", "1", "ダート", "1400"
        second = first.copy()
        second[21] = ""
        second[24], second[25] = "雨", "重"
        horse = [""] * 35
        horse[0], horse[1], horse[2], horse[5], horse[6] = "金沢", "20261012", "1", "1", "検証馬"
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for name, race in (("daily.zip", first), ("monthly.zip", second)):
                path = Path(folder) / name
                with zipfile.ZipFile(path, "w") as archive:
                    for filename, rows in (("x_racelist.csv", [race]), ("x_horselist.csv", [horse])):
                        stream = io.StringIO()
                        csv.writer(stream).writerows(rows)
                        archive.writestr(filename, stream.getvalue().encode("utf-8-sig"))
                paths.append(path)
            run = NarOfficialArchive(paths).horse_history(
                {"name": "検証馬"}, {"date": "2026-10-13"})["allPastRuns"][0]
            self.assertEqual(run["surface"], "ダート")
            self.assertEqual(run["weather"], "雨")
            self.assertEqual(run["condition"], "重")

    def test_overlapping_archive_rows_keep_complementary_observations(self):
        import csv
        import io
        import tempfile
        import zipfile
        from pathlib import Path
        from arvexq.databanks.nar_official_csv import NarOfficialArchive
        race = [""] * 66
        race[0], race[1], race[2] = "金沢", "20261012", "1"
        first = [""] * 35
        first[0], first[1], first[2], first[5], first[6] = "金沢", "20261012", "1", "1", "検証馬"
        first[16] = "51.0"
        second = first.copy()
        second[16] = ""
        second[31] = "1"
        second[34] = "36.1"
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for name, horse in (("daily.zip", first), ("monthly.zip", second)):
                path = Path(folder) / name
                with zipfile.ZipFile(path, "w") as bundle:
                    for filename, rows in (("x_racelist.csv", [race]), ("x_horselist.csv", [horse])):
                        output = io.StringIO()
                        csv.writer(output).writerows(rows)
                        bundle.writestr(filename, output.getvalue().encode("utf-8-sig"))
                paths.append(path)
            rows = NarOfficialArchive(paths).horse_history(
                {"name": "検証馬"}, {"date": "2026-10-13"})["allPastRuns"]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["carriedWeight"], 51.0)
            self.assertEqual(rows[0]["finish"], 1)
            self.assertEqual(rows[0]["last3fSeconds"], 36.1)

    def test_overlapping_archives_prefer_more_complete_observed_horse_record(self):
        import csv
        import io
        import tempfile
        import zipfile
        from pathlib import Path
        from arvexq.databanks.nar_official_csv import NarOfficialArchive
        race = [""] * 66
        race[0], race[1], race[2], race[23] = "金沢", "20261012", "1", "1400"
        sparse = [""] * 35
        sparse[0], sparse[1], sparse[2], sparse[5], sparse[6] = "金沢", "20261012", "1", "1", "検証馬"
        complete = sparse.copy()
        complete[16], complete[31], complete[34] = "▲ 51.0", "1", "36.1"
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for name, horse in (("daily.zip", sparse), ("monthly.zip", complete)):
                path = Path(folder) / name
                with zipfile.ZipFile(path, "w") as archive:
                    for member, rows in (("test_racelist.csv", [race]), ("test_horselist.csv", [horse])):
                        stream = io.StringIO()
                        csv.writer(stream).writerows(rows)
                        archive.writestr(member, stream.getvalue().encode("utf-8-sig"))
                paths.append(path)
            runs = NarOfficialArchive(paths).horse_history(
                {"name": "検証馬"}, {"date": "2026-10-13"})["allPastRuns"]
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["carriedWeight"], 51.0)
            self.assertEqual(runs[0]["finish"], 1)
            self.assertEqual(runs[0]["last3fSeconds"], 36.1)

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


    def test_empty_archive_does_not_mark_official_sync_complete(self):
        import io
        import tempfile
        import zipfile
        from pathlib import Path
        from app import NarArchiveParser, NarStore, NarSync
        with tempfile.TemporaryDirectory() as root:
            store = NarStore(Path(root) / "test.sqlite3")
            sync = NarSync.__new__(NarSync)
            sync.parser, sync.store = NarArchiveParser(), store
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w") as archive:
                archive.writestr("empty_racelist.csv", "")
                archive.writestr("empty_horselist.csv", "")
            with self.assertRaises((ValueError, IndexError)):
                sync.import_zip_bytes(output.getvalue(), "empty-test", Path(root) / "empty.zip")
            self.assertIsNone(store.synced_at("empty-test"))
            store.conn.close()

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
