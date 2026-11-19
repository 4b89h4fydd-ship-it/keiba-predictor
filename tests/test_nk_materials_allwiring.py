"""All-wiring tests (2026-11-19): the audit-driven wiring that
closes the "collected but never reaching the forecast" gaps.

Covered here:
  - the builder's --horse-analysis input (each horse's netkeiba
    data-analysis judgements: overall grade + section marks)
    and the adapter's horse-analysis trial term;
  - the builder's acceptance of the 2026-11-19 odds list shape
    (forecast / actual / actual_zero kinds) with provenance
    intact — forecast odds are carried as forecastWin and are
    never promoted to the actual-odds cells, so the
    odds-movement terms keep their definitions;
  - the builder's --course-persons sire-row fallback for
    pedigree.sireCourse (the full sire table wins when both
    exist);
  - the builder's zeroCoverage record: expected fields at 0
    are named in the output, never silently zero.

The frozen integrated_eval is untouched by all of this; the
horse-analysis term is an adapter-level post-integrate logit
shift (see rewrite/analysis/nk_materials.py).
"""
from __future__ import annotations

from unittest import TestCase

from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.nk_materials import (
    NK_COURSE_PERSONS_LABEL, NK_COURSE_PERSONS_TRIAL,
    NK_HORSE_ANALYSIS_LABEL, NK_HORSE_ANALYSIS_TRIAL,
    apply_nk_materials, horse_analysis_score, person_course_score,
    parse_materials_payload)
from scripts.arvexq_nk_materials_build import build as build_materials

NK_ID = "202646111701"
RACE_ID = "nar-2026-11-17-金沢-01"
DATE = "2026-11-17"
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}
STRENGTHS = {1: 0.30, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.10}

TARGETS = {"targets": [{"netkeiba_race_id": NK_ID,
                        "arvexq_race_id": RACE_ID}]}
SPEED = {"races": {NK_ID: {"horses": {
    str(n): {"nk_best": 65, "nk_avg5": 60, "nk_dist": None,
             "nk_course": None, "nk_recent": [55, 54, 53]}
    for n in NAMES}}}}


def _build(**kwargs):
    return build_materials(DATE, SPEED, {}, TARGETS, **kwargs)


def _forecast() -> RaceForecast:
    runners = [RunnerForecast(
        number=n, name=NAMES[n], ability_score=0.5, strength=s,
        pace_adjustment=1.0, pace_reasons=(), p_win=s, p_top2=None,
        p_top3=None, mark="", status="scored")
        for n, s in STRENGTHS.items()]
    return RaceForecast(RACE_ID, 3.0, "calibrated",
                        tuple(runners), "ok")


def _parsed(per_horse, avg5=60):
    payload = {"version": "nk-materials-v12", "date": DATE,
               "races": {RACE_ID: {
                   "netkeibaRaceId": NK_ID,
                   "horses": {str(n): dict(
                       {"nk_best": None, "nk_avg5": avg5,
                        "nk_dist": None, "nk_course": None,
                        "nk_recent": None},
                       **per_horse.get(n, {}))
                       for n in NAMES},
                   "courseAnalysis": None}}}
    return parse_materials_payload(payload)[RACE_ID]


class HorseAnalysisBuilderTests(TestCase):
    def test_judgements_carried_sections_only(self):
        analysis = {"races": {NK_ID: {"horses": {
            "1": {"馬名": "アアア", "総合評価": "A",
                  "コース": {"判定": "△", "全ダ実績": {"勝率": "47%"}},
                  "距離": {"判定": "○"}},
            "2": {"総合評価": "C", "コース": {"判定": "×"}},
            # No 総合評価 and no 判定 anywhere: no block.
            "3": {"コース": {"勝率": "50%"}},
        }}}}
        payload = _build(horse_analysis=analysis)
        horses = payload["races"][RACE_ID]["horses"]
        self.assertEqual(horses["1"]["horseAnalysis"], {
            "overall": "A",
            "sections": {"コース": "△", "距離": "○"}})
        self.assertEqual(horses["2"]["horseAnalysis"], {
            "overall": "C", "sections": {"コース": "×"}})
        self.assertIsNone(horses["3"]["horseAnalysis"])
        self.assertIsNone(horses["4"]["horseAnalysis"])
        self.assertEqual(payload["fieldCoverage"]["horseAnalysis"], 2)
        self.assertNotIn("horseAnalysis", payload["zeroCoverage"])

    def test_without_input_field_is_null_and_zero_is_named(self):
        payload = _build()
        horse = payload["races"][RACE_ID]["horses"]["1"]
        self.assertIsNone(horse["horseAnalysis"])
        self.assertEqual(payload["fieldCoverage"]["horseAnalysis"], 0)
        self.assertIn("horseAnalysis", payload["zeroCoverage"])


