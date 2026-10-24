"""Regression: retired Banei archive rows are not active result repair work."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import arvexq_result_repair as repair


class RetiredBaneiResultRepairTests(unittest.TestCase):
    def test_legacy_day_rows_do_not_enter_result_refresh_or_d1_payload(self):
        date = "2026-10-08"
        active = "nar-" + date + "-佐賀-01"
        archived = ["nar-" + date + "-帯広ば-01",
                    "nar-" + date + "-帯広-02",
                    "nar-" + date + "-帯広ば-03"]
        rows = [
            {"id": active, "date": date, "track": "佐賀", "circuit": "地方",
             "startTime": "12:00", "raceNumber": 1},
            {"id": archived[0], "date": date, "track": "帯広ば", "startTime": "12:00"},
            {"id": archived[1], "date": date, "track": "帯広", "startTime": "12:00"},
            {"id": archived[2], "date": date, "track": "佐賀", "startTime": "12:00"},
        ]
        details = [
            {"id": active, "date": date, "result": {"status": "確定",
                "finishers": [{"horseNumber": i, "finish": i} for i in (1, 2, 3)],
                "payouts": [{"type": "単勝", "amount": 200}]}},
            {"id": archived[0], "date": date, "result": {}},
        ]
        snapshot = {"date": date, "races": rows, "details": details}
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / n for n in ("source.json", "out.json", "report.json")]
            paths[0].write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
            with patch.object(repair, "started", return_value=True), \
                    patch.object(repair, "result_state", return_value=(True, True, "確定")), \
                    patch.object(repair.app, "_refresh_result_fast",
                                 side_effect=AssertionError("no pending eligible race")) as refresh:
                self.assertEqual(repair.repair(*map(str, paths)), 0)
                refresh.assert_not_called()
            payload = json.loads(paths[1].read_text(encoding="utf-8"))
            report = json.loads(paths[2].read_text(encoding="utf-8"))
            self.assertEqual([r["id"] for r in payload["summaries"]], [active])
            self.assertEqual(payload["details"], [])
            self.assertEqual(report["started"], 1)
            self.assertEqual(report["repaired"], [])
            self.assertEqual(json.loads(paths[0].read_text(encoding="utf-8")), snapshot,
                             "archived input must not be altered")


if __name__ == "__main__":
    unittest.main()
