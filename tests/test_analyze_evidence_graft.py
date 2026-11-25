"""Regression: analyze must not discard computed evidence (2026-11-26).

On 2026-11-26 only 1 of 48 races carried researchEvidence in its pack:
analyze_persisted published the bare fact whenever the diagnosis was
not ready, throwing away the decoration _decorate had just computed —
and the evidence is a past-run observation record, not a prediction,
so the diagnosis gate never applied to it. _graft_evidence moves the
evidence (never anything else) from the decorated detail onto the
published fact, under the carry-over rule: existing evidence is never
overwritten and nothing is invented for uncovered horses.
"""
from __future__ import annotations

from copy import deepcopy
from unittest import TestCase

from arvexq.prediction.race_intelligence import RESEARCH_EVIDENCE_VERSION
from scripts import arvexq_prefetch as prefetch


def _evidence(value: float) -> dict:
    return {"factors": {"version": "v", "items": [
        {"key": "mineta", "weight": .60, "value": value, "available": True},
        {"key": "margin", "weight": .40, "value": value, "available": True}],
        "calibrated": False}, "sectionals": {}, "status": "nar-observed-only"}


def _detail(evidence_by_number: dict[int, float]) -> dict:
    horses = []
    for num in (1, 2, 3):
        h = {"horseNumber": num, "name": f"H{num}", "recentRaces": [{}]}
        if num in evidence_by_number:
            h["researchEvidence"] = _evidence(evidence_by_number[num])
        horses.append(h)
    out = {"id": "nar-2026-11-26-浦和-01", "horses": horses}
    if evidence_by_number:
        out["researchEvidenceVersion"] = RESEARCH_EVIDENCE_VERSION
        out["researchEvidenceHorses"] = len(evidence_by_number)
        out["biasProvenance"] = {"source": "test"}
    return out


class GraftEvidenceTest(TestCase):
    def test_moves_evidence_onto_bare_fact(self):
        fact = _detail({})
        decorated = _detail({1: 0.5, 2: 0.25, 3: 0.75})
        out = prefetch._graft_evidence(fact, decorated)
        self.assertIsNot(out, fact)
        self.assertEqual(
            [h["researchEvidence"]["factors"]["items"][0]["value"]
             for h in out["horses"]], [0.5, 0.25, 0.75])
        self.assertEqual(out["researchEvidenceHorses"], 3)
        self.assertEqual(out["researchEvidenceVersion"],
                         RESEARCH_EVIDENCE_VERSION)
        self.assertEqual(out["biasProvenance"], {"source": "test"})
        # The input fact is left untouched.
        self.assertNotIn("researchEvidence", fact["horses"][0])

    def test_never_overwrites_existing_evidence(self):
        fact = _detail({1: 0.9})
        decorated = _detail({1: 0.5, 2: 0.25})
        out = prefetch._graft_evidence(fact, decorated)
        values = {h["horseNumber"]:
                  h["researchEvidence"]["factors"]["items"][0]["value"]
                  for h in out["horses"] if "researchEvidence" in h}
        self.assertEqual(values, {1: 0.9, 2: 0.25})
        self.assertEqual(out["researchEvidenceHorses"], 2)

    def test_no_donor_evidence_returns_fact_unchanged(self):
        fact = _detail({})
        self.assertIs(prefetch._graft_evidence(fact, _detail({})), fact)
        self.assertIs(prefetch._graft_evidence(fact, None), fact)

    def test_partial_donor_coverage_counts_only_moved(self):
        fact = _detail({})
        decorated = _detail({2: 0.25})
        out = prefetch._graft_evidence(fact, decorated)
        self.assertEqual(out["researchEvidenceHorses"], 1)
        self.assertNotIn("researchEvidence", out["horses"][0])
        self.assertIn("researchEvidence", out["horses"][1])
