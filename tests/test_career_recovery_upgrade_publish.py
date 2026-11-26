"""Career-recovery upgrade (2026-11-26): the one-time re-issue of
a frozen v9b forecast that was published with a runner UNSCORED
(abilityScore null in the sealed diagnosis) because her career
resolution failed transiently at publication time, once the
detail carries her past runs again.

The 2026-11-26 Urawa 3R case: the runner's netkeiba career lookup
timed out during the morning build, so she reached the pack with
no past runs and no ability score; the career data recovered
later the same morning (the detail now carries her four past
runs), but the forecast freeze kept the unscored forecast sealed.
The user directed the re-issue. This branch is the standing
upgrade pattern (nk-materials / nar-decay): a v9b race whose
sealed diagnosis has an active unscored runner WITH scoring
evidence now on the current detail (past runs, or the v8 extras
spd2 pair) is re-issued once from the current payload.
Exactly-once is structural — the re-issue scores the runner, so
the sealed diagnosis no longer carries her null — and races past
their post never reach the branch (the build's post/result
checks run first). A runner with no evidence anywhere never
qualifies: evidence is read, never estimated.

These tests pin the qualification matrix of
_career_recovery_upgrade_info, the structural exactly-once
property, the post-time guard, and — with the heavy collaborators
mocked at the publish module boundary — that a build-level
upgrade rebuilds, stamps the revision chain, and keeps the
frozen forecast when the rebuild still leaves the runner
unscored.
"""
from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from arvexq.prediction.unified_product import verified as verified_unified
from rewrite.analysis.forecast import RunnerForecast
from rewrite.output.api_shape import MODEL_VERSION
from scripts.arvexq_rewrite_publish import (
    NAR_DECAY_V9B_ABILITY_MODEL_VERSION,
    V9B_LANE,
    _career_recovery_upgrade_info,
    build_publish_detail,
)
from tests.test_publish_mass_feature_archive import (
    EXTRAS,
    fabricated_race,
    past_run,
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


def stored_detail(*, lane=V9B_LANE, unscored=(3,), with_runs=True,
                  scratched=()) -> dict:
    horses = []
    for n in (1, 2, 3, 4, 5):
        horse = {"horseNumber": n, "name": NAMES[n], "winOdds": 3.0}
        if with_runs:
            horse["allPastRuns"] = [past_run("2026-10-20", 2),
                                    past_run("2026-10-06", 4)]
            horse["careerStartEvidence"] = {"starts": 2}
        else:
            horse["allPastRuns"] = []
            horse["careerStartEvidence"] = {"starts": 0}
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
    roster = [{"horseNumber": n, "name": NAMES[n]}
              for n in (1, 2, 3, 4, 5) if n not in scratched]
    diagnosis = [{"horseNumber": n,
                  "abilityScore": None if n in unscored else 0.5}
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


class CareerRecoveryQualificationTests(TestCase):
    def test_qualifies_when_unscored_runner_has_past_runs(self):
        info = _career_recovery_upgrade_info(stored_detail(), NOW)
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "career-recovery-upgrade")
        self.assertEqual(info["recoveredHorseNumbers"], [3])
        self.assertEqual(info["publishedAt"], PUBLISHED_AT)
        self.assertEqual(info["previousAbilityLane"], V9B_LANE)

    def test_no_unscored_runner_never_qualifies(self):
        detail = stored_detail(unscored=())
        self.assertIsNone(_career_recovery_upgrade_info(detail, NOW))

    def test_missing_ability_score_key_never_qualifies(self):
        # Diagnosis entries that lack the abilityScore key
        # entirely (an older / partial product shape, e.g. the
        # ticket-upgrade fixtures) are not read as "unscored":
        # the production diagnosis builder always writes the key.
        detail = stored_detail()
        for entry in detail["unifiedForecast"]["diagnosis"]:
            del entry["abilityScore"]
        self.assertIsNone(_career_recovery_upgrade_info(detail, NOW))

    def test_unscored_without_any_evidence_never_qualifies(self):
        # Evidence is read, never estimated: no past runs on the
        # detail and no spd2 pair in the extras — no re-issue.
        detail = stored_detail(with_runs=False)
        with patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                   return_value={}):
            self.assertIsNone(
                _career_recovery_upgrade_info(detail, NOW))

    def test_unscored_with_extras_spd2_pair_qualifies(self):
        # A no-past-runs runner the ability layer can score from
        # the extras spd2 pair (the ability-trial supplement path)
        # also qualifies.
        detail = stored_detail(with_runs=False)
        extras = {RACE_ID: {"segment": "nar", "extras": {
            "3": {"spd2_recent": 0.42, "spd2_best": 0.10}}}}
        with patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                   return_value=extras):
            info = _career_recovery_upgrade_info(detail, NOW)
        self.assertIsNotNone(info)
        self.assertEqual(info["recoveredHorseNumbers"], [3])

    def test_scratched_unscored_runner_never_qualifies(self):
        detail = stored_detail(scratched=(3,))
        self.assertIsNone(_career_recovery_upgrade_info(detail, NOW))

    def test_other_lanes_never_qualify(self):
        for lane in ("v8-elo-speed2", "v1-prior"):
            detail = stored_detail(lane=lane)
            self.assertIsNone(
                _career_recovery_upgrade_info(detail, NOW), lane)

    def test_missing_marker_never_qualifies(self):
        detail = stored_detail()
        del detail["preparedMeta"]
        self.assertIsNone(_career_recovery_upgrade_info(detail, NOW))

    def test_post_guard(self):
        detail = stored_detail()
        just_before = datetime(2026, 11, 4, 12, 49, tzinfo=JST)
        self.assertIsNotNone(
            _career_recovery_upgrade_info(detail, just_before))
        past_post = datetime(2026, 11, 4, 12, 51, tzinfo=JST)
        self.assertIsNone(
            _career_recovery_upgrade_info(detail, past_post))


