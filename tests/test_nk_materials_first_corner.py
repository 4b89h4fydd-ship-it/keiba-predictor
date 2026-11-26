"""First-corner term tests (2026-11-26, nk-materials-v16):
the builder's carriage of the standing course-geometry
record's first-corner distance onto the materials entry, and
the adapter's first_corner term (the course shape priced
against each horse's forecast early frontness).

Covered here:
  - the builder joins the geometry record on the target's
    own (track, surface, distance) into the entry's
    firstCornerMeters (no record -> null, never estimated),
    counts the covered horses in fieldCoverage, records the
    zero as EXPLAINED only when no geometry file reached the
    build at all, and leaves it UNEXPLAINED when a supplied
    file matched nothing (fail-closed, audit S4);
  - the adapter's parser carries the value defensively;
  - first_corner_factor is 0 at the standing records' median
    distance, saturates at the scale's ends, and reads the
    ABSOLUTE distance;
  - first_corner_score's direction: on a short run to the
    first corner a front-forecast horse scores DOWN and a
    closer UP; on a long run the signs reverse — and the
    term fires that way through apply_nk_materials;
  - a median-distance course (factor 0) is exactly inert, a
    horse with no early forecast position is never shifted,
    and the family joins the materials fingerprint.

The frozen integrated_eval is untouched; the first-corner
term is an adapter-level post-integrate logit shift (see
rewrite/analysis/nk_materials.py).
"""
from __future__ import annotations

from unittest import TestCase

from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.nk_materials import (
    NK_FIRST_CORNER_LABEL, NK_FIRST_CORNER_TRIAL,
    apply_nk_materials, first_corner_factor, first_corner_score,
    materials_fingerprint, parse_materials_payload)
from scripts.arvexq_nk_materials_build import build as build_materials

NK_ID = "202642112603"
RACE_ID = "nar-2026-11-26-浦和-03"
DATE = "2026-11-26"
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}
STRENGTHS = {1: 0.30, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.10}

TARGETS = {"targets": [{"netkeiba_race_id": NK_ID,
                        "arvexq_race_id": RACE_ID,
                        "track": "浦和", "race_no": 3,
                        "distance": 1400, "surface": "ダート"}]}
SPEED = {"races": {NK_ID: {"horses": {
    str(n): {"name": NAMES[n], "nk_best": 65, "nk_avg5": 60,
             "nk_dist": None, "nk_course": None,
             "nk_recent": [55, 54, 53]}
    for n in NAMES}}}}
GEOMETRY = {"version": "course-geometry-test",
            "records": [
                {"sourceKind": "official_course_geometry",
                 "track": "浦和", "surface": "ダート",
                 "distance": 1400,
                 "firstCornerDistanceMeters": 280},
                {"sourceKind": "official_course_geometry",
                 "track": "浦和", "surface": "ダート",
                 "distance": 800,
                 "firstCornerDistanceMeters": 300}]}


def _forecast() -> RaceForecast:
    runners = [RunnerForecast(
        number=n, name=NAMES[n], ability_score=0.5, strength=s,
        pace_adjustment=1.0, pace_reasons=(), p_win=s, p_top2=None,
        p_top3=None, mark="", status="scored")
        for n, s in STRENGTHS.items()]
    return RaceForecast(RACE_ID, 3.0, "calibrated",
                        tuple(runners), "ok")


def _parsed(per_horse, meters=None):
    payload = {"version": "nk-materials-v14", "date": DATE,
               "races": {RACE_ID: {
                   "netkeibaRaceId": NK_ID,
                   "horses": {str(n): dict(
                       {"nk_best": None, "nk_avg5": 60,
                        "nk_dist": None, "nk_course": None,
                        "nk_recent": None},
                       **per_horse.get(n, {}))
                       for n in NAMES},
                   "courseAnalysis": None,
                   "paceLabel": None,
                   "firstCornerMeters": meters}}}
    return parse_materials_payload(payload)[RACE_ID]


def _pace(pct):
    return {"start": {"rank": 1, "pct": pct},
            "corner3": {"rank": 1, "pct": pct},
            "corner4": {"rank": 1, "pct": pct}}


