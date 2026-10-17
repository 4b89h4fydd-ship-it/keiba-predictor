"""Ensure archived marks cannot become live marks in a loading racecard."""
from pathlib import Path
import re
import unittest

APP = Path(__file__).resolve().parents[1] / "arvexq/ui/static/app.js"

class PreoffLoadingMarksTest(unittest.TestCase):
    def test_archive_only_after_post(self):
        source = APP.read_text(encoding="utf-8")
        match = re.search(r"function morningSavedMarkRows\(r\)\{(.*?)\n\}", source, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("raceMarkClock(r).started?authorizedPreOffMarks(r):null", body)
        self.assertIn("isScratchHorse(h)?'':String(z.mark||'')", body)

    def test_retired_live_prediction_engine_is_not_executed(self):
        source = APP.read_text(encoding="utf-8")
        active=source.split("function predict(r){",1)[1].split("\\nfunction nextRace()",1)[0]\n        self.assertNotIn("assignPredictionMarks(",active)\n        self.assertIn("learnedD1Prediction(r)",active)
        self.assertNotIn("arvexq-true-run-pure-sectional-v2", source)
        self.assertIn("return assignObservedPredictionMarks(rows,r);", source)

if __name__ == "__main__":
    unittest.main()
