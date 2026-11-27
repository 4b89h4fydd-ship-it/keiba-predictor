"""Override guard (2026-11-27): the final probability stage of the
v9b lane, adopted by user instruction after the 2026-11-26 full
audit found the issued probabilities losing to the market alone
(Brier 0.0663 vs 0.0604, LogLoss 0.2365 vs 0.2067 on 180 races)
and the model's overrides of the favourite winning 19.2% against
the displaced favourites' 30.1%.

The rule (rewrite/analysis/override_guard.py, parameters frozen):
A) when the model's top pick is not the favourite and its issued
win probability exceeds the favourite's market-implied
probability by less than 0.15, the whole win vector is replaced
by the market-implied vector; B) every vector then regresses
halfway toward the market and renormalizes. The market is built
from the payload win odds at compute time — the same odds the v9b
blend consumed — and a race whose odds do not cover the vector is
never guarded.

These tests pin the guard's firing conditions (A's margin rule,
B's regression, the A->B composition), the no-fire behaviour on
incomplete odds, the forecast rebuild (marks and strengths follow
the guarded vector), the qualification matrix of the one-time
_override_guard_upgrade_info re-issue, and — with the heavy
collaborators mocked at the publish module boundary — that a
build-level upgrade rebuilds, stamps the overrideGuard marker
and the revision chain, and keeps the frozen forecast when the
guard cannot land on the rebuild.
"""
from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from arvexq.prediction.unified_product import verified as verified_unified
from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.override_guard import (
    GUARD_VERSION,
    MARGIN_THRESHOLD,
    MARKET_LEAN_WEIGHT,
    NK_FORECAST_LEAN_WEIGHT,
    REGRESSION_LAMBDA,
    apply_override_guard,
    guard_probabilities,
)
from rewrite.analysis.shadow_v9 import postprocess_forecast
from rewrite.data.normalize import Obs, RaceRecord, RunnerRecord, obs
from rewrite.output.api_shape import MODEL_VERSION
from rewrite.safety.contracts import Segment
from scripts.arvexq_rewrite_publish import (
    NAR_DECAY_V9B_ABILITY_MODEL_VERSION,
    V9B_LANE,
    _override_guard_upgrade_info,
    build_publish_detail,
)
from tests.test_publish_mass_feature_archive import (
    EXTRAS,
    ODDS,
    fabricated_race,
    v8_forecast,
)

JST = ZoneInfo("Asia/Tokyo")
RECEIPT = "a" * 64
RACE_ID = "nar-2026-11-04-金沢-01"
DATE = "2026-11-04"
POST = "12:50"
PUBLISHED_AT = "2026-11-04T06:12:00+09:00"
NOW = datetime(2026, 11, 4, 10, 5, tzinfo=JST)  # 165 min before post
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}

# Market for ODDS_A: inverses {0.5, 0.25, 0.2, 0.1} sum to 1.05.
ODDS_A = {1: 2.0, 2: 4.0, 3: 5.0, 4: 10.0}
MARKET_A = {1: 0.5 / 1.05, 2: 0.25 / 1.05, 3: 0.2 / 1.05, 4: 0.1 / 1.05}


