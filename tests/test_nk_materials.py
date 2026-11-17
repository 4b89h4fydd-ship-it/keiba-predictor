"""netkeiba materials in the forecast (2026-11-17).

User instruction: "集めたデータは全部、予想に入れろ" — the
collected netkeiba materials enter the production forecast. The
transport is rewrite/data/nk_materials/<date>.json; the
adjustment is the integrated evaluation (vendored verbatim,
frozen DEFAULT_WEIGHTS) applied inside build_publish_detail
after the v9b post-processing, and races frozen on the v9b lane
without the adjustment are re-issued once by the nk-materials
upgrade.

These tests pin: the loader (missing/corrupt -> no materials),
the adapter (deterministic, probability-conserving, spd2 deficit
sign convention, no-op when nothing can contribute), the
qualification matrix of _nk_materials_upgrade_info, and — with
the heavy collaborators mocked at the publish module boundary —
that a build stamps the nkMaterials marker, that the one-time
upgrade rebuilds with the adjustment and the revision chain,
and that the frozen forecast is kept when the rebuild does not
land the adjustment.
"""
from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from arvexq.prediction.unified_product import verified as verified_unified
from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.nk_materials import (
    apply_nk_materials, parse_materials_payload, speed_coverage)
from rewrite.data.normalize import Obs, RaceRecord, RunnerRecord, obs
from rewrite.output.api_shape import MODEL_VERSION
from rewrite.safety.contracts import Segment
from scripts.arvexq_rewrite_publish import (
    NAR_DECAY_V9B_ABILITY_MODEL_VERSION,
    V9B_LANE,
    _load_nk_materials,
    _nk_materials_upgrade_info,
    build_publish_detail,
)

JST = ZoneInfo("Asia/Tokyo")
RECEIPT = "b" * 64
RACE_ID = "nar-2026-11-17-金沢-01"
NK_ID = "202646111701"
DATE = "2026-11-17"
POST = "20:40"
PUBLISHED_AT = "2026-11-17T06:12:00+09:00"
NOW = datetime(2026, 11, 17, 16, 0, tzinfo=JST)
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}
ODDS = {1: 2.4, 2: 3.1, 3: 5.5, 4: 9.0, 5: 21.0}
STRENGTHS = {1: 0.30, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.10}
# Horse 5 carries the field's best netkeiba index while its own
# spd2 deficit is the field's worst (slowest): the speed residual
# must lift it. Horse 1 is the mirror image.
NK_AVG5 = {1: 40, 2: 55, 3: 60, 4: 75, 5: 95}
SPD2_DEFICIT = {1: 0.5, 2: 1.0, 3: 1.2, 4: 1.5, 5: 2.5}

MATERIALS_PAYLOAD = {
    "version": "nk-materials-v1",
    "date": DATE,
    "races": {
        RACE_ID: {
            "netkeibaRaceId": NK_ID,
            "horses": {
                str(n): {"nk_best": NK_AVG5[n] + 5, "nk_avg5": NK_AVG5[n],
                         "nk_dist": None, "nk_course": None,
                         "nk_recent": [NK_AVG5[n]] * 3}
                for n in NAMES},
            "courseAnalysis": {"コース": "金沢1500m"},
        },
    },
}
MATERIALS = parse_materials_payload(MATERIALS_PAYLOAD)
EXTRAS = {RACE_ID: {"segment": "nar",
                    "extras": {str(n): {"elo": 1500.0,
                                        "spd2_recent": SPD2_DEFICIT[n],
                                        "spd2_best": SPD2_DEFICIT[n] - 0.3}
                               for n in NAMES}}}


def fabricated_race() -> RaceRecord:
    missing = Obs(None, "test", "not_captured")
    runners = []
    for number in (1, 2, 3, 4, 5):
        runners.append(RunnerRecord(
            number=number, horse_id=missing,
            name=obs(NAMES[number], "test"), frame_number=missing,
            age=missing, sex=missing, jockey=missing, trainer=missing,
            carried_weight=missing, body_weight=missing,
            body_weight_change=missing,
            win_odds=obs(ODDS[number], "test"),
            scratched=False, past_runs=()))
    return RaceRecord(
        race_id=RACE_ID, date=DATE, circuit=obs("地方", "test"),
        track="金沢", race_number=obs(1, "test"), title=missing,
        start_time=obs(POST, "test"), distance=obs(1500, "test"),
        surface=obs("ダート", "test"), weather=missing,
        condition=missing, updated_at=missing, segment=Segment.NAR,
        source="test", runners=tuple(runners))


