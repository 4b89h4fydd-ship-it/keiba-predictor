"""Regression: removing an active model must never delete its prior research evidence."""
import copy
import unittest
from datetime import datetime, timedelta, timezone

from arvexq.prediction.prerace_archive import restore_seal

JST = timezone(timedelta(hours=9))


class RetiredResearchRetentionTests(unittest.TestCase):
    def test_existing_archive_survives_sync_without_new_predictions(self):
        old = {
            "id": "nar-2026-10-21-門別-12", "date": "2026-10-21",
            "researchShadow": {
                "stage64": {"raceId": "nar-2026-10-21-門別-12", "stages": {"marks": {"value": 1}}},
                "priorStudy": {"original": True}
            }
        }
        updated = {
            "id": old["id"], "date": old["date"],
            "researchShadow": {"newIndependentStudy": {"original": True}}
        }
        before = copy.deepcopy(old)
        saved = restore_seal(old, updated, now=datetime(2026,10,21,19,0,tzinfo=JST))
        self.assertEqual(saved["researchShadow"]["stage64"], before["researchShadow"]["stage64"])
        self.assertEqual(saved["researchShadow"]["priorStudy"], before["researchShadow"]["priorStudy"])
        self.assertEqual(saved["researchShadow"]["newIndependentStudy"], {"original": True})
        self.assertEqual(old, before)
        self.assertNotIn("preRacePrediction", saved)

    def test_never_copy_research_to_another_race_or_date(self):
        old = {"id": "nar-2026-10-21-門別-12", "date": "2026-10-21",
               "researchShadow": {"stage64": {"frozen": True}}}
        for updated in (
            {"id": "nar-2026-10-21-門別-11", "date": old["date"]},
            {"id": old["id"], "date": "2026-10-22"},
        ):
            self.assertNotIn("researchShadow", restore_seal(old, updated))

if __name__ == "__main__":
    unittest.main()
