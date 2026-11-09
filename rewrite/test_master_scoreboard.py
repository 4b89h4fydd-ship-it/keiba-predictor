"""Frozen forecast pair scoring cannot promote post-result backfill."""
import unittest
import json
from hashlib import sha256

from rewrite.analysis.master_scoreboard import grade_master_pairs


def sample(rid="race-1"):
    payload = {
        "id": rid, "date": "2026-11-10", "startTime": "12:30",
        "circuit": "地方", "track": "名古屋",
        "preRaceBet": {"fixedBeforePost": True},
        "prediction": {
            "capturedAt": "2026-11-09T19:00:00+09:00",
            "stages": {"probability": {"value": {"win": {
                "1": 0.5, "2": 0.3, "3": 0.2,
            }}}},
        },
        "unifiedForecast": {"receiptSha256": "fixture-receipt"},
        "masterAnalysis": {
            "status": "shadow-candidate", "validated": False,
            "runners": [
                {"horseNumber": 1, "pWin": 0.3},
                {"horseNumber": 2, "pWin": 0.5},
                {"horseNumber": 3, "pWin": 0.2},
            ],
        },
        "result": {"status": "確定", "finishers": [
            {"horseNumber": 2, "finish": 1},
            {"horseNumber": 1, "finish": 2},
            {"horseNumber": 3, "finish": 3},
        ]},
    }
    analysis = payload["masterAnalysis"]
    analysis["capturedAt"] = payload["prediction"]["capturedAt"]
    analysis["contentSha256"] = sha256(json.dumps(
        analysis, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()
    return payload


class PairedScoreboardTests(unittest.TestCase):
    def test_same_races_have_correct_candidate_gains(self):
        result = grade_master_pairs([sample()])
        self.assertEqual(result["overall"]["races"], 1)
        self.assertEqual(result["overall"]["incumbent"]["honmeiWinRate"], 0.0)
        self.assertEqual(result["overall"]["candidate"]["honmeiWinRate"], 1.0)
        self.assertEqual(result["overall"]["candidate"]["honmeiTop3Rate"], 1.0)
        self.assertLess(result["overall"]["candidate"]["meanLogLoss"],
                        result["overall"]["incumbent"]["meanLogLoss"])
        self.assertEqual(result["overall"]["verdict"], "comparison-only-not-adoption")

    def test_no_preoff_receipt_excluded(self):
        payload = sample()
        payload["preRaceBet"] = {"fixedBeforePost": False}
        self.assertEqual(grade_master_pairs([payload])["overall"]["races"], 0)

    def test_after_off_capture_excluded(self):
        payload = sample()
        payload["prediction"]["capturedAt"] = "2026-11-10T12:31:00+09:00"
        self.assertEqual(grade_master_pairs([payload])["overall"]["races"], 0)

    def test_roster_mismatch_excluded(self):
        payload = sample()
        payload["masterAnalysis"]["runners"].pop()
        self.assertEqual(grade_master_pairs([payload])["overall"]["races"], 0)

    def test_shadow_checksum_tamper_excluded(self):
        payload = sample()
        payload["masterAnalysis"]["runners"][0]["pWin"] = 0.6
        result = grade_master_pairs([payload])
        self.assertEqual(result["overall"]["races"], 0)
        self.assertEqual(result["excluded"]["shadow-seal-mismatch"], 1)

    def test_pending_and_duplicate_excluded(self):
        payload = sample()
        payload["result"]["status"] = "未確定"
        result = grade_master_pairs([payload, payload])
        self.assertEqual(result["overall"]["races"], 0)
        self.assertEqual(result["excluded"]["pending-result"], 1)
        self.assertEqual(result["excluded"]["missing-or-duplicate-race"], 1)


if __name__ == "__main__":
    unittest.main()
