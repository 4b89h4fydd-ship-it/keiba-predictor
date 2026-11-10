"""Offline regression checks for reuse of already-cached NAR official monthly ZIPs."""
from __future__ import annotations

import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from arvexq.databanks.nar_official_csv import (
    discover_cached_nar_month_archives,
    register_nar_official_archive,
)
from arvexq.databanks.registry import DataBankRegistry


def _csv_bytes(rows):
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode("cp932")


def _archive(directory, month, race_date, complete=True):
    path = directory / f"{month}_race.zip"
    race = [""] * 66
    race[0:3] = ["大井", race_date, "4"]
    race[23], race[26] = "1400", "12"
    horse = [""] * 36
    horse[0:3] = ["大井", race_date, "4"]
    horse[3], horse[5], horse[6] = "1", "1", "公式検証馬"
    horse[10], horse[31], horse[32] = "20180310", "1", "1230"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{month}_racelist.csv", _csv_bytes([race]))
        if complete:
            archive.writestr(f"{month}_horselist.csv", _csv_bytes([horse]))
    return path


class CachedOfficialArchiveTests(unittest.TestCase):
    def test_only_complete_local_archives_in_target_month_window(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "nar" / "archives"
            cache.mkdir(parents=True)
            october = _archive(cache, "202610", "20261004")
            november = _archive(cache, "202611", "20261103")
            _archive(cache, "202609", "20260901", complete=False)
            _archive(cache, "202608", "20260801")
            _archive(cache, "202612", "20261201")  # future race month
            (cache / "202607_race.zip").write_bytes(b"not a ZIP")
            actual = discover_cached_nar_month_archives(root, "2026-11-11", months=3)
            self.assertEqual(actual, [october, november])
            self.assertEqual(
                discover_cached_nar_month_archives(root, "2026-11-11", months="2"),
                [october, november],
            )
            self.assertEqual(
                discover_cached_nar_month_archives(root, "2026-10-11", months=1),
                [october],
            )
            self.assertEqual(discover_cached_nar_month_archives(root, "unknown"), [])

    def test_bad_zip_and_wrong_file_layout_are_skipped_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "nar" / "archives"
            cache.mkdir(parents=True)
            (cache / "202611_race.zip").write_bytes(b"broken")
            _archive(cache, "202610", "20261004", complete=False)
            self.assertEqual(
                discover_cached_nar_month_archives(root, "2026-11-11"),
                [],
            )
            self.assertEqual(
                discover_cached_nar_month_archives(root / "absent", "2026-11-11"),
                [],
            )

    def test_discovered_archive_becomes_real_past_run_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "nar" / "archives"
            cache.mkdir(parents=True)
            _archive(cache, "202610", "20261004")
            paths = discover_cached_nar_month_archives(root, "2026-11-11")
            registry = DataBankRegistry()
            provider = register_nar_official_archive(registry, paths=paths)
            self.assertIsNotNone(provider)
            self.assertEqual(provider.race_count, 1)
            runs = provider.horse_history(
                {"name": "公式検証馬", "birthDate": "2018-03-10"},
                {"date": "2026-11-11"},
            )
            self.assertEqual(len(runs["allPastRuns"]), 1)
            self.assertEqual(runs["allPastRuns"][0]["source"], "NAR公式CSV")
            self.assertEqual(runs["allPastRuns"][0]["date"], "2026-10-04")
            self.assertEqual(
                provider.horse_history(
                    {"name": "公式検証馬", "birthDate": "2018-03-10"},
                    {"date": "2026-10-04"},
                ),
                {},
                "Never use target-day observations as a past run",
            )


if __name__ == "__main__":
    unittest.main()
