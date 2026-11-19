"""Regression: observed research evidence must survive thin writes (2026-11-19).

The observed mineta/margin evidence (attach_evidence) is attached only
by the prefetch analyze stage. The collect stage decorates with
include_evidence=False, and live/result syncs re-send details without
the evidence, so a single thin write through protect_detail erased
researchEvidence from D1 — on 2026-11-19 all 36 races showed every
horse as unevaluated, and the analyze stage then skipped the races
forever because its input hash still matched.

These tests pin the two halves of the fix:
- scripts/arvexq_protect_sync.protect_detail restores the stored
  evidence (top-level keys and per-horse researchEvidence) on
  non-publish writes that lack it;
- scripts.arvexq_prefetch._analysis_current treats a usable card
  without researchEvidenceHorses as not current, so the analyze stage
  re-decorates it.
"""
from __future__ import annotations

from copy import deepcopy
from unittest import TestCase

from arvexq.pipeline.fingerprints import analysis_input_hash
from arvexq.prediction.race_intelligence import RESEARCH_EVIDENCE_VERSION
from scripts import arvexq_prefetch as prefetch
from scripts.arvexq_protect_sync import protect_detail


def _evidence(value: float) -> dict:
    return {"factors": {"version": "arvexq-mineta-margin-observed-60-40-v1",
                        "items": [{"key": "mineta", "weight": .60,
                                   "value": value, "available": True},
                                  {"key": "margin", "weight": .40,
                                   "value": value, "available": True}],
                        "calibrated": False},
            "sectionals": {}, "status": "nar-observed-only"}


def _stored() -> dict:
    return {
        "id": "nar-2026-11-19-園田-01", "date": "2026-11-19",
        "track": "園田",
        "preparedMeta": {"dataVersion": "v1"},
        "researchEvidenceVersion": "arvexq-race-intelligence-v1",
        "researchEvidenceHorses": 2,
        "biasProvenance": {"version": "arvexq-bias-provenance-v1"},
        "horses": [
            {"horseNumber": 1, "name": "馬1",
             "researchEvidence": _evidence(0.5)},
            {"horseNumber": 2, "name": "馬2",
             "researchEvidence": _evidence(0.4)},
        ],
    }


def _thin() -> dict:
    """A collect/live-shaped write: same roster, no evidence anywhere."""
    return {
        "id": "nar-2026-11-19-園田-01", "date": "2026-11-19",
        "track": "園田",
        "preparedMeta": {"dataVersion": "v1", "prefetchedAtEpoch": 1760000000},
        "horses": [
            {"horseNumber": 1, "name": "馬1"},
            {"horseNumber": 2, "name": "馬2"},
        ],
    }


class ProtectResearchEvidenceTests(TestCase):
    def test_thin_write_restores_top_level_and_horse_evidence(self):
        out = protect_detail(deepcopy(_stored()), deepcopy(_thin()))
        self.assertEqual(out["researchEvidenceVersion"],
                         "arvexq-race-intelligence-v1")
        self.assertEqual(out["researchEvidenceHorses"], 2)
        self.assertEqual(out["biasProvenance"],
                         {"version": "arvexq-bias-provenance-v1"})
        by_no = {h["horseNumber"]: h for h in out["horses"]}
        self.assertEqual(by_no[1]["researchEvidence"], _evidence(0.5))
        self.assertEqual(by_no[2]["researchEvidence"], _evidence(0.4))

    def test_analyze_write_introduces_evidence_over_stored_without(self):
        # The analyze stage's own write must not be stripped: the stored
        # detail has no evidence yet, the incoming one carries it.
        old = _thin()
        incoming = _stored()
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["researchEvidenceHorses"], 2)
        by_no = {h["horseNumber"]: h for h in out["horses"]}
        self.assertEqual(by_no[1]["researchEvidence"], _evidence(0.5))

    def test_incoming_horse_evidence_is_not_overwritten(self):
        incoming = _thin()
        incoming["horses"][0]["researchEvidence"] = _evidence(0.9)
        out = protect_detail(deepcopy(_stored()), deepcopy(incoming))
        by_no = {h["horseNumber"]: h for h in out["horses"]}
        self.assertEqual(by_no[1]["researchEvidence"], _evidence(0.9))
        # The other horse still falls back to the stored copy.
        self.assertEqual(by_no[2]["researchEvidence"], _evidence(0.4))


def _analyzed_detail(with_evidence: bool) -> dict:
    horses = [
        {"horseNumber": n, "name": f"馬{n}", "jockey": "騎手",
         "carriedWeight": 57.0, "recentRaces": [], "allPastRuns": []}
        for n in (1, 2, 3)
    ]
    detail = {
        "id": "nar-2026-11-19-園田-01", "date": "2026-11-19",
        "track": "園田", "fieldSize": 3, "horses": horses,
        "preparedMeta": {"diagnosisReady": True},
    }
    if with_evidence:
        detail["researchEvidenceVersion"] = RESEARCH_EVIDENCE_VERSION
        detail["researchEvidenceHorses"] = 3
    detail["preparedMeta"]["analysisInputHash"] = analysis_input_hash(detail)
    return detail


class AnalysisCurrentEvidenceTests(TestCase):
    def test_current_when_hash_matches_and_evidence_present(self):
        self.assertTrue(prefetch._analysis_current(_analyzed_detail(True)))

    def test_not_current_when_evidence_stripped_but_hash_matches(self):
        # The 2026-11-19 regression: hash and diagnosis flags are
        # untouched by the wipe, so only the evidence check reopens it.
        self.assertFalse(prefetch._analysis_current(_analyzed_detail(False)))

    def test_unusable_card_without_evidence_stays_current(self):
        # The evidence gate is scoped to usable cards: a fragment must
        # not be forced through re-decoration by this check.
        detail = _analyzed_detail(False)
        detail["horses"] = detail["horses"][:1]
        detail["fieldSize"] = 1
        detail["preparedMeta"]["analysisInputHash"] = analysis_input_hash(detail)
        self.assertTrue(prefetch._analysis_current(detail))
