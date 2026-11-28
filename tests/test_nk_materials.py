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

v3 (same day): the SAME course weights reach JRA as a marked
trial (user instruction: you cannot know without actually
trying it; provenance course-weights-20261117 REPORT.md §7 —
the NAR weights improved the JRA test segment post-hoc, while
no JRA-learned weight was stable). The tests now pin that the
course terms move JRA probabilities exactly as they move NAR
ones (identical weights), that the stamp-side record carries
the trial label and the courseTrial marker, that the terms
stay inert by default / for unknown segments / without tables,
and that a v2-stamped publication qualifies for exactly one
more re-issue onto v3.

v4 (same day, its own branch, merged into v5): the AI pace
forecast's per-horse forecast positions enter as a pace term
at a trial weight of 0.10 — UNVALIDATED, because no historical
pace-forecast data exists (the diagrams are published only
around race day), so a retrospective validation is
impossible. The tests pin the builder's rank/percentile
conversion and pace coverage, the parser's pace handling, the
term's direction (high pace lifts the forecast back-runners,
slow pace lifts the front), its inertness under a middling
label / without pace material, the paceTrial stamp record,
and that a v3-stamped publication qualifies for exactly one
more re-issue onto v4.

v5 (same day): the all-materials terms join the pace term.
The per-horse blocks the materials file has carried since the
builder's v2 extension (bestTime / headToHead / pedigree) and
the newspaper marks (press) become z terms at marked trial
weights (mochitime -0.10 / h2h +0.10 / pedigree +0.10 /
press +0.10 — NOT validated; the honesty record is in the
adapter's docstring). The tests additionally pin the
shrinkage arithmetic (head-to-head toward 0.5 over 3 prior
duels; the sire-course score toward a generic field over 10
prior starts), the research MARK_POINTS scoring of the press
marks, that each term moves probabilities in its designed
direction on flat speed inputs, that the stamp-side record
carries the all-materials trial label and the materialsTrial
marker, and that v3- and v4-stamped publications qualify for
exactly one more re-issue onto v5.

v6 (same day): the families the full audit found computed but
weightless join as marked trials. The speed-derived terms
(slope / dev / fit / bias at +0.10; the dispersion family vol
/ sd / overlap at -0.10, per integrated_eval's design notes)
ride on the speed columns every entry already carries; the
combo term (+0.10) reads the race record through
combo_inputs_from_race; the judgement (nk_form_dev / nk_ai)
and odds-movement (odds_drift / odds_wp_gap) terms are armed
at +0.10 each but have NO collection data yet, so the tests
pin both their firing on synthetic values and their complete
inertness on today's real-shaped (valueless) entries. The
builder carries the new fields (nkFormDev / nkAiScore / odds)
with uniform nulls and reports their coverage plus the
derived-speed coverage in fieldCoverage. The tests pin the
directions, the stamp records (speedDerivedTrial /
comboTrial / judgementTrial / oddsTrial), the parser's
handling of the new fields, and that a v5-stamped publication
qualifies for exactly one more re-issue onto v6.

v7 (2026-11-18): the closing term joins as a marked trial.
The past-run record now carries the observed last-3F seconds
(PastRun.last3f_seconds — the career / official-CSV /
result-page ingestion writes them, and normalize / store /
api_shape carry them through), so the adapter's closing term
(+0.10, UNVALIDATED) reads each runner's own recent sequence
through closing_inputs_from_race. The tests pin the
oldest-first ordering with gaps kept as None, that the term
lifts the horse whose latest close beat its own recent norm,
its complete inertness without closing inputs, the stamp
record (closingTrial), that normalize keeps the observed
value on past runs, and that a v6-stamped publication
qualifies for exactly one more re-issue onto v7.

Growth + jumps (2026-11-21, audit B1/B5): the stamp now also
records the entryFingerprint of the entry applied, and a
current-version stamp re-qualifies when the materials file
has grown past it — on 2026-11-21 the races stamped off the
evening file (bestTime / headToHead / place-divergence all
zero) never received the morning rebuild's material. The
tests pin the growth matrix (fingerprint and legacy
coverage/terms baselines, the sub-threshold floor, the
fail-closed empty stamp), that jumps races qualify on the
v1 lane with any family at the threshold (their entries
carry no speed index), that the lane upgrade can no longer
trap them, and that a jumps build applies the adjustment
and re-issues exactly once.
"""
from __future__ import annotations

import copy
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from arvexq.prediction.unified_product import verified as verified_unified
from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.clean_forecast import CLEAN_FORECAST_VERSION
from rewrite.analysis.override_guard import GUARD_VERSION
from rewrite.analysis.nk_materials import (
    CLOSING_WEIGHT, COMBO_WEIGHT, NK_ALL_TERMS_LABEL,
    NK_ALL_TERMS_TRIAL, NK_CLOSING_TRIAL, NK_CLOSING_WEIGHTS_LABEL,
    NK_COMBO_LABEL, NK_COMBO_TRIAL, NK_JUDGEMENT_LABEL,
    NK_JUDGEMENT_TRIAL, NK_MATERIALS_VERSION, NK_ODDS_LABEL,
    NK_ODDS_TRIAL, NK_PACE_WEIGHTS_LABEL,
    NK_SPEED_DERIVED_LABEL, NK_SPEED_DERIVED_TRIAL, PACE_WEIGHT,
    SPEED_DERIVED_WEIGHTS,
    apply_nk_materials, best_time_seconds, closing_inputs_from_race,
    combo_inputs_from_race, course_biases,
    course_inputs_from_race, front_rate_from_runs, h2h_shrunk_rate,
    materials_fingerprint, pace_score, parse_materials_payload,
    press_points, sire_course_score,
    speed_coverage)
from rewrite.data.normalize import (
    Obs, PastRun, RaceRecord, RunnerRecord, normalize_runner, obs)
from rewrite.output.api_shape import MODEL_VERSION
from rewrite.safety.contracts import Segment
from scripts.arvexq_nk_materials_build import (
    build as build_materials,
    load_race_details,
)
from scripts.arvexq_rewrite_publish import (
    NAR_DECAY_V9B_ABILITY_MODEL_VERSION,
    V9B_LANE,
    _lane_upgrade_info,
    _load_nk_materials,
    _nk_materials_growth,
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
                  nk_stamp_extra=None,
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
        if nk_stamp_extra:
            marker["nkMaterials"].update(nk_stamp_extra)
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

    def test_course_terms_move_jra_probabilities_as_trial(self):
        # v3 trial: JRA receives the SAME weights as NAR, so on
        # identical inputs the movement matches the NAR test's
        # hand-computed directions exactly — what differs is the
        # record: the weights label carries the trial label with
        # its provenance (REPORT.md §7), never the NAR fit+calib
        # label, and info marks the trial explicitly.
        forecast = v9b_like_forecast()
        adjusted, info = apply_nk_materials(
            forecast, course_entry(), FLAT_EXTRAS, segment="jra",
            course_inputs=COURSE_INPUTS)
        self.assertTrue(info["applied"])
        self.assertIn("course_front", info["terms"])
        self.assertIn("course_frame", info["terms"])
        self.assertIn("course-jra-trial", info["weights"])
        self.assertIn("sec7", info["weights"])
        self.assertNotIn("course-nar-fitcalib", info["weights"])
        self.assertEqual(info["courseTrial"], "jra")
        self.assertEqual(info["coverage"]["course_frame"], 5)
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[4].p_win, STRENGTHS[4])
        self.assertGreater(by_number[1].p_win, STRENGTHS[1])
        self.assertLess(by_number[5].p_win, STRENGTHS[5])
        total = sum(r.strength for r in adjusted.runners)
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_jra_trial_probabilities_equal_nar(self):
        # Identical weights => identical numbers; only the
        # stamp-side record differs. "jra_flat" — the spelling
        # race.segment.value carries in the publish lane — is
        # the same trial segment.
        entry = course_entry()
        nar, nar_info = apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS, segment="nar",
            course_inputs=COURSE_INPUTS)
        for segment in ("jra", "jra_flat"):
            adjusted, info = apply_nk_materials(
                v9b_like_forecast(), entry, FLAT_EXTRAS,
                segment=segment, course_inputs=COURSE_INPUTS)
            self.assertEqual(
                [r.strength for r in adjusted.runners],
                [r.strength for r in nar.runners], segment)
            self.assertEqual(info["courseTrial"], "jra", segment)
        self.assertNotIn("courseTrial", nar_info)

    def test_course_terms_inert_by_default_and_unknown_segment(self):
        entry = course_entry()
        baseline, base_info = apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS)
        for segment in (None, "debut"):
            adjusted, info = apply_nk_materials(
                v9b_like_forecast(), entry, FLAT_EXTRAS,
                segment=segment, course_inputs=COURSE_INPUTS)
            self.assertEqual(
                [r.strength for r in adjusted.runners],
                [r.strength for r in baseline.runners], segment)
            self.assertNotIn("course-nar", info["weights"], segment)
            self.assertNotIn("course-jra-trial", info["weights"],
                             segment)
            self.assertNotIn("courseTrial", info, segment)

    def test_no_course_tables_no_course_terms(self):
        entry = course_entry()
        entry["courseAnalysis"] = None
        baseline, _ = apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS)
        for segment in ("nar", "jra"):
            adjusted, info = apply_nk_materials(
                v9b_like_forecast(), entry, FLAT_EXTRAS,
                segment=segment, course_inputs=COURSE_INPUTS)
            self.assertEqual([r.strength for r in adjusted.runners],
                             [r.strength for r in baseline.runners],
                             segment)
            self.assertNotIn("course_front", info.get("terms") or [],
                             segment)
            self.assertNotIn("courseTrial", info, segment)

    def test_course_adjustment_is_deterministic(self):
        first, _ = apply_nk_materials(
            v9b_like_forecast(), course_entry(), FLAT_EXTRAS,
            segment="nar", course_inputs=COURSE_INPUTS)
        second, _ = apply_nk_materials(
            v9b_like_forecast(), course_entry(), FLAT_EXTRAS,
            segment="nar", course_inputs=COURSE_INPUTS)
        self.assertEqual([r.strength for r in first.runners],
                         [r.strength for r in second.runners])


class AllTermsHelperTests(TestCase):
    def test_best_time_seconds(self):
        self.assertEqual(best_time_seconds({"seconds": 90.2}), 90.2)
        self.assertIsNone(best_time_seconds({"seconds": "90.2"}))
        self.assertIsNone(best_time_seconds({}))
        self.assertIsNone(best_time_seconds(None))

    def test_h2h_shrinkage_toward_neutral(self):
        # (ahead + 3*0.5) / (duels + 3): one lucky duel reads
        # 0.625, not 1.0; a long record approaches its raw rate.
        self.assertAlmostEqual(
            h2h_shrunk_rate({"duels": 1, "ahead": 1}), 0.625)
        self.assertAlmostEqual(
            h2h_shrunk_rate({"duels": 10, "ahead": 9}), 10.5 / 13)
        self.assertAlmostEqual(
            h2h_shrunk_rate({"duels": 10, "ahead": 1}), 2.5 / 13)
        self.assertIsNone(h2h_shrunk_rate({"duels": 0, "ahead": 0}))
        self.assertIsNone(h2h_shrunk_rate({"meetings": 2}))
        self.assertIsNone(h2h_shrunk_rate(None))

    def test_sire_course_score_shrinkage(self):
        # starts 10 / wins 2 / top3 4: shrunk win (2+1)/20 =
        # 0.15, shrunk top3 (4+3)/20 = 0.35, score 0.25.
        ped = {"sireCourse": {"starts": 10, "wins": 2, "top3": 4,
                              "winRate": 0.2}}
        self.assertAlmostEqual(sire_course_score(ped), 0.25)
        self.assertIsNone(sire_course_score(
            {"sireCourse": {"starts": 0, "wins": 0, "top3": 0}}))
        self.assertIsNone(sire_course_score({"sireCourse": None}))
        self.assertIsNone(sire_course_score({}))
        self.assertIsNone(sire_course_score(None))

    def test_press_points_research_scoring(self):
        # MARK_POINTS from the research tree: ◎5 ○4 ▲3 △2 ☆1.
        self.assertEqual(press_points("◎"), 5.0)
        self.assertEqual(press_points({"marks": {"記者": "◎"}}), 5.0)
        self.assertEqual(
            press_points({"marks": {"a": "◎", "b": "△"}}), 3.5)
        self.assertEqual(press_points({"mark": "○"}), 4.0)
        self.assertEqual(press_points({"marks": {"a": "消"}}), 0.0)
        self.assertIsNone(press_points({"marks": {"a": "?"}}))
        self.assertIsNone(press_points({"marks": {}}))
        self.assertIsNone(press_points(None))

    def test_parse_carries_v2_blocks_and_drops_malformed(self):
        payload = {"races": {RACE_ID: {"horses": {
            "1": {"nk_avg5": 50,
                  "bestTime": {"seconds": 90.0, "tier": 1},
                  "headToHead": {"duels": 2, "ahead": 1},
                  "pedigree": {"sire": "種牡馬X"},
                  "press": {"marks": {"記者": "◎"}}},
            "2": {"nk_avg5": 50, "bestTime": "90.0",
                  "headToHead": [1], "pedigree": None,
                  "press": [1, 2]}}}}}
        parsed = parse_materials_payload(payload)
        h1 = parsed[RACE_ID]["horses"][1]
        self.assertEqual(h1["bestTime"], {"seconds": 90.0, "tier": 1})
        self.assertEqual(h1["headToHead"], {"duels": 2, "ahead": 1})
        self.assertEqual(h1["pedigree"], {"sire": "種牡馬X"})
        self.assertEqual(h1["press"], {"marks": {"記者": "◎"}})
        h2 = parsed[RACE_ID]["horses"][2]
        for field in ("bestTime", "headToHead", "pedigree", "press"):
            self.assertIsNone(h2[field], field)


def flat_entry(**blocks):
    """Materials whose speed side is flat (identical index for
    every horse, no spd2 contrast), so only the v5 blocks given
    per horse number can move a probability. Each block maps
    horse number -> the raw materials block."""
    horses = {}
    for n in NAMES:
        horse = {"nk_best": None, "nk_avg5": 60, "nk_dist": None,
                 "nk_course": None, "nk_recent": None,
                 "bestTime": None, "headToHead": None,
                 "pedigree": None, "press": None}
        for field, per_horse in blocks.items():
            if n in per_horse:
                horse[field] = per_horse[n]
        horses[n] = horse
    return {"netkeibaRaceId": NK_ID, "courseAnalysis": None,
            "horses": horses}


class AllTermsAdapterTests(TestCase):
    def _apply(self, entry):
        return apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS)

    def test_mochitime_term_rewards_the_fastest_time(self):
        entry = flat_entry(bestTime={
            n: {"seconds": s, "tier": 1}
            for n, s in ((1, 88.0), (2, 92.0), (3, 92.0),
                         (4, 92.0), (5, 96.0))})
        adjusted, info = self._apply(entry)
        self.assertTrue(info["applied"])
        self.assertIn("mochitime", info["terms"])
        self.assertEqual(info["coverage"]["mochitime"], 5)
        by_number = {r.number: r for r in adjusted.runners}
        # Negative weight on raw seconds: fastest gains,
        # slowest loses.
        self.assertGreater(by_number[1].p_win, STRENGTHS[1])
        self.assertLess(by_number[5].p_win, STRENGTHS[5])
        total = sum(r.strength for r in adjusted.runners)
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_h2h_term_rewards_the_dominant_record(self):
        entry = flat_entry(headToHead={
            n: {"duels": 10, "ahead": a}
            for n, a in ((1, 5), (2, 9), (3, 5), (4, 1), (5, 5))})
        adjusted, info = self._apply(entry)
        self.assertTrue(info["applied"])
        self.assertIn("h2h", info["terms"])
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[2].p_win, STRENGTHS[2])
        self.assertLess(by_number[4].p_win, STRENGTHS[4])

    def test_pedigree_term_rewards_the_sire_course_record(self):
        def ped(wins, top3):
            return {"sire": "種牡馬", "sireCourse": {
                "starts": 90, "wins": wins, "top3": top3,
                "winRate": wins / 90}}
        entry = flat_entry(pedigree={
            1: ped(9, 27), 2: ped(9, 27), 3: ped(18, 45),
            4: ped(9, 27), 5: ped(0, 9)})
        adjusted, info = self._apply(entry)
        self.assertTrue(info["applied"])
        self.assertIn("pedigree", info["terms"])
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[3].p_win, STRENGTHS[3])
        self.assertLess(by_number[5].p_win, STRENGTHS[5])

    def test_press_term_rewards_the_top_mark(self):
        entry = flat_entry(press={
            1: {"marks": {"記者": "○"}}, 2: {"marks": {"記者": "◎"}},
            3: {"marks": {"記者": "○"}}, 4: {"marks": {"記者": "☆"}}})
        adjusted, info = self._apply(entry)
        self.assertTrue(info["applied"])
        self.assertIn("press", info["terms"])
        self.assertEqual(info["coverage"]["press"], 4)
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[2].p_win, STRENGTHS[2])
        self.assertLess(by_number[4].p_win, STRENGTHS[4])

    def test_all_terms_together_carry_the_trial_record(self):
        entry = flat_entry(
            bestTime={n: {"seconds": 88.0 + n, "tier": 1}
                      for n in NAMES},
            headToHead={n: {"duels": 10, "ahead": n} for n in NAMES},
            pedigree={n: {"sireCourse": {
                "starts": 90, "wins": 3 * n, "top3": 9 * n,
                "winRate": 0.1}} for n in NAMES},
            press={n: {"marks": {"記者": "○"}} for n in NAMES})
        adjusted, info = self._apply(entry)
        self.assertTrue(info["applied"])
        for term in ("mochitime", "h2h", "pedigree"):
            self.assertIn(term, info["terms"])
        # All five press entries are identical, so the press
        # z-scores are all zero: the term exists in coverage
        # but cannot rank the field — the trial record is
        # carried by the terms that did contribute.
        self.assertIn(NK_ALL_TERMS_LABEL, info["weights"])
        self.assertIn("unvalidated", info["weights"])
        self.assertEqual(info["materialsTrial"], NK_ALL_TERMS_TRIAL)
        for field in ("mochitime", "h2h", "pedigree", "press"):
            self.assertEqual(info["coverage"][field], 5, field)

    def test_too_few_valued_horses_returns_same_object(self):
        # Only two horses carry a best time and nothing else
        # can contribute (no speed index either): the z-scores
        # need three valued horses, so nothing may move.
        forecast = v9b_like_forecast()
        entry = {"netkeibaRaceId": NK_ID, "courseAnalysis": None,
                 "horses": {
                     1: {"bestTime": {"seconds": 88.0, "tier": 1}},
                     2: {"bestTime": {"seconds": 96.0, "tier": 1}}}}
        adjusted, info = apply_nk_materials(
            forecast, entry, FLAT_EXTRAS)
        self.assertIs(adjusted, forecast)
        self.assertFalse(info["applied"])

    def test_all_terms_adjustment_is_deterministic(self):
        entry = flat_entry(
            bestTime={n: {"seconds": 88.0 + n, "tier": 1}
                      for n in NAMES},
            headToHead={n: {"duels": 10, "ahead": n} for n in NAMES})
        first, _ = self._apply(entry)
        second, _ = self._apply(entry)
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
        # The current stamp is the clean-forecast-v2 foundation
        # stamp (2026-11-28 rebuild): a race already standing on
        # it, with no materials growth recorded against it,
        # never qualifies again.
        self.assertIsNone(self._info(stored_detail(
            nk_stamp=True, nk_stamp_version=CLEAN_FORECAST_VERSION)))

    def test_v19_stamp_qualifies_once_more_for_clean_forecast(self):
        # The last nk-materials stamp (v19) predates the
        # clean-forecast-v2 foundation: it qualifies exactly
        # once more, and the rebuilt product — stamped
        # clean-forecast-v2 — does not qualify again (see the
        # build-level tests).
        info = self._info(stored_detail(
            nk_stamp=True, nk_stamp_version=NK_MATERIALS_VERSION))
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "nk-materials-upgrade")

    def test_older_version_stamp_qualifies_once_more(self):
        # A v1 (speed-only) publication predates the course
        # weights: it qualifies exactly once more, and the
        # rebuilt product — stamped at the current version —
        # does not qualify again (see the build-level test).
        info = self._info(stored_detail(
            nk_stamp=True, nk_stamp_version="nk-materials-v1"))
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "nk-materials-upgrade")

    def test_v2_stamp_qualifies_once_more_for_the_jra_trial(self):
        # A v2 publication (course weights for NAR only)
        # predates the v3 definition (the JRA course trial): it
        # qualifies exactly once more, and the rebuilt product —
        # stamped v3 — does not qualify again (see the
        # build-level test).
        info = self._info(stored_detail(
            nk_stamp=True, nk_stamp_version="nk-materials-v2"))
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "nk-materials-upgrade")

    def test_v3_and_v4_stamps_qualify_once_more_for_v5(self):
        # v3 (course trial) and v4 (the pace term, merged from
        # its own branch) both predate the v5 definition (the
        # all-materials terms): each qualifies exactly once
        # more, and the rebuilt product — stamped v5 — does not
        # qualify again (see the build-level test). This covers
        # the pace branch's v3-qualifies-once-more case as well.
        for version in ("nk-materials-v3", "nk-materials-v4"):
            info = self._info(stored_detail(
                nk_stamp=True, nk_stamp_version=version))
            self.assertIsNotNone(info, version)
            self.assertEqual(info["reason"], "nk-materials-upgrade")

    def test_v5_stamp_qualifies_once_more_for_v6(self):
        # A v5 publication (pace + all-materials terms) predates
        # the v6 definition (the speed-derived / combo /
        # judgement / odds families): it qualifies exactly once
        # more, and the rebuilt product — stamped v6 — does not
        # qualify again (see the build-level tests, which assert
        # the rebuilt stamp carries NK_MATERIALS_VERSION).
        info = self._info(stored_detail(
            nk_stamp=True, nk_stamp_version="nk-materials-v5"))
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "nk-materials-upgrade")

    def test_v6_stamp_qualifies_once_more_for_v7(self):
        # A v6 publication (speed-derived / combo / judgement /
        # odds families) predates the v7 definition (the closing
        # term): it qualifies exactly once more, and the rebuilt
        # product — stamped v7 — does not qualify again (see the
        # build-level tests, which assert the rebuilt stamp
        # carries NK_MATERIALS_VERSION).
        info = self._info(stored_detail(
            nk_stamp=True, nk_stamp_version="nk-materials-v6"))
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


# ------------------------------------- growth + jumps (2026-11-21)

GROWN_PAYLOAD = {
    "version": "nk-materials-v5", "date": DATE,
    "races": {RACE_ID: {
        "netkeibaRaceId": NK_ID,
        "horses": {str(n): {
            "nk_best": NK_AVG5[n] + 5, "nk_avg5": NK_AVG5[n],
            "nk_dist": None, "nk_course": None,
            "nk_recent": [NK_AVG5[n]] * 3,
            "bestTime": {"seconds": 88.0 + n, "tier": 1},
            "headToHead": {"duels": 10, "ahead": n}}
            for n in NAMES},
        "courseAnalysis": {"コース": "金沢1500m"}}}}
GROWN = parse_materials_payload(GROWN_PAYLOAD)

JUMPS_ID = "jra-2026-11-21-福島-04"
JUMPS_DATE = "2026-11-21"
JUMPS_POST = "10:45"
JUMPS_NOW = datetime(2026, 11, 21, 8, 0, tzinfo=JST)

JUMPS_PAYLOAD = {
    "version": "nk-materials-v12", "date": JUMPS_DATE,
    "races": {JUMPS_ID: {
        "netkeibaRaceId": "202603010404",
        "horses": {str(n): {
            "nk_best": None, "nk_avg5": None, "nk_dist": None,
            "nk_course": None, "nk_recent": None,
            "bestTime": {"seconds": 190.0 + n, "tier": 1},
            "press": {"marks": {"記者": "○"}}}
            for n in NAMES},
        "courseAnalysis": {"コース": "福島2750m"}}}}
JUMPS_MATERIALS = parse_materials_payload(JUMPS_PAYLOAD)


def jumps_stored_detail(*, nk_stamp=False,
                        nk_stamp_version=CLEAN_FORECAST_VERSION) -> dict:
    detail = stored_detail(lane="v1-prior", date=JUMPS_DATE,
                           post=JUMPS_POST, nk_stamp=nk_stamp,
                           nk_stamp_version=nk_stamp_version)
    detail.update({"id": JUMPS_ID, "circuit": "中央", "venue": "福島",
                   "track": "福島", "surface": "障害"})
    return detail


class GrowthQualificationTests(TestCase):
    """B1 (2026-11-21): a current-version stamp used to be
    final even when the materials file grew after the stamp
    was written — on 2026-11-21 the morning rebuild lit
    bestTime (560 horses) / headToHead / the place-divergence
    cells the evening file had shipped as zero, and every
    race stamped before it kept the thin adjustment all day.
    The stamp now records what it stood on (entryFingerprint;
    older stamps fall back to their coverage/terms) and
    growth re-qualifies the race exactly once per materials
    state."""

    def _info(self, detail, materials, now=NOW):
        with patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                   return_value=materials):
            return _nk_materials_upgrade_info(detail, now)

    def test_grown_materials_requalify_a_current_version_stamp(self):
        detail = stored_detail(
            nk_stamp=True, nk_stamp_version=CLEAN_FORECAST_VERSION,
            nk_stamp_extra={"terms": ["speed"],
                            "coverage": {"speed": 5, "mochitime": 0,
                                         "h2h": 0}})
        self.assertIsNotNone(self._info(detail, GROWN))

    def test_unchanged_materials_do_not_requalify(self):
        # The stamp's coverage records what the adjustment stood
        # on, in the current adapter's own coverage keys — since
        # nk-materials-v14 that includes nk_best (the fixture's
        # five horses all carry nk_best / nk_recent). A stamp
        # recorded by the current adapter over unchanged
        # materials therefore shows no growth.
        detail = stored_detail(
            nk_stamp=True, nk_stamp_version=CLEAN_FORECAST_VERSION,
            nk_stamp_extra={"terms": ["speed"],
                            "coverage": {"speed": 5, "mochitime": 0,
                                         "h2h": 0, "nk_best": 5}})
        self.assertIsNone(self._info(detail, MATERIALS))

    def test_fingerprint_stamp_requalifies_only_on_growth(self):
        detail = stored_detail(
            nk_stamp=True, nk_stamp_version=CLEAN_FORECAST_VERSION,
            nk_stamp_extra={"entryFingerprint":
                            materials_fingerprint(MATERIALS[RACE_ID])})
        self.assertIsNone(self._info(detail, MATERIALS))
        self.assertIsNotNone(self._info(detail, GROWN))

    def test_subthreshold_growth_never_requalifies(self):
        thin_growth = parse_materials_payload({"races": {RACE_ID: {
            "horses": {str(n): {"nk_avg5": NK_AVG5[n],
                                "bestTime": {"seconds": 88.0,
                                             "tier": 1}}
                       for n in (1, 2)}}}})
        detail = stored_detail(
            nk_stamp=True, nk_stamp_version=CLEAN_FORECAST_VERSION,
            nk_stamp_extra={"terms": ["speed"],
                            "coverage": {"speed": 5, "mochitime": 0}})
        self.assertIsNone(self._info(detail, thin_growth))

    def test_growth_helper_reads_only_what_the_stamp_recorded(self):
        entry = MATERIALS[RACE_ID]
        self.assertFalse(_nk_materials_growth(
            {"entryFingerprint": materials_fingerprint(entry)}, entry))
        self.assertTrue(_nk_materials_growth(
            {"entryFingerprint": materials_fingerprint(entry)},
            GROWN[RACE_ID]))
        # A stamp with neither fingerprint nor coverage/terms
        # proves nothing: fail-closed, as before.
        self.assertFalse(_nk_materials_growth({"applied": True}, entry))


class JumpsQualificationTests(TestCase):
    """B5 (2026-11-21): jumps races stand on the v1 lane (no
    fitted v8 candidate exists for the segment), so they never
    qualified for the materials upgrade at all — the day's two
    Fukushima jump races were published with their collected
    materials (full bestTime / press coverage, no speed index)
    never applied."""

    def _info(self, detail, materials=JUMPS_MATERIALS, now=JUMPS_NOW):
        with patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                   return_value=materials):
            return _nk_materials_upgrade_info(detail, now)

    def test_unstamped_jumps_race_qualifies_without_speed(self):
        info = self._info(jumps_stored_detail())
        self.assertIsNotNone(info)
        self.assertEqual(info["previousAbilityLane"], "v1-prior")

    def test_jumps_thin_materials_never_qualify(self):
        thin = parse_materials_payload({"races": {JUMPS_ID: {
            "horses": {str(n): {"bestTime": {"seconds": 190.0,
                                             "tier": 1}}
                       for n in (1, 2)}}}})
        self.assertIsNone(self._info(jumps_stored_detail(), thin))

    def test_jumps_post_guard(self):
        self.assertIsNone(self._info(
            jumps_stored_detail(),
            now=datetime(2026, 11, 21, 10, 46, tzinfo=JST)))

    def test_stamped_jumps_race_requalifies_on_growth_only(self):
        detail = jumps_stored_detail(nk_stamp=True)
        detail["preparedMeta"]["rewritePublish"]["nkMaterials"].update(
            {"terms": ["mochitime", "press"],
             "coverage": {"mochitime": 5, "press": 5}})
        self.assertIsNone(self._info(detail))
        grown = parse_materials_payload({"races": {JUMPS_ID: {
            "netkeibaRaceId": "202603010404",
            "horses": {str(n): {
                "bestTime": {"seconds": 190.0 + n, "tier": 1},
                "press": {"marks": {"記者": "○"}},
                "headToHead": {"duels": 8, "ahead": n}}
                for n in NAMES}}}})
        self.assertIsNotNone(self._info(detail, grown))

    def test_lane_upgrade_never_traps_a_jumps_race(self):
        # The extras export DOES carry the jump races; before
        # the segment guard, _lane_upgrade_info qualified them
        # for a lane upgrade that can never land (no v8 weights
        # for the segment), trapping them in a permanent
        # keep-frozen loop ahead of every other exception.
        extras = {JUMPS_ID: {"segment": "jumps", "extras": {
            str(n): {"elo": 1500.0, "spd2_recent": 1.0}
            for n in NAMES}}}
        with patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                   return_value=extras):
            self.assertIsNone(_lane_upgrade_info(jumps_stored_detail()))


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


# Forecast odds the clean-forecast-v2 foundation stands on:
# they invert the market's order (horse 5 shortest, horse 1
# longest), so a build on the foundation is visibly a
# different vector from both the lane's and the market's.
NK_FORECAST_ODDS = {1: 15.0, 2: 9.0, 3: 6.0, 4: 4.0, 5: 3.0}


def v2_materials(horse_extra=None):
    """Parsed materials in the shape the clean-forecast-v2
    foundation consumes: per-horse forecast odds (the base)
    plus the nk_best index the nk_best lean reads.
    horse_extra maps a horse number to extra parsed-shape
    fields (pace, coursePersons, press, ...) merged in."""
    horses = {}
    for n in NAMES:
        horse = {"nk_best": NK_AVG5[n] + 5, "nk_avg5": NK_AVG5[n],
                 "nk_dist": None, "nk_course": None,
                 "nk_recent": [NK_AVG5[n]] * 3,
                 "odds": {"forecastWin": NK_FORECAST_ODDS[n]}}
        horse.update((horse_extra or {}).get(n, {}))
        horses[str(n)] = horse
    return parse_materials_payload({
        "version": "nk-materials-v19", "date": DATE,
        "races": {RACE_ID: {"netkeibaRaceId": NK_ID,
                            "horses": horses,
                            "courseAnalysis": {"コース": "金沢1500m"}}}})


class BuildTests(TestCase):
    def test_first_publication_carries_the_stamp(self):
        new, receipt = _build(fresh_detail(), materials=v2_materials())
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        stamp = marker["nkMaterials"]
        self.assertTrue(stamp["applied"])
        # The clean-forecast-v2 foundation stamp (2026-11-28
        # rebuild): the base it stood on, the leans that fired
        # with their weights, and the field coverage of each —
        # the retired terms/weights record is gone.
        self.assertEqual(stamp["version"], CLEAN_FORECAST_VERSION)
        self.assertEqual(stamp["path"], "clean-forecast")
        self.assertEqual(stamp["base"], "nk")
        self.assertEqual(stamp["netkeibaRaceId"], NK_ID)
        self.assertEqual(stamp["coverage"]["nkForecast"], 5)
        self.assertEqual(stamp["coverage"]["nk_best"], 5)
        self.assertEqual(stamp["leans"]["nk_best"]["weight"], 0.20)
        self.assertTrue(stamp["leans"]["nk_best"]["fired"])
        self.assertTrue(stamp["blendApplied"])
        self.assertNotIn("terms", stamp)
        self.assertNotIn("revision", marker)
        self.assertIsNotNone(verified_unified(new))

    def test_first_publication_without_materials_is_unstamped(self):
        new, receipt = _build(fresh_detail(), materials={})
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertNotIn("nkMaterials", marker)

    def test_materials_move_the_published_probabilities(self):
        with_mat, _ = _build(fresh_detail(), materials=v2_materials())
        without_mat, _ = _build(fresh_detail(), materials={})
        win_with = with_mat["prediction"]["stages"]["probability"]["value"]["win"]
        win_without = without_mat["prediction"]["stages"]["probability"]["value"]["win"]
        # The foundation stands on netkeiba's forecast odds,
        # which invert the market in this fixture: horse 5 (the
        # forecast's shortest price, the market's longest) is
        # lifted and horse 1 (the market favourite the forecast
        # dismisses) is cut, against the no-materials build.
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

    def test_first_publication_stamps_the_entry_fingerprint(self):
        new, receipt = _build(fresh_detail())
        self.assertIsNotNone(new, receipt)
        stamp = new["preparedMeta"]["rewritePublish"]["nkMaterials"]
        self.assertEqual(stamp["entryFingerprint"]["speed"], 5)
        self.assertEqual(stamp["entryFingerprint"]["mochitime"], 0)
        self.assertEqual(stamp["entryFingerprint"]["course_analysis"], 1)

    def test_grown_materials_reissue_exactly_once(self):
        first, receipt = _build(fresh_detail())
        self.assertIsNotNone(first, receipt)
        new, receipt = _build(first, materials=GROWN)
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        revision = marker["revision"]
        self.assertEqual(revision["kind"], "nk-materials-upgrade")
        self.assertEqual(revision["previousAbilityLane"], V9B_LANE)
        self.assertEqual(revision["abilityLane"], V9B_LANE)
        self.assertEqual(
            marker["nkMaterials"]["entryFingerprint"]["mochitime"], 5)
        self.assertIsNotNone(verified_unified(new))
        # The re-stamped fingerprint closes the qualification:
        # the same materials never qualify the race again.
        with patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                   return_value=GROWN):
            self.assertIsNone(_nk_materials_upgrade_info(new, NOW))

    def test_v1_stamped_race_is_reissued_once_to_current_version(self):
        new, receipt = _build(stored_detail(
            nk_stamp=True, nk_stamp_version="nk-materials-v1"))
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        stamp = marker["nkMaterials"]
        self.assertTrue(stamp["applied"])
        self.assertEqual(stamp["version"], CLEAN_FORECAST_VERSION)
        self.assertEqual(marker["revision"]["kind"],
                         "nk-materials-upgrade")
        self.assertIsNotNone(verified_unified(new))
        # The rebuilt detail carries the current stamp, so it
        # never qualifies again.
        self.assertIsNone(self._recheck(new))

    def test_v2_stamped_race_is_reissued_once_to_current(self):
        new, receipt = _build(stored_detail(
            nk_stamp=True, nk_stamp_version="nk-materials-v2"))
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        stamp = marker["nkMaterials"]
        self.assertTrue(stamp["applied"])
        self.assertEqual(stamp["version"], CLEAN_FORECAST_VERSION)
        self.assertEqual(marker["revision"]["kind"],
                         "nk-materials-upgrade")
        self.assertIsNotNone(verified_unified(new))
        # The rebuilt detail carries the current stamp, so it
        # never qualifies again.
        self.assertIsNone(self._recheck(new))

    def test_v3_stamped_race_is_reissued_once_to_current(self):
        new, receipt = _build(stored_detail(
            nk_stamp=True, nk_stamp_version="nk-materials-v3"))
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        stamp = marker["nkMaterials"]
        self.assertTrue(stamp["applied"])
        self.assertEqual(stamp["version"], CLEAN_FORECAST_VERSION)
        self.assertEqual(marker["revision"]["kind"],
                         "nk-materials-upgrade")
        self.assertIsNotNone(verified_unified(new))
        self.assertIsNone(self._recheck(new))

    def test_build_stamp_records_leans_not_retired_trials(self):
        # The clean-forecast-v2 stamp (2026-11-28 rebuild)
        # shows exactly which leans fired, at what weight,
        # with what coverage. The retired trial families
        # (bestTime / headToHead / pedigree terms) no longer
        # stand in the probability path: they are recorded
        # only in the entryFingerprint as material the
        # publication stood on, never as a fired term or a
        # trial marker.
        extra = {n: {
            "bestTime": {"seconds": 88.0 + n, "tier": 1},
            "headToHead": {"duels": 10, "ahead": n},
            "pedigree": {"sire": "種牡馬", "sireCourse": {
                "starts": 90, "wins": 3 * n, "top3": 9 * n,
                "winRate": 0.1}},
            "press": {"marks": {"CP予想": cp}}}
            for n, cp in ((1, "○"), (2, "▲"), (3, "△"),
                          (4, "☆"), (5, "◎"))}
        new, receipt = _build(
            fresh_detail(), materials=v2_materials(extra))
        self.assertIsNotNone(new, receipt)
        stamp = new["preparedMeta"]["rewritePublish"]["nkMaterials"]
        self.assertTrue(stamp["applied"])
        self.assertEqual(stamp["version"], CLEAN_FORECAST_VERSION)
        self.assertNotIn("terms", stamp)
        self.assertNotIn("materialsTrial", stamp)
        self.assertNotIn("weights", stamp)
        self.assertTrue(stamp["leans"]["press_cp"]["fired"])
        self.assertEqual(stamp["leans"]["press_cp"]["weight"], 0.10)
        self.assertEqual(stamp["coverage"]["press_cp"], 5)
        self.assertEqual(stamp["entryFingerprint"]["mochitime"], 5)
        self.assertEqual(stamp["entryFingerprint"]["h2h"], 5)
        self.assertEqual(stamp["entryFingerprint"]["pedigree"], 5)
        self.assertIsNotNone(verified_unified(new))

    def test_build_applies_course_jockey_lean_for_nar(self):
        # The course family's place in the clean-forecast-v2
        # path is the course_jockey lean: each horse's
        # jockey's win rate at today's course, read from the
        # entry's coursePersons block. The retired
        # course_front / course_frame logit terms no longer
        # stand in the path and leave no record in the stamp.
        rates = {1: 0.30, 2: 0.05, 3: 0.10, 4: 0.15, 5: 0.20}
        extra = {n: {"coursePersons": {
            "jockey": {"winRate": rates[n]},
            "trainer": {"winRate": 0.10}}} for n in NAMES}
        with_persons, _ = _build(
            fresh_detail(), materials=v2_materials(extra),
            race=fabricated_course_race())
        self.assertIsNotNone(with_persons)
        stamp = with_persons["preparedMeta"]["rewritePublish"]["nkMaterials"]
        self.assertEqual(stamp["coverage"]["course_jockey"], 5)
        self.assertEqual(stamp["leans"]["course_jockey"]["weight"],
                         0.20)
        self.assertTrue(stamp["leans"]["course_jockey"]["fired"])
        self.assertNotIn("terms", stamp)
        # Direction: horse 1's rider owns the course's best
        # win rate and horse 2's the worst, so 1 sits higher
        # and 2 lower than the same build without the persons
        # block.
        without_persons, _ = _build(
            fresh_detail(), materials=v2_materials(),
            race=fabricated_course_race())
        win_with = with_persons["prediction"]["stages"]["probability"]["value"]["win"]
        win_without = without_persons["prediction"]["stages"]["probability"]["value"]["win"]
        self.assertGreater(win_with[1], win_without[1])
        self.assertLess(win_with[2], win_without[2])
        self.assertIsNotNone(verified_unified(with_persons))

    def test_frozen_race_without_materials_stays_frozen(self):
        detail = stored_detail()
        # The override-guard one-time adoption is a separate re-issue
        # path that does not depend on materials; stamp it as already
        # applied so this test isolates the nk-materials path.
        detail["preparedMeta"]["rewritePublish"]["overrideGuard"] = {
            "version": GUARD_VERSION, "applied": True}
        new, reason = _build(detail, materials={})
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


def _v2_run(day, race_no, distance, finish, seconds, title="C1",
            track="金沢", surface="ダート"):
    return {"date": day, "track": track, "raceNumber": race_no,
            "distance": distance, "surface": surface, "condition": "良",
            "finish": finish, "timeSeconds": seconds, "title": title,
            "raceId": f"nar-{day}-{track}-{race_no:02d}"}


def _v2_inputs():
    """One race: #1 and #2 met on 2026-11-03 (#2 in front); #1 and
    #5 share a key whose titles disagree (dropped); #3 has only an
    off-track timed run; #4 is a debutant."""
    targets = {"targets": [{"netkeiba_race_id": NK_ID,
                            "arvexq_race_id": RACE_ID}]}
    speed = {"races": {NK_ID: {"horses": {
        str(n): {"nk_best": 60, "nk_avg5": 55, "nk_dist": None,
                 "nk_course": None, "nk_recent": [55, 54, 53]}
        for n in NAMES}}}}
    course = {NK_ID: {
        "arvexq_race_id": RACE_ID, "コース": "金沢1500m",
        "得意な種牡馬": {
            "見出し": ["項目", "1着", "2着", "3着", "4着以下",
                        "出走回数", "勝率"],
            "行": [["種牡馬X", 2, 1, 1, 6, 10, "20%"]]}}}
    detail = {"id": RACE_ID, "track": "金沢", "surface": "ダート",
              "distance": 1500, "horses": [
                  {"horseNumber": 1, "name": NAMES[1], "allPastRuns": [
                      _v2_run("2026-11-03", 3, 1500, 2, 92.0),
                      _v2_run("2026-10-20", 5, 1400, 1, 90.0, title="A"),
                      _v2_run("2026-10-06", 2, 1500, 4, 93.5)]},
                  {"horseNumber": 2, "name": NAMES[2], "allPastRuns": [
                      _v2_run("2026-11-03", 3, 1500, 1, 91.8)]},
                  {"horseNumber": 3, "name": NAMES[3], "allPastRuns": [
                      _v2_run("2026-11-01", 4, 1200, 3, 75.0,
                              track="船橋")]},
                  {"horseNumber": 4, "name": NAMES[4], "allPastRuns": []},
                  {"horseNumber": 5, "name": NAMES[5], "allPastRuns": [
                      _v2_run("2026-10-20", 5, 1400, 2, 91.0, title="B")]},
              ]}
    profiles = {"horses": {
        "2024000001": {"name": NAMES[1], "sire": "種牡馬X", "dam": "母1",
                       "damSire": "母父1",
                       "siblings": [{"name": "兄", "wins": 3},
                                    {"name": "弟", "wins": 0}]},
        "2024000002": {"name": NAMES[2], "sire": "種牡馬Y", "dam": "母2",
                       "damSire": "母父2", "siblings": []}}}
    newspaper = {"races": {NK_ID: {"horses": {
        "1": {"marks": {"記者": "◎"}, "comment": "短評"}}}}}
    return targets, speed, course, {RACE_ID: detail}, profiles, newspaper


class BuilderV2Tests(TestCase):
    def _build(self, **overrides):
        targets, speed, course, details, profiles, newspaper = \
            _v2_inputs()
        kwargs = {"race_details": details, "horse_profiles": profiles,
                  "newspaper": newspaper}
        kwargs.update(overrides)
        payload = build_materials(DATE, speed, course, targets, **kwargs)
        return payload["races"][RACE_ID]["horses"]

    def test_version_and_v1_fields_unchanged(self):
        targets, speed, course, details, profiles, newspaper = \
            _v2_inputs()
        payload = build_materials(DATE, speed, course, targets,
                                  race_details=details,
                                  horse_profiles=profiles,
                                  newspaper=newspaper)
        self.assertEqual(payload["version"], "nk-materials-v14")
        entry = payload["races"][RACE_ID]
        self.assertEqual(entry["netkeibaRaceId"], NK_ID)
        self.assertEqual(entry["courseAnalysis"]["コース"], "金沢1500m")
        self.assertNotIn("arvexq_race_id", entry["courseAnalysis"])
        horse = entry["horses"]["1"]
        self.assertEqual(horse["nk_avg5"], 55)
        self.assertEqual(horse["nk_recent"], [55, 54, 53])
        self.assertEqual(payload["fieldCoverage"]["horses"], 5)
        self.assertEqual(payload["fieldCoverage"]["press"], 1)

    def test_best_time_tiers(self):
        horses = self._build()
        best1 = horses["1"]["bestTime"]
        self.assertEqual(best1["seconds"], 92.0)  # tier 1, not the 93.5
        self.assertEqual(best1["tier"], 1)
        self.assertEqual(best1["date"], "2026-11-03")
        best3 = horses["3"]["bestTime"]
        self.assertEqual(best3["seconds"], 75.0)
        self.assertEqual(best3["tier"], 3)  # surface kind anywhere
        self.assertIsNone(horses["4"]["bestTime"])  # debutant

    def test_head_to_head_and_ambiguous_key_dropped(self):
        horses = self._build()
        h1 = horses["1"]["headToHead"]
        self.assertEqual(h1["meetings"], 1)  # only the #2 meeting
        self.assertEqual(h1["duels"], 1)
        self.assertEqual(h1["ahead"], 0)
        self.assertEqual(h1["aheadRate"], 0.0)
        h2 = horses["2"]["headToHead"]
        self.assertEqual(h2["ahead"], 1)
        self.assertEqual(h2["aheadRate"], 1.0)
        # #5's only shared key disagreed on the title: no meeting.
        self.assertIsNone(horses["5"]["headToHead"])
        self.assertIsNone(horses["4"]["headToHead"])

    def test_pedigree_and_sire_course(self):
        horses = self._build()
        ped1 = horses["1"]["pedigree"]
        self.assertEqual(ped1["sire"], "種牡馬X")
        self.assertEqual(ped1["sireCourse"],
                         {"starts": 10, "wins": 2, "top3": 4,
                          "winRate": 0.2})
        self.assertEqual(ped1["siblings"], {"count": 2, "wins": 3})
        ped2 = horses["2"]["pedigree"]
        self.assertIsNotNone(ped2)
        self.assertIsNone(ped2["sireCourse"])  # sire not in the table
        self.assertIsNone(horses["3"]["pedigree"])  # no profile

    def test_press_carried_verbatim(self):
        horses = self._build()
        self.assertEqual(horses["1"]["press"],
                         {"marks": {"記者": "◎"}, "comment": "短評"})
        self.assertIsNone(horses["2"]["press"])

    def test_without_optional_inputs_fields_are_null(self):
        targets, speed, course, _, _, _ = _v2_inputs()
        payload = build_materials(DATE, speed, course, targets)
        horse = payload["races"][RACE_ID]["horses"]["1"]
        self.assertEqual(horse["nk_avg5"], 55)
        for field in ("bestTime", "headToHead", "pedigree", "press"):
            self.assertIsNone(horse[field])
        self.assertEqual(payload["fieldCoverage"]["bestTime"], 0)

    def test_load_race_details_shapes(self):
        detail = {"id": RACE_ID, "horses": []}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.json").write_text(
                json.dumps({"ok": True, "detail": detail}),
                encoding="utf-8")
            (Path(tmp) / "b.json").write_text(
                json.dumps({"id": "other-race", "horses": []}),
                encoding="utf-8")
            (Path(tmp) / "c.json").write_text("{broken",
                                              encoding="utf-8")
            loaded = load_race_details(tmp)
        self.assertEqual(set(loaded), {RACE_ID, "other-race"})


def _pace_forecast_input():
    """arvexq-pace-forecast-v1 shape for the fabricated race:
    horse 5 is forecast to lead at the start but drop to last
    by the 4th corner; horse 1 is the mirror image."""
    return {"version": "arvexq-pace-forecast-v1", "date": DATE,
            "races": {NK_ID: {
                "track": "金沢", "race_no": 1, "pace": "H",
                "n_runners": 5,
                "positions": {
                    "start": [[5], [4], [3], [2], [1]],
                    "corner3": [[4, 5], [3], [2], [1]],
                    "corner4": [[1], [2], [3], [4], [5]]}}}}


def _pace_materials(label="H"):
    """Parsed materials whose only live material is pace: the
    4-corner forecast order is 1,2,3,4,5 (percentiles
    .2,.4,.6,.8,1.0); no speed index anywhere."""
    horses = {}
    for n in NAMES:
        horses[str(n)] = {
            "nk_best": None, "nk_avg5": None, "nk_dist": None,
            "nk_course": None, "nk_recent": None,
            "pace": {ph: {"rank": n, "pct": n / 5.0}
                     for ph in ("start", "corner3", "corner4")}}
    return parse_materials_payload({
        "version": "nk-materials-v4", "date": DATE,
        "races": {RACE_ID: {"netkeibaRaceId": NK_ID,
                            "paceLabel": label, "horses": horses,
                            "courseAnalysis": None}}})


class PaceBuilderTests(TestCase):
    def _build(self, **kwargs):
        targets, speed, course, details, profiles, newspaper = \
            _v2_inputs()
        return build_materials(DATE, speed, course, targets,
                               race_details=details,
                               horse_profiles=profiles,
                               newspaper=newspaper, **kwargs)

    def test_pace_positions_become_rank_and_percentile(self):
        payload = self._build(pace_forecast=_pace_forecast_input())
        entry = payload["races"][RACE_ID]
        self.assertEqual(entry["paceLabel"], "H")
        horses = entry["horses"]
        self.assertEqual(horses["5"]["pace"]["start"],
                         {"rank": 1, "pct": 0.2})
        self.assertEqual(horses["5"]["pace"]["corner3"],
                         {"rank": 2, "pct": 0.4})
        self.assertEqual(horses["5"]["pace"]["corner4"],
                         {"rank": 5, "pct": 1.0})
        self.assertEqual(horses["1"]["pace"]["corner4"],
                         {"rank": 1, "pct": 0.2})
        self.assertEqual(horses["4"]["pace"]["corner3"],
                         {"rank": 1, "pct": 0.2})
        self.assertEqual(payload["fieldCoverage"]["pace"], 5)
        # The v1 fields are untouched by the pace input.
        self.assertEqual(horses["1"]["nk_avg5"], 55)

    def test_without_pace_input_fields_are_null(self):
        payload = self._build()
        entry = payload["races"][RACE_ID]
        self.assertIsNone(entry["paceLabel"])
        for horse in entry["horses"].values():
            self.assertIsNone(horse["pace"])
        self.assertEqual(payload["fieldCoverage"]["pace"], 0)


class PaceAdapterTests(TestCase):
    def test_pace_score_arithmetic(self):
        back = {"corner4": {"rank": 5, "pct": 1.0}}
        front = {"corner4": {"rank": 1, "pct": 0.0}}
        self.assertEqual(pace_score(back, "H"), 1.0)
        self.assertEqual(pace_score(front, "H"), -1.0)
        self.assertEqual(pace_score(back, "S"), -1.0)
        self.assertEqual(pace_score(front, "S"), 1.0)
        self.assertIsNone(pace_score(back, "M"))
        self.assertIsNone(pace_score(back, None))
        self.assertIsNone(pace_score(None, "H"))
        self.assertIsNone(pace_score({"start": {"rank": 1, "pct": 0.2}},
                                     "H"))

    def test_parse_drops_malformed_pace_cells(self):
        payload = {"races": {RACE_ID: {"horses": {"1": {
            "pace": {"corner4": {"rank": "x", "pct": 0.5},
                     "start": {"rank": 1, "pct": 0.2}}}}}}}
        parsed = parse_materials_payload(payload)
        self.assertEqual(parsed[RACE_ID]["horses"][1]["pace"],
                         {"start": {"rank": 1, "pct": 0.2}})

    def test_high_pace_lifts_forecast_back_runners(self):
        forecast = v9b_like_forecast()
        adjusted, info = apply_nk_materials(
            forecast, _pace_materials("H")[RACE_ID], {})
        self.assertTrue(info["applied"])
        # Since nk-materials-v14 the fixture's start / corner3
        # phases also fire the pace_early full-coverage term,
        # in the same direction as the corner4 pace term.
        self.assertEqual(info["terms"], ["pace", "pace_early"])
        self.assertEqual(info["paceTrial"], "ai-pace-forecast")
        self.assertIn(NK_PACE_WEIGHTS_LABEL, info["weights"])
        self.assertEqual(info["coverage"]["pace"], 5)
        self.assertEqual(PACE_WEIGHT, 0.10)
        by_number = {r.number: r for r in adjusted.runners}
        # Horse 5 is forecast last at the 4th corner: in a high
        # pace that is the advantaged seat. Horse 1 leads the
        # forecast and is discounted.
        self.assertGreater(by_number[5].p_win, STRENGTHS[5])
        self.assertLess(by_number[1].p_win, STRENGTHS[1])
        total = sum(r.p_win for r in adjusted.runners)
        self.assertAlmostEqual(total, 1.0, places=3)

    def test_slow_pace_lifts_forecast_front_runners(self):
        forecast = v9b_like_forecast()
        adjusted, info = apply_nk_materials(
            forecast, _pace_materials("S")[RACE_ID], {})
        self.assertTrue(info["applied"])
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[1].p_win, STRENGTHS[1])
        self.assertLess(by_number[5].p_win, STRENGTHS[5])

    def test_middling_label_is_inert(self):
        forecast = v9b_like_forecast()
        adjusted, info = apply_nk_materials(
            forecast, _pace_materials("M")[RACE_ID], {})
        self.assertIs(adjusted, forecast)
        self.assertFalse(info["applied"])

    def test_no_pace_material_is_inert(self):
        payload = {"races": {RACE_ID: {"horses": {
            str(n): {"nk_avg5": None} for n in NAMES}}}}
        forecast = v9b_like_forecast()
        adjusted, info = apply_nk_materials(
            forecast, parse_materials_payload(payload)[RACE_ID], {})
        self.assertIs(adjusted, forecast)
        self.assertFalse(info["applied"])

    def test_pace_adjustment_is_deterministic(self):
        first, _ = apply_nk_materials(
            v9b_like_forecast(), _pace_materials("H")[RACE_ID], {})
        second, _ = apply_nk_materials(
            v9b_like_forecast(), _pace_materials("H")[RACE_ID], {})
        self.assertEqual([r.p_win for r in first.runners],
                         [r.p_win for r in second.runners])


