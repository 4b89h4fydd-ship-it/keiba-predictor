"""Historical revision receipts survive model retirement and future syncs."""
from __future__ import annotations

from copy import deepcopy
import unittest

from arvexq.prediction.archived_forecast_revisions import (
    VERSION, _digest, preserve_archived_revisions,
)
from scripts.arvexq_protect_sync import protect_detail


def make_revision():
    body = {
        "version": VERSION, "raceId": "nar-2026-10-10-高知-01",
        "raceDate": "2026-10-10", "analysisType": "retrospective",
        "predictionStatus": "candidate-analysis",
    }
    body["revisionId"] = _digest(body)
    body["createdAt"] = "2026-10-10T20:00:00+09:00"
    return body


class ArchivedForecastRevisionTests(unittest.TestCase):
    def test_sync_retains_original_chain_without_forecast_engine(self):
        revision = make_revision()
        original = {
            "id": revision["raceId"], "date": revision["raceDate"],
            "forecastRevisions": [revision],
            "currentForecastRevisionId": revision["revisionId"],
            "preRacePrediction": {"original": "untouched"},
            "horses": [],
        }
        before = deepcopy(original)
        updated = {
            "id": original["id"], "date": original["date"],
            "horses": [], "newOddsTimestamp": "2026-10-10T20:15:00+09:00",
        }
        output = protect_detail(original, updated)
        self.assertEqual(output["forecastRevisions"], [revision])
        self.assertEqual(output["currentForecastRevisionId"], revision["revisionId"])
        self.assertEqual(output["preRacePrediction"], before["preRacePrediction"])
        self.assertEqual(original, before)

    def test_chain_rewrite_and_invalid_pointer_fail_closed(self):
        revision = make_revision()
        base = {"id": revision["raceId"], "date": revision["raceDate"],
                "forecastRevisions": [revision],
                "currentForecastRevisionId": revision["revisionId"]}
        bad = {"id": base["id"], "date": base["date"],
               "forecastRevisions": [{**revision, "analysisType": "changed"}]}
        with self.assertRaisesRegex(ValueError, "prefix changed"):
            preserve_archived_revisions(base, bad)
        with self.assertRaisesRegex(ValueError, "pointer is invalid"):
            preserve_archived_revisions(base, {
                "id": base["id"], "date": base["date"],
                "currentForecastRevisionId": "invalid",
            })
        with self.assertRaisesRegex(ValueError, "owner race mismatch"):
            preserve_archived_revisions(base, {"id": "another-race", "date": base["date"]})

    def test_no_old_history_stays_empty_and_does_not_predict(self):
        old = {"id": "R", "date": "2026-10-10"}
        new = {"id": "R", "date": "2026-10-10", "horses": []}
        output = preserve_archived_revisions(old, new)
        self.assertNotIn("forecastRevisions", output)
        self.assertNotIn("predictionStatus", output)
        self.assertNotIn("recommendedBetPlan", output)


if __name__ == "__main__":
    unittest.main()
