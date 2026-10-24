from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from scripts.arvexq_data_source_readiness import audit


class DataSourceReadinessTests(unittest.TestCase):
    def test_discovery_is_not_misreported_as_actual_extraction(self):
        result=audit(env={})
        self.assertGreaterEqual(result["candidateSources"],25)
        self.assertEqual(result["localArchivePathsConfigured"],0)
        self.assertEqual(result["localRaceZips"],0)
        self.assertEqual(result["localDailyPreoffOddsZips"],0)
        self.assertTrue(result["candidateSourcesAreNotConnected"])
        self.assertFalse(result["sourceAuthorizationVerified"])

    def test_distinguish_preoff_daily_odds_from_monthly_final_only(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("202610_1234567890_race.zip", "20261025_1790000000_odds.zip",
                         "202610_1790000000_odds.zip"):
                (Path(d)/name).write_bytes(b"sample")
            report=audit(env={},archive_dir=d)
            self.assertEqual(report["localRaceZips"],1)
            self.assertEqual(report["localDailyPreoffOddsZips"],1)
            self.assertEqual(report["localFinalOddsZipsNotEligibleForPreoff"],1)

    def test_research_catalog_tracks_weather_track_ground_and_video_without_banei(self):
        from arvexq.databanks.source_catalog import discovery_inventory, NAR_VENUES
        ids={s["id"] for s in discovery_inventory()}
        self.assertTrue({"jra_going_history","jma_weather_history","jra_official_video"}.issubset(ids))
        self.assertNotIn("banei_official", ids)
        self.assertNotIn("帯広", NAR_VENUES)
        self.assertTrue(all(not s["enabledForExtraction"] for s in discovery_inventory()))

    def test_missing_paths_remain_missing(self):
        result=audit(env={"ARVEXQ_NAR_OFFICIAL_CSV_ARCHIVES":"/missing/nonexistent.zip"})
        self.assertEqual(len(result["localArchivePathsMissing"]),1)
        self.assertEqual(result["localZipFilesFound"],0)


if __name__=="__main__":
    unittest.main()