class ClosingAdapterTests(TestCase):
    """Closing trial (v7, 2026-11-18): the horses' own observed
    last-3F seconds, carried on the rewrite PastRun as
    last3f_seconds."""

    def _race_with_closings(self):
        missing = Obs(None, "test", "not_captured")

        def run(seconds):
            return PastRun(
                date="2026-11-03", track=missing, distance=missing,
                surface=missing, finish=missing,
                field_size=obs(10, "test"), corner_positions=(),
                margin_text=missing, time_seconds=missing,
                jockey=missing,
                last3f_seconds=(obs(seconds, "test")
                                if seconds is not None else missing))

        # Past runs are stored newest-first on the record. Horse 1
        # closed much faster last time than its own recent mean;
        # horse 2 is the mirror image; horse 4 has one unobserved
        # run in between; horse 5 has no observed closing at all.
        closings = {1: [36.0, 40.0, 40.0, 40.0],
                    2: [40.0, 36.0, 36.0, 36.0],
                    3: [38.0, 38.0, 38.0, 38.0],
                    4: [38.0, None, 38.0, 38.0],
                    5: [None, None, None, None]}
        runners = []
        for number in (1, 2, 3, 4, 5):
            runners.append(RunnerRecord(
                number=number, horse_id=missing,
                name=obs(NAMES[number], "test"),
                frame_number=missing, age=missing, sex=missing,
                jockey=missing, trainer=missing,
                carried_weight=missing, body_weight=missing,
                body_weight_change=missing,
                win_odds=obs(ODDS[number], "test"),
                scratched=False,
                past_runs=tuple(run(s) for s in closings[number])))
        return RaceRecord(
            race_id=RACE_ID, date=DATE, circuit=obs("地方", "test"),
            track="金沢", race_number=obs(1, "test"), title=missing,
            start_time=obs(POST, "test"), distance=obs(1500, "test"),
            surface=obs("ダート", "test"), weather=missing,
            condition=missing, updated_at=missing, segment=Segment.NAR,
            source="test", runners=tuple(runners))

    def test_closing_inputs_are_oldest_first_with_gaps_kept(self):
        inputs = closing_inputs_from_race(self._race_with_closings())
        self.assertEqual(inputs[1], [40.0, 40.0, 40.0, 36.0])
        self.assertEqual(inputs[2], [36.0, 36.0, 36.0, 40.0])
        self.assertEqual(inputs[4], [38.0, 38.0, None, 38.0])
        self.assertNotIn(5, inputs)

    def test_closing_term_lifts_the_fast_finisher(self):
        payload = {"races": {RACE_ID: {"horses": {
            str(n): {"nk_avg5": None} for n in NAMES}}}}
        entry = parse_materials_payload(payload)[RACE_ID]
        forecast = v9b_like_forecast()
        adjusted, info = apply_nk_materials(
            forecast, entry, {},
            closing_inputs=closing_inputs_from_race(
                self._race_with_closings()))
        self.assertTrue(info["applied"])
        self.assertEqual(info["terms"], ["closing"])
        self.assertEqual(info["closingTrial"], NK_CLOSING_TRIAL)
        self.assertIn(NK_CLOSING_WEIGHTS_LABEL, info["weights"])
        self.assertEqual(info["coverage"]["closing"], 4)
        self.assertEqual(CLOSING_WEIGHT, 0.10)
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[1].p_win, STRENGTHS[1])
        self.assertLess(by_number[2].p_win, STRENGTHS[2])
        total = sum(r.p_win for r in adjusted.runners)
        self.assertAlmostEqual(total, 1.0, places=3)

    def test_no_closing_inputs_is_inert(self):
        payload = {"races": {RACE_ID: {"horses": {
            str(n): {"nk_avg5": None} for n in NAMES}}}}
        forecast = v9b_like_forecast()
        adjusted, info = apply_nk_materials(
            forecast, parse_materials_payload(payload)[RACE_ID], {})
        self.assertIs(adjusted, forecast)
        self.assertFalse(info["applied"])

    def test_normalize_keeps_observed_last3f_on_past_runs(self):
        runner = {"horseNumber": 1, "name": "アアア",
                  "allPastRuns": [past_run("2026-11-03", 2)]}
        record = normalize_runner(runner, DATE, "test")
        self.assertEqual(record.past_runs[0].last3f_seconds.value, 38.0)
        runner = {"horseNumber": 1, "name": "アアア",
                  "allPastRuns": [{"date": "2026-11-03"}]}
        record = normalize_runner(runner, DATE, "test")
        self.assertIsNone(record.past_runs[0].last3f_seconds.value)