class GuardProbabilitiesTests(TestCase):
    def test_a_fires_on_weak_override_and_b_leaves_market_unchanged(self):
        probs = {1: 0.30, 2: 0.34, 3: 0.20, 4: 0.16}
        guarded, info = guard_probabilities(probs, ODDS_A)
        self.assertTrue(info["applied"])
        self.assertTrue(info["aFired"])
        self.assertEqual(info["modelPick"], 2)
        self.assertEqual(info["favourite"], 1)
        self.assertAlmostEqual(info["margin"], 0.34 - MARKET_A[1], places=9)
        # A replaced the vector with the market; B regresses the
        # market toward itself, so the result IS the market.
        for n in probs:
            self.assertAlmostEqual(guarded[n], MARKET_A[n], places=9)
        self.assertAlmostEqual(sum(guarded.values()), 1.0, places=12)

    def test_a_holds_on_strong_override_and_b_still_regresses(self):
        # margin = 0.60 - 0.43796 = 0.162 >= 0.15: the override
        # stands, but B still moves the vector halfway to market.
        probs = {1: 0.15, 2: 0.60, 3: 0.15, 4: 0.10}
        odds = {1: 2.2, 2: 3.0, 3: 6.0, 4: 12.0}
        guarded, info = guard_probabilities(probs, odds)
        self.assertTrue(info["applied"])
        self.assertFalse(info["aFired"])
        self.assertEqual(info["modelPick"], 2)
        self.assertEqual(info["favourite"], 1)
        self.assertGreaterEqual(info["margin"], MARGIN_THRESHOLD)
        market2 = (1 / 3.0) / (1 / 2.2 + 1 / 3.0 + 1 / 6.0 + 1 / 12.0)
        # B output for horse 2, then step C leans the whole
        # B vector geometrically toward the market (v2).
        b2 = 0.5 * 0.60 + 0.5 * market2
        market = {n: (1 / odds[n]) / sum(1 / odds[k] for k in odds)
                  for n in odds}
        b = {n: 0.5 * probs[n] + 0.5 * market[n] for n in probs}
        leaned = {n: (b[n] ** (1 - MARKET_LEAN_WEIGHT))
                  * (market[n] ** MARKET_LEAN_WEIGHT) for n in probs}
        total = sum(leaned.values())
        self.assertAlmostEqual(guarded[2], leaned[2] / total,
                               places=9)
        self.assertEqual(max(guarded, key=guarded.get), 2)

    def test_b_regresses_when_pick_is_the_favourite(self):
        probs = {1: 0.50, 2: 0.25, 3: 0.15, 4: 0.10}
        guarded, info = guard_probabilities(probs, ODDS_A)
        self.assertTrue(info["applied"])
        self.assertFalse(info["aFired"])
        self.assertEqual(info["modelPick"], 1)
        self.assertEqual(info["favourite"], 1)
        # B regresses arithmetically; C then leans the result
        # geometrically toward the market (v2 composition).
        b = {n: (1 - REGRESSION_LAMBDA) * probs[n]
             + REGRESSION_LAMBDA * MARKET_A[n] for n in probs}
        leaned = {n: (b[n] ** (1 - MARKET_LEAN_WEIGHT))
                  * (MARKET_A[n] ** MARKET_LEAN_WEIGHT) for n in probs}
        total = sum(leaned.values())
        for n in probs:
            self.assertAlmostEqual(guarded[n], leaned[n] / total,
                                   places=9)

    def test_d_leans_toward_nk_forecast_on_full_coverage(self):
        # v3 step D: after A->B->C, the vector leans
        # geometrically toward the netkeiba forecast vector.
        probs = {1: 0.50, 2: 0.25, 3: 0.15, 4: 0.10}
        nk_odds = {1: 4.0, 2: 2.0, 3: 8.0, 4: 16.0}
        guarded, info = guard_probabilities(probs, ODDS_A, nk_odds)
        self.assertTrue(info["applied"])
        self.assertTrue(info["nkLeanApplied"])
        self.assertEqual(info["nkForecastLean"],
                         NK_FORECAST_LEAN_WEIGHT)
        b = {n: (1 - REGRESSION_LAMBDA) * probs[n]
             + REGRESSION_LAMBDA * MARKET_A[n] for n in probs}
        c = {n: (b[n] ** (1 - MARKET_LEAN_WEIGHT))
             * (MARKET_A[n] ** MARKET_LEAN_WEIGHT) for n in probs}
        cs = sum(c.values())
        c = {n: v / cs for n, v in c.items()}
        nk = {n: (1 / nk_odds[n]) / sum(1 / nk_odds[k]
                                        for k in nk_odds)
              for n in probs}
        d = {n: (c[n] ** (1 - NK_FORECAST_LEAN_WEIGHT))
             * (nk[n] ** NK_FORECAST_LEAN_WEIGHT) for n in probs}
        ds = sum(d.values())
        for n in probs:
            self.assertAlmostEqual(guarded[n], d[n] / ds, places=9)
        # The nk favourite (horse 2) gains from the lean.
        plain, _ = guard_probabilities(probs, ODDS_A)
        self.assertGreater(guarded[2], plain[2])

    def test_d_skipped_on_partial_nk_coverage(self):
        probs = {1: 0.50, 2: 0.25, 3: 0.15, 4: 0.10}
        partial = {1: 4.0, 2: 2.0, 3: 8.0}  # horse 4 missing
        guarded, info = guard_probabilities(probs, ODDS_A, partial)
        plain, _ = guard_probabilities(probs, ODDS_A)
        self.assertTrue(info["applied"])
        self.assertFalse(info["nkLeanApplied"])
        for n in probs:
            self.assertAlmostEqual(guarded[n], plain[n], places=12)

    def test_margin_just_below_and_above_threshold(self):
        # Market favourite implied exactly 0.40 (inverses sum to 1).
        odds = {1: 2.5, 2: 5.0, 3: 5.0, 4: 5.0}
        below, info_below = guard_probabilities(
            {1: 0.20, 2: 0.54, 3: 0.16, 4: 0.10}, odds)
        self.assertTrue(info_below["aFired"])
        self.assertIsNotNone(below)
        above, info_above = guard_probabilities(
            {1: 0.20, 2: 0.56, 3: 0.14, 4: 0.10}, odds)
        self.assertFalse(info_above["aFired"])
        self.assertIsNotNone(above)

    def test_no_fire_when_odds_incomplete(self):
        probs = {1: 0.30, 2: 0.34, 3: 0.20, 4: 0.16}
        for odds in ({1: 2.0, 2: 4.0, 3: 5.0},          # one missing
                     {1: 2.0, 2: 4.0, 3: 5.0, 4: 1.0},   # not > 1.0
                     {1: 2.0, 2: 4.0, 3: 5.0, 4: None},  # not a number
                     {}):
            guarded, info = guard_probabilities(probs, odds)
            self.assertIsNone(guarded, odds)
            self.assertFalse(info["applied"])
            self.assertEqual(info["reason"], "market-incomplete")

    def test_no_fire_on_degenerate_inputs(self):
        guarded, info = guard_probabilities({1: 0.6, 2: 0.4}, ODDS_A)
        self.assertIsNone(guarded)
        self.assertEqual(info["reason"], "insufficient-runners")
        guarded, info = guard_probabilities(
            {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}, ODDS_A)
        self.assertIsNone(guarded)
        self.assertEqual(info["reason"], "degenerate-vector")

    def test_unnormalized_vector_behaves_like_normalized(self):
        scaled, _ = guard_probabilities(
            {1: 30.0, 2: 34.0, 3: 20.0, 4: 16.0}, ODDS_A)
        plain, _ = guard_probabilities(
            {1: 0.30, 2: 0.34, 3: 0.20, 4: 0.16}, ODDS_A)
        for n in plain:
            self.assertAlmostEqual(scaled[n], plain[n], places=12)


