"""Regression: the result-repair lane must repair historical races whose
stored detail was compacted to a summary (no horses), where the fast
refresher has no local detail to read and returns None.

Before the bundle fallback, such races errored with "result refresher
returned no usable detail" on every pass and could never be repaired —
the 2026-11-09 payout-duplicate census found 345 of them, including
quinella payouts stored twice for one combination.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import arvexq_result_repair as repair


FINISHERS = [
    {"finish": 1, "horseNumber": 4, "name": "ダイワキャグニー"},
    {"finish": 2, "horseNumber": 5, "name": "テストホース"},
    {"finish": 3, "horseNumber": 8, "name": "サンプルホース"},
]


def _payouts(quinella_amounts):
    rows = [
        {"type": "単勝", "combination": "4", "amount": 210},
        {"type": "複勝", "combination": "4", "amount": 110},
        {"type": "複勝", "combination": "5", "amount": 130},
        {"type": "複勝", "combination": "8", "amount": 150},
        {"type": "枠連", "combination": "4-5", "amount": 300},
    ]
    for amount in quinella_amounts:
        rows.append({"type": "馬連", "combination": "4-5", "amount": amount})
    rows += [
        {"type": "枠連単", "combination": "4-5", "amount": 950},
        {"type": "馬単", "combination": "4-5", "amount": 630},
        {"type": "ワイド", "combination": "4-5", "amount": 240},
        {"type": "ワイド", "combination": "4-8", "amount": 260},
        {"type": "ワイド", "combination": "5-8", "amount": 280},
        {"type": "3連複", "combination": "4-5-8", "amount": 890},
        {"type": "3連単", "combination": "4-5-8", "amount": 2830},
    ]
    return rows


class BundleFallbackTests(unittest.TestCase):
    def test_compacted_nar_race_with_duplicate_payout_is_repaired(self):
        date = "2026-10-13"
        rid = f"nar-{date}-川崎-06"
        broken = {
            "id": rid, "date": date, "track": "川崎", "raceNumber": 6,
            "circuit": "地方", "compactedAt": "2026-10-20T00:00:00+09:00",
            "result": {"status": "確定", "finishers": FINISHERS,
                       "payouts": _payouts([450, 600])},
        }
        official = {"status": "確定", "finishers": FINISHERS,
                    "payouts": _payouts([450]),
                    "weather": "晴", "condition": "良"}
        rows = [{"id": rid, "date": date, "track": "川崎", "circuit": "地方",
                 "startTime": "17:30", "raceNumber": 6}]
        bundle = {"date": date, "races": rows, "details": [broken]}
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / n
                     for n in ("bundle.json", "payload.json", "report.json")]
            paths[0].write_text(json.dumps(bundle, ensure_ascii=False),
                                encoding="utf-8")
            with patch.object(repair, "started", return_value=True), \
                    patch.object(repair.app, "_refresh_result_fast",
                                 return_value=None), \
                    patch.object(repair.app, "_nar_official_result_fast",
                                 return_value=official) as fetch, \
                    patch.object(repair.app, "_attach_nar_payouts",
                                 side_effect=lambda d: d):
                rc = repair.repair(str(paths[0]), str(paths[1]),
                                   str(paths[2]), workers=1)
            self.assertEqual(rc, 0)
            self.assertEqual(fetch.call_count, 1)
            report = json.loads(paths[2].read_text(encoding="utf-8"))
            self.assertIn(rid, report["repaired"])
            payload = json.loads(paths[1].read_text(encoding="utf-8"))
            written = {d["id"]: d for d in payload["details"]}
            payouts = written[rid]["result"]["payouts"]
            quinella = [p for p in payouts if p["type"] == "馬連"]
            self.assertEqual(quinella, [{"type": "馬連",
                                         "combination": "4-5",
                                         "amount": 450}])

    def test_fallback_not_used_when_fast_refresher_answers(self):
        date = "2026-10-13"
        rid = f"nar-{date}-川崎-07"
        broken = {
            "id": rid, "date": date, "track": "川崎", "raceNumber": 7,
            "circuit": "地方",
            "result": {"status": "確定", "finishers": FINISHERS,
                       "payouts": _payouts([450, 600])},
        }
        fresh = dict(broken)
        fresh["result"] = {"status": "確定", "finishers": FINISHERS,
                           "payouts": _payouts([450])}
        rows = [{"id": rid, "date": date, "track": "川崎", "circuit": "地方",
                 "startTime": "18:00", "raceNumber": 7}]
        bundle = {"date": date, "races": rows, "details": [broken]}
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / n
                     for n in ("bundle.json", "payload.json", "report.json")]
            paths[0].write_text(json.dumps(bundle, ensure_ascii=False),
                                encoding="utf-8")
            with patch.object(repair, "started", return_value=True), \
                    patch.object(repair.app, "_refresh_result_fast",
                                 return_value=fresh), \
                    patch.object(repair.app, "_nar_official_result_fast",
                                 side_effect=AssertionError(
                                     "fallback must not run")) as fetch:
                rc = repair.repair(str(paths[0]), str(paths[1]),
                                   str(paths[2]), workers=1)
            self.assertEqual(rc, 0)
            self.assertEqual(fetch.call_count, 0)
            report = json.loads(paths[2].read_text(encoding="utf-8"))
            self.assertIn(rid, report["repaired"])


if __name__ == "__main__":
    unittest.main()
