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


    def test_failed_ticket_is_replaced_only_by_genuine_preoff_recovery(self):
        from arvexq.prediction.prerace_archive import restore_seal
        d = race()
        post = datetime(2026, 10, 10, 11, tzinfo=JST)
        failed = record_failed_attempt(
            d, None, message="temporary engine failure",
            fixed_at="2026-10-10T10:25:00+09:00")
        d["preRaceBet"] = failed
        incoming = dict(d)
        repaired = {"raceId": d["id"], "fixedAt": "2026-10-10T10:35:00+09:00",
                    "decision": "通常買い", "items": [{"kind": "馬連", "combos": [[1, 2]]}],
                    "betInputGate": {"ready": True}}
        incoming["preRaceBet"] = repaired
        incoming["preRaceBetCaptureFailures"] = [
            {"fixedAt": "2026-10-10T10:31:00+09:00", "error": "retry timeout"}]
        out = restore_seal(d, incoming, now=post - timedelta(minutes=20))
        self.assertEqual(out["preRaceBet"], repaired)
        self.assertEqual(out["preRacePrediction"], d["preRacePrediction"])
        self.assertEqual(len(out["preRaceBetCaptureFailures"]), 2)
        self.assertEqual(d["preRaceBet"], failed, "source must stay immutable")

    def test_genuine_original_wins_against_all_later_tickets(self):
        from arvexq.prediction.prerace_archive import restore_seal
        d = race()
        post = datetime(2026, 10, 10, 11, tzinfo=JST)
        original = {"raceId": d["id"], "fixedAt": "2026-10-10T10:32:00+09:00",
                    "decision": "見送り", "items": []}
        d["preRaceBet"] = original
        incoming = dict(d)
        incoming["preRaceBet"] = {"raceId": d["id"], "fixedAt": "2026-10-10T10:44:00+09:00",
                                 "decision": "通常買い",
                                 "items": [{"kind": "馬連", "combos": [[2, 3]]}]}
        for clock in [post - timedelta(minutes=15), post + timedelta(minutes=1)]:
            self.assertEqual(restore_seal(d, incoming, now=clock)["preRaceBet"], original)

    def test_postoff_submission_cannot_resurrect_missing_ticket(self):
        from arvexq.prediction.prerace_archive import restore_seal
        d = race()
        post = datetime(2026, 10, 10, 11, tzinfo=JST)
        failed = record_failed_attempt(
            d, None, message="missing early data",
            fixed_at="2026-10-10T10:20:00+09:00")
        d["preRaceBet"] = failed
        incoming = dict(d)
        incoming["preRaceBet"] = {"raceId": d["id"],
             "fixedAt": "2026-10-10T10:45:00+09:00",
             "decision": "通常買い", "items": [{"kind": "馬連", "combos": [[1, 2]]}]}
        self.assertEqual(restore_seal(d, incoming, now=post + timedelta(minutes=1))["preRaceBet"], failed)

    def test_unverified_legacy_original_is_never_silently_replaced(self):
        from arvexq.prediction.prerace_archive import restore_seal
        d = race()
        old = {"fixedAt": "2026-10-10T10:10:00+09:00", "decision": "見送り", "items": []}
        d["preRaceBet"] = old
        incoming = dict(d)
        incoming["preRaceBet"] = {"raceId": d["id"],
             "fixedAt": "2026-10-10T10:35:00+09:00",
             "decision": "通常買い", "items": [{"kind": "ワイド", "combos": [[1, 3]]}]}
        clock = datetime(2026, 10, 10, 10, 40, tzinfo=JST)
        self.assertEqual(restore_seal(d, incoming, now=clock)["preRaceBet"], old)

    def test_unavailable_or_incomplete_ticket_never_counts_as_original(self):
        post = datetime(2026, 10, 10, 11, tzinfo=JST)
        base = {"raceId": "r", "fixedAt": "2026-10-10T10:35:00+09:00",
                "decision": "見送り", "items": []}
        for extra in ({"captureStatus": "engine-missing"},
                      {"decision": "データ不足"},
                      {"betInputGate": {"ready": False}}):
            self.assertFalse(has_valid_original({**base, **extra},
                               race_id="r", start_at=post))
        self.assertTrue(has_valid_original(base, race_id="r", start_at=post))
        script = open("scripts/arvexq_capture_prerace_bet.js", encoding="utf-8").read()
        self.assertIn("if(!result)throw Error(", script)
        self.assertNotIn("if(!result){console.log(JSON.stringify", script)


if __name__ == "__main__":
    unittest.main()
