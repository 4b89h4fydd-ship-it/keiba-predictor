import copy
import unittest
from arvexq.prediction.final_marks import apply_core_marks
from arvexq.prediction.observed_model import MODEL_VERSION, apply_nar_marks, rank_nar
from arvexq.research.margin_abcde_candidate import score as margin_score


def race():
    horses = []
    for no in range(1, 7):
        runs = []
        for i, day in enumerate((1, 8, 15, 22, 29)):
            runs.append({
                "date": f"2026-09-{day:02d}", "track": "園田", "raceNumber": i + 1,
                "distance": 1400, "surface": "ダート", "fieldSize": 10,
                "finish": min(no + i % 3, 10), "opponentLevel": 0.6,
                "cornerPositions": [min(no, 10), min(no + i % 2, 10)],
                "timeBehindWinner": round((no - 1) * .15 + i * .01, 2),
            })
        horses.append({"name": f"馬{no}", "horseNumber": no,
                       "frameNumber": no, "recentRaces": list(reversed(runs))})
    return {"id": "nar-2026-10-12-園田-01", "circuit": "地方",
            "date": "2026-10-12", "track": "園田",
            "surface": "ダート", "distance": 1400, "horses": horses}


class NarAuthorityTests(unittest.TestCase):
    def test_consensus_uses_observed_inputs(self):
        d = race()
        before = copy.deepcopy(d)
        self.assertEqual(rank_nar(d['horses'], d), [])
        self.assertEqual(d, before)
        # Observed research remains available without entering live predictions.
        self.assertIsNotNone(margin_score(d['horses'][0], d))

    def test_new_marks_replace_old_fields_and_leave_seal_untouched(self):
        d = race()
        d['morningMarkSnapshot'] = {'fixedAt':'2026-10-12T09:00:00+09:00','horses':[{'horseNumber':1,'mark':'○'}]}
        original = copy.deepcopy(d['morningMarkSnapshot'])
        for h in d['horses']: h['integratedEvaluation'] = {'mark':'注','factorEvidence':{'old':1}}
        apply_core_marks(d)
        self.assertEqual(d['predictionStatus'], 'disabled')
        self.assertNotIn('factorRanking',d)
        self.assertTrue(all('integratedEvaluation' not in h for h in d['horses']))
        # Immutable internal evidence remains untouched; public projection removes it.
        self.assertEqual(d['morningMarkSnapshot'],original)
        from arvexq.forecast.publication import public_race
        self.assertNotIn('morningMarkSnapshot',public_race(d))

    def test_missing_margins_never_get_legacy_scores(self):
        d = race()
        for run in d['horses'][5]['recentRaces']: run.pop('timeBehindWinner')
        before=copy.deepcopy(d['horses'])
        apply_nar_marks(d)
        self.assertEqual(d['predictionStatus'],'disabled')
        self.assertNotIn('observedModelCoverage', d)
        self.assertEqual(d['horses'],before)

    def test_zero_winner_margin_is_valid(self):
        d = race()
        self.assertEqual(d["horses"][0]["recentRaces"][0]["timeBehindWinner"], .04)
        self.assertEqual(d["horses"][0]["recentRaces"][-1]["timeBehindWinner"], 0.)
        self.assertIsNotNone(margin_score(d["horses"][0], d))
        self.assertIsNotNone(rank_nar(d["horses"], d))

    def test_local_evidence_exposes_only_new_two_axes(self):
        from arvexq.prediction.race_intelligence import attach_evidence
        d = apply_nar_marks(race())
        attach_evidence(d)
        factors = d["horses"][0]["researchEvidence"]["factors"]
        self.assertEqual(factors["version"], MODEL_VERSION)
        self.assertEqual([(x["key"], x["weight"]) for x in factors["items"]],
                         [("mineta", .60), ("margin", .40)])
        self.assertNotIn("trueRun", [x["key"] for x in factors["items"]])

    def test_star_mark_requires_independent_race_pace_evidence(self):
        from unittest.mock import patch
        d = race()
        d['horses'][4]['recentRaces'][-1].update(finish=2,cornerPositions=[8,8,8],timeBehindWinner=.2)
        # A retired authority cannot execute even if a caller supplies ranked evidence.
        with patch('arvexq.prediction.observed_model.rank_observed',side_effect=AssertionError('retired scorer executed')):
            apply_nar_marks(d)
        self.assertTrue(all('integratedEvaluation' not in h and 'mark' not in h for h in d['horses']))
        self.assertEqual(d['predictionStatus'],'disabled')

    def test_central_dispatch_never_uses_nar_model(self):
        with self.assertRaises(ValueError):
            apply_nar_marks({"circuit": "中央", "date": "2026-10-12", "horses": []})


if __name__ == "__main__":
    unittest.main()