def v9b_like_forecast() -> RaceForecast:
    """A forecast as it stands after the v9b post-processing:
    strength and p_win carry the blended probabilities."""
    runners = [RunnerForecast(
        number=n, name=NAMES[n], ability_score=0.5, strength=s,
        pace_adjustment=1.0, pace_reasons=(), p_win=s, p_top2=None,
        p_top3=None, mark="", status="scored")
        for n, s in STRENGTHS.items()]
    return RaceForecast(RACE_ID, 3.0, "calibrated",
                        tuple(runners), "ok")


def past_run(day: str, finish: int) -> dict:
    return {
        "date": day, "track": "金沢", "raceNumber": 3,
        "distance": 1400, "surface": "ダート", "condition": "良",
        "finish": finish, "fieldSize": 10, "timeSeconds": 92.0 + finish,
        "last3fSeconds": 38.0, "cornerPositions": [3, 3, 2],
        "carriedWeight": 55, "jockey": "騎手", "winOdds": 4.0,
        "bodyWeight": 470, "marginSeconds": 0.4,
    }


def fresh_detail() -> dict:
    horses = []
    for number in (1, 2, 3, 4, 5):
        horses.append({
            "horseNumber": number, "name": NAMES[number],
            "frameNumber": number, "age": 4, "sex": "牡",
            "carriedWeight": 55.0, "jockey": "騎手", "trainer": "調教師",
            "winOdds": ODDS[number], "popularity": number,
            "allPastRuns": [past_run("2026-11-03", number),
                            past_run("2026-10-20", (number % 5) + 1)],
        })
    return {
        "id": RACE_ID, "date": DATE, "circuit": "地方", "track": "金沢",
        "raceNumber": 1, "scheduledStartTime": POST,
        "distance": 1500, "surface": "ダート", "condition": "良",
        "horses": horses,
    }


def stored_detail(*, nk_stamp=False, lane=V9B_LANE, date=DATE,
                  post=POST) -> dict:
    horses = [{"horseNumber": n, "name": NAMES[n], "winOdds": 3.0}
              for n in (1, 2, 3, 4, 5)]
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
        "evidenceDecay": {"type": "evidence-runs-shrinkage", "k": 2.0,
                          "scope": "nar-only"},
    }
    if nk_stamp:
        marker["nkMaterials"] = {"version": "nk-materials-v1",
                                 "applied": True}
    roster = [{"horseNumber": h["horseNumber"], "name": h["name"]}
              for h in horses]
    unified = {"receiptSha256": RECEIPT, "roster": roster,
               "abilityModelVersion": NAR_DECAY_V9B_ABILITY_MODEL_VERSION}
    return {
        "id": RACE_ID, "date": date, "scheduledStartTime": post,
        "circuit": "地方", "venue": "金沢",
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preparedMeta": {"rewritePublish": marker},
        "unifiedForecast": unified,
        "horses": horses,
    }


class LoaderTests(TestCase):
    def test_missing_file_is_no_materials(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.arvexq_rewrite_publish.NK_MATERIALS_DIR",
                       Path(tmp)):
                self.assertEqual(_load_nk_materials(DATE), {})

    def test_corrupt_file_is_no_materials(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / f"{DATE}.json").write_text("{broken",
                                                    encoding="utf-8")
            with patch("scripts.arvexq_rewrite_publish.NK_MATERIALS_DIR",
                       Path(tmp)):
                self.assertEqual(_load_nk_materials(DATE), {})

    def test_valid_file_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / f"{DATE}.json").write_text(
                json.dumps(MATERIALS_PAYLOAD), encoding="utf-8")
            with patch("scripts.arvexq_rewrite_publish.NK_MATERIALS_DIR",
                       Path(tmp)):
                loaded = _load_nk_materials(DATE)
        entry = loaded[RACE_ID]
        self.assertEqual(entry["netkeibaRaceId"], NK_ID)
        self.assertEqual(entry["horses"][5]["nk_avg5"], 95)
        self.assertEqual(entry["courseAnalysis"], {"コース": "金沢1500m"})
        self.assertEqual(speed_coverage(entry), 5)

    def test_parse_drops_non_numeric_values(self):
        payload = {"races": {RACE_ID: {"horses": {
            "1": {"nk_avg5": "77", "nk_best": 90},
            "x": {"nk_avg5": 50}}}}}
        parsed = parse_materials_payload(payload)
        self.assertIsNone(parsed[RACE_ID]["horses"][1]["nk_avg5"])
        self.assertEqual(parsed[RACE_ID]["horses"][1]["nk_best"], 90)
        self.assertNotIn("x", parsed[RACE_ID]["horses"])