def _forecast(probs, *, status="ok", unscored=()):
    runners = []
    for n in sorted(probs):
        if n in unscored:
            runners.append(RunnerForecast(
                number=n, name=NAMES[n], ability_score=None,
                strength=None, pace_adjustment=1.0, pace_reasons=(),
                p_win=None, p_top2=None, p_top3=None, mark="",
                status="unscored"))
        else:
            runners.append(RunnerForecast(
                number=n, name=NAMES[n], ability_score=0.5,
                strength=probs[n], pace_adjustment=1.0,
                pace_reasons=(), p_win=probs[n], p_top2=None,
                p_top3=None, mark="", status="scored"))
    return RaceForecast(RACE_ID, 3.0, "uncalibrated-prior",
                        tuple(runners), status)


class ApplyOverrideGuardTests(TestCase):
    def test_rebuild_moves_mark_and_strength_to_the_guarded_pick(self):
        forecast = _forecast({1: 0.30, 2: 0.34, 3: 0.20, 4: 0.16})
        guarded, info = apply_override_guard(forecast, ODDS_A)
        self.assertTrue(info["applied"])
        self.assertTrue(info["aFired"])
        by_number = {r.number: r for r in guarded.runners}
        self.assertEqual(by_number[1].mark, "◎")
        self.assertAlmostEqual(by_number[1].strength, MARKET_A[1],
                               places=6)
        self.assertAlmostEqual(
            sum(r.p_win for r in guarded.runners), 1.0, places=3)
        # The input forecast is untouched (frozen dataclass, new
        # object returned).
        self.assertIsNot(guarded, forecast)

    def test_unscored_runner_passes_through_unchanged(self):
        forecast = _forecast(
            {1: 0.30, 2: 0.34, 3: 0.20, 4: 0.16, 5: 0.0}, unscored=(5,))
        guarded, info = apply_override_guard(forecast, ODDS_A)
        self.assertTrue(info["applied"])
        original = {r.number: r for r in forecast.runners}
        rebuilt = {r.number: r for r in guarded.runners}
        self.assertIs(rebuilt[5], original[5])

    def test_passthrough_shapes(self):
        forecast = _forecast({1: 0.30, 2: 0.34, 3: 0.20, 4: 0.16},
                             status="insufficient-scored-runners")
        out, info = apply_override_guard(forecast, ODDS_A)
        self.assertIs(out, forecast)
        self.assertFalse(info["applied"])
        self.assertEqual(info["reason"], "insufficient-scored-runners")

        forecast = _forecast({1: 0.30, 2: 0.34, 3: 0.20, 4: 0.16})
        out, info = apply_override_guard(forecast, {1: 2.0, 2: 4.0})
        self.assertIs(out, forecast)
        self.assertEqual(info["reason"], "market-incomplete")

        forecast = _forecast({1: 0.60, 2: 0.40, 3: 0.0, 4: 0.0},
                             unscored=(3, 4))
        out, info = apply_override_guard(forecast, ODDS_A)
        self.assertIs(out, forecast)
        self.assertEqual(info["reason"], "insufficient-strengths")


