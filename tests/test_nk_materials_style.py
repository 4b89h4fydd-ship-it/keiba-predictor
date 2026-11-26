"""Style-term tests (2026-11-26, nk-materials-v15): the
builder's carriage of the pace page's per-horse style
classification / stretch rating, and the adapter's style
terms (style_fit / stretch).

Covered here:
  - the builder reads the pace-forecast entry's horses_extra
    block into each horse's styleClass / stretch fields
    (invalid labels and out-of-range ratings dropped, never
    guessed), counts both in fieldCoverage, and accepts a
    pace diagram saved under "positions_groups";
  - a build with no pace forecast at all records the two
    zeros as EXPLAINED (the values ride the pace file);
  - the adapter's parser carries the two fields defensively;
  - style_fit_score is the trait/forecast agreement on the
    shared closingness scale and never reads the pace label;
  - stretch_score passes the 1..3 rating through and nothing
    else;
  - both terms fire as post-integrate logit shifts when
    their material exists (style_fit even under an "M" label,
    which silences pace / pace_early — the label is not its
    input), stay inert when it does not, leave an unrated
    horse unshifted, and join the materials fingerprint.

The frozen integrated_eval is untouched; the style terms are
adapter-level post-integrate logit shifts (see
rewrite/analysis/nk_materials.py).
"""
from __future__ import annotations

from unittest import TestCase

from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.nk_materials import (
    NK_STYLE_LABEL, NK_STYLE_TRIAL, apply_nk_materials,
    materials_fingerprint, parse_materials_payload,
    stretch_score, style_fit_score)
from scripts.arvexq_nk_materials_build import build as build_materials

NK_ID = "202642112603"
RACE_ID = "nar-2026-11-26-浦和-03"
DATE = "2026-11-26"
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}
STRENGTHS = {1: 0.30, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.10}

TARGETS = {"targets": [{"netkeiba_race_id": NK_ID,
                        "arvexq_race_id": RACE_ID}]}
SPEED = {"races": {NK_ID: {"horses": {
    str(n): {"name": NAMES[n], "nk_best": 65, "nk_avg5": 60,
             "nk_dist": None, "nk_course": None,
             "nk_recent": [55, 54, 53]}
    for n in NAMES}}}}


def _forecast() -> RaceForecast:
    runners = [RunnerForecast(
        number=n, name=NAMES[n], ability_score=0.5, strength=s,
        pace_adjustment=1.0, pace_reasons=(), p_win=s, p_top2=None,
        p_top3=None, mark="", status="scored")
        for n, s in STRENGTHS.items()]
    return RaceForecast(RACE_ID, 3.0, "calibrated",
                        tuple(runners), "ok")