class PaceBuildTests(TestCase):
    def test_build_stamps_the_pace_arrow_lean(self):
        # The pace forecast's place in the clean-forecast-v2
        # path is the pace_arrow lean: corner4 pct minus start
        # pct, leaned in the fade direction the walk-forward
        # supported (the forecast odds over-price the horses
        # their own pace forecast sends forward). The stamp
        # records the lean's weight, whether it fired, and its
        # field coverage; the retired pace-trial record
        # (paceTrial / terms / weights label) is gone.
        extra = {n: {"pace": {
            "start": {"rank": n, "pct": n / 5.0},
            "corner3": {"rank": n, "pct": n / 5.0},
            "corner4": {"rank": n, "pct": (6 - n) / 5.0}}}
            for n in NAMES}
        new, receipt = _build(
            fresh_detail(), materials=v2_materials(extra))
        self.assertIsNotNone(new, receipt)
        stamp = new["preparedMeta"]["rewritePublish"]["nkMaterials"]
        self.assertTrue(stamp["applied"])
        self.assertEqual(stamp["coverage"]["pace_arrow"], 5)
        self.assertEqual(stamp["leans"]["pace_arrow"]["weight"],
                         0.10)
        self.assertTrue(stamp["leans"]["pace_arrow"]["fired"])
        self.assertNotIn("paceTrial", stamp)
        self.assertNotIn("terms", stamp)
        # Direction: horse 1 carries the field's largest
        # corner4-minus-start (the pace forecast sends her
        # backwards through the race) and is lifted; horse 5,
        # the mirror image, is cut.
        plain, _ = _build(fresh_detail(), materials=v2_materials())
        win = new["prediction"]["stages"]["probability"]["value"]["win"]
        win_plain = plain["prediction"]["stages"]["probability"]["value"]["win"]
        self.assertGreater(win[1], win_plain[1])
        self.assertLess(win[5], win_plain[5])
        self.assertIsNotNone(verified_unified(new))


