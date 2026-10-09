"""Regression checks for immutable morning/static/D1 authority and ticket funnel."""
from __future__ import annotations
import unittest
from scripts.arvexq_bet_funnel import summarize
from scripts.arvexq_morning_d1_audit import validate


def manifest():
    return {"version": "v1", "date": "2026-10-10", "fixedAt": "2026-10-10T06:20:00+09:00",
            "scope": 2, "races": [
                {"id": "r1", "selected": True, "special": False, "selectedScore": 75,
                 "primaryType": "的中重視型", "types": ["的中重視型"], "ticketKinds": ["ワイド"]},
                {"id": "r2", "selected": False, "special": True, "selectedScore": 0,
                 "primaryType": "", "types": [], "ticketKinds": []}]}


class StaticD1MonitorTests(unittest.TestCase):
    def test_schema_omission_is_visible_and_not_fabricated(self):
        m = manifest()
        d = {"date": m["date"], "races": [{"id": "r1"}, {"id": "r2"}]}
        q = validate(m, d)
        self.assertEqual(q["schemaOmittedInD1"], 2)
        self.assertEqual(q["verifiedInD1"], 0)
        self.assertTrue(q["safeToDisplayFromStatic"])
        self.assertEqual(q["manifestSelected"], 1)

    def test_conflicting_or_missing_d1_race_fails_closed(self):
        m = manifest()
        d = {"date": m["date"], "races": [{"id": "r1", "morningPickVersion": "v1",
              "morningPickFixedAt": m["fixedAt"], "morningSelected": False,
              "morningSpecial": False, "morningSelectedScore": 75}, {"id": "r2"}]}
        q = validate(m, d)
        self.assertEqual(q["contradictoryInD1"], ["r1"])
        self.assertFalse(q["safeToDisplayFromStatic"])
        q = validate(m, {"date": m["date"], "races": [{"id": "r1"}]})
        self.assertEqual(q["missingD1Races"], ["r2"])
        self.assertFalse(q["safeToDisplayFromStatic"])

    def test_invalid_manifest_is_never_reconstructed(self):
        m = manifest()
        m["races"].append(m["races"][0])
        with self.assertRaises(ValueError):
            validate(m, {"date": m["date"], "races": []})

    def test_funnel_distinguishes_real_skip_from_capture_failure(self):
        reports = [
            {"status": "sealed", "ticket": "recorded", "bet_decision": "通常買い",
             "bet_item_kinds": ["馬連"], "morning_primary_type": "的中重視型",
             "ticket_result": {"version": "arvexq-frozen-result-audit-v1",
                               "honmeiPresent": True, "honmeiTop3Hit": True, "honmeiWinHit": False}},
            {"status": "sealed", "ticket": "recorded", "bet_decision": "見送り",
             "bet_item_kinds": [], "bet_reason": "先行位置取りの観測根拠不足"},
            {"status": "sealed", "ticket": "capture-failed"},
            {"status": "missing-preoff-seal"},
        ]
        a = summarize(reports)
        self.assertEqual(a["scheduledRaces"], 4)
        self.assertEqual(a["issuedRaces"], 1)
        self.assertEqual(a["intentionalSkippedRaces"], 1)
        self.assertEqual(a["unavailableOrInvalidBets"], 1)
        self.assertEqual(a["skipReasons"]["pace-evidence"], 1)
        self.assertEqual(a["honmei"]["evaluatedFinalRacesWithMark"], 1)
        self.assertEqual(a["honmei"]["top3ObservedRate"], 1)
        self.assertEqual(a["honmei"]["winObservedRate"], 0)
        self.assertEqual(a["issueRateAmongRecorded"], .5)

    def test_empty_funnel_has_no_fake_success_rate(self):
        a = summarize([])
        self.assertIsNone(a["issueRateAmongRecorded"])
        self.assertIsNone(a["honmei"]["top3ObservedRate"])


if __name__ == "__main__":
    unittest.main()
