"""Regression: JRA weather/going placeholders must not survive result repair.

On 2026-11-07/08, 44 of 72 JRA races kept weather/condition "不明"
in the stored records: the netkeiba list builder hardcodes the
placeholder, and the values only landed when a best-effort live
refresh or an official-result merge happened to run for the race.
The result repair lane never touched races whose result/payout were
already complete, so nothing steady ever filled them. The lane now
backfills started JRA races whose values are still unknown, using
the app's official environment fetcher, and publishes them.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import arvexq_result_repair as repair


def _detail(rid: str, **over):
    detail = {
        "id": rid, "date": "2026-11-07", "track": "京都", "raceNumber": 1,
        "surface": "ダート", "weather": "不明", "condition": "不明",
        "result": {"status": "確定",
                   "finishers": [{"horseNumber": i, "finish": i}
                                 for i in (1, 2, 3)],
                   "payouts": [{"type": "単勝", "amount": 200}]},
    }
    detail.update(over)
    return detail


class FillMissingEnvironmentTests(unittest.TestCase):
    def test_fills_both_fields_and_updates_summary(self):
        rid = "jra-2026-11-07-京都-01"
        by_id = {rid: _detail(rid)}
        summary = {rid: {"id": rid, "weather": "不明", "condition": "不明"}}
        filled = repair._fill_missing_environment(
            by_id, summary, [rid],
            lambda probe: {"weather": "晴", "condition": "良",
                           "source": "JRA公式優先"})
        self.assertEqual(filled, [rid])
        self.assertEqual(by_id[rid]["weather"], "晴")
        self.assertEqual(by_id[rid]["condition"], "良")
        self.assertEqual(summary[rid]["weather"], "晴")
        self.assertEqual(summary[rid]["condition"], "良")
        self.assertEqual(by_id[rid]["environmentMeta"]["filledBy"],
                         "result-repair-env-backfill")

    def test_never_overwrites_known_values(self):
        rid = "jra-2026-11-07-福島-01"
        by_id = {rid: _detail(rid, track="福島", weather="小雨",
                              condition="稍重")}
        calls = []
        filled = repair._fill_missing_environment(
            by_id, {}, [rid],
            lambda probe: calls.append(probe) or {"weather": "晴"})
        self.assertEqual(filled, [])
        self.assertEqual(calls, [])  # nothing missing -> fetcher unused
        self.assertEqual(by_id[rid]["weather"], "小雨")

    def test_partial_fill_only_touches_missing_fields(self):
        rid = "jra-2026-11-08-東京-03"
        by_id = {rid: _detail(rid, track="東京", weather="晴")}
        filled = repair._fill_missing_environment(
            by_id, {}, [rid], lambda probe: {"condition": "稍重"})
        self.assertEqual(filled, [rid])
        self.assertEqual(by_id[rid]["weather"], "晴")
        self.assertEqual(by_id[rid]["condition"], "稍重")

    def test_skips_nar_and_missing_details(self):
        nar = "nar-2026-11-07-佐賀-01"
        by_id = {nar: _detail(nar, track="佐賀")}
        calls = []
        filled = repair._fill_missing_environment(
            by_id, {}, [nar, "jra-2026-11-07-京都-09"],
            lambda probe: calls.append(probe) or {"weather": "晴"})
        self.assertEqual(filled, [])
        self.assertEqual(calls, [])

    def test_fetcher_failure_is_per_race(self):
        ok = "jra-2026-11-07-京都-02"
        bad = "jra-2026-11-07-京都-01"
        by_id = {ok: _detail(ok, raceNumber=2), bad: _detail(bad)}

        def fetch(probe):
            if probe["raceNumber"] == 1:
                raise RuntimeError("boom")
            return {"weather": "曇", "condition": "良"}

        filled = repair._fill_missing_environment(by_id, {}, [bad, ok], fetch)
        self.assertEqual(filled, [ok])
        self.assertEqual(by_id[bad]["weather"], "不明")

    def test_attempt_cap_is_respected(self):
        ids = [f"jra-2026-11-07-京都-{i:02d}" for i in range(1, 6)]
        by_id = {rid: _detail(rid, raceNumber=i)
                 for i, rid in enumerate(ids, start=1)}
        calls = []
        filled = repair._fill_missing_environment(
            by_id, {}, ids,
            lambda probe: calls.append(probe) or {"weather": "晴",
                                                  "condition": "良"},
            limit=2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(filled), 2)


class RepairLaneIntegrationTests(unittest.TestCase):
    def test_completed_jra_race_gets_environment_and_is_published(self):
        date = "2026-11-07"
        rid = f"jra-{date}-京都-01"
        rows = [{"id": rid, "date": date, "track": "京都", "circuit": "中央",
                 "startTime": "10:05", "raceNumber": 1,
                 "weather": "不明", "condition": "不明"}]
        details = [_detail(rid)]
        snapshot = {"date": date, "races": rows, "details": details}
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / n
                     for n in ("bundle.json", "payload.json", "report.json")]
            paths[0].write_text(json.dumps(snapshot, ensure_ascii=False),
                                encoding="utf-8")
            with patch.object(repair, "started", return_value=True), \
                    patch.object(repair, "result_state",
                                 return_value=(True, True, "確定")), \
                    patch.object(repair.app, "_refresh_result_fast",
                                 side_effect=AssertionError(
                                     "complete race must not be refreshed")), \
                    patch.object(repair.app, "_jra_fetch_environment",
                                 return_value={"weather": "晴",
                                               "condition": "良",
                                               "source": "JRA公式優先"}) as fetch:
                rc = repair.repair(str(paths[0]), str(paths[1]),
                                   str(paths[2]), workers=1)
            self.assertEqual(rc, 0)
            self.assertEqual(fetch.call_count, 1)
            payload = json.loads(paths[1].read_text(encoding="utf-8"))
            report = json.loads(paths[2].read_text(encoding="utf-8"))
            self.assertEqual(report["environment_filled"], [rid])
            self.assertEqual(payload["meta"]["environment_filled_count"], 1)
            written = {d["id"]: d for d in payload["details"]}
            self.assertIn(rid, written)
            self.assertEqual(written[rid]["weather"], "晴")
            self.assertEqual(written[rid]["condition"], "良")
            summaries = {s["id"]: s for s in payload["summaries"]}
            self.assertEqual(summaries[rid]["weather"], "晴")
            self.assertEqual(summaries[rid]["condition"], "良")


if __name__ == "__main__":
    unittest.main()