# ------------------------------------------------------------ v6
def derived_entry(recent=None, dist=None, course=None):
    """Parsed-shape materials on a flat speed level (identical
    avg5 and spd2 for every horse, so the speed residual is 0):
    only the v6 derived features can move a probability."""
    horses = {}
    for n in NAMES:
        horses[n] = {
            "nk_best": None, "nk_avg5": 60,
            "nk_dist": (dist or {}).get(n),
            "nk_course": (course or {}).get(n),
            "nk_recent": (recent or {}).get(n),
            "bestTime": None, "headToHead": None,
            "pedigree": None, "press": None, "pace": None,
            "nkFormDev": None, "nkAiScore": None, "odds": None}
    return {"netkeibaRaceId": NK_ID, "courseAnalysis": None,
            "horses": horses}


class SpeedDerivedAdapterTests(TestCase):
    def test_trend_terms_reward_the_rising_horse(self):
        # Every sequence is a permutation of {40, 55, 70}, so
        # the dispersion features (vol / sd / overlap) are
        # identical for the whole field and cannot differentiate
        # anyone: only slope and dev move the probabilities.
        # Horse 1 rises steeply into the race (slope +15, last
        # run 10 above its average); horse 5 is the mirror.
        entry = derived_entry(recent={
            1: [40, 55, 70], 2: [40, 70, 55], 3: [70, 40, 55],
            4: [55, 70, 40], 5: [70, 55, 40]})
        adjusted, info = apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS)
        self.assertTrue(info["applied"])
        for term in ("speed_slope", "speed_dev", "speed_vol",
                     "speed_sd"):
            self.assertIn(term, info["terms"])
        self.assertEqual(info["speedDerivedTrial"],
                         NK_SPEED_DERIVED_TRIAL)
        self.assertIn(NK_SPEED_DERIVED_LABEL, info["weights"])
        self.assertIn("unvalidated", info["weights"])
        self.assertEqual(info["coverage"]["speed_trend"], 5)
        self.assertEqual(info["coverage"]["speed_dev"], 5)
        self.assertEqual(info["coverage"]["speed_sd"], 5)
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[1].p_win, STRENGTHS[1])
        self.assertLess(by_number[5].p_win, STRENGTHS[5])
        total = sum(r.strength for r in adjusted.runners)
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_fit_term_rewards_condition_aptitude(self):
        entry = derived_entry(
            dist={1: 70, 2: 60, 3: 60, 4: 60, 5: 50},
            course={1: 70, 2: 60, 3: 60, 4: 60, 5: 50})
        adjusted, info = apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS)
        self.assertTrue(info["applied"])
        self.assertIn("speed_fit", info["terms"])
        self.assertEqual(info["coverage"]["speed_fit"], 5)
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[1].p_win, STRENGTHS[1])
        self.assertLess(by_number[5].p_win, STRENGTHS[5])

    def test_no_derived_inputs_no_derived_terms(self):
        # Today's real shape for a horse with an index but no
        # recent sequence and no condition columns: the derived
        # family stays completely inert and leaves no stamp.
        horses = {n: {"nk_best": None, "nk_avg5": NK_AVG5[n],
                      "nk_dist": None, "nk_course": None,
                      "nk_recent": None}
                  for n in NAMES}
        entry = {"netkeibaRaceId": NK_ID, "courseAnalysis": None,
                 "horses": horses}
        adjusted, info = apply_nk_materials(
            v9b_like_forecast(), entry,
            {n: {"spd2_recent": SPD2_DEFICIT[n]} for n in NAMES})
        self.assertTrue(info["applied"])
        self.assertEqual(info["terms"], ["speed"])
        self.assertNotIn("speedDerivedTrial", info)
        self.assertNotIn("speed-derived-trial", info["weights"])

    def test_derived_weights_are_the_trial_values(self):
        self.assertEqual(SPEED_DERIVED_WEIGHTS, {
            "speed_slope": 0.10, "speed_dev": 0.10,
            "speed_vol": -0.10, "speed_sd": -0.10,
            "speed_overlap": -0.10, "speed_fit": 0.10,
            "speed_bias": 0.10})


