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

v2 (same day): the course terms are weighted in for NAR. The
tests additionally pin the bias arithmetic read from the
collected course-analysis tables, the validation's front_rate
definition, that the course terms move NAR probabilities and
stay inert for JRA / by default / without tables, and that a
v1-stamped (speed-only) publication qualifies for exactly one
more re-issue while a current-version stamp never does.
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
    NK_MATERIALS_VERSION, apply_nk_materials, course_biases,
    course_inputs_from_race, front_rate_from_runs,
    parse_materials_payload, speed_coverage)
from rewrite.data.normalize import (
    Obs, PastRun, RaceRecord, RunnerRecord, obs)
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


def stored_detail(*, nk_stamp=False, nk_stamp_version="nk-materials-v1",
                  lane=V9B_LANE, date=DATE, post=POST) -> dict:
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
        marker["nkMaterials"] = {"version": nk_stamp_version,
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


TABLE_HEADERS = ["項目", "1着", "2着", "3着", "4着以下", "出走回数",
                 "勝率", "連対率", "複勝率", "単勝回収率", "複勝回収率"]


def _table(rows):
    return {"見出し": TABLE_HEADERS, "行": rows}


# A course that punishes inner frames and rewards both the
# front styles and the outer frames (see CourseBiasTests for
# the arithmetic).
COURSE_ANALYSIS = {
    "コース": "金沢1500m",
    "有利な枠順": _table([
        ["1枠", 10, 10, 10, 970, 1000],
        ["2枠", 10, 10, 10, 970, 1000],
        ["3枠", 30, 30, 30, 910, 1000],
        ["4枠", 30, 30, 30, 910, 1000],
        ["5枠", 30, 30, 30, 910, 1000],
        ["6枠", 60, 60, 60, 820, 1000],
        ["7枠", 60, 60, 60, 820, 1000],
        ["8枠", 60, 60, 60, 820, 1000]]),
    "有利な脚質": _table([
        ["逃", 40, 40, 40, 880, 1000],
        ["先", 40, 40, 40, 880, 1000],
        ["差", 15, 15, 15, 955, 1000],
        ["追", 15, 15, 15, 955, 1000]]),
}
COURSE_INPUTS = {1: {"front_rate": 0.9, "frame": 1},
                 2: {"front_rate": 0.5, "frame": 3},
                 3: {"front_rate": 0.5, "frame": 5},
                 4: {"front_rate": 0.5, "frame": 7},
                 5: {"front_rate": 0.1, "frame": 8}}
FLAT_EXTRAS = {n: {"spd2_recent": 1.0} for n in NAMES}


def course_entry():
    """Materials whose speed side is flat (identical index and
    spd2 for every horse), so only the course terms can move a
    probability."""
    return {"netkeibaRaceId": NK_ID, "courseAnalysis": COURSE_ANALYSIS,
            "horses": {n: {"nk_best": None, "nk_avg5": 60,
                           "nk_dist": None, "nk_course": None,
                           "nk_recent": None} for n in NAMES}}


class CourseBiasTests(TestCase):
    def test_biases_from_tables(self):
        front_bias, frame_bias = course_biases(COURSE_ANALYSIS)
        # front styles 240/2000 vs back styles 90/2000
        self.assertAlmostEqual(front_bias, 0.075, places=9)
        # overall top-3 rate 870/8000 = 0.10875
        self.assertAlmostEqual(frame_bias["inner"], 0.03 - 0.10875,
                               places=9)
        self.assertAlmostEqual(frame_bias["mid"], 0.09 - 0.10875,
                               places=9)
        self.assertAlmostEqual(frame_bias["outer"], 0.18 - 0.10875,
                               places=9)

    def test_missing_tables_yield_no_bias(self):
        self.assertEqual(course_biases(None), (None, {}))
        self.assertEqual(course_biases({"コース": "金沢1500m"}),
                         (None, {}))
        front_bias, frame_bias = course_biases(
            {"有利な枠順": COURSE_ANALYSIS["有利な枠順"]})
        self.assertIsNone(front_bias)
        self.assertIn("outer", frame_bias)

    def test_front_rate_matches_validation_definition(self):
        missing = Obs(None, "test", "not_captured")

        def run(corners, field=12):
            return PastRun(
                date="2026-11-03", track=missing, distance=missing,
                surface=missing, finish=missing,
                field_size=obs(field, "test"),
                corner_positions=corners, margin_text=missing,
                time_seconds=missing, jockey=missing)

        # idx0: 2/12 <= 1/3 -> 1.0 (w=1); idx1: 9/12 -> 0.0
        # (w=0.85); idx2: no corners (consumes its index);
        # idx3: 3/9 = 1/3 -> 1.0 (w=0.85**3).
        runs = (run((2,)), run((9,)), run(()), run((3,), field=9))
        expected = (1.0 + 0.85 ** 3) / (1.0 + 0.85 + 0.85 ** 3)
        self.assertAlmostEqual(front_rate_from_runs(runs), expected,
                               places=9)
        self.assertIsNone(front_rate_from_runs((run(()),)))
        self.assertIsNone(front_rate_from_runs(()))


class CourseAdapterTests(TestCase):
    def test_course_terms_move_nar_probabilities(self):
        forecast = v9b_like_forecast()
        adjusted, info = apply_nk_materials(
            forecast, course_entry(), FLAT_EXTRAS, segment="nar",
            course_inputs=COURSE_INPUTS)
        self.assertTrue(info["applied"])
        self.assertIn("course_front", info["terms"])
        self.assertIn("course_frame", info["terms"])
        self.assertIn("course-nar", info["weights"])
        self.assertEqual(info["coverage"]["course_frame"], 5)
        by_number = {r.number: r for r in adjusted.runners}
        # Direction check against the hand-computed raw values
        # (front bias +0.075, frame biases inner -0.0788 / mid
        # -0.0188 / outer +0.0713, weights 0.10 / 0.05): the
        # outer-frame horse 4 gains on the frame term alone; the
        # front-running horse 1 gains net (its front z outweighs
        # its inner-frame penalty); the closing horse 5 loses
        # (front penalty outweighs its outer-frame gain).
        self.assertGreater(by_number[4].p_win, STRENGTHS[4])
        self.assertGreater(by_number[1].p_win, STRENGTHS[1])
        self.assertLess(by_number[5].p_win, STRENGTHS[5])
        total = sum(r.strength for r in adjusted.runners)
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_course_terms_inert_for_jra_and_by_default(self):
        entry = course_entry()
        baseline, base_info = apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS)
        for segment in ("jra", None):
            adjusted, info = apply_nk_materials(
                v9b_like_forecast(), entry, FLAT_EXTRAS,
                segment=segment, course_inputs=COURSE_INPUTS)
            self.assertEqual(
                [r.strength for r in adjusted.runners],
                [r.strength for r in baseline.runners], segment)
            self.assertNotIn("course-nar", info["weights"], segment)

    def test_no_course_tables_no_course_terms(self):
        entry = course_entry()
        entry["courseAnalysis"] = None
        adjusted, info = apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS, segment="nar",
            course_inputs=COURSE_INPUTS)
        baseline, _ = apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS)
        self.assertEqual([r.strength for r in adjusted.runners],
                         [r.strength for r in baseline.runners])
        self.assertNotIn("course_front", info.get("terms") or [])

    def test_course_adjustment_is_deterministic(self):
        first, _ = apply_nk_materials(
            v9b_like_forecast(), course_entry(), FLAT_EXTRAS,
            segment="nar", course_inputs=COURSE_INPUTS)
        second, _ = apply_nk_materials(
            v9b_like_forecast(), course_entry(), FLAT_EXTRAS,
            segment="nar", course_inputs=COURSE_INPUTS)
        self.assertEqual([r.strength for r in first.runners],
                         [r.strength for r in second.runners])


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

    def test_current_version_stamp_never_qualifies(self):
        self.assertIsNone(self._info(stored_detail(
            nk_stamp=True, nk_stamp_version=NK_MATERIALS_VERSION)))

    def test_older_version_stamp_qualifies_once_more(self):
        # A v1 (speed-only) publication predates the course
        # weights: it qualifies exactly once more, and the
        # rebuilt product — stamped at the current version —
        # does not qualify again (see the build-level test).
        info = self._info(stored_detail(
            nk_stamp=True, nk_stamp_version="nk-materials-v1"))
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "nk-materials-upgrade")

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


