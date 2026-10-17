from pathlib import Path
import unittest
SOURCE=Path(__file__).resolve().parents[1]/"arvexq/ui/static/app.js"
class RetiredV312Rescue(unittest.TestCase):
    def test_unused_rescue_helpers_removed(self):
        s=SOURCE.read_text(encoding="utf-8")
        for old in ("thirdRescueScoreV312","thirdRescueCandidateV312","comboHasV312","appendRescueRankedV312"):
            self.assertNotIn(old,s)
    def test_current_prediction_untouched(self):
        s=SOURCE.read_text(encoding="utf-8")
        self.assertIn("function assignPredictionMarks(rows,r)",s)
        self.assertNotIn("score:.45*(tr===null?.5:tr)+.35*(pure===null?.5:pure)+.20*(sec===null?.5:sec)",s)
        self.assertIn("return assignObservedPredictionMarks(rows,r);",s)
if __name__=="__main__":unittest.main()
