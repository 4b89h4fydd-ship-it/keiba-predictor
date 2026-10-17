from pathlib import Path
import unittest
S=Path(__file__).resolve().parents[1]/"arvexq/ui/static/app.js"
class CurrentHorseDetailFactors(unittest.TestCase):
    def test_no_old_fallback_in_live_detail(self):
        s=S.read_text(encoding="utf-8")
        a=s.index("function runnerDetailBody(")
        b=s.index("function horseModal(",a)
        detail=s[a:b]
        for old in ("x.resultsScore","x.levelFit","x.distFit","x.trackFit","x.condFit","x.ability","x.paceScore"):
            self.assertNotIn(old,detail)
        self.assertIn("var ability=rf.ability,form=rf.form,klass=rf.classLevel",detail)
        self.assertIn("n(x.threeFactorCoverage,0)/3",detail)
    def test_original_three_factor_unchanged(self):
        s=S.read_text(encoding="utf-8")
        self.assertNotIn("score:.45*(tr===null?.5:tr)+.35*(pure===null?.5:pure)+.20*(sec===null?.5:sec)",s)
        self.assertIn("return assignObservedPredictionMarks(rows,r);",s)
if __name__=="__main__": unittest.main()
