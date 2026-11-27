"""Static API pack builder: career history carry-over guard.

Regression for the 2026-11-27 truncation: the packs published in
the morning carried full career histories (one horse with 65 stored
runs), but a 09:43 JST full build from a daytime refresh payload —
whose collection had only re-fetched the recent-form view — cut 122
horses to exactly five stored runs, and the career readiness stamps
followed the thinner data down.  Career history is accumulated
fact: a build must never let a horse's stored past-run lists (or
the audit describing them) shrink below what the race's own
existing pack already holds, must never replace an incoming list
that is at least as rich, and must not invent history for races
whose pack never carried it.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import arvexq_static_api_build as b

DATE = "2026-11-27"
RID1 = f"nar-{DATE}-名古屋-03"
RID2 = f"nar-{DATE}-名古屋-04"


def runs(n, tag):
    return [{"date": f"2026-01-{i + 1:02d}", "tag": tag} for i in range(n)]


def summary(rid):
    return {"id": rid, "date": DATE, "circuit": "地方", "track": "名古屋",
            "raceNumber": 3, "startTime": "11:00", "title": "3R",
            "surface": "ダート", "distance": 1400, "weather": "晴",
            "condition": "良", "volatility": {"label": "", "score": None},
            "raceStatus": "", "updatedAtEpoch": 0}


def rich_detail(rid):
    return {
        "id": rid, "date": DATE, "track": "名古屋", "raceNumber": 3,
        "horses": [
            {"horseNumber": 1, "name": "甲",
             "allPastRuns": runs(45, "full"),
             "_careerHistoryAudit": {"observedRuns": 45,
                                     "reportedStarts": 45}},
            {"horseNumber": 2, "name": "乙",
             "allPastRuns": runs(7, "full"),
             "_careerHistoryAudit": {"observedRuns": 7,
                                     "reportedStarts": 7}},
        ],
        "preparedMeta": {"diagnosisReady": True},
    }


def thin_detail(rid):
    """A refresh payload detail carrying only the recent-form view."""
    return {
        "id": rid, "date": DATE, "track": "名古屋", "raceNumber": 3,
        "horses": [
            {"horseNumber": 1, "name": "甲",
             "allPastRuns": runs(5, "recent"),
             "_careerHistoryAudit": {"observedRuns": 5,
                                     "reportedStarts": 45}},
            {"horseNumber": 2, "name": "乙",
             "allPastRuns": runs(5, "recent"),
             "_careerHistoryAudit": {"observedRuns": 5,
                                     "reportedStarts": 7}},
        ],
        "preparedMeta": {"diagnosisReady": True},
    }


def sync_payload(details):
    return {"summaries": [summary(d["id"]) for d in details],
            "details": details, "odds_current": []}


def read_pack(out_dir, rid):
    body = json.loads((Path(out_dir) / "race" / f"{rid}.json")
                      .read_text(encoding="utf-8"))
    return body["detail"]


class CareerCarryoverTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name) / "packs"

    def tearDown(self):
        self._tmp.cleanup()

    def _seed_existing(self, details):
        model = b.model_from_sync_payload(sync_payload(details))
        b.build(model, self.out, "2026-11-27T07:00:00+09:00")

    def test_full_build_never_shrinks_stored_history(self):
        self._seed_existing([rich_detail(RID1)])
        incoming = b.model_from_sync_payload(
            sync_payload([thin_detail(RID1)]))
        healed = b.carry_over_career_history(incoming, self.out)
        self.assertEqual(healed, [RID1])
        b.build(incoming, self.out, "2026-11-27T12:00:00+09:00")
        detail = read_pack(self.out, RID1)
        by_no = {h["horseNumber"]: h for h in detail["horses"]}
        self.assertEqual(len(by_no[1]["allPastRuns"]), 45)
        self.assertEqual(by_no[1]["allPastRuns"][0]["tag"], "full")
        self.assertEqual(by_no[1]["_careerHistoryAudit"]["observedRuns"], 45)
        self.assertEqual(len(by_no[2]["allPastRuns"]), 7)

    def test_richer_incoming_history_is_kept(self):
        self._seed_existing([thin_detail(RID1)])
        incoming = b.model_from_sync_payload(
            sync_payload([rich_detail(RID1)]))
        healed = b.carry_over_career_history(incoming, self.out)
        self.assertEqual(healed, [])
        detail = incoming.details[RID1]
        by_no = {h["horseNumber"]: h for h in detail["horses"]}
        self.assertEqual(len(by_no[1]["allPastRuns"]), 45)
        self.assertEqual(by_no[1]["allPastRuns"][0]["tag"], "full")

    def test_race_without_published_history_stays_bare(self):
        bare_seed = thin_detail(RID2)
        for h in bare_seed["horses"]:
            h.pop("allPastRuns")
            h.pop("_careerHistoryAudit")
        self._seed_existing([bare_seed])
        bare = thin_detail(RID2)
        for h in bare["horses"]:
            h.pop("allPastRuns")
            h.pop("_careerHistoryAudit")
        incoming = b.model_from_sync_payload(sync_payload([bare]))
        healed = b.carry_over_career_history(incoming, self.out)
        self.assertEqual(healed, [])
        detail = incoming.details[RID2]
        for h in detail["horses"]:
            self.assertNotIn("allPastRuns", h)


if __name__ == "__main__":
    unittest.main()
