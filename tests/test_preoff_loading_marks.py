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

    def test_live_prediction_engine_unchanged(self):
        source = APP.read_text(encoding="utf-8")
        self.assertIn("assignPredictionMarks(rows,modelRace);", source)
        self.assertIn("arvexq-form-condition-no-sectional-proposal-v1", source)

if __name__ == "__main__":
    unittest.main()