def _combo_race() -> RaceRecord:
    """Runners with named jockeys and past runs: horse 2's pair
    record with today's jockey is all top-3, horse 3's is all
    unplaced; horse 5's jockey is unknown (no pair record)."""
    missing = Obs(None, "test", "not_captured")

    def run(jockey, finish):
        return PastRun(
            date="2026-11-03", track=missing, distance=missing,
            surface=missing,
            finish=obs(finish, "test") if finish else missing,
            field_size=obs(10, "test"), corner_positions=(),
            margin_text=missing, time_seconds=missing,
            jockey=obs(jockey, "test") if jockey else missing)

    rides = {
        1: [("騎手A", 2), ("騎手A", 3), ("騎手A", 2), ("騎手A", 8)],
        2: [("騎手B", 1), ("騎手B", 1), ("騎手B", 2), ("騎手B", 1)],
        3: [("騎手C", 5), ("騎手C", 6), ("騎手C", 7), ("騎手C", 8)],
        4: [("騎手D", 3), ("騎手D", 4), ("騎手D", 5), ("騎手D", 6)],
        5: [("騎手E", 1), ("騎手E", 2)],
    }
    today = {1: "騎手A", 2: "騎手B", 3: "騎手C", 4: "騎手D", 5: None}
    runners = []
    for number in (1, 2, 3, 4, 5):
        runners.append(RunnerRecord(
            number=number, horse_id=missing,
            name=obs(NAMES[number], "test"), frame_number=missing,
            age=missing, sex=missing,
            jockey=obs(today[number], "test") if today[number]
            else missing,
            trainer=missing, carried_weight=missing,
            body_weight=missing, body_weight_change=missing,
            win_odds=obs(ODDS[number], "test"), scratched=False,
            past_runs=tuple(run(j, f) for j, f in rides[number])))
    return RaceRecord(
        race_id=RACE_ID, date=DATE, circuit=obs("地方", "test"),
        track="金沢", race_number=obs(1, "test"), title=missing,
        start_time=obs(POST, "test"), distance=obs(1500, "test"),
        surface=obs("ダート", "test"), weather=missing,
        condition=missing, updated_at=missing, segment=Segment.NAR,
        source="test", runners=tuple(runners))


