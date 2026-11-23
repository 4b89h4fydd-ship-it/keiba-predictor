"""Full-coverage tests (2026-11-23, nk-materials-v14): the
builder's details-independent joins and the adapter's
full-coverage trial terms.

Covered here:
  - the builder assigns pedigree (and sireCourse from the
    course-analysis full sire table, and the siblings block)
    from the horse profiles joined on the entered horses'
    names — WITHOUT any race-details input (until v14 the
    assignment lived only inside the details runners loop, so
    a details-less day produced pedigree = 0 with the profiles
    on file);
  - the builder fills coursePersons jockey / trainer records
    from the course-analysis FULL tables （得意な騎手 /
    得意な調教師） joined on the entered horse's jockey /
    trainer names (race-entries input or details runners),
    with collected per-horse rows winning over the table join;
  - the adapter's five full-coverage terms (nk_best /
    siblings / press_rating / pace_early / odds_forecast)
    fire and move probabilities when their material exists,
    stay inert when it does not, and join the materials
    fingerprint.

The frozen integrated_eval is untouched; the five terms are
adapter-level post-integrate logit shifts (see
rewrite/analysis/nk_materials.py).
"""
from __future__ import annotations

from unittest import TestCase

from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.nk_materials import (
    NK_FULL_COVERAGE_LABEL, NK_FULL_COVERAGE_TRIAL,
    apply_nk_materials, materials_fingerprint, nk_best_score,
    odds_forecast_score, pace_early_score,
    parse_materials_payload, siblings_score)
from scripts.arvexq_nk_materials_build import build as build_materials

NK_ID = "202603030601"
RACE_ID = "jra-2026-11-23-福島-01"
DATE = "2026-11-23"
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}
STRENGTHS = {1: 0.30, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.10}

TARGETS = {"targets": [{"netkeiba_race_id": NK_ID,
                        "arvexq_race_id": RACE_ID}]}
SPEED = {"races": {NK_ID: {"horses": {
    str(n): {"name": NAMES[n], "nk_best": 65, "nk_avg5": 60,
             "nk_dist": None, "nk_course": None,
             "nk_recent": [55, 54, 53]}
    for n in NAMES}}}}
COURSE = {NK_ID: {
    "得意な種牡馬": {"行": [["チチチ", 3, 2, 1, 4, 10, 30, 50, 60]]},
    "得意な騎手": {"行": [["騎手甲", 4, 2, 1, 3, 10, 40, 60, 70]]},
    "得意な調教師": {"行": [["調教師乙", 2, 1, 1, 6, 10, 20, 30, 40]]},
}}
PROFILES = {"horses": {
    f"id{n}": {"name": NAMES[n], "sire": "チチチ", "dam": "ハハハ",
               "damSire": "ジジジ",
               "siblings": [{"name": "キョウダイ", "wins": 3}]}
    for n in NAMES}}
ENTRIES = {"races": {NK_ID: {"horses": {
    str(n): {"name": NAMES[n], "jockey": "騎手甲",
             "trainer": "調教師乙"} for n in NAMES}}}}


def _forecast() -> RaceForecast:
    runners = [RunnerForecast(
        number=n, name=NAMES[n], ability_score=0.5, strength=s,
        pace_adjustment=1.0, pace_reasons=(), p_win=s, p_top2=None,
        p_top3=None, mark="", status="scored")
        for n, s in STRENGTHS.items()]
    return RaceForecast(RACE_ID, 3.0, "calibrated",
                        tuple(runners), "ok")


def _parsed(per_horse, pace_label=None):
    payload = {"version": "nk-materials-v12", "date": DATE,
               "races": {RACE_ID: {
                   "netkeibaRaceId": NK_ID,
                   "horses": {str(n): dict(
                       {"nk_best": None, "nk_avg5": 60,
                        "nk_dist": None, "nk_course": None,
                        "nk_recent": None},
                       **per_horse.get(n, {}))
                       for n in NAMES},
                   "courseAnalysis": None,
                   "paceLabel": pace_label}}}
    return parse_materials_payload(payload)[RACE_ID]