class AdapterTests(TestCase):
    def _extras(self):
        return {n: {"spd2_recent": SPD2_DEFICIT[n]} for n in NAMES}

    def test_adjustment_moves_probabilities_and_conserves(self):
        forecast = v9b_like_forecast()
        adjusted, info = apply_nk_materials(
            forecast, MATERIALS[RACE_ID], self._extras())
        self.assertTrue(info["applied"])
        self.assertIn("speed", info["terms"])
        by_number = {r.number: r for r in adjusted.runners}
        # The residual lifts the horse netkeiba rates far above
        # its own spd2, and damps the mirror-image favourite.
        self.assertGreater(by_number[5].p_win, STRENGTHS[5])
        self.assertLess(by_number[1].p_win, STRENGTHS[1])
        total = sum(r.strength for r in adjusted.runners)
        self.assertAlmostEqual(total, 1.0, places=5)
        # Marks follow the adjusted order: the top probability
        # carries ◎.
        top = max(adjusted.runners, key=lambda r: r.p_win)
        self.assertEqual(top.mark, "◎")

    def test_adjustment_is_deterministic(self):
        first, _ = apply_nk_materials(
            v9b_like_forecast(), MATERIALS[RACE_ID], self._extras())
        second, _ = apply_nk_materials(
            v9b_like_forecast(), MATERIALS[RACE_ID], self._extras())
        self.assertEqual([r.strength for r in first.runners],
                         [r.strength for r in second.runners])

    def test_spd2_deficit_sign_convention(self):
        # Equal v9b, equal netkeiba index: the horse whose OWN
        # evidence is weaker (larger spd2 deficit) must gain —
        # the residual is z(nk) - z(own speed), and the extras'
        # spd2 is a deficit, so it enters negated. With the sign
        # flipped this ordering inverts.
        strengths = {1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25}
        runners = [RunnerForecast(
            number=n, name=NAMES[n], ability_score=0.5, strength=s,
            pace_adjustment=1.0, pace_reasons=(), p_win=s, p_top2=None,
            p_top3=None, mark="", status="scored")
            for n, s in strengths.items()]
        forecast = RaceForecast(RACE_ID, 3.0, "calibrated",
                                tuple(runners), "ok")
        entry = {"netkeibaRaceId": NK_ID, "courseAnalysis": None,
                 "horses": {n: {"nk_best": None, "nk_avg5": v,
                                "nk_dist": None, "nk_course": None,
                                "nk_recent": None}
                            for n, v in ((1, 80), (2, 80), (3, 50),
                                         (4, 50))}}
        extras = {1: {"spd2_recent": 2.0}, 2: {"spd2_recent": 0.5},
                  3: {"spd2_recent": 1.0}, 4: {"spd2_recent": 1.0}}
        adjusted, info = apply_nk_materials(forecast, entry, extras)
        self.assertTrue(info["applied"])
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[1].p_win, by_number[2].p_win)

    def test_no_materials_returns_same_object(self):
        forecast = v9b_like_forecast()
        for entry in (None, {}, {"horses": {}}):
            adjusted, info = apply_nk_materials(
                forecast, entry, self._extras())
            self.assertIs(adjusted, forecast)
            self.assertFalse(info["applied"])

    def test_too_few_indexed_horses_returns_same_object(self):
        # Two indexed horses cannot produce a z-score (integrate
        # needs three), so no term exists and nothing may move.
        forecast = v9b_like_forecast()
        entry = {"netkeibaRaceId": NK_ID, "courseAnalysis": None,
                 "horses": {n: {"nk_best": None, "nk_avg5": NK_AVG5[n],
                                "nk_dist": None, "nk_course": None,
                                "nk_recent": None}
                            for n in (1, 2)}}
        adjusted, info = apply_nk_materials(
            forecast, entry, self._extras())
        self.assertIs(adjusted, forecast)
        self.assertFalse(info["applied"])


