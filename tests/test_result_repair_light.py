"""Light lane: the result-repair script's --light mode refreshes only
races that started within the window, through the netkeiba-only light
refresher, in a single pass. Older incomplete races stay untouched
for the heavy lane, and the heavy refresher is never called.
"""
import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import arvexq_result_repair as repair
from arvexq.results import JST


FINISHERS = [
    {"finish": 1, "horseNumber": 4, "name": "ダイワキャグニー"},
    {"finish": 2, "horseNumber": 5, "name": "テストホース"},
    {"finish": 3, "horseNumber": 8, "name": "サンプルホース"},
]
PAYOUTS = [
    {"type": "単勝", "combination": "4", "amount": 210},
    {"type": "複勝", "combination": "4", "amount": 110},
    {"type": "複勝", "combination": "5", "amount": 130},
    {"type": "複勝", "combination": "8", "amount": 150},
    {"type": "馬連", "combination": "4-5", "amount": 450},
    {"type": "3連単", "combination": "4-5-8", "amount": 2830},
]


def _detail(rid, date, start, track, no):
    return {
        "id": rid, "date": date, "track": track, "raceNumber": no,
        "circuit": "地方", "startTime": start,
        "horses": [{"horseNumber": f["horseNumber"], "name": f["name"]}
                   for f in FINISHERS],
    }


class LightRepairTests(unittest.TestCase):
    def test_light_mode_refreshes_only_just_started_races(self):
        now = datetime.now(JST)
        date = now.strftime("%Y-%m-%d")
        recent_start = (now - timedelta(minutes=10)).strftime("%H:%M")
        old_start = (now - timedelta(minutes=180)).strftime("%H:%M")
        recent_id = f"nar-{date}-川崎-06"
        old_id = f"nar-{date}-川崎-01"
        rows = [
            {"id": recent_id, "date": date, "track": "川崎",
             "circuit": "地方", "startTime": recent_start, "raceNumber": 6},
            {"id": old_id, "date": date, "track": "川崎",
             "circuit": "地方", "startTime": old_start, "raceNumber": 1},
        ]
        details = [_detail(recent_id, date, recent_start, "川崎", 6),
                   _detail(old_id, date, old_start, "川崎", 1)]
        bundle = {"date": date, "races": rows, "details": details}
        light_calls = []

        def fake_light(rid):
            light_calls.append(rid)
            fresh = copy.deepcopy(details[0])
            fresh["result"] = {"status": "確定", "finishers": FINISHERS,
                               "payouts": PAYOUTS, "source": "netkeiba結果"}
            return fresh

        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / n
                     for n in ("bundle.json", "payload.json", "report.json")]
            paths[0].write_text(json.dumps(bundle, ensure_ascii=False),
                                encoding="utf-8")
            with patch.object(repair.app, "_refresh_result_light",
                              side_effect=fake_light), \
                    patch.object(repair.app, "_refresh_result_fast",
                                 side_effect=AssertionError(
                                     "heavy refresher must not run in light mode")), \
                    patch.object(repair.app, "_store_fast_snapshot",
                                 side_effect=lambda d: None):
                rc = repair.repair(str(paths[0]), str(paths[1]),
                                   str(paths[2]), workers=1,
                                   light=True, light_window_min=60)
            self.assertEqual(rc, 0)
            self.assertEqual(light_calls, [recent_id])
            report = json.loads(paths[2].read_text(encoding="utf-8"))
            self.assertTrue(report["light_mode"])
            self.assertIn(recent_id, report["repaired"])
            self.assertNotIn(old_id, report["repaired"])
            payload = json.loads(paths[1].read_text(encoding="utf-8"))
            self.assertTrue(payload["meta"]["light_mode"])
            written = {d["id"]: d for d in payload["details"]}
            self.assertEqual(written[recent_id]["result"]["source"],
                             "netkeiba結果")
            self.assertNotIn(old_id, written)


if __name__ == "__main__":
    unittest.main()
