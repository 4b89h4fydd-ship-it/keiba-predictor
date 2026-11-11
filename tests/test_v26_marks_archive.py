"""Contract tests for the v26 sealed-marks archive validator.

The validator (scripts/arvexq_v26_marks_archive.py) is the watchdog's
eyes: it must accept the archives the lane actually produced and
fail loudly on the failure mode of 2026-11-11 — the dated file
simply never arrived — and on malformed substitutes.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "arvexq_v26_marks_archive.py"
REAL_ARCHIVE_DIR = ROOT / "arvexq" / "ui" / "static" / "v26-marks"


def run_validator(date: str, archive_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--date", date,
         "--archive-dir", str(archive_dir)],
        capture_output=True, text=True)


def sample_payload(date: str) -> dict:
    return {
        "date": date, "generatedAt": f"{date}T01:00:00+09:00",
        "modelKey": "arvexq-shadow-v26-multieye1-fitd3573056",
        "modelVersion": "arvexq-shadow-v26-candidate",
        "raceCount": 1, "version": "v1",
        "races": {
            f"nar-{date}-名古屋-01": {
                "marks": {"2": "◎", "8": "○"},
                "signals": {"2": "軸", "8": "紐"},
                "v28": {"addedPartners": [3], "band": 5},
            },
        },
    }


class V26MarksArchiveTests(unittest.TestCase):
    def test_real_archive_is_valid(self):
        # The last archive the external lane actually delivered.
        result = run_validator("2026-11-10", REAL_ARCHIVE_DIR)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("59 races", result.stdout)

    def test_missing_archive_fails_loudly(self):
        # The 2026-11-11 failure mode: no file for the date at all.
        result = run_validator("2026-11-11", REAL_ARCHIVE_DIR)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing", result.stderr)

    def test_valid_sample_passes_and_tampered_copies_fail(self):
        date = "2026-12-01"
        with tempfile.TemporaryDirectory() as tmp:
            archive_dir = Path(tmp)
            path = archive_dir / f"{date}.json"

            path.write_text(json.dumps(sample_payload(date), ensure_ascii=False),
                            encoding="utf-8")
            self.assertEqual(run_validator(date, archive_dir).returncode, 0)

            wrong_date = sample_payload(date)
            wrong_date["date"] = "2026-12-02"
            path.write_text(json.dumps(wrong_date), encoding="utf-8")
            self.assertEqual(run_validator(date, archive_dir).returncode, 1)

            bad_count = sample_payload(date)
            bad_count["raceCount"] = 7
            path.write_text(json.dumps(bad_count), encoding="utf-8")
            self.assertEqual(run_validator(date, archive_dir).returncode, 1)

            bad_mark = sample_payload(date)
            bad_mark["races"][f"nar-{date}-名古屋-01"]["marks"]["2"] = "★"
            path.write_text(json.dumps(bad_mark), encoding="utf-8")
            self.assertEqual(run_validator(date, archive_dir).returncode, 1)

            path.write_text("<!doctype html><html></html>", encoding="utf-8")
            self.assertEqual(run_validator(date, archive_dir).returncode, 1)


if __name__ == "__main__":
    unittest.main()
