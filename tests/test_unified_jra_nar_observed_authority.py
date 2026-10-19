"""JRA/NAR share 60/40 ranking but JRA requires official recorded margins."""
import copy
import unittest
from arvexq.prediction.observed_model import (
    apply_observed_marks,
    JRA_MODEL_VERSION, NAR_MODEL_VERSION,
)


def race(circuit):
    runs=[]
    for j in range(5):
        runs.append({
            "date":f"2026-09-{25-j:02d}", "track":"東京" if circuit=="中央" else "園田",
            "surface":"芝" if circuit=="中央" else "ダート", "distance":1600,
            "fieldSize":12, "finish":j%3+1, "cornerPositions":[j%4+1,j%4+1],
            "marginSeconds":round(j*.2,2),
            "marginEvidenceSource":"JRA official",
            "marginEvidence":{"winnerTimeSeconds":95.1, "horseTimeSeconds":95.1+j*.2},
            "opponentLevel":.7,
        })
    return {"id":"jra-test" if circuit=="中央" else "nar-test",
            "circuit":circuit,"date":"2026-10-12",
            "track":"東京" if circuit=="中央" else "園田",
            "surface":"芝" if circuit=="中央" else "ダート","distance":1600,
            "horses":[{"horseNumber":i,"frameNumber":i,
                       "name":f"runner {i}","recentRaces":copy.deepcopy(runs)}
                      for i in range(1,7)]}


class ObservedAuthorityTests(unittest.TestCase):
    def test_consensus_axes_and_separate_model_ids(self):
        for circuit in ('中央','地方'):
            with self.subTest(circuit=circuit):
                d=race(circuit);before=copy.deepcopy(d['horses'])
                apply_observed_marks(d)
                self.assertEqual(d['predictionStatus'],'disabled')
                self.assertNotIn('factorRanking',d)
                self.assertEqual(d['horses'],before)

    def test_jra_unverified_margins_not_scored_or_replaced_by_old_model(self):
        d=race('中央')
        for run in d['horses'][2]['recentRaces']: run.pop('marginEvidence')
        apply_observed_marks(d)
        self.assertEqual(d['predictionStatus'],'disabled')
        self.assertTrue(all('integratedEvaluation' not in h for h in d['horses']))

    def test_retired_ranking_entrypoints_deleted(self):
        import arvexq.prediction.observed_model as model
        for name in ("rank_jra", "rank_nar", "rank_observed", "model_version"):
            self.assertFalse(hasattr(model, name), name)

    def test_zero_seconds_are_observed_with_official_proof(self):
        d=race('中央')
        for run in d['horses'][0]['recentRaces']:
            run['marginSeconds']=0.0
            run['marginEvidence']={'winnerTimeSeconds':95.1,'horseTimeSeconds':95.1}
        before=copy.deepcopy(d['horses'])
        apply_observed_marks(d)
        self.assertEqual(d['horses'],before)
        self.assertEqual(d['predictionStatus'],'disabled')



if __name__=="__main__":
    unittest.main()