class DetailsIndependentBuilderTests(TestCase):
    def test_pedigree_without_race_details(self):
        payload = build_materials(
            DATE, SPEED, COURSE, TARGETS, horse_profiles=PROFILES)
        horses = payload["races"][RACE_ID]["horses"]
        for n in NAMES:
            ped = horses[str(n)]["pedigree"]
            self.assertIsNotNone(ped)
            self.assertEqual(ped["sire"], "チチチ")
            self.assertEqual(ped["sireCourse"], {
                "starts": 10, "wins": 3, "top3": 6,
                "winRate": 0.3})
            self.assertEqual(ped["siblings"],
                             {"count": 1, "wins": 3})
        cov = payload["fieldCoverage"]
        self.assertEqual(cov["pedigree"], 5)
        self.assertEqual(cov["sireCourse"], 5)
        self.assertEqual(cov["siblings"], 5)
        self.assertNotIn("pedigree", payload["zeroCoverage"])

    def test_course_persons_from_full_tables_via_entries(self):
        payload = build_materials(
            DATE, SPEED, COURSE, TARGETS, race_entries=ENTRIES)
        horses = payload["races"][RACE_ID]["horses"]
        for n in NAMES:
            block = horses[str(n)]["coursePersons"]
            self.assertEqual(block["jockey"], {
                "name": "騎手甲", "starts": 10, "wins": 4,
                "top3": 7, "winRate": 0.4})
            self.assertEqual(block["trainer"], {
                "name": "調教師乙", "starts": 10, "wins": 2,
                "top3": 4, "winRate": 0.2})
        cov = payload["fieldCoverage"]
        self.assertEqual(cov["courseJockey"], 5)
        self.assertEqual(cov["courseTrainer"], 5)

    def test_person_absent_from_table_carries_no_record(self):
        entries = {"races": {NK_ID: {"horses": {
            str(n): {"name": NAMES[n], "jockey": "無名騎手",
                     "trainer": "無名調教師"} for n in NAMES}}}}
        payload = build_materials(
            DATE, SPEED, COURSE, TARGETS, race_entries=entries)
        horses = payload["races"][RACE_ID]["horses"]
        for n in NAMES:
            self.assertIsNone(horses[str(n)]["coursePersons"])
        self.assertIn("courseJockey", payload["zeroCoverage"])
        self.assertIn("courseTrainer", payload["zeroCoverage"])

    def test_collected_persons_row_wins_over_table_join(self):
        persons = {"races": {NK_ID: {
            "jockeys": [{"no": 1, "name": "騎手甲",
                         "finishes": {"1st": 9, "2nd": 0, "3rd": 0},
                         "starts": 9}],
            "trainers": [], "sires": []}}}
        payload = build_materials(
            DATE, SPEED, COURSE, TARGETS, race_entries=ENTRIES,
            course_persons=persons)
        block = payload["races"][RACE_ID]["horses"]["1"][
            "coursePersons"]
        # The collected row's record (9 starts) wins for horse 1;
        # its trainer still comes from the table join.
        self.assertEqual(block["jockey"]["starts"], 9)
        self.assertEqual(block["trainer"]["starts"], 10)


class FullCoverageScoreTests(TestCase):
    def test_nk_best_score_is_last_minus_best(self):
        self.assertEqual(nk_best_score(
            {"nk_best": 65, "nk_recent": [55, None, 60]}), -5)
        self.assertIsNone(nk_best_score(
            {"nk_best": None, "nk_recent": [55]}))
        self.assertIsNone(nk_best_score(
            {"nk_best": 65, "nk_recent": [None]}))

    def test_siblings_score_shrinks_toward_one(self):
        self.assertAlmostEqual(
            siblings_score({"siblings": {"count": 1, "wins": 3}}),
            (3 + 2.0) / 3.0)
        self.assertIsNone(siblings_score({"siblings": None}))
        self.assertIsNone(siblings_score(
            {"siblings": {"count": 0, "wins": 0}}))
        self.assertIsNone(siblings_score(None))

    def test_pace_early_score_uses_start_and_corner3(self):
        pace = {"start": {"rank": 1, "pct": 0.1},
                "corner3": {"rank": 2, "pct": 0.3},
                "corner4": {"rank": 5, "pct": 0.9}}
        self.assertAlmostEqual(
            pace_early_score(pace, "H"), (0.2 - 0.5) * 2.0)
        self.assertIsNone(pace_early_score(pace, "M"))
        self.assertIsNone(pace_early_score(None, "H"))

    def test_odds_forecast_score_is_negative_log(self):
        self.assertAlmostEqual(
            odds_forecast_score({"forecastWin": 2.0}),
            -0.6931471805599453)
        self.assertIsNone(odds_forecast_score({"forecastWin": 1.0}))
        self.assertIsNone(odds_forecast_score({}))
        self.assertIsNone(odds_forecast_score(None))


