from pathlib import Path
import unittest
APP=Path(__file__).resolve().parents[1]/"arvexq/ui/static/app.js"
class RetiredSameDayCorrection(unittest.TestCase):
    def test_obsolete_display_and_calculator_absent(self):
        s=APP.read_text(encoding="utf-8")
        self.assertNotIn("sameDayCorrectionProfileV313",s)
        self.assertNotIn("当日補正 ON",s)
    def test_existing_mark_signature_and_three_factor_model_preserved(self):
        s=APP.read_text(encoding="utf-8")
        self.assertIn("function sameDayTrendSignatureV313(",s)
        self.assertIn("function assignPredictionMarks(rows,r)",s)
        self.assertIn("score:.45*(tr===null?.5:tr)+.35*(pure===null?.5:pure)+.20*(sec===null?.5:sec)",s)
if __name__=="__main__": unittest.main()
