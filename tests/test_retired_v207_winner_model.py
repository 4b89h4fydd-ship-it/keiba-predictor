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
        # There is no client prediction engine left to execute
        # a retired model in (minimal app, 2026-11-28, user
        # instruction): no predict(), no D1 learner and no
        # production-prediction builder. The marks shown are
        # the published pack's own.
        self.assertNotIn("function predict(r){",s)
        self.assertNotIn("assignPredictionMarks(",s)
        self.assertNotIn("learnedD1Prediction(r)",s)
        self.assertNotIn("ARVEXQProductionPrediction",s)
        self.assertNotIn("score:.45*(tr===null?.5:tr)+.35*(pure===null?.5:pure)+.20*(sec===null?.5:sec)",s)
        self.assertIn("function marksByNumber(detail)",s)
        self.assertIn("map[Number(m.horseNumber)] = String(m.markSymbol)",s)
if __name__=="__main__":
    unittest.main()
