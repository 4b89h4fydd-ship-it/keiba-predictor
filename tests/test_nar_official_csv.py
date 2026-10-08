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
    row[10], row[14], row[31], row[34] = dob, "矢野貴", "2", "38.2"
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


if __name__ == "__main__":
    unittest.main()