def _parsed(per_horse, pace_label=None):
    payload = {"version": "nk-materials-v13", "date": DATE,
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


def _pace(pct):
    return {"start": {"rank": 1, "pct": pct},
            "corner3": {"rank": 1, "pct": pct},
            "corner4": {"rank": 1, "pct": pct}}


class BuilderStyleCarriageTests(TestCase):
    PACE = {"races": {NK_ID: {
        "pace_ai": "H",
        "positions": {"start": [1, 2, 3, 4, 5],
                      "c3": [1, 2, 3, 4, 5],
                      "c4": [1, 2, 3, 4, 5]},
        "horses_extra": {
            "1": {"name": NAMES[1], "style_class": "逃げ",
                  "stretch": 3},
            "2": {"name": NAMES[2], "style_class": "先行",
                  "stretch": 2},
            "3": {"name": NAMES[3], "style_class": "差し",
                  "stretch": None},
            "4": {"name": NAMES[4], "style_class": "追込",
                  "stretch": 1},
            "5": {"name": NAMES[5], "style_class": "自在",
                  "stretch": 9}}}}}

    def test_style_and_stretch_carried_from_horses_extra(self):
        payload = build_materials(
            DATE, SPEED, {}, TARGETS, pace_forecast=self.PACE)
        horses = payload["races"][RACE_ID]["horses"]
        self.assertEqual(horses["1"]["styleClass"], "逃げ")
        self.assertEqual(horses["1"]["stretch"], 3)
        self.assertEqual(horses["2"]["styleClass"], "先行")
        self.assertEqual(horses["2"]["stretch"], 2)
        self.assertEqual(horses["3"]["styleClass"], "差し")
        self.assertIsNone(horses["3"]["stretch"])
        self.assertEqual(horses["4"]["styleClass"], "追込")
        self.assertEqual(horses["4"]["stretch"], 1)
        # An unknown label and an out-of-range rating are
        # dropped, never guessed.
        self.assertIsNone(horses["5"]["styleClass"])
        self.assertIsNone(horses["5"]["stretch"])
        cov = payload["fieldCoverage"]
        self.assertEqual(cov["styleClass"], 4)
        self.assertEqual(cov["stretch"], 3)
        self.assertNotIn("styleClass", payload["zeroCoverage"])
        self.assertNotIn("stretch", payload["zeroCoverage"])

    def test_positions_groups_diagram_is_accepted(self):
        pace = {"races": {NK_ID: {
            "pace_ai": "H",
            "positions_groups": {
                "start": [[1, 2], [3, 4, 5]],
                "c3": [[1, 2], [3, 4, 5]],
                "c4": [[5, 4], [3, 2, 1]]},
            "horses_extra": {
                str(n): {"style_class": "差し", "stretch": 2}
                for n in NAMES}}}}
        payload = build_materials(
            DATE, SPEED, {}, TARGETS, pace_forecast=pace)
        horses = payload["races"][RACE_ID]["horses"]
        for n in NAMES:
            self.assertIsNotNone(horses[str(n)]["pace"])
        self.assertEqual(
            horses["5"]["pace"]["corner4"]["rank"], 1)
        self.assertEqual(payload["fieldCoverage"]["pace"], 5)
        self.assertEqual(
            payload["fieldCoverage"]["styleClass"], 5)

    def test_no_pace_forecast_zero_is_explained(self):
        payload = build_materials(DATE, SPEED, {}, TARGETS)
        self.assertIn("styleClass", payload["zeroCoverage"])
        self.assertIn("stretch", payload["zeroCoverage"])
        explained = payload["zeroCoverageExplained"]
        self.assertIn("styleClass", explained)
        self.assertIn("stretch", explained)
        self.assertNotIn("styleClass",
                         payload["zeroCoverageUnexplained"])
        self.assertNotIn("stretch",
                         payload["zeroCoverageUnexplained"])


class StyleScoreTests(TestCase):
    def test_style_fit_rewards_trait_forecast_agreement(self):
        # A front trait forecast to run at the front agrees.
        self.assertAlmostEqual(
            style_fit_score("逃げ", _pace(0.1)), 0.9)
        # A closer forecast to be dragged to the front does
        # not.
        self.assertAlmostEqual(
            style_fit_score("追込", _pace(0.1)), 0.1)
        # A 差し trait forecast mid-field (closingness 0)
        # sits 1/3 away on the shared scale.
        self.assertAlmostEqual(
            style_fit_score("差し", _pace(0.5)), 1.0 - 1.0 / 6.0)
        # A closer forecast to close agrees fully at the
        # scale's own end.
        self.assertAlmostEqual(
            style_fit_score("追込", _pace(1.0)), 1.0)

    def test_style_fit_needs_style_and_positions(self):
        self.assertIsNone(style_fit_score(None, _pace(0.5)))
        self.assertIsNone(style_fit_score("自在", _pace(0.5)))
        self.assertIsNone(style_fit_score("先行", None))
        self.assertIsNone(style_fit_score("先行", {}))

    def test_stretch_score_passes_the_rating_through(self):
        self.assertEqual(stretch_score(3), 3.0)
        self.assertEqual(stretch_score(2), 2.0)
        self.assertEqual(stretch_score(1), 1.0)
        self.assertIsNone(stretch_score(0))
        self.assertIsNone(stretch_score(4))
        self.assertIsNone(stretch_score(None))
        self.assertIsNone(stretch_score("2"))


class StyleParseTests(TestCase):
    def test_parse_carries_valid_fields_and_drops_invalid(self):
        entry = _parsed({
            1: {"styleClass": "逃げ", "stretch": 3},
            2: {"styleClass": "自在", "stretch": 7},
            3: {"styleClass": "差し", "stretch": None},
        })
        horses = entry["horses"]
        self.assertEqual(horses[1]["styleClass"], "逃げ")
        self.assertEqual(horses[1]["stretch"], 3)
        self.assertIsNone(horses[2]["styleClass"])
        self.assertIsNone(horses[2]["stretch"])
        self.assertEqual(horses[3]["styleClass"], "差し")
        self.assertIsNone(horses[3]["stretch"])


class StyleTermTests(TestCase):
    def _apply(self, per_horse, pace_label=None):
        entry = _parsed(per_horse, pace_label=pace_label)
        return apply_nk_materials(_forecast(), entry)

    def test_style_fit_fires_without_a_directional_label(self):
        # Label "M" silences pace / pace_early (they price
        # position x label); style_fit never reads the label
        # and still fires on the trait/forecast agreement.
        per_horse = {
            1: {"styleClass": "先行", "pace": _pace(0.1)},
            2: {"styleClass": "追込", "pace": _pace(0.1)},
            3: {"styleClass": "差し", "pace": _pace(0.9)},
            4: {"styleClass": "逃げ", "pace": _pace(0.9)},
            5: {"styleClass": "先行", "pace": _pace(0.5)},
        }
        adjusted, info = self._apply(per_horse, pace_label="M")
        self.assertTrue(info["applied"])
        self.assertIn("style_fit", info["terms"])
        self.assertNotIn("pace_early", info["terms"])
        self.assertEqual(info["styleTrial"], NK_STYLE_TRIAL)
        self.assertIn(NK_STYLE_LABEL, info["weights"])
        self.assertEqual(info["coverage"]["style_fit"], 5)
        moved = {r.number: r.p_win for r in adjusted.runners}
        origin = {r.number: r.p_win for r in _forecast().runners}
        # The best agreement (horse 5, then 1/3) gains on the
        # worst (horse 4: a front trait forecast to close).
        self.assertGreater(moved[5] / origin[5],
                           moved[4] / origin[4])
        self.assertGreater(moved[1] / origin[1],
                           moved[2] / origin[2])

    def test_stretch_fires_and_unrated_horse_is_unshifted(self):
        per_horse = {
            1: {"stretch": 3},
            2: {"stretch": 1},
            3: {"stretch": 2},
            4: {},
            5: {"stretch": 2},
        }
        adjusted, info = self._apply(per_horse)
        self.assertTrue(info["applied"])
        self.assertIn("stretch", info["terms"])
        self.assertEqual(info["styleTrial"], NK_STYLE_TRIAL)
        self.assertEqual(info["coverage"]["stretch"], 4)
        moved = {r.number: r.p_win for r in adjusted.runners}
        origin = {r.number: r.p_win for r in _forecast().runners}
        # The strongest stretch gains on the weakest.
        self.assertGreater(moved[1] / origin[1],
                           moved[2] / origin[2])
        # Horse 4 (no rating) and horse 5 (rating 2, the
        # field's mean — a zero z-score) are both unshifted:
        # their probabilities move only by the shared
        # renormalisation, so their ratios agree (to the
        # 4-decimal rounding of the published p_win; a
        # shifted horse's ratio differs by ~0.3).
        self.assertAlmostEqual(moved[4] / origin[4],
                               moved[5] / origin[5], places=2)

    def test_no_style_material_leaves_no_marker(self):
        adjusted, info = self._apply({n: {} for n in NAMES})
        self.assertNotIn("style_fit", info.get("terms") or [])
        self.assertNotIn("stretch", info.get("terms") or [])
        self.assertNotIn("styleTrial", info)

    def test_flat_style_scores_leave_no_marker(self):
        per_horse = {n: {"styleClass": "差し", "pace": _pace(0.5),
                         "stretch": 2}
                     for n in NAMES}
        adjusted, info = self._apply(per_horse, pace_label="M")
        self.assertNotIn("style_fit", info.get("terms") or [])
        self.assertNotIn("stretch", info.get("terms") or [])
        self.assertNotIn("styleTrial", info)

    def test_fingerprint_counts_style_families(self):
        entry = _parsed({
            1: {"styleClass": "逃げ", "pace": _pace(0.2),
                "stretch": 3},
            2: {"styleClass": "差し", "pace": _pace(0.8)},
            3: {"stretch": 1},
        })
        counts = materials_fingerprint(entry)
        self.assertEqual(counts["style_fit"], 2)
        self.assertEqual(counts["stretch"], 2)