class OddsShapeBuilderTests(TestCase):
    def test_forecast_list_shape_carried_under_its_own_name(self):
        odds = {"races": {NK_ID: {"kind": "forecast", "horses": [
            {"no": 1, "name": "アアア", "win_odds": 1.7,
             "place_min": None, "place_max": None},
            {"no": 2, "name": "イイイ", "win_odds": 3.0,
             "place_min": None, "place_max": None},
            # A 0.0 line is "not published", never an odds value.
            {"no": 3, "name": "ウウウ", "win_odds": 0.0,
             "place_min": None, "place_max": None},
        ]}}}
        payload = _build(odds=odds)
        horses = payload["races"][RACE_ID]["horses"]
        self.assertEqual(horses["1"]["odds"], {
            "publishWin": None, "finalWin": None, "placeLow": None,
            "placeHigh": None, "forecastWin": 1.7})
        self.assertIsNone(horses["3"]["odds"])
        cov = payload["fieldCoverage"]
        self.assertEqual(cov["oddsForecast"], 2)
        # Yesterday's definitions cannot be met by a forecast
        # file: no drift, no win/place gap — and both are named
        # as zero rather than silently absent.
        self.assertEqual(cov["oddsDrift"], 0)
        self.assertEqual(cov["oddsWpGap"], 0)
        self.assertIn("oddsWpGap", payload["zeroCoverage"])
        self.assertNotIn("oddsForecast", payload["zeroCoverage"])

    def test_actual_list_shape_fills_the_actual_cells(self):
        odds = {"races": {NK_ID: {"kind": "actual", "horses": [
            {"no": 1, "name": "アアア", "win_odds": 2.2,
             "place_min": 1.3, "place_max": 1.6},
            {"no": 2, "name": "イイイ", "win_odds": 65.0,
             "place_min": 6.0, "place_max": 9.2},
        ]}}}
        payload = _build(odds=odds)
        horses = payload["races"][RACE_ID]["horses"]
        self.assertEqual(horses["1"]["odds"], {
            "publishWin": None, "finalWin": 2.2, "placeLow": 1.3,
            "placeHigh": 1.6})
        cov = payload["fieldCoverage"]
        self.assertEqual(cov["oddsWpGap"], 2)
        self.assertEqual(cov["oddsForecast"], 0)

    def test_actual_zero_shape_carries_nothing(self):
        odds = {"races": {NK_ID: {"kind": "actual_zero", "horses": [
            {"no": 1, "name": "アアア", "win_odds": 0.0,
             "place_min": 0.0, "place_max": 0.0},
        ]}}}
        payload = _build(odds=odds)
        horses = payload["races"][RACE_ID]["horses"]
        self.assertIsNone(horses["1"]["odds"])
        self.assertEqual(payload["fieldCoverage"]["oddsForecast"], 0)

    def test_unlabelled_list_shape_is_never_promoted(self):
        odds = {"races": {NK_ID: {"horses": [
            {"no": 1, "name": "アアア", "win_odds": 2.2,
             "place_min": 1.3, "place_max": 1.6},
        ]}}}
        payload = _build(odds=odds)
        block = payload["races"][RACE_ID]["horses"]["1"]["odds"]
        self.assertIsNone(block["finalWin"])
        self.assertEqual(block["forecastWin"], 2.2)
        self.assertEqual(payload["fieldCoverage"]["oddsWpGap"], 0)


