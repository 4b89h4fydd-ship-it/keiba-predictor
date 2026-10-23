"""Stage 1: existing NAR official CSV history must resolve calendar racing age safely.

Uses tiny synthetic local CSVs; no network, provider registration, model or D1 write.
"""
from __future__ import annotations

import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from arvexq.databanks.nar_official_csv import NarOfficialArchive


NAME = "同名馬"


def archive_race(yyyymmdd):
    row = [""] * 66
    row[0], row[1], row[2] = "大井", yyyymmdd, "4"
    row[23], row[26] = "1200", "12"
    return row


def archive_horse(yyyymmdd, dob, horse_number=2):
    row = [""] * 36
    row[0], row[1], row[2] = "大井", yyyymmdd, "4"
    row[5], row[6], row[10] = str(horse_number), NAME, dob
    row[31], row[32] = "2", "1130"
    return row


def cp932(rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    return buf.getvalue().encode("cp932")


class NarOfficialRacingIdentityTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "nar-official.zip"

    def make_archive(self, horses):
        dates = sorted({row[1] for row in horses})
        with zipfile.ZipFile(self.path, "w") as archive:
            archive.writestr("2026_racelist.csv", cp932([archive_race(d) for d in dates]))
            archive.writestr("2026_horselist.csv", cp932(horses))
        return NarOfficialArchive([self.path])

    def test_three_year_old_recovers_two_year_old_run_from_previous_calendar_year(self):
        source = self.make_archive([
            archive_horse("20250930", "20230310"),
            archive_horse("20260930", "20220310"),
        ])
        result = source.horse_history(
            {"name": NAME, "age": 3, "sex": "牡"},
            {"date": "2026-10-16", "circuit": "地方"}, limit=100,
        )
        self.assertEqual([r["date"] for r in result["allPastRuns"]], ["2025-09-30"])
        self.assertEqual(result["recentRaces"], result["allPastRuns"])
        self.assertEqual(result["allPastRuns"][0]["birthDate"], "2023-03-10")

    def test_four_year_old_selects_different_namesake_without_new_source(self):
        source = self.make_archive([
            archive_horse("20250930", "20230310"),
            archive_horse("20260930", "20220310"),
        ])
        result = source.horse_history(
            {"name": NAME, "age": "牡4"}, {"date": "2026-10-16"})
        self.assertEqual([r["date"] for r in result["allPastRuns"]], ["2026-09-30"])
        self.assertEqual(result["allPastRuns"][0]["birthDate"], "2022-03-10")

    def test_same_birth_year_but_different_exact_birth_dates_is_ambiguous(self):
        source = self.make_archive([
            archive_horse("20250930", "20230310"),
            archive_horse("20260930", "20230410"),
        ])
        self.assertEqual(source.horse_history(
            {"name": NAME, "age": 3}, {"date": "2026-10-16"}), {})

    def test_exact_birth_date_resolves_same_age_namesakes(self):
        source = self.make_archive([
            archive_horse("20250930", "20230310"),
            archive_horse("20260930", "20230410"),
        ])
        result = source.horse_history(
            {"name": NAME, "age": 3, "birthDate": "2023-03-10"},
            {"date": "2026-10-16"})
        self.assertEqual([r["date"] for r in result["allPastRuns"]], ["2025-09-30"])

    def test_conflicting_age_and_exact_dob_fail_closed(self):
        source = self.make_archive([archive_horse("20250930", "20230310")])
        self.assertEqual(source.horse_history(
            {"name": NAME, "age": 4, "birthDate": "2023-03-10"},
            {"date": "2026-10-16"}), {})
        self.assertEqual(source.horse_history(
            {"name": NAME, "age": 3},
            {"date": "2025-09-30"}), {}, "target-day runs are not history")

    def test_other_birth_year_not_returned_and_missing_dob_not_guessed(self):
        source = self.make_archive([
            archive_horse("20250930", "20230310"),
            archive_horse("20260830", ""),
            archive_horse("20260930", "20220310"),
        ])
        result = source.horse_history(
            {"name": NAME, "age": 3}, {"date": "2026-10-16"})
        self.assertEqual([r["date"] for r in result["allPastRuns"]], ["2025-09-30"])
        self.assertNotIn("2026-08-30", [r["date"] for r in result["allPastRuns"]])

    def test_no_age_or_birthdate_does_not_select_namesake(self):
        source = self.make_archive([
            archive_horse("20250930", "20230310"),
            archive_horse("20260930", "20220310"),
        ])
        self.assertEqual(source.horse_history(
            {"name": NAME}, {"date": "2026-10-16"}), {})

    def test_single_known_birth_preserves_legacy_unverified_age_path(self):
        source = self.make_archive([archive_horse("20250930", "20230310")])
        # The pre-existing source still works when target age is unavailable.
        self.assertEqual(len(source.horse_history(
            {"name": NAME}, {"date": "2026-10-16"})["allPastRuns"]), 1)
        self.assertEqual(source.horse_history(
            {"name": NAME, "age": 4}, {"date": "2026-10-16"}), {})


if __name__ == "__main__":
    unittest.main()
