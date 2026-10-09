"""Do not mistake failed ticket computation for a genuine immutable skip."""
from __future__ import annotations
from datetime import datetime, timedelta
import unittest

from arvexq.prediction.prerace_archive import JST, seal_detail
from scripts.arvexq_freeze_predictions import prepare_seal
from scripts.arvexq_prerace_bet_integrity import has_valid_original, record_failed_attempt


def race():
    t = datetime(2026, 10, 10, 11, 0, tzinfo=JST)
    d = {"id": "nar-2026-10-10-大井-03", "date": "2026-10-10", "startTime": "11:00",
         "horses": [{"horseNumber": n, "name": f"H{n}"} for n in range(1, 4)]}
    lock = {"raceId": d["id"], "raceDate": d["date"],
            "capturedAtEpoch": int((t - timedelta(minutes=40)).timestamp()),
            "horses": [{"horseNumber": 1, "mark": "◎"},
                       {"horseNumber": 2, "mark": "○"},
                       {"horseNumber": 3, "mark": "▲"}]}
    return seal_detail(d, lock, t - timedelta(minutes=30))


class RetryableOriginalTests(unittest.TestCase):
    def test_failed_original_is_retryable_only_before_post(self):
        d = race()
        original = record_failed_attempt(d, None, message="temporary data read error",
                                         fixed_at="2026-10-10T10:30:00+09:00")
        d["preRaceBet"] = original
        self.assertFalse(has_valid_original(original, race_id=d["id"],
                                            start_at=datetime(2026, 10, 10, 11, tzinfo=JST)))
        self.assertEqual(prepare_seal(d, now=datetime(2026, 10, 10, 10, 40, tzinfo=JST))["status"], "sealed")
        self.assertEqual(prepare_seal(d, now=datetime(2026, 10, 10, 11, tzinfo=JST))["status"], "already-sealed")
        self.assertEqual(d["preRacePrediction"]["horses"][0]["mark"], "◎")

    def test_deliberate_skip_is_an_immutable_valid_original(self):
        d = race()
        original = {"raceId": d["id"], "fixedAt": "2026-10-10T10:35:00+09:00",
                    "decision": "見送り", "items": []}
        self.assertTrue(has_valid_original(original, race_id=d["id"],
                                           start_at=datetime(2026, 10, 10, 11, tzinfo=JST)))
        d["preRaceBet"] = original
        self.assertEqual(prepare_seal(d, now=datetime(2026, 10, 10, 10, 40, tzinfo=JST))["status"],
                         "already-sealed")

    def test_invalid_after_start_never_accepted(self):
        d = race()
        original = {"raceId": d["id"], "fixedAt": "2026-10-10T11:01:00+09:00",
                    "decision": "通常買い", "items": [{"kind": "ワイド", "combos": [[1, 2]]}]}
        self.assertFalse(has_valid_original(original, race_id=d["id"],
                                            start_at=datetime(2026, 10, 10, 11, tzinfo=JST)))

    def test_capture_errors_are_kept_separate_from_prediction(self):
        d = race()
        old = record_failed_attempt(d, None, message="first error",
                                    fixed_at="2026-10-10T10:22:00+09:00")
        record_failed_attempt(d, old, message="second error",
                              fixed_at="2026-10-10T10:28:00+09:00")
        self.assertEqual(len(d["preRaceBetCaptureFailures"]), 2)
        self.assertEqual(d["preRacePrediction"]["horses"][0]["mark"], "◎")


if __name__ == "__main__":
    unittest.main()