class ComboTests(TestCase):
    def test_combo_inputs_shape_and_unknown_jockey_guard(self):
        inputs = combo_inputs_from_race(_combo_race())
        self.assertEqual(inputs[2]["jockey"], "騎手B")
        self.assertEqual(inputs[2]["past_rides"][0],
                         {"jockey": "騎手B", "finish": 1,
                          "field_size": 10})
        self.assertEqual(len(inputs[1]["past_rides"]), 4)
        # Today's jockey unknown: no attributable rides at all.
        self.assertIsNone(inputs[5]["jockey"])
        self.assertEqual(inputs[5]["past_rides"], [])

    def test_combo_term_rewards_the_proven_pair(self):
        entry = derived_entry()
        adjusted, info = apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS,
            combo_inputs=combo_inputs_from_race(_combo_race()))
        self.assertTrue(info["applied"])
        self.assertIn("combo", info["terms"])
        self.assertEqual(info["comboTrial"], NK_COMBO_TRIAL)
        self.assertIn(NK_COMBO_LABEL, info["weights"])
        self.assertEqual(info["coverage"]["combo"], 4)
        self.assertEqual(COMBO_WEIGHT, 0.10)
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[2].p_win, STRENGTHS[2])
        self.assertLess(by_number[3].p_win, STRENGTHS[3])

    def test_no_combo_inputs_no_combo_term(self):
        adjusted, info = apply_nk_materials(
            v9b_like_forecast(), derived_entry(), FLAT_EXTRAS)
        self.assertNotIn("combo", info.get("terms") or [])
        self.assertNotIn("comboTrial", info)