class PersonsSireFallbackTests(TestCase):
    PERSONS = {"races": {NK_ID: {"sires": [
        {"no": 1, "name": "サトノアラジン", "horse": "アアア",
         "finishes": {"1st": 18, "2nd": 20, "3rd": 13,
                      "4th_or_lower": 110},
         "starts": 161}]}}}

    def test_persons_row_fills_sire_course_without_profiles(self):
        payload = _build(course_persons=self.PERSONS)
        horses = payload["races"][RACE_ID]["horses"]
        self.assertEqual(horses["1"]["pedigree"], {
            "sire": "サトノアラジン", "dam": None, "damSire": None,
            "sireCourse": {"starts": 161, "wins": 18, "top3": 51,
                           "winRate": round(18 / 161, 4)},
            "siblings": None})
        self.assertIsNone(horses["2"]["pedigree"])
        self.assertEqual(payload["fieldCoverage"]["sireCourse"], 1)

    def test_full_sire_table_wins_over_persons_row(self):
        course = {NK_ID: {"得意な種牡馬": {
            "見出し": ["種牡馬", "1着", "2着", "3着", "4着以下", "出走回数"],
            "行": [["サトノアラジン", 30, 20, 10, 140, 200]]}}}
        profiles = {"horses": {"h1": {
            "name": "アアア", "sire": "サトノアラジン",
            "dam": "ダム", "damSire": "ダムサイア", "siblings": []}}}
        details = {RACE_ID: {
            "id": RACE_ID, "track": "金沢", "surface": "ダート",
            "distance": 1500,
            "horses": [{"horseNumber": n, "name": NAMES[n],
                        "allPastRuns": [], "recentRaces": []}
                       for n in NAMES]}}
        payload = build_materials(
            DATE, SPEED, course, TARGETS, race_details=details,
            horse_profiles=profiles, course_persons=self.PERSONS)
        pedigree = payload["races"][RACE_ID]["horses"]["1"]["pedigree"]
        self.assertEqual(pedigree["sireCourse"], {
            "starts": 200, "wins": 30, "top3": 60, "winRate": 0.15})


class ZeroCoverageTests(TestCase):
    def test_zero_fields_are_named_and_nonzero_are_not(self):
        payload = _build()
        zero = payload["zeroCoverage"]
        for field in ("nkFormDev", "nkAiScore", "oddsDrift",
                      "oddsWpGap", "oddsForecast", "horseAnalysis",
                      "courseJockey", "courseTrainer",
                      "bestTime", "headToHead", "pedigree",
                      "sireCourse", "pace"):
            self.assertIn(field, zero)
        for field in ("horses", "speed", "speedDev"):
            self.assertNotIn(field, zero)


class HorseAnalysisScoreTests(TestCase):
    def test_score_is_the_mean_of_saved_components(self):
        block = {"overall": "A",
                 "sections": {"コース": "△", "距離": "○"}}
        self.assertAlmostEqual(
            horse_analysis_score(block), (0.8 + 0.25 + 0.75) / 3)

    def test_unknown_symbols_are_ignored_not_guessed(self):
        self.assertIsNone(horse_analysis_score(
            {"overall": "不明", "sections": {"コース": "?"}}))
        self.assertIsNone(horse_analysis_score(None))
        self.assertIsNone(horse_analysis_score({}))
        self.assertEqual(horse_analysis_score(
            {"overall": None, "sections": {"枠順": "◎"}}), 1.0)

    def test_parse_carries_block_and_drops_malformed(self):
        entry = _parsed({
            1: {"horseAnalysis": {"overall": "A",
                                   "sections": {"コース": "△"}}},
            2: {"horseAnalysis": "not-a-dict"}})
        self.assertEqual(entry["horses"][1]["horseAnalysis"],
                         {"overall": "A", "sections": {"コース": "△"}})
        self.assertIsNone(entry["horses"][2]["horseAnalysis"])


class HorseAnalysisAdapterTests(TestCase):
    BLOCKS = {
        1: {"overall": "D", "sections": {"コース": "×"}},
        2: {"overall": "C", "sections": {"コース": "△"}},
        3: {"overall": "B", "sections": {"コース": "▲"}},
        4: {"overall": "B", "sections": {"コース": "○"}},
        5: {"overall": "A", "sections": {"コース": "◎"}},
    }

    def test_term_fires_and_moves_probabilities(self):
        entry = _parsed({n: {"horseAnalysis": b}
                         for n, b in self.BLOCKS.items()})
        adjusted, info = apply_nk_materials(_forecast(), entry, None)
        self.assertTrue(info["applied"])
        self.assertIn("horse_analysis", info["terms"])
        self.assertEqual(info["horseAnalysisTrial"],
                         NK_HORSE_ANALYSIS_TRIAL)
        self.assertIn(NK_HORSE_ANALYSIS_LABEL, info["weights"])
        self.assertEqual(info["coverage"]["horse_analysis"], 5)
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[5].p_win, STRENGTHS[5])
        self.assertLess(by_number[1].p_win, STRENGTHS[1])

    def test_term_alone_applies_the_adjustment(self):
        # No integrated term can stand (every index null), yet
        # the horse-analysis term must still apply — the old
        # "no terms, no adjustment" gate must not swallow it.
        entry = _parsed({n: {"horseAnalysis": b}
                         for n, b in self.BLOCKS.items()},
                        avg5=None)
        adjusted, info = apply_nk_materials(_forecast(), entry, None)
        self.assertTrue(info["applied"])
        self.assertEqual(info["terms"], ["horse_analysis"])
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[5].p_win, STRENGTHS[5])

    def test_flat_scores_leave_no_marker(self):
        block = {"overall": "B", "sections": {"コース": "▲"}}
        entry = _parsed({n: {"horseAnalysis": block} for n in NAMES})
        _, info = apply_nk_materials(_forecast(), entry, None)
        self.assertNotIn("horseAnalysisTrial", info)
        self.assertNotIn("horse_analysis", info.get("terms") or [])

    def test_fewer_than_three_scores_leave_no_marker(self):
        entry = _parsed({n: {"horseAnalysis": self.BLOCKS[n]}
                         for n in (1, 5)})
        _, info = apply_nk_materials(_forecast(), entry, None)
        self.assertNotIn("horseAnalysisTrial", info)
        self.assertEqual(info["coverage"]["horse_analysis"], 2)