def stored_detail(*, lane=V9B_LANE, stamp="absent", missing_odds=(),
                  scratched=(), odds_value=3.0) -> dict:
    horses = []
    for n in (1, 2, 3, 4, 5):
        horse = {"horseNumber": n, "name": NAMES[n]}
        if n not in missing_odds:
            horse["winOdds"] = odds_value
        if n in scratched:
            horse["status"] = "出走取消"
        horses.append(horse)
    marker = {
        "modelVersion": MODEL_VERSION,
        "publishedAt": PUBLISHED_AT,
        "receiptSha256": RECEIPT,
        "abilityLane": lane,
        "temperature": 0.6692,
        "blendApplied": True,
        "postProcessing": {
            "type": "temperature+market-blend", "temperature": 0.6692,
            "blendWeight": 0.5, "blendApplied": True},
    }
    if stamp == "current":
        marker["overrideGuard"] = {
            "version": GUARD_VERSION, "applied": True,
            "marginThreshold": MARGIN_THRESHOLD,
            "regressionLambda": REGRESSION_LAMBDA, "aFired": False,
            "modelPick": 1, "favourite": 1, "margin": -0.017}
    elif stamp == "old-version":
        marker["overrideGuard"] = {
            "version": "override-guard-v0", "applied": True}
    elif stamp == "not-applied":
        marker["overrideGuard"] = {
            "version": GUARD_VERSION, "applied": False}
    roster = [{"horseNumber": n, "name": NAMES[n]}
              for n in (1, 2, 3, 4, 5) if n not in scratched]
    diagnosis = [{"horseNumber": n, "abilityScore": 0.5}
                 for n in (1, 2, 3, 4, 5)]
    unified = {"receiptSha256": RECEIPT, "roster": roster,
               "diagnosis": diagnosis,
               "abilityModelVersion":
                   NAR_DECAY_V9B_ABILITY_MODEL_VERSION}
    return {
        "id": RACE_ID, "date": DATE, "scheduledStartTime": POST,
        "circuit": "地方", "venue": "金沢",
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preparedMeta": {"rewritePublish": marker},
        "unifiedForecast": unified,
        "horses": horses,
    }


class OverrideGuardQualificationTests(TestCase):
    def test_qualifies_without_stamp(self):
        info = _override_guard_upgrade_info(stored_detail(), NOW)
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "override-guard-upgrade")
        self.assertEqual(info["publishedAt"], PUBLISHED_AT)
        self.assertEqual(info["previousAbilityLane"], V9B_LANE)

    def test_current_stamp_never_qualifies(self):
        detail = stored_detail(stamp="current")
        self.assertIsNone(_override_guard_upgrade_info(detail, NOW))

    def test_old_version_stamp_qualifies_once_more(self):
        detail = stored_detail(stamp="old-version")
        self.assertIsNotNone(_override_guard_upgrade_info(detail, NOW))

    def test_not_applied_stamp_qualifies(self):
        detail = stored_detail(stamp="not-applied")
        self.assertIsNotNone(_override_guard_upgrade_info(detail, NOW))

    def test_other_lanes_never_qualify(self):
        for lane in ("v8-elo-speed2", "v1-prior"):
            detail = stored_detail(lane=lane)
            self.assertIsNone(
                _override_guard_upgrade_info(detail, NOW), lane)

    def test_missing_marker_never_qualifies(self):
        detail = stored_detail()
        del detail["preparedMeta"]
        self.assertIsNone(_override_guard_upgrade_info(detail, NOW))

    def test_incomplete_current_odds_never_qualify(self):
        detail = stored_detail(missing_odds=(4,))
        self.assertIsNone(_override_guard_upgrade_info(detail, NOW))
        detail = stored_detail(odds_value=1.0)
        self.assertIsNone(_override_guard_upgrade_info(detail, NOW))

    def test_scratched_runner_without_odds_still_qualifies(self):
        detail = stored_detail(missing_odds=(5,), scratched=(5,))
        self.assertIsNotNone(_override_guard_upgrade_info(detail, NOW))

    def test_post_guard(self):
        detail = stored_detail()
        just_before = datetime(2026, 11, 4, 12, 49, tzinfo=JST)
        self.assertIsNotNone(
            _override_guard_upgrade_info(detail, just_before))
        at_post = datetime(2026, 11, 4, 12, 50, tzinfo=JST)
        self.assertIsNone(_override_guard_upgrade_info(detail, at_post))


