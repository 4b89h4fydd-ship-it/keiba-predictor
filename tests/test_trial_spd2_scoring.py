"""Trial-backed debutants must be scored from their converted
ability-trial spd2 instead of floored as evidence-free.

Regression for the 2026-11-25 production pack, where exactly two of
415 runners carried ``abilityScore: null``:

* ポルタデリオーキ (名古屋4R 2番): a first starter whose official
  Nagoya ability trial (2026-11-13, 900m, 57.2s, passed) had been
  converted onto the production spd2 scale (spd2 = 0.05) and merged
  into extras by the trial supplement — yet the forecast floored her
  with "過去走の証拠不足のため能力スコアなし" because the scoring
  gate keyed only on payload past runs (``evidence_runs == 0``).

These tests pin the fix in ``forecast_race_v8``: extras carrying
both spd2 keys count as observed speed evidence (one observation).
A runner with neither payload runs nor extras spd2 stays floored —
nothing is invented for genuinely evidence-free horses.
"""
from __future__ import annotations

import unittest

from rewrite.analysis.shadow_v8 import forecast_race_v8
from rewrite.data.normalize import Obs, PastRun, RaceRecord, RunnerRecord, obs
from rewrite.safety.contracts import Segment


def _run(date, track, dist, surf, finish, field, jockey="他騎手",
         behind=0.6, corners=(3, 3, 2)):
    return PastRun(
        date=date, track=obs(track, "t"), distance=obs(dist, "t"),
        surface=obs(surf, "t"), finish=obs(finish, "t"),
        field_size=obs(field, "t"), corner_positions=tuple(corners),
        margin_text=obs(None, "t"), time_seconds=obs(None, "t"),
        jockey=obs(jockey, "t"), race_title=obs("B1", "t"),
        condition=obs("良", "t"), weather=obs("晴", "t"),
        time_behind_winner=obs(behind, "t"), carried_weight=obs(55.0, "t"),
    )


def _runner(number, name, jockey, runs):
    return RunnerRecord(
        number=number, horse_id=obs(None, "t"), name=obs(name, "t"),
        frame_number=obs(number, "t"), age=obs(4, "t"), sex=obs("牡", "t"),
        jockey=obs(jockey, "t"), trainer=obs("調教師", "t"),
        carried_weight=obs(56.0, "t"),
        body_weight=obs(None, "t"), body_weight_change=obs(None, "t"),
        win_odds=obs(None, "t"), scratched=False, past_runs=tuple(runs),
    )


def _vet_runs(finishes, jockey):
    dates = ["2026-10-18", "2026-10-04", "2026-09-20", "2026-09-06",
             "2026-08-23", "2026-08-09", "2026-07-26", "2026-07-12"]
    return [
        _run(dates[i], "佐賀", 1400, "ダート", f, 11, jockey=jockey)
        for i, f in enumerate(finishes)
    ]


def synthetic_race() -> RaceRecord:
    """6-horse NAR race: #6 is a first starter (no past runs)."""
    runners = [
        _runner(1, "ベテラン1", "騎手B", _vet_runs([4, 5, 4, 6, 5, 4, 6, 5], "騎手B")),
        _runner(2, "ベテラン2", "騎手C", _vet_runs([5, 6, 5, 4, 6, 5, 7, 6], "騎手C")),
        _runner(3, "ベテラン3", "騎手D", _vet_runs([6, 5, 7, 6, 5, 7, 6, 5], "騎手D")),
        _runner(4, "ベテラン4", "騎手E", _vet_runs([3, 4, 3, 5, 4, 3, 5, 4], "騎手E")),
        _runner(5, "エース", "騎手A", _vet_runs([2, 1, 3, 2, 4, 2, 3, 2], "騎手A")),
        _runner(6, "初出走", "騎手F", []),
    ]
    return RaceRecord(
        race_id="nar-2026-11-25-佐賀-99", date="2026-11-25",
        circuit=obs("nar", "t"), track="佐賀", race_number=obs(4, "t"),
        title=obs("テスト2歳", "t"), start_time=obs(None, "t"),
        distance=obs(1400, "t"), surface=obs("ダート", "t"),
        weather=obs("晴", "t"), condition=obs("良", "t"),
        updated_at=Obs(None, "t", "null"), segment=Segment.NAR,
        source="test", runners=tuple(runners),
    )


# The trial supplement's extras shape for a supplemented debutant:
# elo_evidence is present (0.0 — trials never derive Elo), and the
# single converted trial value fills both spd2 keys.
TRIAL_EXTRAS = {6: {"elo_evidence": 0.0, "spd2_recent": -0.4, "spd2_best": -0.4}}


def _by_number(forecast):
    return {r.number: r for r in forecast.runners}


class TrialBackedDebutantTests(unittest.TestCase):
    def test_no_extras_debutant_stays_unscored(self):
        fc = forecast_race_v8(synthetic_race(), extras={})
        self.assertEqual(fc.status, "ok")
        debutant = _by_number(fc)[6]
        self.assertIsNone(debutant.ability_score)
        self.assertEqual(debutant.status, "unscored-floor-strength")

    def test_trial_spd2_scores_the_debutant(self):
        fc = forecast_race_v8(synthetic_race(), extras=TRIAL_EXTRAS)
        self.assertEqual(fc.status, "ok")
        debutant = _by_number(fc)[6]
        self.assertIsNotNone(debutant.ability_score)
        self.assertNotEqual(debutant.status, "unscored-floor-strength")
        self.assertIsNotNone(debutant.p_win)

    def test_trial_spd2_scores_the_debutant_under_nar_decay(self):
        fc = forecast_race_v8(synthetic_race(), extras=TRIAL_EXTRAS,
                              evidence_decay_k=2.0)
        debutant = _by_number(fc)[6]
        self.assertIsNotNone(debutant.ability_score)
        # One trial observation under k=2 decay must not collapse the
        # score exactly onto the scored-field mean (that is what an
        # effective evidence of 0 would produce).
        scored = [r.ability_score for r in fc.runners
                  if r.ability_score is not None]
        mean = sum(scored) / len(scored)
        self.assertNotAlmostEqual(debutant.ability_score, mean, places=4)

    def test_extras_without_spd2_do_not_score_the_debutant(self):
        fc = forecast_race_v8(
            synthetic_race(), extras={6: {"elo_evidence": 0.0}})
        debutant = _by_number(fc)[6]
        self.assertIsNone(debutant.ability_score)
        self.assertEqual(debutant.status, "unscored-floor-strength")

    def test_veterans_unaffected_by_trial_extras_presence(self):
        base = forecast_race_v8(synthetic_race(), extras={})
        with_trial = forecast_race_v8(synthetic_race(), extras=TRIAL_EXTRAS)
        # Veterans keep scores in both runs (renormalisation over the
        # enlarged scored field may shift values, but nobody who was
        # scored becomes unscored or vice versa).
        for n in (1, 2, 3, 4, 5):
            self.assertIsNotNone(_by_number(base)[n].ability_score)
            self.assertIsNotNone(_by_number(with_trial)[n].ability_score)


if __name__ == "__main__":
    unittest.main()