def _person_row(no, name, first, second, third, starts):
    return {"no": no, "name": name, "horse": NAMES[no],
            "finishes": {"1st": first, "2nd": second, "3rd": third,
                         "4th_or_lower": starts - first - second
                         - third},
            "starts": starts}


class CoursePersonsBuilderTests(TestCase):
    PERSONS = {"races": {NK_ID: {
        "jockeys": [_person_row(1, "騎手甲", 19, 40, 49, 674),
                    _person_row(2, "騎手乙", 270, 208, 225, 1738)],
        "trainers": [_person_row(1, "調教師甲", 30, 20, 10, 200)]}}}

    def test_rows_carried_as_course_records(self):
        payload = _build(course_persons=self.PERSONS)
        horses = payload["races"][RACE_ID]["horses"]
        self.assertEqual(horses["1"]["coursePersons"], {
            "jockey": {"name": "騎手甲", "starts": 674, "wins": 19,
                       "top3": 108, "winRate": round(19 / 674, 4)},
            "trainer": {"name": "調教師甲", "starts": 200,
                        "wins": 30, "top3": 60, "winRate": 0.15}})
        self.assertEqual(horses["2"]["coursePersons"], {
            "jockey": {"name": "騎手乙", "starts": 1738, "wins": 270,
                       "top3": 703,
                       "winRate": round(270 / 1738, 4)}})
        self.assertIsNone(horses["3"]["coursePersons"])
        cov = payload["fieldCoverage"]
        self.assertEqual(cov["courseJockey"], 2)
        self.assertEqual(cov["courseTrainer"], 1)
        self.assertNotIn("courseJockey", payload["zeroCoverage"])
        self.assertNotIn("courseTrainer", payload["zeroCoverage"])

    def test_course_analysis_rows_are_a_second_source(self):
        course = {NK_ID: {"jockeys": [
            _person_row(3, "騎手丙", 10, 10, 10, 100)]}}
        payload = build_materials(DATE, SPEED, course, TARGETS)
        block = payload["races"][RACE_ID]["horses"]["3"][
            "coursePersons"]
        self.assertEqual(block["jockey"]["name"], "騎手丙")
        self.assertEqual(payload["fieldCoverage"]["courseJockey"], 1)

    def test_persons_file_wins_over_course_analysis(self):
        course = {NK_ID: {"jockeys": [
            _person_row(1, "別人", 1, 1, 1, 10)]}}
        payload = build_materials(
            DATE, SPEED, course, TARGETS,
            course_persons=self.PERSONS)
        block = payload["races"][RACE_ID]["horses"]["1"][
            "coursePersons"]
        self.assertEqual(block["jockey"]["name"], "騎手甲")

    def test_unreadable_rows_are_dropped_never_repaired(self):
        persons = {"races": {NK_ID: {"jockeys": [
            {"no": 1, "name": "壊", "finishes": {"2nd": 3},
             "starts": 10},
            {"no": 2, "name": "零", "finishes": {"1st": 0},
             "starts": 0}]}}}
        payload = _build(course_persons=persons)
        horses = payload["races"][RACE_ID]["horses"]
        self.assertIsNone(horses["1"]["coursePersons"])
        self.assertIsNone(horses["2"]["coursePersons"])
        self.assertEqual(payload["fieldCoverage"]["courseJockey"], 0)
        self.assertIn("courseJockey", payload["zeroCoverage"])

    def test_without_input_field_is_null_and_zero_is_named(self):
        payload = _build()
        horse = payload["races"][RACE_ID]["horses"]["1"]
        self.assertIsNone(horse["coursePersons"])
        self.assertIn("courseTrainer", payload["zeroCoverage"])


