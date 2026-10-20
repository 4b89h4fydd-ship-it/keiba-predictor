"""Official NAR CSV documented offsets and historical runner joins (synthetic rows)."""
from __future__ import annotations

import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from arvexq.databanks.nar_official_csv import (
    NarOfficialArchive, ranks, register_nar_official_archive,
)
from arvexq.databanks.registry import DataBankRegistry


def encode(rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    return buf.getvalue().encode("cp932")


def race(date="20260930"):
    row = [""] * 66
    row[0:3] = ["大井", date, "4"]
    row[23], row[26] = "1400", "12"
    for i, t in enumerate(("12.3", "11.0", "12.1", "12.9", "12.6", "12.2", "12.4")):
        row[35 + i] = t
    row[50:54] = ["１角", "２角", "３角", "４角"]
    row[58:62] = ["1,3,10,2,7", "1,3,10,2,7", "1,10,3-2,7", "1,10,(2,7),3"]
    return row


def horse(name="サンプル", number=10, dob="20180310", date="20260930"):
    row = [""] * 36
    row[0:3] = ["大井", date, "4"]
    row[3], row[5], row[6] = "5", str(number), name
    row[10], row[14], row[31], row[33], row[34] = dob, "矢野貴", "2", "0.3", "38.2"
    return row


class NarOfficialCsvTests(unittest.TestCase):
    def test_official_corner_order_and_tied_group(self):
        self.assertEqual(ranks("1,3,13,15,10,8,12,16,6,14,11,(2,7),4,5")[2], 12)
        self.assertEqual(ranks("1,3,13,15,10,8,12,16,6,14,11,(2,7),4,5")[7], 12)
        self.assertEqual(ranks("1,3-2,7")[2], 3)

    def test_cp932_zip_history_and_laps(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "202609_race.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("202609_racelist.csv", encode([race()]))
                z.writestr("202609_horselist.csv", encode([
                    horse(), horse("先行馬", 1, "20190101"),
                    horse("サンプル", 8, "20200101"),
                ]))
            reg = DataBankRegistry()
            index = register_nar_official_archive(reg, [path])
            self.assertEqual(index.race_count, 1)
            self.assertEqual(len(reg.providers("horse_history", circuit="NAR")), 1)
            result = index.horse_history({
                "name": "サンプル", "birthDate": "2018-03-10",
            }, {"date": "2026-10-08"}, 5)
            self.assertEqual(len(result["recentRaces"]), 1)
            item = result["recentRaces"][0]
            self.assertEqual(item["cornerPositions"], [3, 3, 2, 2])
            self.assertEqual(item["cornerNames"], ["１角", "２角", "３角", "４角"])
            self.assertEqual(item["frameNumber"], 5)
            self.assertEqual(item["distance"], 1400)
            self.assertEqual(item["finish"], 2)
            self.assertEqual(item["marginText"], "0.3")
            self.assertEqual(item["last3fSeconds"], 38.2)
            self.assertAlmostEqual(item["raceFirst3FSeconds"], 35.4)
            self.assertNotIn("horseFirst3FSeconds", item)
            self.assertEqual(index.horse_history(
                {"name": "サンプル"}, {"date": "2026-09-30"}, 5
            ), {}, "target race is not a previous race")
            self.assertEqual(index.horse_history(
                {"name": "サンプル", "birthDate": "2017-01-01"},
                {"date": "2026-10-08"}, 5
            ), {}, "birth date protects against namesakes")
            self.assertEqual(index.horse_history(
                {"name": "該当なし"}, {"date": "2026-10-08"}, 5
            ), {})

    def test_off_by_one_date_and_missing_zip_do_not_invent_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data"
            path.mkdir()
            (path / "202609_racelist.csv").write_bytes(encode([race("20260930")]))
            (path / "202609_horselist.csv").write_bytes(encode([horse(date="20260929")]))
            index = NarOfficialArchive([path])
            self.assertEqual(index.horse_history(
                {"name": "サンプル"}, {"date": "2026-10-08"}, 5
            ), {}, "date mismatch must not join to unrelated race")



class OfficialArchiveObservedFields(unittest.TestCase):
    def test_full_evidence_clock_gap_and_identity_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'official.zip'
            winner, runner = horse('勝馬', 1), horse()
            winner[31], winner[32] = '1', '1230'
            runner[32], runner[18] = '1234', '公式厩舎'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('racelist.csv', encode([race()]))
                z.writestr('horselist.csv', encode([winner, runner]))
            archive = NarOfficialArchive([path])
            result = archive.horse_history({'name': 'サンプル', 'birthDate': '20180310'}, {'date': '2026-10-17'})
            run = result['allPastRuns'][0]
            self.assertEqual(run['birthDate'], '2018-03-10')
            self.assertEqual(run['trainer'], '公式厩舎')
            self.assertEqual(run['timeSeconds'], 83.4)
            self.assertEqual(run['marginSeconds'], .4)
            self.assertEqual(run['marginEvidence'], {'winnerTimeSeconds': 83., 'horseTimeSeconds': 83.4})
            self.assertEqual(result['recentRaces'], result['allPastRuns'])
            wrong = Path(directory) / 'conflict.zip'
            other = horse('別馬', 10)
            with zipfile.ZipFile(wrong, 'w') as z:
                z.writestr('horselist.csv', encode([other]))
            with self.assertRaisesRegex(ValueError, 'identity'):
                NarOfficialArchive([path, wrong])

    def test_invalid_date_and_timing_are_unknown(self):
        from arvexq.databanks.nar_official_csv import date, time_seconds
        self.assertEqual(date('20260230'), '')
        self.assertEqual(date('2026-02-28'), '2026-02-28')
        self.assertIsNone(time_seconds('1600'))
        self.assertIsNone(time_seconds('中止'))
        self.assertEqual(time_seconds('594'), 59.4)

    def test_future_namesake_cannot_remove_preoff_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'namesakes.zip'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('racelist.csv', encode([race('20260930'), race('20261020')]))
                z.writestr('horselist.csv', encode([horse(dob='',date='20260930'),
                    horse(dob='20200101',date='20261020')]))
            index = NarOfficialArchive([path])
            result = index.horse_history({'name':'サンプル','birthDate':'20180310'}, {'date':'2026-10-17'})
            self.assertEqual(len(result['allPastRuns']), 1)
            self.assertEqual(result['allPastRuns'][0]['date'], '2026-09-30')


    def test_legacy_nar_sqlite_name_query_against_birth_verified_official_rows(self):
        import app
        from arvexq.databanks.legacy_bridge import audit_nar_store_history
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"saved.sqlite"
            store=app.NarStore(path)
            try:
                starts=[
                    ("20260901", "20180310", 1, 2),
                    ("20260910", "20200101", 1, 3),
                    ("20260915", "20180310", 1, 0),
                ]
                archive=Path(directory)/"original.zip"
                with zipfile.ZipFile(archive,"w") as zipped:
                    zipped.writestr("racelist.csv",encode([race(day) for day,*_ in starts]))
                    official=[]
                    for day,birth,no,finish in starts:
                        row=horse("同名馬",no,birth,day)
                        row[31]=str(finish)
                        official.append(row)
                    zipped.writestr("horselist.csv",encode(official))
                index=NarOfficialArchive([archive])
                for day,birth,no,finish in starts:
                    day_iso=f"{day[:4]}-{day[4:6]}-{day[6:]}"
                    store.conn.execute(
                        "INSERT INTO races(track,date,race_no) VALUES (?,?,?)",
                        ("大井",day_iso,4))
                    store.conn.execute(
                        "INSERT INTO entries(track,date,race_no,horse_no,name,age,sex,finish)"
                        " VALUES (?,?,?,?,?,?,?,?)",
                        ("大井",day_iso,4,no,"同名馬",8 if birth=="20180310" else 6,"牡",finish))
                store.conn.execute("INSERT INTO races(track,date,race_no) VALUES (?,?,?)",
                                   ("大井","2026-09-20",4))
                store.conn.execute(
                    "INSERT INTO entries(track,date,race_no,horse_no,name,age,sex,finish)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    ("大井","2026-09-20",4,1,"同名馬",8,"牡",2))
                store.conn.commit()
                before=tuple(store.conn.execute(
                    "SELECT COUNT(*),SUM(finish) FROM entries").fetchone())
                old=store.recent_races("同名馬","2026-10-01",20)
                self.assertEqual(len(old),3,
                                 "production SQL includes the different-birth namesake")
                report=audit_nar_store_history(
                    store.conn,{"name":"同名馬","birthDate":"2018-03-10"},
                    "2026-10-01",index)
                self.assertEqual(report["dbRowsBeforeLegacyFinishFilter"],4)
                self.assertEqual(report["legacyPositiveRows"],3)
                self.assertEqual(report["officialBirthCompatiblePositiveRows"],1)
                self.assertEqual(report["conflictingBirthPositiveRows"],1)
                self.assertEqual(report["unverifiedPositiveRows"],1)
                self.assertEqual(report["excludedByLegacyFinishFilter"],1)
                self.assertEqual(report["reasonCounts"],{
                    "conflicting-official-birth-date":1,
                    "excluded-by-legacy-finish-filter":1,
                    "official-birth-date-compatible":1,
                    "unverified-official-row-not-in-supplied-archive":1,
                })
                self.assertFalse(report["identityConfirmedByStableHorseId"])
                no_archive=audit_nar_store_history(
                    store.conn,{"name":"同名馬"},"2026-10-01")
                self.assertEqual(no_archive["unverifiedPositiveRows"],3)
                self.assertEqual(tuple(store.conn.execute(
                    "SELECT COUNT(*),SUM(finish) FROM entries").fetchone()),before)
            finally:
                store.conn.close()


if __name__ == '__main__':
    unittest.main()