def _build(detail, fake_v8):
    with patch("scripts.arvexq_rewrite_publish.normalize_race",
               return_value=fabricated_race()), \
            patch("scripts.arvexq_rewrite_publish.forecast_race_v8",
                  side_effect=fake_v8), \
            patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                  return_value=EXTRAS):
        return build_publish_detail(
            detail, {"race_id": RACE_ID, "id": RACE_ID}, NOW)


class CareerRecoveryBuildTests(TestCase):
    def test_build_reissues_and_stamps_revision(self):
        new, receipt = _build(stored_detail(),
                              lambda race, extras, **kw: v8_forecast())
        self.assertIsNotNone(new, receipt)
        diagnosis = {d["horseNumber"]: d["abilityScore"]
                     for d in new["unifiedForecast"]["diagnosis"]}
        self.assertTrue(all(v is not None for v in diagnosis.values()),
                        diagnosis)
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertEqual(marker["firstPublishedAt"], PUBLISHED_AT)
        revision = marker["revision"]
        self.assertEqual(revision["kind"], "career-recovery-upgrade")
        self.assertEqual(revision["reason"], "career-recovery-upgrade")
        self.assertEqual(revision["revisionCount"], 1)
        self.assertEqual(revision["previousReceiptSha256"], RECEIPT)
        self.assertEqual(revision["recoveredHorseNumbers"], [3])
        self.assertIsNotNone(verified_unified(new))
        # Structural exactly-once: the re-issued detail no longer
        # qualifies.
        self.assertIsNone(_career_recovery_upgrade_info(new, NOW))

    def test_build_keeps_frozen_when_runner_still_unscored(self):
        def fake_v8(race, extras, **kwargs):
            base = v8_forecast()
            runners = []
            for r in base.runners:
                if r.number == 3:
                    runners.append(RunnerForecast(
                        number=r.number, name=r.name,
                        ability_score=None, strength=r.strength,
                        pace_adjustment=r.pace_adjustment,
                        pace_reasons=r.pace_reasons, p_win=None,
                        p_top2=None, p_top3=None, mark="",
                        status="unscored"))
                else:
                    runners.append(r)
            return type(base)(base.race_id, base.beta,
                              base.probability_status,
                              tuple(runners), base.status)

        new, reason = _build(stored_detail(), fake_v8)
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("frozen:"), reason)
        self.assertIn("career-recovery rebuild did not score", reason)


if __name__ == "__main__":
    import unittest
    unittest.main()
