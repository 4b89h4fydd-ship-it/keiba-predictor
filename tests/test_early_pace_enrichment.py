"""First-turn positioning must be fetched and merged, not guessed from five rows."""
from __future__ import annotations

import unittest

from arvexq.databanks.registry import DataBankRegistry, DataSource, SourceCapabilities
from arvexq.ingest.fallback_enrichment import (
    _first_corner_coverage,
    _merge_runs,
    _needs_history,
    enrich_race_missing,
)


def run(day: int, positions: list[int | None]) -> dict:
    return {
        "date": f"2026-09-{day:02}",
        "track": "大井",
        "distance": 1400,
        "raceNumber": 4,
        "fieldSize": 12,
        "cornerPositions": positions,
        "finish": 4,
    }


class EarlyPaceSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_five_runs_with_missing_first_turn_are_refetched(self):
        existing = [
            run(30, [1, 2, 3, 3]),
            run(24, [None, 3, 3, 3]),
            run(18, []),
            run(12, [2, 3, 2, 4]),
            run(6, [None, 5, 4]),
        ]
        horse = {"horseNumber": 1, "name": "test", "recentRaces": existing}
        assert _needs_history(horse, cutoff="2026-10-08", limit=5)
        registry = DataBankRegistry()
        calls: list[str] = []

        def fetch_history(horse, race, limit):
            calls.append("nar_official")
            return {"recentRaces": [
                run(30, [9, 9, 9, 9]), # Existing legitimate position must win.
                run(24, [2, 3, 3, 3]),
                run(18, [3, 4, 4, 5]),
                run(12, [1, 3, 2, 4]), # Do not overwrite official first turn.
                run(6, [4, 5, 4, 3]),
                {"date":"2026-10-09", "track":"大井", "distance":1400,
                 "raceNumber":4, "cornerPositions":[1,1,1,1]},
            ]}
        registry.register(DataSource(
            name="nar_test_official", circuit="NAR", priority=1,
            capabilities=SourceCapabilities(horse_history=True),
            fetchers={"horse_history": fetch_history},
        ))
        detail = {
            "id":"nar-2026-10-08-大井-04", "circuit":"地方",
            "date":"2026-10-08", "horses":[horse],
        }
        filled = await enrich_race_missing(detail, bank_registry=registry)
        self.assertEqual(calls, ["nar_official"])
        result = filled["horses"][0]["recentRaces"]
        self.assertEqual(len(result), 5)
        self.assertEqual([r["cornerPositions"][0] for r in result], [1,2,3,2,4])
        self.assertEqual(filled["preparedMeta"]["supplementalSearch"]["firstCornerEvidenceReadyHorses"], 1)
        self.assertEqual(filled["preparedMeta"]["supplementalSearch"]["firstCornerSamplesByHorse"]["1"], 5)
        self.assertEqual(existing[1]["cornerPositions"][0], None, "original unchanged")

    async def test_complete_corners_do_not_trigger_redundant_history_fetch(self):
        horse = {"horseNumber":2, "recentRaces":[run(d,[2,3,2,2]) for d in (30,24,18,12,6)]}
        self.assertFalse(_needs_history(horse, cutoff="2026-10-08", limit=5))
        reg = DataBankRegistry()
        calls = []
        def fetch_history(*args):
            calls.append(True)
            return {"recentRaces":[]}
        reg.register(DataSource(
            name="nar_test_official", circuit="NAR", priority=1,
            capabilities=SourceCapabilities(horse_history=True),
            fetchers={"horse_history":fetch_history},
        ))
        detail={"circuit":"地方", "date":"2026-10-08", "horses":[horse]}
        enriched=await enrich_race_missing(detail, bank_registry=reg)
        self.assertEqual(calls, [])
        self.assertEqual(enriched["preparedMeta"]["supplementalSearch"]["firstCornerEvidenceReadyHorses"],1)

    async def test_individual_timing_coverage_requires_source_and_prior_date(self):
        from arvexq.ingest.fallback_enrichment import _horse_early_timing_count
        old = [
            dict(run(30, [1, 2]), earlyTiming={
                "sourceKind": "individual_sensor", "sourceRef": "provider:123",
                "first200mSeconds": 12.9
            }),
            dict(run(24, [2, 2]), earlyTiming={
                "sourceKind": "official_race_lap", "sourceRef": "jra:race:123",
                "first200mSeconds": 12.2
            }),
            dict(run(18, [1, 2]), earlyTiming={
                "sourceKind": "video_estimate", "sourceRef": "video:456",
                "gateReactionSeconds": 0.4
            }),
            {"date":"2026-10-09", "track":"大井", "distance":1400,
             "raceNumber":4, "earlyTiming":{
                 "sourceKind":"individual_sensor", "sourceRef":"future",
                 "first200mSeconds":10.0}},
        ]
        self.assertEqual(_horse_early_timing_count(
            {"recentRaces":old}, "2026-10-08", 5
        ), 2)

    async def test_future_run_cannot_satisfy_corner_evidence(self):
        horse={"horseNumber":3,"recentRaces":[run(30,[None,2]),{
            "date":"2026-10-09","track":"大井","distance":1400,
            "raceNumber":4,"cornerPositions":[1,1],
        }]}
        self.assertEqual(_first_corner_coverage(horse, "2026-10-08", 5),0)
        merged=_merge_runs(horse["recentRaces"], [], cutoff="2026-10-08", limit=5)
        self.assertEqual(len(merged),1)


if __name__ == "__main__":
    unittest.main()
