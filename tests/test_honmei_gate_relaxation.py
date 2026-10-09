import unittest
from arvexq.prediction.honmei_gate import evaluate_honmei_gate, GATE_VERSION

def row(no, rank, strength, recent, factor=.78, families=10):
    f={"ability":3,"record":3,"suitability":2,"pace":2} if families==10 else {"ability":2,"record":2,"suitability":2,"pace":1}
    return {"rank":rank,"horse":{"horseNumber":no,"recentRaces":[{"finish":v,"fieldSize":10} for v in recent]},
            "ability":factor,"record":factor,"suitability":factor,"pace":factor,
            "sample":5,"evidenceFamilyCounts":f,
            "pillarRanks":{"ability":rank,"record":rank,"suitability":rank,"pace":rank},
            "multiHead":{"strengthScore":strength,"strengthRank":rank}}

class TestHonmeiWiden(unittest.TestCase):
    def test_short_history_requires_extra_evidence(self):
        a=row(1,1,.92,[1,6]); b=row(2,2,.61,[5,6,6],.45)
        q=evaluate_honmei_gate([a,b],None,{"circuit":"地方"})
        self.assertEqual(GATE_VERSION,"arvexq-podium-axis-gate-v4")
        self.assertTrue(q["eligible"],q["failed"])
        for bad in ([1],[6,7]):
            q=evaluate_honmei_gate([row(1,1,.92,bad),b],None,{"circuit":"地方"})
            self.assertFalse(q["eligible"])
    def test_missing_evidence_never_forces_honmei(self):
        q=evaluate_honmei_gate([row(1,1,.92,[1,6],families=7),
                                row(2,2,.61,[5,6,6],.45)],None,{"circuit":"地方"})
        self.assertFalse(q["eligible"])
if __name__=="__main__":
    unittest.main()
