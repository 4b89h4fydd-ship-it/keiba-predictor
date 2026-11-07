"""Research candidate invariants; production v9b is never patched."""
from dataclasses import replace
from math import fsum
from unittest import TestCase

from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.pace_market_candidate import (
    _scenario_weights, postprocess_pace_market_candidate,
)
from rewrite.analysis.shadow_v9 import postprocess_forecast
from rewrite.analysis.tickets import formation_b_selections, mark_order
from rewrite.data.normalize import normalize_race

ODDS = {1: 2., 2: 4., 3: 6., 4: 9., 5: 12.}


def sample(circuit="中央", *, no_history=False):
    horses = []
    for n in range(1, 6):
        past = [] if no_history else [
            {"date": day, "track": "東京" if circuit == "中央" else "園田",
             "fieldSize": 8, "finish": 6 - n,
             "cornerPositions": [n, n, n + 1, n + 1],
             "distance": 1600, "surface": "芝" if circuit == "中央" else "ダート"}
            for day in ("2026-10-01", "2026-10-12")
        ]
        horses.append({"horseNumber": n, "name": f"馬{n}",
                       "winOdds": ODDS[n], "recentRaces": past})
    detail = {
        "id": f"pace-{circuit}-20261107", "date": "2026-11-07",
        "circuit": circuit, "track": "東京" if circuit == "中央" else "園田",
        "title": "通常競走", "distance": 1600,
        "surface": "芝" if circuit == "中央" else "ダート",
        "horses": horses,
    }
    race = normalize_race(detail, detail, "sealed-test")
    runners = tuple(RunnerForecast(
        number=n, name=f"馬{n}", ability_score=.5,
        strength={1:.3, 2:.25, 3:.2, 4:.15, 5:.1}[n],
        pace_adjustment=1., pace_reasons=(), p_win=None, p_top2=None,
        p_top3=None, mark="", status="scored") for n in range(1, 6))
    base = RaceForecast(race.race_id, 3., "uncalibrated-prior",
                        runners, "ok")
    return race, base


class ResearchPaceMarketTests(TestCase):
    def test_exact_v9b_control_both_circuits(self):
        for circuit in ("中央", "地方"):
            race, base = sample(circuit)
            for odds in (ODDS, None, {1: 2.}):
                out, info = postprocess_pace_market_candidate(
                    race, base, win_odds=odds,
                    pace_scale=0., market_weight=.5)
                expected, _ = postprocess_forecast(
                    base, arm="v9b", win_odds=odds)
                self.assertEqual(out, expected)
                self.assertTrue(info["baselineExact"])

    def test_scenarios_change_probabilities_and_keep_b_tickets(self):
        for circuit in ("中央", "地方"):
            race, base = sample(circuit)
            base_output, _ = postprocess_pace_market_candidate(
                race, base, win_odds=ODDS,
                pace_scale=0., market_weight=.5)
            candidate, info = postprocess_pace_market_candidate(
                race, base, win_odds=ODDS,
                pace_scale=.6, market_weight=.25)
            self.assertTrue(info["paceApplied"])
            self.assertEqual(info["paceObservedRunners"], 5)
            self.assertTrue(info["blendApplied"])
            self.assertAlmostEqual(
                fsum(r.p_win for r in candidate.runners), 1., places=3)
            self.assertNotEqual(
                [r.p_win for r in candidate.runners],
                [r.p_win for r in base_output.runners])
            self.assertEqual(len(formation_b_selections(mark_order(candidate))), 36)
            self.assertEqual(
                {r.mark for r in candidate.runners},
                {"◎", "○", "▲", "△", "☆"})

    def test_missing_evidence_remains_neutral(self):
        race, base = sample(no_history=True)
        out, info = postprocess_pace_market_candidate(
            race, base, win_odds=ODDS, pace_scale=.8)
        control, _ = postprocess_forecast(
            base, arm="v9b", win_odds=ODDS)
        self.assertFalse(info["paceApplied"])
        self.assertEqual(out, control)

    def test_no_market_odds_uses_model_only(self):
        race, base = sample("地方")
        out, info = postprocess_pace_market_candidate(
            race, base, win_odds={1: 2.},
            pace_scale=.4, market_weight=.25)
        self.assertFalse(info["blendApplied"])
        self.assertTrue(info["paceApplied"])
        self.assertAlmostEqual(
            fsum(r.p_win for r in out.runners), 1., places=3)

    def test_current_race_history_is_rejected(self):
        race, base = sample()
        horse = race.runners[0]
        injected = replace(horse.past_runs[0], date=race.date)
        tampered = replace(
            race, runners=(replace(
                horse, past_runs=(injected,) + horse.past_runs[1:]),)
            + race.runners[1:])
        with self.assertRaisesRegex(ValueError, "future"):
            postprocess_pace_market_candidate(
                tampered, base, win_odds=ODDS,
                pace_scale=.2, market_weight=.25)

    def test_roster_must_match(self):
        race, base = sample()
        with self.assertRaisesRegex(ValueError, "field"):
            postprocess_pace_market_candidate(
                replace(race, runners=race.runners[:-1]), base,
                win_odds=ODDS, pace_scale=.2)

    def test_parameters_rejected(self):
        race, base = sample()
        for bad in (-.1, 1.1, float("nan"), True):
            with self.assertRaises(ValueError):
                postprocess_pace_market_candidate(
                    race, base, win_odds=ODDS, pace_scale=bad)
        with self.assertRaises(ValueError):
            postprocess_pace_market_candidate(
                race, base, win_odds=ODDS, pace_scale=.1,
                market_weight=.53)

    def test_pace_scenario_priors_are_normalised(self):
        for n in range(10):
            self.assertAlmostEqual(sum(_scenario_weights(n).values()), 1.)