def fabricated_course_race() -> RaceRecord:
    """A race whose runners carry frame numbers and corner
    evidence: horse 1 is the field's only habitual front-runner
    (first-corner ratio 1/10), horses 2-5 sit mid-pack or
    behind (5/10, 10/10); frames are 1/3/5/7/8."""
    missing = Obs(None, "test", "not_captured")

    def run(corner):
        return PastRun(
            date="2026-11-03", track=missing, distance=missing,
            surface=missing, finish=missing,
            field_size=obs(10, "test"), corner_positions=(corner,),
            margin_text=missing, time_seconds=missing,
            jockey=missing)

    corners = {1: 1, 2: 5, 3: 5, 4: 5, 5: 10}
    frames = {1: 1, 2: 3, 3: 5, 4: 7, 5: 8}
    runners = []
    for number in (1, 2, 3, 4, 5):
        runners.append(RunnerRecord(
            number=number, horse_id=missing,
            name=obs(NAMES[number], "test"),
            frame_number=obs(frames[number], "test"),
            age=missing, sex=missing, jockey=missing, trainer=missing,
            carried_weight=missing, body_weight=missing,
            body_weight_change=missing,
            win_odds=obs(ODDS[number], "test"),
            scratched=False,
            past_runs=(run(corners[number]), run(corners[number]))))
    return RaceRecord(
        race_id=RACE_ID, date=DATE, circuit=obs("地方", "test"),
        track="金沢", race_number=obs(1, "test"), title=missing,
        start_time=obs(POST, "test"), distance=obs(1500, "test"),
        surface=obs("ダート", "test"), weather=missing,
        condition=missing, updated_at=missing, segment=Segment.NAR,
        source="test", runners=tuple(runners))


