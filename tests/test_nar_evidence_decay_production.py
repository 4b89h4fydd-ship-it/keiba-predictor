"""F1 evidence decay in production (NAR only, 2026-11-12).

The research challenger (arvexq/research/f1_evidence_decay.py,
candidate runs-k2) is now wired into the production path:

- ``forecast_race_v8`` accepts ``evidence_decay_k``; the shrinkage
  runs only when the race's segment is NAR (the gate lives in the
  function itself, so no caller can decay a JRA race), after the
  raw scores are fixed and before strengths are derived, with the
  exact arithmetic of the evaluated challenger.
- The publish lane passes k = NAR_EVIDENCE_DECAY_K for NAR races
  only, and stamps the decayed publications so they stay
  distinguishable: the sealed product's abilityModelVersion gains
  "-nar-decay2" and the lane marker records an evidenceDecay entry.

These tests pin: production-with-decay reproduces the research
runs-k2 output exactly on the audit's synthetic race; the default
(no argument) is the undamped candidate unchanged; a JRA race is
bit-identical with and without the argument; probabilities and
marks stay well-formed; and the publish build stamps NAR and JRA
publications correctly (and the NAR seal still verifies).
"""
from __future__ import annotations

import dataclasses
from unittest import TestCase
from unittest.mock import patch

from arvexq.prediction.unified_product import verified as verified_unified
from arvexq.research.f1_evidence_decay import forecast_race_v8_decay
from rewrite.analysis.shadow_v8 import NAR_EVIDENCE_DECAY_K, forecast_race_v8
from rewrite.data.normalize import RaceRecord, obs
from rewrite.safety.contracts import Segment
from scripts.arvexq_rewrite_publish import (
    NAR_DECAY_V9B_ABILITY_MODEL_VERSION,
    V9B_ABILITY_MODEL_VERSION,
    build_publish_detail,
)
from tests.test_f1_evidence_decay import synthetic_race
from tests.test_publish_mass_feature_archive import (
    EXTRAS as NAR_EXTRAS,
)
from tests.test_publish_mass_feature_archive import (
    NAMES,
    NOW,
    fabricated_race,
    fresh_detail,
    v8_forecast,
)

JRA_RACE_ID = "jra-2026-11-04-東京-01"
JRA_EXTRAS = {JRA_RACE_ID: {"segment": "jra_flat",
                            "extras": {str(n): {"elo": 1500.0}
                                       for n in NAMES}}}


def _fields(forecast):
    return (forecast.race_id, forecast.beta, forecast.probability_status,
            forecast.status,
            tuple(dataclasses.astuple(r) for r in forecast.runners))


def _by_number(forecast):
    return {r.number: r for r in forecast.runners}


def jra_synthetic_race() -> RaceRecord:
    """The audit's synthetic race re-homed to JRA flat."""
    base = synthetic_race()
    return dataclasses.replace(
        base, race_id="jra-2026-11-01-東京-99", circuit=obs("中央", "t"),
        track="東京", segment=Segment.JRA_FLAT)