class JudgementOddsTests(TestCase):
    def _parsed(self, per_horse):
        payload = {"version": "nk-materials-v6", "date": DATE,
                   "races": {RACE_ID: {
                       "netkeibaRaceId": NK_ID,
                       "horses": {str(n): dict(
                           {"nk_best": None, "nk_avg5": 60,
                            "nk_dist": None, "nk_course": None,
                            "nk_recent": None},
                           **per_horse.get(n, {}))
                           for n in NAMES},
                       "courseAnalysis": None}}}
        return parse_materials_payload(payload)[RACE_ID]

    def test_parse_carries_v6_fields_and_drops_malformed(self):
        entry = self._parsed({
            1: {"nkFormDev": 55.5, "nkAiScore": 0.8,
                "odds": {"publishWin": 3.0, "finalWin": 2.5,
                         "placeLow": 1.2, "placeHigh": 1.6}},
            2: {"nkFormDev": "55", "nkAiScore": None,
                "odds": "not-a-dict"}})
        h1 = entry["horses"][1]
        self.assertEqual(h1["nkFormDev"], 55.5)
        self.assertEqual(h1["nkAiScore"], 0.8)
        self.assertEqual(h1["odds"]["publishWin"], 3.0)
        h2 = entry["horses"][2]
        self.assertIsNone(h2["nkFormDev"])
        self.assertIsNone(h2["nkAiScore"])
        self.assertIsNone(h2["odds"])

    def test_judgement_terms_fire_on_values(self):
        entry = self._parsed({
            n: {"nkFormDev": v, "nkAiScore": a}
            for n, v, a in ((1, 40, 0.2), (2, 55, 0.5),
                            (3, 50, 0.4), (4, 45, 0.3),
                            (5, 60, 0.9))})
        adjusted, info = apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS)
        self.assertTrue(info["applied"])
        self.assertIn("nk_form_dev", info["terms"])
        self.assertIn("nk_ai", info["terms"])
        self.assertEqual(info["judgementTrial"], NK_JUDGEMENT_TRIAL)
        self.assertIn(NK_JUDGEMENT_LABEL, info["weights"])
        self.assertEqual(info["coverage"]["nk_form_dev"], 5)
        self.assertEqual(info["coverage"]["nk_ai"], 5)
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[5].p_win, STRENGTHS[5])
        self.assertLess(by_number[1].p_win, STRENGTHS[1])

    def test_odds_terms_fire_on_values(self):
        # Win/place gap held constant across the field (place
        # range proportional to the final win odds), so only
        # the drift differentiates: horse 1's odds shortened
        # into the race, horse 5's drifted out.
        def odds(publish, final):
            return {"publishWin": publish, "finalWin": final,
                    "placeLow": final * 0.4, "placeHigh": final * 0.6}
        entry = self._parsed({
            1: {"odds": odds(3.0, 2.0)}, 2: {"odds": odds(3.0, 3.0)},
            3: {"odds": odds(3.0, 3.0)}, 4: {"odds": odds(3.0, 3.0)},
            5: {"odds": odds(2.0, 4.0)}})
        adjusted, info = apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS)
        self.assertTrue(info["applied"])
        self.assertIn("odds_drift", info["terms"])
        self.assertEqual(info["oddsTrial"], NK_ODDS_TRIAL)
        self.assertIn(NK_ODDS_LABEL, info["weights"])
        self.assertEqual(info["coverage"]["odds_drift"], 5)
        self.assertEqual(info["coverage"]["odds_wp_gap"], 5)
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[1].p_win, STRENGTHS[1])
        self.assertLess(by_number[5].p_win, STRENGTHS[5])

    def test_armed_families_inert_without_values(self):
        # Today's real shape: the fields exist in the format but
        # no collection has ever filled them. No judgement or
        # odds term may fire and no trial marker may appear.
        entry = self._parsed({})
        adjusted, info = apply_nk_materials(
            v9b_like_forecast(), entry, FLAT_EXTRAS)
        for term in ("nk_form_dev", "nk_ai", "odds_drift",
                     "odds_wp_gap"):
            self.assertNotIn(term, info.get("terms") or [])
        self.assertNotIn("judgementTrial", info)
        self.assertNotIn("oddsTrial", info)
        self.assertEqual(info["coverage"]["nk_form_dev"], 0)
        self.assertEqual(info["coverage"]["nk_ai"], 0)
        self.assertEqual(info["coverage"]["odds_drift"], 0)
        self.assertEqual(info["coverage"]["odds_wp_gap"], 0)


