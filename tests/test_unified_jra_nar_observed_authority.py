"""JRA/NAR share 60/40 ranking but JRA requires official recorded margins."""
import copy
import unittest
from arvexq.prediction.observed_model import (
    apply_observed_marks, rank_jra, rank_nar,
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
        for circuit in ("中央","地方"):
            with self.subTest(circuit=circuit):
                d=race(circuit)
                apply_observed_marks(d)
                self.assertEqual(d["predictionModelVersion"],
                                 JRA_MODEL_VERSION if circuit=="中央" else NAR_MODEL_VERSION)
                self.assertEqual(d["factorRanking"][0]["modelVersion"], d["predictionModelVersion"])
                for row in d["factorRanking"]:
                    rates = d["horses"][row["horseNumber"]-1]["integratedEvaluation"]["historicalRates"]
                    axes = [row["factors"]["mineta"], row["factors"]["margin"]]
                    if rates["starts"] >= 2:
                        axes.append((rates["winRate"] + rates["top2Rate"] + rates["top3Rate"]) / 3)
                    if rates["transferClassEvidenceStarts"] >= 2:
                        axes.append(.5 + rates["transferClassSignal"])
                    self.assertAlmostEqual(row["dominanceScore"], round(sum(axes)/len(axes)*100,2))
                self.assertEqual(d["observedModelCoverage"]["fullyObserved"],6)

    def test_jra_unverified_margins_not_scored_or_replaced_by_old_model(self):
        d=race("中央")
        for run in d["horses"][2]["recentRaces"]:
            run.pop("marginEvidence")
        apply_observed_marks(d)
        self.assertEqual(d["observedModelCoverage"]["fullyObserved"],5)
        self.assertEqual(d["horses"][2]["integratedEvaluation"]["mark"],"")
        self.assertNotEqual(d["predictionStatus"],"ready")

    def test_flat_race_never_borrows_jumps_and_obstacles_do_not_borrow_flat(self):
        d=race("中央")
        for run in d["horses"][0]["recentRaces"]:
            run["surface"]="障害"
            run["title"]="障害レース"
        ranks=rank_jra(d["horses"],d)
        self.assertEqual(len(ranks),5)
        jump=copy.deepcopy(d)
        jump["analysisMode"]="障害"
        self.assertEqual(len(rank_jra(jump["horses"],jump)),0)  # One observed jump horse cannot establish field occupancy

    def test_zero_seconds_are_observed_with_official_proof(self):
        d=race("中央")
        ranks=rank_jra(d["horses"],d)
        self.assertEqual(len(ranks),6)
        self.assertEqual(d["horses"][0]["recentRaces"][0]["marginSeconds"],0.)

    def test_cross_circuit_entrypoint_raises(self):
        d=race("中央")
        with self.assertRaises(ValueError):rank_nar(d["horses"],d)
        d=race("地方")
        with self.assertRaises(ValueError):rank_jra(d["horses"],d)


if __name__=="__main__":
    unittest.main()
