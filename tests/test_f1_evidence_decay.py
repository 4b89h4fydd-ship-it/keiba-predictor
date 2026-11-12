"""F1 evidence-decay challenger: synthetic reproduction tests.

Rebuilds the 2026-11-11 code audit's F1 reproduction (a NAR race
where a horse with ONE career start takes the race maximum on its
only three available features — form / top3_rate / rest — and is
scored 1.0 / ◎, outranking eight-start horses) and pins that the
research challenger's evidence-decay shrinkage corrects the order.

Research-only: exercises ``arvexq.research.f1_evidence_decay``
against the untouched production ``forecast_race_v8``.
"""
from __future__ import annotations

import unittest

from arvexq.research.f1_evidence_decay import (
    CANDIDATES,
    forecast_race_v8_decay,
    reliability,
)
from rewrite.analysis.shadow_v8 import forecast_race_v8
from rewrite.data.normalize import Obs, PastRun, RaceRecord, RunnerRecord, obs
from rewrite.safety.contracts import Segment


def _run(date, track, dist, surf, finish, field, title="テストレース",
         jockey="他騎手", behind=None, corners=(), cw=55.0):
    return PastRun(
        date=date, track=obs(track, "t"), distance=obs(dist, "t"),
        surface=obs(surf, "t"), finish=obs(finish, "t"),
        field_size=obs(field, "t"), corner_positions=tuple(corners),
        margin_text=obs(None, "t"), time_seconds=obs(None, "t"),
        jockey=obs(jockey, "t"), race_title=obs(title, "t"),
        condition=obs("良", "t"), weather=obs("晴", "t"),
        time_behind_winner=(obs(behind, "t") if behind is not None
                            else Obs(None, "t", "null")),
        carried_weight=obs(cw, "t"),
    )


def _runner(number, name, jockey, runs, cw=56.0):
    return RunnerRecord(
        number=number, horse_id=obs(None, "t"), name=obs(name, "t"),
        frame_number=obs(number, "t"), age=obs(4, "t"), sex=obs("牡", "t"),
        jockey=obs(jockey, "t"), trainer=obs("調教師", "t"),
        carried_weight=(obs(cw, "t") if cw is not None
                        else Obs(None, "t", "null")),
        body_weight=obs(None, "t"), body_weight_change=obs(None, "t"),
        win_odds=obs(None, "t"), scratched=False, past_runs=tuple(runs),
    )


def _vet_runs(finishes, jockey, behinds=None):
    dates = ["2026-10-18", "2026-10-04", "2026-09-20", "2026-09-06",
             "2026-08-23", "2026-08-09", "2026-07-26", "2026-07-12"]
    dists = [1400, 1400, 1300, 1400, 1500, 1400, 1300, 1400]
    titles = ["B1", "A2", "B1", "B2", "A2", "B1", "B2", "A1"]
    return [
        _run(dates[i], "佐賀", dists[i], "ダート", f, 11, title=titles[i],
             jockey=jockey, behind=(behinds[i] if behinds else 0.6),
             corners=(3, 3, 2))
        for i, f in enumerate(finishes)
    ]


def synthetic_race() -> RaceRecord:
    """6-horse NAR race: #2 has one career start (won, in alien
    context: other track / distance / surface / jockey, no corners,
    no time-behind-winner); the rest have eight full-evidence starts.
    #5 is the genuine ace (mostly podium finishes, fast times)."""
    sparse = [_run("2026-10-25", "門別", 1000, "芝", 1, 8,
                   jockey="別騎手")]
    runners = [
        _runner(1, "ベテラン1", "騎手B",
                _vet_runs([4, 5, 4, 6, 5, 4, 6, 5], "騎手B")),
        _runner(2, "スパース", "騎手S", sparse, cw=None),
        _runner(3, "ベテラン3", "騎手C",
                _vet_runs([5, 6, 5, 4, 6, 5, 7, 6], "騎手C")),
        _runner(4, "ベテラン4", "騎手D",
                _vet_runs([6, 5, 7, 6, 5, 7, 6, 5], "騎手D")),
        _runner(5, "エース", "騎手A",
                _vet_runs([2, 1, 3, 2, 4, 2, 3, 2], "騎手A",
                          behinds=[0.2, 0.0, 0.4, 0.2, 0.6, 0.2, 0.3, 0.2])),
        _runner(6, "ベテラン6", "騎手F",
                _vet_runs([7, 6, 8, 7, 6, 8, 7, 6], "騎手F")),
    ]
    return RaceRecord(
        race_id="nar-2026-11-01-佐賀-99", date="2026-11-01",
        circuit=obs("nar", "t"), track="佐賀", race_number=obs(11, "t"),
        title=obs("テストB1", "t"), start_time=obs(None, "t"),
        distance=obs(1400, "t"), surface=obs("ダート", "t"),
        weather=obs("晴", "t"), condition=obs("良", "t"),
        updated_at=Obs(None, "t", "null"), segment=Segment.NAR,
        source="test", runners=tuple(runners),
    )


def _by_number(forecast):
    return {r.number: r for r in forecast.runners}


class F1ReproductionTests(unittest.TestCase):
    def test_baseline_reproduces_f1(self):
        fc = forecast_race_v8(synthetic_race(), extras={})
        self.assertEqual(fc.status, "ok")
        runners = _by_number(fc)
        # The pathology: one-start horse, perfect score, ◎, ~50%.
        self.assertEqual(runners[2].ability_score, 1.0)
        self.assertEqual(runners[2].mark, "◎")
        self.assertGreater(runners[2].p_win, 0.45)
        # ... above the eight-start ace.
        self.assertLess(runners[5].ability_score, 1.0)
        self.assertEqual(runners[5].mark, "○")

    def test_challenger_corrects_the_order(self):
        race = synthetic_race()
        for name, cfg in CANDIDATES.items():
            with self.subTest(candidate=name):
                fc = forecast_race_v8_decay(race, extras={}, **cfg)
                self.assertEqual(fc.status, "ok")
                runners = _by_number(fc)
                self.assertEqual(runners[5].mark, "◎")
                self.assertNotEqual(runners[2].mark, "◎")
                self.assertLess(runners[2].ability_score,
                                runners[5].ability_score)
                self.assertLess(runners[2].p_win, 0.30)

    def test_reliability_bounds(self):
        # No evidence -> no trust; long evidence -> approaches 1.
        self.assertEqual(reliability(0, 1.0, k=4.0, coverage_power=0.0), 0.0)
        self.assertAlmostEqual(
            reliability(8, 1.0, k=4.0, coverage_power=0.0), 8 / 12)
        # Coverage can only damp further when coverage_power > 0.
        self.assertLess(
            reliability(8, 0.2, k=4.0, coverage_power=1.0),
            reliability(8, 1.0, k=4.0, coverage_power=1.0))


if __name__ == "__main__":
    unittest.main()