class UpgradeQualificationTests(TestCase):
    def _info(self, detail, now=NOW):
        with patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                   return_value=MATERIALS):
            return _nk_materials_upgrade_info(detail, now)

    def test_qualifies_when_all_conditions_hold(self):
        info = self._info(stored_detail())
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "nk-materials-upgrade")
        self.assertEqual(info["previousAbilityLane"], V9B_LANE)

    def test_already_stamped_never_qualifies(self):
        self.assertIsNone(self._info(stored_detail(nk_stamp=True)))

    def test_before_cutover_never_qualifies(self):
        self.assertIsNone(self._info(stored_detail(date="2026-11-16")))

    def test_other_lanes_never_qualify(self):
        for lane in ("v8-elo-speed2", "v1-prior"):
            self.assertIsNone(self._info(stored_detail(lane=lane)), lane)

    def test_no_materials_entry_never_qualifies(self):
        with patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                   return_value={}):
            self.assertIsNone(
                _nk_materials_upgrade_info(stored_detail(), NOW))

    def test_thin_materials_never_qualify(self):
        thin = parse_materials_payload({"races": {RACE_ID: {
            "horses": {str(n): {"nk_avg5": 50} for n in (1, 2)}}}})
        with patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                   return_value=thin):
            self.assertIsNone(
                _nk_materials_upgrade_info(stored_detail(), NOW))

    def test_post_guard(self):
        self.assertIsNotNone(self._info(
            stored_detail(), datetime(2026, 11, 17, 20, 39, tzinfo=JST)))
        self.assertIsNone(self._info(
            stored_detail(), datetime(2026, 11, 17, 20, 41, tzinfo=JST)))


def _build(detail, materials=MATERIALS, **patches):
    ctx = [
        patch("scripts.arvexq_rewrite_publish.normalize_race",
              return_value=fabricated_race()),
        patch("scripts.arvexq_rewrite_publish.forecast_race_v8",
              return_value=v9b_like_forecast()),
        patch("scripts.arvexq_rewrite_publish._load_v8_extras",
              return_value=EXTRAS),
        patch("scripts.arvexq_rewrite_publish._load_nk_materials",
              return_value=materials),
    ]
    for extra in patches.values():
        ctx.append(extra)
    for c in ctx:
        c.start()
    try:
        return build_publish_detail(
            detail, {"race_id": RACE_ID, "id": RACE_ID}, NOW)
    finally:
        for c in reversed(ctx):
            c.stop()


class BuildTests(TestCase):
    def test_first_publication_carries_the_stamp(self):
        new, receipt = _build(fresh_detail())
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        stamp = marker["nkMaterials"]
        self.assertTrue(stamp["applied"])
        self.assertEqual(stamp["netkeibaRaceId"], NK_ID)
        self.assertEqual(stamp["coverage"]["speed"], 5)
        self.assertNotIn("revision", marker)
        self.assertIsNotNone(verified_unified(new))

    def test_first_publication_without_materials_is_unstamped(self):
        new, receipt = _build(fresh_detail(), materials={})
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertNotIn("nkMaterials", marker)

    def test_materials_move_the_published_probabilities(self):
        with_mat, _ = _build(fresh_detail())
        without_mat, _ = _build(fresh_detail(), materials={})
        win_with = with_mat["prediction"]["stages"]["probability"]["value"]["win"]
        win_without = without_mat["prediction"]["stages"]["probability"]["value"]["win"]
        self.assertGreater(win_with[5], win_without[5])
        self.assertLess(win_with[1], win_without[1])

    def test_frozen_race_is_reissued_once_with_revision(self):
        new, receipt = _build(stored_detail())
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertTrue(marker["nkMaterials"]["applied"])
        self.assertEqual(marker["firstPublishedAt"], PUBLISHED_AT)
        revision = marker["revision"]
        self.assertEqual(revision["kind"], "nk-materials-upgrade")
        self.assertEqual(revision["reason"], "nk-materials-upgrade")
        self.assertEqual(revision["revisionCount"], 1)
        self.assertEqual(revision["previousReceiptSha256"], RECEIPT)
        self.assertIsNotNone(verified_unified(new))
        # And the rebuilt detail itself no longer qualifies.
        self.assertIsNone(self._recheck(new))

    def _recheck(self, detail):
        with patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                   return_value=MATERIALS):
            return _nk_materials_upgrade_info(detail, NOW)

    def test_frozen_race_without_materials_stays_frozen(self):
        new, reason = _build(stored_detail(), materials={})
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("frozen:"), reason)

    def test_frozen_kept_when_rebuild_does_not_land(self):
        # The v9b transform passes through on the rebuild, so the
        # adjustment cannot apply: the frozen forecast is kept.
        passthrough = patch(
            "scripts.arvexq_rewrite_publish.postprocess_forecast",
            side_effect=lambda forecast, **kw: (
                forecast, {"passthrough": "degenerate vector"}))
        new, reason = _build(stored_detail(), postprocess=passthrough)
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("frozen:"), reason)
        self.assertIn("nk-materials rebuild did not land", reason)


if __name__ == "__main__":
    import unittest
    unittest.main()
