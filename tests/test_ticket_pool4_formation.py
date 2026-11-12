"""Formation P4A2 (pool4-axis2) — the NAR trifecta formation.

Adopted for NAR only by user order 2026-11-12 after the offline
threshold sweep (research branch research/r24-threshold-sweep-
20261112): on the frozen sweep corpus the pool4-axis2 subset of
R24 returned 0.662 vs R24's 0.486 (set A: 139 local test races)
and 0.800 vs 0.629 (set AB: 200 races). JRA keeps R24.

The centrepiece test re-implements the research construction
independently — the sweep script's ``race_outcomes`` for
kind="trifecta": pool = marks[:4], axis = marks[:2], combos =
every permutation of the pool tuple whose first leg is an axis
horse, cut = 0 — and pins the production formation to it for a
spread of mark orders, so the two can never drift apart silently.
"""
from itertools import permutations
from unittest import TestCase

from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.tickets import (
    TRIFECTA_FORMATIONS,
    formation_pool4_axis2_selections,
    formation_r24_selections,
    generate_tickets,
)

MARK_ORDER = [2, 1, 3, 5, 4]  # ◎ ○ ▲ △ ☆


def research_pool4_axis2(marks):
    """The sweep's construction, transcribed from
    scripts/arvexq_r24_threshold_sweep.py (race_outcomes,
    kind="trifecta", axis_n=2, pool_n=4, cut=0)."""
    pool = list(marks[:4])
    axis = set(marks[:2])
    return [combo for combo in permutations(pool, 3)
            if combo[0] in axis]


class Pool4Axis2FormationTests(TestCase):
    def test_registered(self):
        self.assertIn("P4A2", TRIFECTA_FORMATIONS)

    def test_matches_research_construction(self):
        orders = [
            MARK_ORDER,
            [1, 2, 3, 4, 5],
            [5, 4, 3, 2, 1],
            [9, 7, 12, 3, 11, 2],
            [3, 1, 4, 2],       # four marks exactly
            [8, 6, 1],          # three marks
            [4, 2],             # two marks: no trifecta at all
        ]
        for marks in orders:
            self.assertEqual(
                formation_pool4_axis2_selections(marks),
                research_pool4_axis2(marks),
                f"mark order {marks}")

    def test_twelve_points_and_star_in_no_leg(self):
        combos = formation_pool4_axis2_selections(MARK_ORDER)
        self.assertEqual(len(combos), 12)
        self.assertEqual(len(set(combos)), 12)
        star = MARK_ORDER[4]
        for combo in combos:
            self.assertIn(combo[0], MARK_ORDER[:2])
            self.assertLessEqual(set(combo), set(MARK_ORDER[:4]))
            self.assertNotIn(star, combo)

    def test_strict_subset_of_r24(self):
        pool4 = set(formation_pool4_axis2_selections(MARK_ORDER))
        r24 = set(formation_r24_selections(MARK_ORDER))
        self.assertEqual(len(r24), 24)
        self.assertTrue(pool4 < r24)
        # The 12 dropped combos are exactly the ones carrying
        # ☆ in the 2nd or 3rd leg (the win leg stays top-2).
        dropped = r24 - pool4
        self.assertEqual(len(dropped), 12)
        for combo in dropped:
            self.assertIn(combo[0], MARK_ORDER[:2])
            self.assertIn(MARK_ORDER[4], combo[1:])

    def test_four_marks_identical_to_r24(self):
        marks = MARK_ORDER[:4]
        self.assertEqual(
            set(formation_pool4_axis2_selections(marks)),
            set(formation_r24_selections(marks)))

    def test_three_marks_shrink_and_two_marks_empty(self):
        self.assertEqual(
            set(formation_pool4_axis2_selections(MARK_ORDER[:3])),
            {(2, 1, 3), (2, 3, 1), (1, 2, 3), (1, 3, 2)})
        self.assertEqual(
            formation_pool4_axis2_selections(MARK_ORDER[:2]), [])


def _forecast() -> RaceForecast:
    strengths = {2: 0.30, 1: 0.22, 3: 0.18, 5: 0.12, 4: 0.10, 6: 0.08}
    marks = {2: "◎", 1: "○", 3: "▲", 5: "△", 4: "☆"}
    runners = tuple(
        RunnerForecast(
            number=n, name=f"H{n}", ability_score=1.0, strength=s,
            pace_adjustment=0.0, pace_reasons=(), p_win=s,
            p_top2=min(1.0, 2 * s), p_top3=min(1.0, 3 * s),
            mark=marks.get(n, ""), status="scored")
        for n, s in strengths.items())
    return RaceForecast("nar-2026-11-12-テスト-01", 1.0, "ok",
                        runners, "ok")


class Pool4Axis2GenerateTicketsTests(TestCase):
    def test_generate_tickets_p4a2(self):
        plan = generate_tickets(_forecast(), {},
                                calibration_validated=False,
                                trifecta_formation="P4A2")
        got = [t.selection for t in plan.probability_tickets
               if t.kind == "trifecta"]
        self.assertEqual(set(got),
                         set(formation_pool4_axis2_selections(MARK_ORDER)))
        self.assertEqual(len(got), 12)
        star = MARK_ORDER[4]
        for selection in got:
            self.assertNotIn(star, selection)

    def test_generate_tickets_r24_shape_unchanged(self):
        # The R24 formation (the JRA path, passed explicitly by
        # the publisher) is untouched: 24 points, ☆ still
        # allowed in the 2nd/3rd legs.
        plan = generate_tickets(_forecast(), {},
                                calibration_validated=False,
                                trifecta_formation="R24")
        got = [t.selection for t in plan.probability_tickets
               if t.kind == "trifecta"]
        self.assertEqual(set(got),
                         set(formation_r24_selections(MARK_ORDER)))
        self.assertEqual(len(got), 24)
