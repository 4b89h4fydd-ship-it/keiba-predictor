import unittest
from arvexq.prediction.final_marks import optional_star_candidate, CORE_MARKS, LOWER_MARKS

def row(no,tr,pure,sec,score,fit=None):
    factors={"trueRun":tr,"pure":pure,"sectional":sec}
    horse={"horseNumber":no}
    if fit is not None:
        horse["paceFitScore"]=fit
    return {"horse":horse,"score":score,
            "primaryPillarCoverage":sum(v is not None for v in factors.values()),
            "factors":factors}

class TestOptionalStar(unittest.TestCase):
    def setUp(self):
        self.base=[row(i,.85,.8,.75,.92-i*.04) for i in range(1,5)]

    def test_core_marks(self):
        self.assertEqual(CORE_MARKS,("◎","○","▲","△"))
        self.assertEqual(LOWER_MARKS,("☆",))

    def test_missing_pace_evidence_no_star(self):
        self.assertIsNone(optional_star_candidate(self.base+[row(5,.80,.70,.72,.70)]))

    def test_jra_pace_upside(self):
        fifth=row(5,.73,.62,.70,.70,77)
        self.assertIs(optional_star_candidate(self.base+[fifth],{"circuit":"中央"}),fifth["horse"])

    def test_local_separate_threshold(self):
        fifth=row(5,.69,.60,.65,.63,.69)
        self.assertIsNone(optional_star_candidate(self.base+[fifth],{"circuit":"中央"}))
        self.assertIs(optional_star_candidate(self.base+[fifth],{"circuit":"地方"}),fifth["horse"])

    def test_missing_independent_support(self):
        fifth=row(5,.50,.64,.50,.63,.95)
        self.assertIsNone(optional_star_candidate(self.base+[fifth],{"circuit":"地方"}))

    def test_one_best_fit_star(self):
        fifth=row(5,.74,.70,.70,.70,.79)
        sixth=row(6,.75,.70,.73,.69,.85)
        self.assertIs(optional_star_candidate(self.base+[fifth,sixth],{"circuit":"中央"}),sixth["horse"])

    def test_invalid_fit_and_large_gap(self):
        fifth=row(5,.75,.70,.70,.58,"bad")
        self.assertIsNone(optional_star_candidate(self.base+[fifth],{"circuit":"中央"}))
        sixth=row(6,.75,.70,.70,.55,.90)
        self.assertIsNone(optional_star_candidate(self.base+[sixth],{"circuit":"中央"}))

if __name__=="__main__":
    unittest.main()
