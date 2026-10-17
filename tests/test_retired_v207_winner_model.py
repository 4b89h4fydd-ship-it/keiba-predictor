"""Prevent old V207 winner model from re-entering the current frontend."""
from pathlib import Path
import unittest
SOURCE=Path(__file__).resolve().parents[1]/"arvexq/ui/static/app.js"
class OldWinnerModelRemoved(unittest.TestCase):
    def test_retired_v207_model_removed(self):
        s=SOURCE.read_text(encoding="utf-8")
        for key in ("V207_WINNER_WEIGHTS","v207WinnerScoreHorse","v207UsesWinnerModel","function v207Unit(","function v207Comp("):
            self.assertNotIn(key,s)
    def test_new_d1_authority_and_retired_engine_not_executed(self):
        s=SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("function arvexqFactorValues(z,r)",s)
        active=s.split("function predict(r){",1)[1].split("function nextRace()",1)[0]
        self.assertNotIn("assignPredictionMarks(",active)
        self.assertNotIn("learnedD1Prediction(r)",active)
        self.assertIn("ARVEXQProductionPrediction.build(r)",active)
        self.assertNotIn("score:.45*(tr===null?.5:tr)+.35*(pure===null?.5:pure)+.20*(sec===null?.5:sec)",s)
        self.assertNotIn("function assignPredictionMarks(",s)
if __name__=="__main__":
    unittest.main()