class FullCoverageTermTests(TestCase):
    def _apply(self, per_horse, pace_label=None):
        entry = _parsed(per_horse, pace_label=pace_label)
        return apply_nk_materials(_forecast(), entry)

    def test_nk_best_term_fires(self):
        per_horse = {
            1: {"nk_best": 60, "nk_recent": [58, 59, 60]},
            2: {"nk_best": 70, "nk_recent": [58, 59, 60]},
            3: {"nk_best": 65, "nk_recent": [58, 59, 60]},
            4: {"nk_best": 80, "nk_recent": [58, 59, 60]},
            5: {"nk_best": 62, "nk_recent": [58, 59, 60]},
        }
        adjusted, info = self._apply(per_horse)
        self.assertTrue(info["applied"])
        self.assertIn("nk_best", info["terms"])
        self.assertEqual(info["fullCoverageTrial"],
                         NK_FULL_COVERAGE_TRIAL)
        self.assertIn(NK_FULL_COVERAGE_LABEL, info["weights"])
        self.assertEqual(info["coverage"]["nk_best"], 5)
        base = _forecast()
        moved = {r.number: r.p_win for r in adjusted.runners}
        origin = {r.number: r.p_win for r in base.runners}
        self.assertTrue(any(
            abs(moved[n] - origin[n]) > 1e-9 for n in NAMES))
        # The horse at its peak (last == best) gains on the
        # horse far below its best.
        self.assertGreater(moved[1] / origin[1],
                           moved[4] / origin[4])

    def test_siblings_term_fires(self):
        per_horse = {
            n: {"pedigree": {"sire": "チチチ", "dam": None,
                             "damSire": None, "sireCourse": None,
                             "siblings": {"count": 2, "wins": w}}}
            for n, w in ((1, 6), (2, 0), (3, 2), (4, 1), (5, 4))}
        adjusted, info = self._apply(per_horse)
        self.assertTrue(info["applied"])
        self.assertIn("siblings", info["terms"])
        self.assertEqual(info["coverage"]["siblings"], 5)

    def test_press_rating_term_fires_when_ratings_exist(self):
        per_horse = {n: {"pressRating": r} for n, r in
                     ((1, 105.0), (2, 95.0), (3, 100.0),
                      (4, 90.0), (5, 98.0))}
        adjusted, info = self._apply(per_horse)
        self.assertTrue(info["applied"])
        self.assertIn("press_rating", info["terms"])
        self.assertEqual(info["coverage"]["press_rating"], 5)

    def test_pace_early_term_fires(self):
        def pace(pct):
            return {"start": {"rank": 1, "pct": pct},
                    "corner3": {"rank": 1, "pct": pct},
                    "corner4": {"rank": 1, "pct": pct}}
        per_horse = {n: {"pace": pace(p)} for n, p in
                     ((1, 0.1), (2, 0.9), (3, 0.5), (4, 0.3),
                      (5, 0.7))}
        adjusted, info = self._apply(per_horse, pace_label="H")
        self.assertTrue(info["applied"])
        self.assertIn("pace_early", info["terms"])
        self.assertEqual(info["coverage"]["pace_early"], 5)

    def test_odds_forecast_term_fires(self):
        per_horse = {n: {"odds": {"forecastWin": o}} for n, o in
                     ((1, 1.5), (2, 9.0), (3, 4.0), (4, 20.0),
                      (5, 6.0))}
        adjusted, info = self._apply(per_horse)
        self.assertTrue(info["applied"])
        self.assertIn("odds_forecast", info["terms"])
        self.assertEqual(info["coverage"]["odds_forecast"], 5)
        moved = {r.number: r.p_win for r in adjusted.runners}
        origin = {r.number: r.p_win for r in _forecast().runners}
        # The shortest forecast price gains the most.
        self.assertGreater(moved[1] / origin[1],
                           moved[4] / origin[4])

    def test_flat_scores_leave_no_marker(self):
        per_horse = {
            n: {"nk_best": 65, "nk_recent": [55, 54, 53]}
            for n in NAMES}
        adjusted, info = self._apply(per_horse)
        self.assertNotIn("nk_best", info.get("terms") or [])
        self.assertNotIn("fullCoverageTrial", info)

    def test_fingerprint_counts_full_coverage_families(self):
        entry = _parsed({
            1: {"nk_best": 60, "nk_recent": [58, 59, 60],
                "pedigree": {"siblings": {"count": 1, "wins": 2}},
                "pressRating": 101.0,
                "odds": {"forecastWin": 3.0}},
            2: {"nk_best": 70, "nk_recent": [58, 59, 60],
                "odds": {"forecastWin": 5.0}},
        })
        counts = materials_fingerprint(entry)
        self.assertEqual(counts["nk_best"], 2)
        self.assertEqual(counts["siblings"], 1)
        self.assertEqual(counts["press_rating"], 1)
        self.assertEqual(counts["odds_forecast"], 2)
        self.assertEqual(counts["pace_early"], 0)
