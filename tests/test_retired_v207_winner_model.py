"""Prevent old V207 winner model from re-entering the current frontend."""
from pathlib import Path
import unittest
SOURCE=Path(__file__).resolve().parents[1]/"arvexq/ui/static/app.js"
class OldWinnerModelRemoved(unittest.TestCase):
    def test_retired_v207_model_removed(self):
        s=SOURCE.read_text(encoding="utf-8")
        for key in ("V207_WINNER_WEIGHTS","v207WinnerScoreHorse","v207UsesWinnerModel","function v207Unit(","function v207Comp("):
            self.assertNotIn(key,s)
    def test_current_three_factor_authority_preserved(self):
        s=SOURCE.read_text(encoding="utf-8")
        self.assertIn("function arvexqFactorValues(z,r)",s)
        self.assertIn("assignPredictionMarks(rows,modelRace);",s)
        self.assertIn("score=(1-strength)*recentForm+strength*conditionForm",s)
if __name__=="__main__":
    unittest.main()
