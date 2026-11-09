"""Regression: a result-repair payload entry for a nightly-compact
tombstone stub must be rebuilt on the API display detail so the write
stays result-only in protect's comparison.

2026-10-30 Kanazawa 01/08: the bundle-built payload diverged from the
API-served stub in oddsSource/oddsUpdatedAt, protect failed closed,
and the whole date's payout repair could not sync.
"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.arvexq_payout_payload_shape_stubs import shape_payload


def _stub(rid, **overrides):
    detail = {
        "id": rid, "date": "2026-10-30", "track": "金沢", "raceNumber": 1,
        "predictionStatus": "disabled",
        "predictionModelVersion": "arvexq-prediction-removed",
        "compactedFrom": "nightly-compact",
        "oddsSource": "NAR公式", "oddsUpdatedAt": "11:44:30",
        "result": {"status": "確定", "payouts": [
            {"type": "馬連", "combination": "1-3", "amount": 570},
            {"type": "馬連", "combination": "1-3", "amount": 640},
        ]},
    }
    detail.update(overrides)
    return detail


class ShapeStubsTests(unittest.TestCase):
    def test_stub_entry_rebuilt_on_display_detail(self):
        rid = "nar-2026-10-30-金沢-01"
        stored = _stub(rid)
        entry = _stub(rid, oddsSource="netkeiba最終",
                      oddsUpdatedAt="01:09:21")
        entry["result"] = {"status": "確定", "payouts": [
            {"type": "馬連", "combination": "1-3", "amount": 570},
            {"type": "枠連単", "combination": "1-3", "amount": 640},
        ]}
        payload = {"details": [entry]}
        shaped = shape_payload(payload, lambda r: copy.deepcopy(stored))
        self.assertEqual(shaped, [rid])
        out = payload["details"][0]
        self.assertEqual(out["oddsSource"], "NAR公式")
        self.assertEqual(out["oddsUpdatedAt"], "11:44:30")
        self.assertEqual(out["result"]["payouts"], [
            {"type": "馬連", "combination": "1-3", "amount": 570},
            {"type": "枠連単", "combination": "1-3", "amount": 640},
        ])

    def test_non_stub_entry_untouched_and_fetch_not_called(self):
        rid = "nar-2026-10-30-金沢-02"
        entry = _stub(rid, predictionStatus="ready",
                      predictionModelVersion="arvexq-rewrite-v3-v9b")
        payload = {"details": [entry]}
        calls = []
        shaped = shape_payload(
            payload, lambda r: calls.append(r) or None)
        self.assertEqual(shaped, [])
        self.assertEqual(calls, [])
        self.assertEqual(entry["predictionStatus"], "ready")

    def test_fetch_failure_leaves_entry_unchanged(self):
        rid = "nar-2026-10-30-金沢-01"
        entry = _stub(rid, oddsSource="netkeiba最終")
        before = copy.deepcopy(entry)
        payload = {"details": [entry]}
        shaped = shape_payload(payload, lambda r: None)
        self.assertEqual(shaped, [])
        self.assertEqual(payload["details"][0], before)


if __name__ == "__main__":
    unittest.main()
