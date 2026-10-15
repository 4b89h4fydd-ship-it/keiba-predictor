"""Backfill factual NAR race margins without fallback to retired scoring."""
import asyncio
import unittest

from arvexq.databanks.legacy_bridge import _nar_official_past_result_adapter
from arvexq.databanks.registry import DataBankRegistry, DataSource, SourceCapabilities
from arvexq.ingest.fallback_enrichment import enrich_race_missing, _needs_nar_margins
from arvexq.prediction.past_performance import observed_runs


def fixture():
    horse = {"horseNumber": 2, "frameNumber": 2, "name": "地元の馬",
             "recentRaces": [
                 {"date": f"2026-10-{day:02d}", "track": "園田", "raceNumber": 1,
                  "distance": 1400, "surface": "ダート", "fieldSize": 9, "finish": 2,
                  "cornerPositions": [1, 2]}
                 for day in (10, 9, 8, 7, 6)
             ]}
    return {"id": "nar-2026-10-15-園田-01", "date": "2026-10-15", "circuit": "地方",
            "track": "園田", "distance": 1400, "surface": "ダート",
            "horses": [horse]}


def make_registry(getter):
    adapter = _nar_official_past_result_adapter({"_nar_official_result_fast": getter})
    bank = DataBankRegistry()
    bank.register(DataSource(
        name="nar_official_past_results", circuit="NAR", priority=12,
        capabilities=SourceCapabilities(horse_history=True),
        fetchers={"horse_history": adapter},
    ))
    return bank


class NAROfficialMarginBackfillTests(unittest.TestCase):
    def test_complete_corners_without_any_margin_trigger_official_lookup(self):
        calls = []
        def official(previous):
            calls.append(previous["date"])
            if previous["date"] == "2026-10-10":
                return {"finishers": [{"finish": 1, "name": "別の馬", "timeSeconds": 60.0}]}
            return {"finishers": [
                {"finish": 1, "name": "勝ち馬", "timeSeconds": 60.0},
                {"finish": 2, "name": "地元の馬", "timeSeconds": 60.8, "last3FSeconds": 38.0},
            ]}
        race = fixture()
        self.assertTrue(_needs_nar_margins(race["horses"][0], race["date"]))
        enriched = asyncio.run(enrich_race_missing(
            race, bank_registry=make_registry(official), history_limit=5,
            max_parallel_horses=1,
        ))
        runs = observed_runs(enriched["horses"][0], race, limit=5)
        observed = [r for r in runs if r.get("timeBehindWinner") is not None]
        self.assertEqual(calls, ["2026-10-10", "2026-10-09"])
        self.assertEqual(len(observed), 1)
        self.assertAlmostEqual(observed[0]["timeBehindWinner"], .8)
        self.assertFalse(_needs_nar_margins(enriched["horses"][0], race["date"]))
        self.assertEqual(enriched["horses"][0]["_supplementalSources"],
                         ["nar_official_past_results"])

    def test_genuine_zero_margin_does_not_refetch(self):
        race = fixture()
        race["horses"][0]["recentRaces"][0]["timeBehindWinner"] = 0.0
        self.assertFalse(_needs_nar_margins(race["horses"][0], race["date"]))
        called = []
        enriched = asyncio.run(enrich_race_missing(
            race, bank_registry=make_registry(lambda _: called.append(True)),
            history_limit=5, max_parallel_horses=1,
        ))
        self.assertEqual(called, [])
        self.assertEqual(enriched["horses"][0]["recentRaces"][0]["timeBehindWinner"], 0.0)

    def test_never_match_target_or_future_date(self):
        race = fixture()
        race["horses"][0]["recentRaces"][0]["date"] = race["date"]
        called = []
        adapter = _nar_official_past_result_adapter({
            "_nar_official_result_fast": lambda row: called.append(row["date"]) or {}
        })
        adapter(race["horses"][0], race)
        self.assertNotIn(race["date"], called)


if __name__ == "__main__":
    unittest.main()