def _race_with_missing_odds() -> RaceRecord:
    missing = Obs(None, "test", "not_captured")
    runners = []
    for number in (1, 2, 3, 4, 5):
        runners.append(RunnerRecord(
            number=number, horse_id=missing,
            name=obs(NAMES[number], "test"), frame_number=missing,
            age=missing, sex=missing, jockey=missing, trainer=missing,
            carried_weight=missing, body_weight=missing,
            body_weight_change=missing,
            win_odds=(missing if number == 5
                      else obs(ODDS[number], "test")),
            scratched=False, past_runs=()))
    return RaceRecord(
        race_id=RACE_ID, date=DATE, circuit=obs("地方", "test"),
        track="金沢", race_number=obs(1, "test"), title=missing,
        start_time=obs(POST, "test"), distance=obs(1500, "test"),
        surface=obs("ダート", "test"), weather=missing,
        condition=missing, updated_at=missing, segment=Segment.NAR,
        source="test", runners=tuple(runners))


def _build(detail, race=None):
    with patch("scripts.arvexq_rewrite_publish.normalize_race",
               return_value=race or fabricated_race()), \
            patch("scripts.arvexq_rewrite_publish.forecast_race_v8",
                  return_value=v8_forecast()), \
            patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                  return_value=EXTRAS), \
            patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                  return_value={}):
        return build_publish_detail(
            detail, {"race_id": RACE_ID, "id": RACE_ID}, NOW)


class OverrideGuardBuildTests(TestCase):
    def test_build_reissues_and_stamps_guard(self):
        new, receipt = _build(stored_detail())
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        stamp = marker["overrideGuard"]
        self.assertTrue(stamp["applied"])
        self.assertEqual(stamp["version"], GUARD_VERSION)
        self.assertEqual(stamp["marginThreshold"], MARGIN_THRESHOLD)
        self.assertEqual(stamp["regressionLambda"], REGRESSION_LAMBDA)
        # Fixture: the blended pick IS the favourite, so step A
        # does not fire; step B still applies.
        self.assertFalse(stamp["aFired"])
        self.assertEqual(stamp["modelPick"], 1)
        self.assertEqual(stamp["favourite"], 1)
        self.assertEqual(marker["firstPublishedAt"], PUBLISHED_AT)
        revision = marker["revision"]
        self.assertEqual(revision["kind"], "override-guard-upgrade")
        self.assertEqual(revision["reason"], "override-guard-upgrade")
        self.assertEqual(revision["revisionCount"], 1)
        self.assertEqual(revision["previousReceiptSha256"], RECEIPT)
        self.assertIsNotNone(verified_unified(new))
        # Structural exactly-once: the re-issued detail no longer
        # qualifies.
        self.assertIsNone(_override_guard_upgrade_info(new, NOW))

    def test_build_probabilities_match_manual_chain(self):
        new, _receipt = _build(stored_detail())
        self.assertIsNotNone(new)
        blended, _pp_info = postprocess_forecast(
            v8_forecast(), arm="v9b", win_odds=ODDS)
        expected_forecast, info = apply_override_guard(blended, ODDS)
        self.assertTrue(info["applied"])
        expected = {r.number: r.p_win
                    for r in expected_forecast.runners}
        built = {d["horseNumber"]: d["winProbability"]
                 for d in new["unifiedForecast"]["diagnosis"]}
        self.assertEqual(sorted(built), sorted(expected))
        for n in expected:
            self.assertAlmostEqual(built[n], expected[n], places=4)

    def test_build_keeps_frozen_when_guard_cannot_land(self):
        # The stored detail qualifies (its recorded odds are
        # complete), but the rebuild payload's odds no longer
        # cover the vector, so the guard cannot land: the frozen
        # forecast is kept and the qualification stands.
        new, reason = _build(stored_detail(),
                             race=_race_with_missing_odds())
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("frozen:"), reason)
        self.assertIn("override-guard rebuild did not land", reason)


if __name__ == "__main__":
    import unittest
    unittest.main()