class ProductionDecayForecastTests(TestCase):
    def test_production_decay_matches_research_runs_k2(self):
        race = synthetic_race()
        production = forecast_race_v8(
            race, extras={}, evidence_decay_k=NAR_EVIDENCE_DECAY_K)
        research = forecast_race_v8_decay(
            race, extras={}, k=2.0, coverage_power=0.0)
        self.assertEqual(_fields(production), _fields(research))

    def test_synthetic_pathology_corrected_in_production(self):
        fc = forecast_race_v8(
            synthetic_race(), extras={},
            evidence_decay_k=NAR_EVIDENCE_DECAY_K)
        self.assertEqual(fc.status, "ok")
        runners = _by_number(fc)
        # The eight-start ace takes ◎ back from the one-start horse,
        # whose probability is damped (research runs-k2: 0.269).
        self.assertEqual(runners[5].mark, "◎")
        self.assertNotEqual(runners[2].mark, "◎")
        self.assertLess(runners[2].ability_score,
                        runners[5].ability_score)
        self.assertLess(runners[2].p_win, 0.30)

    def test_default_without_argument_is_undamped(self):
        fc = forecast_race_v8(synthetic_race(), extras={})
        runners = _by_number(fc)
        # The F1 pathology is still there by default: the decay is
        # an opt-in the publish lane makes for NAR only.
        self.assertEqual(runners[2].ability_score, 1.0)
        self.assertEqual(runners[2].mark, "◎")

    def test_jra_bit_identical_with_decay_argument(self):
        race = jra_synthetic_race()
        plain = forecast_race_v8(race, extras={})
        argued = forecast_race_v8(
            race, extras={}, evidence_decay_k=NAR_EVIDENCE_DECAY_K)
        self.assertEqual(plain.status, "ok")
        self.assertEqual(_fields(plain), _fields(argued))

    def test_shrinkage_factor_follows_evidence_runs(self):
        race = synthetic_race()
        base = _by_number(forecast_race_v8(race, extras={}))
        decayed = _by_number(forecast_race_v8(
            race, extras={}, evidence_decay_k=NAR_EVIDENCE_DECAY_K))
        scored = [n for n, r in base.items()
                  if r.ability_score is not None]
        raw_mean = sum(base[n].ability_score for n in scored) / len(scored)
        # #2 has 1 evidence run: deviation kept at 1 / (1 + 2).
        dev2 = base[2].ability_score - raw_mean
        self.assertAlmostEqual(
            decayed[2].ability_score - raw_mean, dev2 / 3.0, delta=0.0011)
        # #5 has 8 evidence runs: deviation kept at 8 / (8 + 2) —
        # the shrink fades as evidence grows (identity in the
        # large-n limit).
        dev5 = base[5].ability_score - raw_mean
        self.assertAlmostEqual(
            decayed[5].ability_score - raw_mean, dev5 * 0.8, delta=0.0011)

    def test_probabilities_and_marks_stay_wellformed(self):
        fc = forecast_race_v8(
            synthetic_race(), extras={},
            evidence_decay_k=NAR_EVIDENCE_DECAY_K)
        live = [r for r in fc.runners if r.p_win is not None]
        self.assertAlmostEqual(
            sum(r.p_win for r in live), 1.0, delta=0.002)
        for r in live:
            self.assertGreaterEqual(r.p_top2, r.p_win - 0.0002)
            self.assertGreaterEqual(r.p_top3, r.p_top2 - 0.0002)
        ranked = sorted(live, key=lambda r: (-r.p_win, -r.p_top3,
                                             r.number))
        self.assertEqual(ranked[0].mark, "◎")


def _build(detail, summary, race, extras):
    calls = {}

    def fake_v8(race_arg, extras_arg, **kwargs):
        calls["evidence_decay_k"] = kwargs.get("evidence_decay_k")
        return v8_forecast()

    with patch("scripts.arvexq_rewrite_publish.normalize_race",
               return_value=race), \
            patch("scripts.arvexq_rewrite_publish.forecast_race_v8",
                  side_effect=fake_v8), \
            patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                  return_value=extras):
        new, receipt = build_publish_detail(detail, summary, NOW)
    return new, receipt, calls


class PublishDecayStampingTests(TestCase):
    def test_nar_publication_is_decayed_and_stamped(self):
        new, receipt, calls = _build(
            fresh_detail(),
            {"race_id": "nar-2026-11-04-金沢-01",
             "id": "nar-2026-11-04-金沢-01"},
            fabricated_race(), NAR_EXTRAS)
        self.assertIsNotNone(new, receipt)
        self.assertEqual(calls["evidence_decay_k"], NAR_EVIDENCE_DECAY_K)
        self.assertEqual(new["unifiedForecast"]["abilityModelVersion"],
                         NAR_DECAY_V9B_ABILITY_MODEL_VERSION)
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertEqual(marker["evidenceDecay"], {
            "type": "evidence-runs-shrinkage",
            "k": NAR_EVIDENCE_DECAY_K,
            "scope": "nar-only"})
        self.assertEqual(marker["modelVersion"],
                         new["predictionModelVersion"])
        # The seal (with the decay label inside it) still verifies.
        self.assertIsNotNone(verified_unified(new))

    def test_jra_publication_is_never_decayed(self):
        detail = fresh_detail()
        detail["id"] = JRA_RACE_ID
        detail["circuit"] = "中央"
        detail["track"] = "東京"
        race = dataclasses.replace(
            fabricated_race(), race_id=JRA_RACE_ID,
            circuit=obs("中央", "test"), segment=Segment.JRA_FLAT)
        new, receipt, calls = _build(
            detail, {"race_id": JRA_RACE_ID, "id": JRA_RACE_ID},
            race, JRA_EXTRAS)
        self.assertIsNotNone(new, receipt)
        self.assertIsNone(calls["evidence_decay_k"])
        self.assertEqual(new["unifiedForecast"]["abilityModelVersion"],
                         V9B_ABILITY_MODEL_VERSION)
        self.assertNotIn("evidenceDecay",
                         new["preparedMeta"]["rewritePublish"])
        self.assertIsNotNone(verified_unified(new))


if __name__ == "__main__":
    import unittest
    unittest.main()