class BuilderFirstCornerCarriageTests(TestCase):
    def test_record_joined_on_the_targets_own_key(self):
        payload = build_materials(
            DATE, SPEED, {}, TARGETS, course_geometry=GEOMETRY)
        entry = payload["races"][RACE_ID]
        self.assertEqual(entry["firstCornerMeters"], 280)
        # Coverage counts the horses the term can stand on:
        # every horse of a covered race.
        self.assertEqual(payload["fieldCoverage"]["firstCorner"], 5)
        self.assertNotIn("firstCorner", payload["zeroCoverage"])

    def test_course_without_a_record_carries_null(self):
        targets = {"targets": [{"netkeiba_race_id": NK_ID,
                                "arvexq_race_id": RACE_ID,
                                "track": "名古屋", "race_no": 3,
                                "distance": 1500,
                                "surface": "ダート"}]}
        payload = build_materials(
            DATE, SPEED, {}, targets, course_geometry=GEOMETRY)
        entry = payload["races"][RACE_ID]
        self.assertIsNone(entry["firstCornerMeters"])
        self.assertEqual(payload["fieldCoverage"]["firstCorner"], 0)

    def test_no_geometry_supplied_zero_is_explained(self):
        payload = build_materials(DATE, SPEED, {}, TARGETS)
        entry = payload["races"][RACE_ID]
        self.assertIsNone(entry["firstCornerMeters"])
        self.assertIn("firstCorner", payload["zeroCoverage"])
        self.assertIn("firstCorner",
                      payload["zeroCoverageExplained"])
        self.assertNotIn("firstCorner",
                         payload["zeroCoverageUnexplained"])

    def test_geometry_supplied_but_unmatched_is_unexplained(self):
        # A geometry file reached the build and matched no
        # course of the day: a missing material with no
        # registered reason — fail-closed (audit S4).
        targets = {"targets": [{"netkeiba_race_id": NK_ID,
                                "arvexq_race_id": RACE_ID,
                                "track": "名古屋", "race_no": 3,
                                "distance": 1500,
                                "surface": "ダート"}]}
        payload = build_materials(
            DATE, SPEED, {}, targets, course_geometry=GEOMETRY)
        self.assertIn("firstCorner",
                      payload["zeroCoverageUnexplained"])


class FirstCornerFactorTests(TestCase):
    def test_factor_is_zero_at_the_median_distance(self):
        self.assertEqual(first_corner_factor(300), 0.0)

    def test_factor_reads_the_absolute_distance(self):
        self.assertAlmostEqual(first_corner_factor(150), -0.5)
        self.assertAlmostEqual(first_corner_factor(450), 0.5)
        self.assertAlmostEqual(first_corner_factor(100),
                               -200.0 / 300.0)

    def test_factor_saturates_at_the_scales_ends(self):
        self.assertEqual(first_corner_factor(600), 1.0)
        self.assertEqual(first_corner_factor(836), 1.0)
        self.assertEqual(first_corner_factor(72), -0.76)

    def test_factor_needs_a_recorded_distance(self):
        self.assertIsNone(first_corner_factor(None))
        self.assertIsNone(first_corner_factor(0))
        self.assertIsNone(first_corner_factor(-50))
        self.assertIsNone(first_corner_factor("280"))


class FirstCornerScoreTests(TestCase):
    def test_short_course_front_down_closer_up(self):
        # D=100: factor -2/3. A front-forecast horse (early
        # pct 0.1 -> frontness +0.8) pays for its position; a
        # closer (pct 0.9 -> frontness -0.8) gains.
        self.assertAlmostEqual(
            first_corner_score(100, _pace(0.1)), -0.8 * 2 / 3)
        self.assertAlmostEqual(
            first_corner_score(100, _pace(0.9)), 0.8 * 2 / 3)
        # A mid-field forecast is untouched by the shape.
        self.assertAlmostEqual(
            first_corner_score(100, _pace(0.5)), 0.0)

    def test_long_course_reverses_the_signs(self):
        # D=500: factor +2/3 — the front horse takes its
        # position cheaply, the closer is left behind.
        self.assertAlmostEqual(
            first_corner_score(500, _pace(0.1)), 0.8 * 2 / 3)
        self.assertAlmostEqual(
            first_corner_score(500, _pace(0.9)), -0.8 * 2 / 3)

    def test_score_needs_record_and_early_position(self):
        self.assertIsNone(first_corner_score(None, _pace(0.1)))
        self.assertIsNone(first_corner_score(100, None))
        self.assertIsNone(first_corner_score(100, {}))
        # A corner4-only forecast has no early position: the
        # run to the FIRST corner is not read off the last
        # phase.
        self.assertIsNone(first_corner_score(
            100, {"corner4": {"rank": 1, "pct": 0.1}}))
        # A start-only forecast still scores.
        self.assertAlmostEqual(
            first_corner_score(
                100, {"start": {"rank": 1, "pct": 0.1}}),
            -0.8 * 2 / 3)


