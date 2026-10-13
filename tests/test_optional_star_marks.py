import unittest
from arvexq.prediction.final_marks import optional_star_candidate, CORE_MARKS, LOWER_MARKS

def row(no,tr,pure,sec,score):
    f={"trueRun":tr,"pure":pure,"sectional":sec}
    return {"horse":{"horseNumber":no},"score":score,
        "primaryPillarCoverage":sum(x is not None for x in f.values()),"factors":f}

class TestOptionalStar(unittest.TestCase):
    def test_core_marks(self):
        self.assertEqual(CORE_MARKS,("◎","○","▲","△"))
        self.assertEqual(LOWER_MARKS,("☆",))
    def test_no_automatic_fifth(self):
        base=[row(i,.85,.8,.75,.92-i*.04) for i in range(1,5)]
        self.assertIsNone(optional_star_candidate(base+[row(5,.70,.50,.60,.69)]))
    def test_multiple_independent_factors_required(self):
        base=[row(i,.85,.8,.75,.92-i*.04) for i in range(1,5)]
        self.assertIsNone(optional_star_candidate(base+[row(5,.77,.50,.55,.70)]))
        self.assertIsNone(optional_star_candidate(base+[row(5,.85,None,.75,.71)]))
    def test_one_supported_star(self):
        base=[row(i,.85,.8,.75,.92-i*.04) for i in range(1,5)]
        fifth=row(5,.76,.71,.67,.72)
        sixth=row(6,.76,.70,.68,.70)
        self.assertIs(optional_star_candidate(base+[fifth,sixth]),fifth["horse"])
    def test_score_gap_gate(self):
        base=[row(i,.85,.8,.75,.94-i*.02) for i in range(1,5)]
        self.assertIsNone(optional_star_candidate(base+[row(5,.77,.72,.69,.70)]))
if __name__=="__main__":unittest.main()
