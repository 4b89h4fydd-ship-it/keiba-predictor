"""Static API pack builder: research evidence carry-over guard.

Regression for the 2026-11-22..25 unevaluated-horses incident: the
observed mineta/margin evidence (horses[].researchEvidence, attached
by the prefetch analyze stage) reaches a lane payload only when that
stage decorated the race in that run.  On the retired D1 path the
stored detail was protected by arvexq_protect_sync, but the GitHub-only
pack lanes build straight from payloads, so the first undecorated
full build of the day erased the evidence an earlier build had
published (2026-11-25: a 14:04 JST full build published evidence for
6 races; the 14:41 JST full build wiped it to zero) and the app
rendered every horse as unevaluated.  The build must graft the
evidence from the race's own existing pack onto incoming details
whose horses lack it, must never replace an incoming value, and must
not invent evidence for races whose pack never carried it.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import arvexq_static_api_build as b

DATE = "2026-11-25"
RID1 = f"nar-{DATE}-浦和-01"
RID2 = f"nar-{DATE}-浦和-02"


def evidence(value):
    return {"factors": {"version": "arvexq-empirical-fusion-v1",
                        "items": [{"key": "mineta", "weight": .60,
                                   "value": value, "available": True},
                                  {"key": "margin", "weight": .40,
                                   "value": value, "available": True}],
                        "calibrated": False},
            "sectionals": {}, "status": "nar-observed-only"}


def summary(rid):
    return {"id": rid, "date": DATE, "circuit": "地方", "track": "浦和",
            "raceNumber": 1, "startTime": "11:00", "title": "1R",
            "surface": "ダート", "distance": 1400, "weather": "晴",
            "condition": "良", "volatility": {"label": "", "score": None},
            "raceStatus": "", "updatedAtEpoch": 0}


def decorated_detail(rid):
    return {
        "id": rid, "date": DATE, "track": "浦和", "raceNumber": 1,
        "horses": [{"horseNumber": 1, "name": "甲",
                    "researchEvidence": evidence(0.5)},
                   {"horseNumber": 2, "name": "乙",
                    "researchEvidence": evidence(0.4)}],
        "researchEvidenceVersion": "arvexq-race-intelligence-v2",
        "researchEvidenceHorses": 2,
        "biasProvenance": {"version": "arvexq-bias-provenance-v1"},
        "preparedMeta": {"diagnosisReady": True},
    }


def thin_detail(rid):
    """A lane payload detail that never passed the analyze stage."""
    return {
        "id": rid, "date": DATE, "track": "浦和", "raceNumber": 1,
        "horses": [{"horseNumber": 1, "name": "甲"},
                   {"horseNumber": 2, "name": "乙"}],
        "preparedMeta": {"diagnosisReady": True},
    }


def sync_payload(details):
    return {"summaries": [summary(d["id"]) for d in details],
            "details": details, "odds_current": []}


def read_pack(out_dir, rid):
    body = json.loads((Path(out_dir) / "race" / f"{rid}.json")
                      .read_text(encoding="utf-8"))
    return body["detail"]


class EvidenceCarryoverTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name) / "packs"

    def tearDown(self):
        self._tmp.cleanup()

    def _seed_existing(self, details):
        model = b.model_from_sync_payload(sync_payload(details))
        b.build(model, self.out, "2026-11-25T07:00:00+09:00")

    def test_full_build_keeps_published_evidence(self):
        self._seed_existing([decorated_detail(RID1)])
        incoming = b.model_from_sync_payload(
            sync_payload([thin_detail(RID1)]))
        healed = b.carry_over_research_evidence(incoming, self.out)
        self.assertEqual(healed, [RID1])
        b.build(incoming, self.out, "2026-11-25T12:00:00+09:00")
        detail = read_pack(self.out, RID1)
        by_no = {h["horseNumber"]: h for h in detail["horses"]}
        self.assertEqual(by_no[1]["researchEvidence"], evidence(0.5))
        self.assertEqual(by_no[2]["researchEvidence"], evidence(0.4))
        self.assertEqual(detail["researchEvidenceVersion"],
                         "arvexq-race-intelligence-v2")
        self.assertEqual(detail["researchEvidenceHorses"], 2)
        self.assertEqual(detail["biasProvenance"],
                         {"version": "arvexq-bias-provenance-v1"})

    def test_race_without_published_evidence_stays_bare(self):
        self._seed_existing([thin_detail(RID2)])
        incoming = b.model_from_sync_payload(
            sync_payload([thin_detail(RID2)]))
        healed = b.carry_over_research_evidence(incoming, self.out)
        self.assertEqual(healed, [])
        b.build(incoming, self.out, "2026-11-25T12:00:00+09:00")
        detail = read_pack(self.out, RID2)
        for h in detail["horses"]:
            self.assertNotIn("researchEvidence", h)
        self.assertNotIn("researchEvidenceHorses", detail)

    def test_incoming_evidence_is_never_overwritten(self):
        self._seed_existing([decorated_detail(RID1)])
        own = thin_detail(RID1)
        own["horses"][0]["researchEvidence"] = evidence(0.9)
        own["researchEvidenceVersion"] = "arvexq-race-intelligence-v2"
        own["researchEvidenceHorses"] = 2
        incoming = b.model_from_sync_payload(sync_payload([own]))
        healed = b.carry_over_research_evidence(incoming, self.out)
        # Only horse 2 was missing its block, so the race is healed
        # but horse 1 keeps the incoming (newer) value.
        self.assertEqual(healed, [RID1])
        detail = incoming.details[RID1]
        by_no = {h["horseNumber"]: h for h in detail["horses"]}
        self.assertEqual(by_no[1]["researchEvidence"], evidence(0.9))
        self.assertEqual(by_no[2]["researchEvidence"], evidence(0.4))
        self.assertEqual(detail["researchEvidenceHorses"], 2)


if __name__ == "__main__":
    unittest.main()