def _build(detail, materials=MATERIALS, race=None, **patches):
    ctx = [
        patch("scripts.arvexq_rewrite_publish.normalize_race",
              return_value=race if race is not None
              else fabricated_race()),
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

    def test_v1_stamped_race_is_reissued_once_to_current_version(self):
        new, receipt = _build(stored_detail(
            nk_stamp=True, nk_stamp_version="nk-materials-v1"))
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        stamp = marker["nkMaterials"]
        self.assertTrue(stamp["applied"])
        self.assertEqual(stamp["version"], NK_MATERIALS_VERSION)
        self.assertEqual(marker["revision"]["kind"],
                         "nk-materials-upgrade")
        self.assertIsNotNone(verified_unified(new))
        # The rebuilt detail carries the current stamp, so it
        # never qualifies again.
        self.assertIsNone(self._recheck(new))

    def test_build_applies_course_terms_for_nar(self):
        payload = {
            "version": "nk-materials-v2", "date": DATE,
            "races": {RACE_ID: {
                "netkeibaRaceId": NK_ID,
                "horses": {str(n): {"nk_best": None, "nk_avg5": 60,
                                    "nk_dist": None, "nk_course": None,
                                    "nk_recent": None}
                           for n in NAMES},
                "courseAnalysis": COURSE_ANALYSIS}}}
        with_course, _ = _build(
            fresh_detail(), materials=parse_materials_payload(payload),
            race=fabricated_course_race())
        self.assertIsNotNone(with_course)
        stamp = with_course["preparedMeta"]["rewritePublish"]["nkMaterials"]
        self.assertIn("course_front", stamp["terms"])
        self.assertIn("course_frame", stamp["terms"])
        self.assertIn("course-nar", stamp["weights"])
        self.assertEqual(stamp["coverage"]["course_frame"], 5)
        self.assertEqual(stamp["coverage"]["course_front"], 5)
        # Same build without the course tables: the field's only
        # front-runner (horse 1, net course logit +0.128 — the
        # largest in the field) must sit higher with the course
        # terms in, and a mid-frame non-front horse (2, net
        # -0.071) lower.
        payload["races"][RACE_ID]["courseAnalysis"] = None
        without_course, _ = _build(
            fresh_detail(), materials=parse_materials_payload(payload),
            race=fabricated_course_race())
        win_with = with_course["prediction"]["stages"]["probability"]["value"]["win"]
        win_without = without_course["prediction"]["stages"]["probability"]["value"]["win"]
        self.assertGreater(win_with[1], win_without[1])
        self.assertLess(win_with[2], win_without[2])
        self.assertIsNotNone(verified_unified(with_course))

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