class PersonCourseScoreTests(TestCase):
    def test_score_shrinks_toward_a_generic_field(self):
        record = {"starts": 200, "wins": 30, "top3": 60}
        win = (30 + 10.0 * 0.10) / (200 + 10.0)
        top3 = (60 + 10.0 * 0.30) / (200 + 10.0)
        self.assertAlmostEqual(person_course_score(record),
                               (win + top3) / 2)

    def test_missing_or_empty_record_scores_none(self):
        self.assertIsNone(person_course_score(None))
        self.assertIsNone(person_course_score({}))
        self.assertIsNone(person_course_score(
            {"starts": 0, "wins": 0, "top3": 0}))
        self.assertIsNone(person_course_score({"starts": 10}))

    def test_parse_carries_block_and_drops_malformed(self):
        record = {"name": "騎手甲", "starts": 674, "wins": 19,
                  "top3": 108, "winRate": 0.0282}
        entry = _parsed({
            1: {"coursePersons": {"jockey": record}},
            2: {"coursePersons": "not-a-dict"}})
        self.assertEqual(entry["horses"][1]["coursePersons"],
                         {"jockey": record})
        self.assertIsNone(entry["horses"][2]["coursePersons"])


class CoursePersonsAdapterTests(TestCase):
    # Monotone jockey records: horse 1 weakest, horse 5
    # strongest; trainer records identical (flat) unless a
    # test overrides them.
    JOCKEYS = {
        1: {"starts": 500, "wins": 10, "top3": 40},
        2: {"starts": 500, "wins": 30, "top3": 90},
        3: {"starts": 500, "wins": 50, "top3": 140},
        4: {"starts": 500, "wins": 75, "top3": 200},
        5: {"starts": 500, "wins": 110, "top3": 280},
    }

    def _entry(self, jockeys=None, trainers=None):
        per_horse = {}
        for n in NAMES:
            block = {}
            if jockeys and n in jockeys:
                block["jockey"] = jockeys[n]
            if trainers and n in trainers:
                block["trainer"] = trainers[n]
            if block:
                per_horse[n] = {"coursePersons": block}
        return _parsed(per_horse)

    def test_jockey_term_fires_and_moves_probabilities(self):
        entry = self._entry(jockeys=self.JOCKEYS)
        adjusted, info = apply_nk_materials(_forecast(), entry, None)
        self.assertTrue(info["applied"])
        self.assertIn("course_jockey", info["terms"])
        self.assertNotIn("course_trainer", info["terms"])
        self.assertEqual(info["coursePersonsTrial"],
                         NK_COURSE_PERSONS_TRIAL)
        self.assertIn(NK_COURSE_PERSONS_LABEL, info["weights"])
        self.assertEqual(info["coverage"]["course_jockey"], 5)
        self.assertEqual(info["coverage"]["course_trainer"], 0)
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[5].p_win, STRENGTHS[5])
        self.assertLess(by_number[1].p_win, STRENGTHS[1])

    def test_trainer_term_alone_applies_the_adjustment(self):
        # No integrated term can stand (every index null) and
        # no jockey rows: the trainer term must still apply.
        trainers = {n: {"starts": 400, "wins": 10 * n,
                        "top3": 30 * n} for n in NAMES}
        per_horse = {n: {"coursePersons": {"trainer": trainers[n]}}
                     for n in NAMES}
        entry = _parsed(per_horse, avg5=None)
        adjusted, info = apply_nk_materials(_forecast(), entry, None)
        self.assertTrue(info["applied"])
        self.assertEqual(info["terms"], ["course_trainer"])
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[5].p_win, STRENGTHS[5])

    def test_flat_records_leave_no_marker(self):
        flat = {"starts": 500, "wins": 50, "top3": 150}
        entry = self._entry(jockeys={n: flat for n in NAMES},
                            trainers={n: flat for n in NAMES})
        _, info = apply_nk_materials(_forecast(), entry, None)
        self.assertNotIn("coursePersonsTrial", info)
        self.assertNotIn("course_jockey", info.get("terms") or [])
        self.assertNotIn("course_trainer", info.get("terms") or [])

    def test_fewer_than_three_records_leave_no_marker(self):
        entry = self._entry(
            jockeys={n: self.JOCKEYS[n] for n in (1, 5)})
        _, info = apply_nk_materials(_forecast(), entry, None)
        self.assertNotIn("coursePersonsTrial", info)
        self.assertEqual(info["coverage"]["course_jockey"], 2)


if __name__ == "__main__":
    import unittest
    unittest.main()