class BuilderV6Tests(TestCase):
    def _build(self, **kwargs):
        targets, speed, course, details, profiles, newspaper = \
            _v2_inputs()
        return build_materials(DATE, speed, course, targets,
                               race_details=details,
                               horse_profiles=profiles,
                               newspaper=newspaper, **kwargs)

    def test_derived_coverage_counts_from_raw_columns(self):
        payload = self._build()
        cov = payload["fieldCoverage"]
        # _v2_inputs: every horse has nk_recent [55, 54, 53]
        # (slope / dev / vol / sd computable) but no dist /
        # course columns (no fit / bias).
        self.assertEqual(cov["speedSlope"], 5)
        self.assertEqual(cov["speedDev"], 5)
        self.assertEqual(cov["speedVol"], 5)
        self.assertEqual(cov["speedSd"], 5)
        self.assertEqual(cov["speedOverlap"], 5)
        self.assertEqual(cov["speedFit"], 0)
        self.assertEqual(cov["speedBias"], 0)

    def test_judgement_and_odds_fields_carried(self):
        judgements = {"races": {NK_ID: {"horses": {
            "1": {"nkFormDev": 55.5, "nkAiScore": 0.8},
            "2": {"nkFormDev": "x"}}}}}
        odds = {"races": {NK_ID: {"horses": {
            "1": {"publishWin": 3.0, "finalWin": 2.5,
                  "placeLow": 1.2, "placeHigh": 1.6},
            "3": {"publishWin": None}}}}}
        payload = self._build(nk_judgements=judgements, odds=odds)
        horses = payload["races"][RACE_ID]["horses"]
        self.assertEqual(horses["1"]["nkFormDev"], 55.5)
        self.assertEqual(horses["1"]["nkAiScore"], 0.8)
        self.assertIsNone(horses["2"]["nkFormDev"])
        self.assertEqual(horses["1"]["odds"],
                         {"publishWin": 3.0, "finalWin": 2.5,
                          "placeLow": 1.2, "placeHigh": 1.6})
        self.assertIsNone(horses["3"]["odds"])  # all cells null
        cov = payload["fieldCoverage"]
        self.assertEqual(cov["nkFormDev"], 1)
        self.assertEqual(cov["nkAiScore"], 1)
        self.assertEqual(cov["oddsDrift"], 1)
        self.assertEqual(cov["oddsWpGap"], 1)

    def test_without_v6_inputs_fields_are_null(self):
        payload = self._build()
        horse = payload["races"][RACE_ID]["horses"]["1"]
        for field in ("nkFormDev", "nkAiScore", "odds"):
            self.assertIsNone(horse[field])
        cov = payload["fieldCoverage"]
        self.assertEqual(cov["nkFormDev"], 0)
        self.assertEqual(cov["nkAiScore"], 0)
        self.assertEqual(cov["oddsDrift"], 0)
        self.assertEqual(cov["oddsWpGap"], 0)

    def test_press_flows_without_race_details(self):
        # The marks join on (race, horse number) alone: a build
        # with a newspaper input but NO race-details input must
        # still carry them (the 2026-11-18 collection run lost
        # every mark this way — press coverage 0 on file).
        targets, speed, course, _, _, newspaper = _v2_inputs()
        payload = build_materials(DATE, speed, course, targets,
                                  newspaper=newspaper)
        horses = payload["races"][RACE_ID]["horses"]
        self.assertEqual(horses["1"]["press"],
                         {"marks": {"記者": "◎"}, "comment": "短評"})
        self.assertIsNone(horses["2"]["press"])
        self.assertEqual(payload["fieldCoverage"]["press"], 1)


class V6BuildStampTests(TestCase):
    def test_build_stamps_the_clean_forecast_record(self):
        new, receipt = _build(fresh_detail(), race=_combo_race())
        self.assertIsNotNone(new, receipt)
        stamp = new["preparedMeta"]["rewritePublish"]["nkMaterials"]
        self.assertTrue(stamp["applied"])
        self.assertEqual(stamp["version"], CLEAN_FORECAST_VERSION)
        self.assertEqual(stamp["path"], "clean-forecast")
        # The retired v6 trial families (speed-derived /
        # combo / judgement / odds) no longer stand in the
        # probability path: the stamp carries no terms list,
        # no weights label and no trial markers for them.
        self.assertNotIn("terms", stamp)
        self.assertNotIn("weights", stamp)
        self.assertNotIn("speedDerivedTrial", stamp)
        self.assertNotIn("comboTrial", stamp)
        self.assertNotIn("judgementTrial", stamp)
        self.assertNotIn("oddsTrial", stamp)
        # This entry carries no forecast odds, so the
        # foundation stands on the market base and records no
        # leans; what the publication stood on is the
        # fingerprint.
        self.assertEqual(stamp["base"], "market")
        self.assertEqual(stamp["leans"], {})
        self.assertEqual(stamp["entryFingerprint"]["speed"], 5)
        self.assertIsNotNone(verified_unified(new))


def fabricated_jumps_race() -> RaceRecord:
    """A Fukushima jumps race whose runners carry scored past
    runs (the v1 forecast needs them; there is no v8 lane for
    the segment)."""
    missing = Obs(None, "test", "not_captured")

    def run(finish):
        return PastRun(
            date="2026-10-25", track=obs("福島", "test"),
            distance=obs(2750, "test"), surface=obs("障害", "test"),
            finish=obs(finish, "test"), field_size=obs(12, "test"),
            corner_positions=(3, 3), margin_text=missing,
            time_seconds=obs(190.0 + finish, "test"), jockey=missing)

    runners = []
    for number in (1, 2, 3, 4, 5):
        runners.append(RunnerRecord(
            number=number, horse_id=missing,
            name=obs(NAMES[number], "test"),
            frame_number=obs(number, "test"),
            age=missing, sex=missing, jockey=missing, trainer=missing,
            carried_weight=missing, body_weight=missing,
            body_weight_change=missing,
            win_odds=obs(ODDS[number], "test"),
            scratched=False,
            past_runs=(run(number), run((number % 5) + 1))))
    return RaceRecord(
        race_id=JUMPS_ID, date=JUMPS_DATE, circuit=obs("中央", "test"),
        track="福島", race_number=obs(4, "test"), title=missing,
        start_time=obs(JUMPS_POST, "test"), distance=obs(2750, "test"),
        surface=obs("障害", "test"), weather=missing,
        condition=missing, updated_at=missing, segment=Segment.JUMPS,
        source="test", runners=tuple(runners))


def fresh_jumps_detail() -> dict:
    return {
        "id": JUMPS_ID, "date": JUMPS_DATE, "circuit": "中央",
        "track": "福島", "raceNumber": 4,
        "scheduledStartTime": JUMPS_POST, "distance": 2750,
        "surface": "障害", "condition": "良",
        "horses": [{
            "horseNumber": n, "name": NAMES[n], "winOdds": ODDS[n],
            "frameNumber": n, "age": 5, "sex": "牡",
            "carriedWeight": 60.0, "jockey": "騎手",
            "trainer": "調教師", "popularity": n,
            "allPastRuns": [past_run("2026-11-03", n)]}
            for n in (1, 2, 3, 4, 5)],
    }


def _build_jumps(detail, materials=JUMPS_MATERIALS, extras=None):
    ctx = [
        patch("scripts.arvexq_rewrite_publish.normalize_race",
              return_value=fabricated_jumps_race()),
        patch("scripts.arvexq_rewrite_publish.forecast_race_v8",
              return_value=v9b_like_forecast()),
        patch("scripts.arvexq_rewrite_publish._load_v8_extras",
              return_value=extras or {}),
        patch("scripts.arvexq_rewrite_publish._load_nk_materials",
              return_value=materials),
    ]
    for c in ctx:
        c.start()
    try:
        return build_publish_detail(
            detail, {"race_id": JUMPS_ID, "id": JUMPS_ID}, JUMPS_NOW)
    finally:
        for c in reversed(ctx):
            c.stop()


class JumpsBuildTests(TestCase):
    """B5 (2026-11-21): the build applies the materials
    adjustment to a jumps race's v1 vector — before this, the
    segment never reached the adjustment block at all."""

    def test_first_publication_applies_materials_on_the_v1_lane(self):
        new, receipt = _build_jumps(fresh_jumps_detail())
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertEqual(marker["abilityLane"], "v1-prior")
        stamp = marker["nkMaterials"]
        self.assertTrue(stamp["applied"])
        # Clean-forecast-v2 (2026-11-28 rebuild): the jumps
        # entry carries no forecast odds, so the foundation
        # stands on the market base and no lean fires; the
        # collected materials the publication stood on
        # (bestTime / press) are recorded in the fingerprint,
        # not as retired terms.
        self.assertEqual(stamp["version"], CLEAN_FORECAST_VERSION)
        self.assertEqual(stamp["base"], "market")
        self.assertEqual(stamp["leans"], {})
        self.assertNotIn("terms", stamp)
        self.assertEqual(stamp["entryFingerprint"]["mochitime"], 5)
        self.assertEqual(stamp["entryFingerprint"]["press"], 5)
        self.assertIsNotNone(verified_unified(new))

    def test_frozen_jumps_race_reissues_once_with_materials(self):
        first, receipt = _build_jumps(fresh_jumps_detail())
        self.assertIsNotNone(first, receipt)
        frozen = copy.deepcopy(first)
        frozen["preparedMeta"]["rewritePublish"].pop("nkMaterials")
        new, receipt = _build_jumps(frozen)
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        revision = marker["revision"]
        self.assertEqual(revision["kind"], "nk-materials-upgrade")
        self.assertEqual(revision["previousAbilityLane"], "v1-prior")
        self.assertEqual(revision["abilityLane"], "v1-prior")
        self.assertTrue(marker["nkMaterials"]["applied"])
        self.assertIsNotNone(verified_unified(new))
        # Exactly once: the re-issued detail no longer qualifies.
        with patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                   return_value=JUMPS_MATERIALS):
            self.assertIsNone(
                _nk_materials_upgrade_info(new, JUMPS_NOW))


if __name__ == "__main__":
    import unittest
    unittest.main()