class FirstCornerParseTests(TestCase):
    def test_parse_carries_a_valid_distance(self):
        entry = _parsed({}, meters=280)
        self.assertEqual(entry["firstCornerMeters"], 280)

    def test_parse_drops_an_invalid_distance(self):
        for bad in (0, -50, "280", None):
            entry = _parsed({}, meters=bad)
            self.assertIsNone(entry["firstCornerMeters"])


class FirstCornerTermTests(TestCase):
    PER_HORSE = {
        1: {"pace": _pace(0.1)},
        2: {"pace": _pace(0.5)},
        3: {},
        4: {"pace": _pace(0.9)},
        5: {"pace": _pace(0.3)},
    }

    def _apply(self, per_horse, meters=None):
        entry = _parsed(per_horse, meters=meters)
        return apply_nk_materials(_forecast(), entry)

    def _ratios(self, adjusted):
        moved = {r.number: r.p_win for r in adjusted.runners}
        origin = {r.number: r.p_win for r in _forecast().runners}
        return {n: moved[n] / origin[n] for n in origin}

    def test_short_course_shifts_against_the_front(self):
        adjusted, info = self._apply(self.PER_HORSE, meters=100)
        self.assertTrue(info["applied"])
        self.assertIn("first_corner", info["terms"])
        self.assertEqual(info["firstCornerTrial"],
                         NK_FIRST_CORNER_TRIAL)
        self.assertIn(NK_FIRST_CORNER_LABEL, info["weights"])
        self.assertEqual(info["coverage"]["first_corner"], 4)
        ratios = self._ratios(adjusted)
        # Front (1) down, mid (2, score 0) as the hinge, back
        # (4) up — the mineta direction, not its reverse.
        self.assertLess(ratios[1], ratios[2])
        self.assertLess(ratios[2], ratios[4])
        # Horse 3 (no early position) is never shifted: its
        # ratio agrees with the zero-score horse 2's, up to
        # the shared renormalisation.
        self.assertAlmostEqual(ratios[3], ratios[2], places=2)

    def test_long_course_shifts_for_the_front(self):
        adjusted, info = self._apply(self.PER_HORSE, meters=500)
        self.assertIn("first_corner", info["terms"])
        ratios = self._ratios(adjusted)
        self.assertGreater(ratios[1], ratios[2])
        self.assertGreater(ratios[2], ratios[4])

    def test_median_course_is_exactly_inert(self):
        at_median, info_median = self._apply(
            self.PER_HORSE, meters=300)
        no_record, info_none = self._apply(
            self.PER_HORSE, meters=None)
        self.assertNotIn("first_corner", info_median["terms"])
        self.assertNotIn("firstCornerTrial", info_median)
        self.assertEqual(
            [r.p_win for r in at_median.runners],
            [r.p_win for r in no_record.runners])

    def test_no_record_leaves_no_marker(self):
        adjusted, info = self._apply(self.PER_HORSE, meters=None)
        self.assertNotIn("first_corner", info.get("terms") or [])
        self.assertNotIn("firstCornerTrial", info)
        self.assertEqual(info["coverage"]["first_corner"], 0)

    def test_fingerprint_counts_the_family(self):
        entry = _parsed(self.PER_HORSE, meters=100)
        counts = materials_fingerprint(entry)
        self.assertEqual(counts["first_corner"], 4)
        entry = _parsed(self.PER_HORSE, meters=None)
        counts = materials_fingerprint(entry)
        self.assertEqual(counts["first_corner"], 0)
