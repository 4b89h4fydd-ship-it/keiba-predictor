"""Ensure archived marks cannot become live marks in a loading racecard.

The minimal app (2026-11-28, user instruction) renders
exactly one mark source: the published pack's
unifiedForecast.marks, read by horse number. There is no
morning-saved / archived mark row builder, no pre-off mark
authoriser and no client-side prediction engine that could
substitute archived or locally computed marks while a
racecard loads."""
from pathlib import Path
import unittest

APP = Path(__file__).resolve().parents[1] / "arvexq/ui/static/app.js"

class PreoffLoadingMarksTest(unittest.TestCase):
    def test_archive_only_after_post(self):
        source = APP.read_text(encoding="utf-8")
        # No archived-mark path exists in the client at all.
        self.assertNotIn("function morningSavedMarkRows(", source)
        self.assertNotIn("function authorizedPreOffMarks(", source)
        self.assertNotIn("raceMarkClock(", source)
        # The only marks rendered are the pack's own, placed
        # on the row of the horse number they were sealed for.
        self.assertIn("function marksByNumber(detail)", source)
        self.assertIn("map[Number(m.horseNumber)] = String(m.markSymbol)", source)
        self.assertIn("marks[row.number] || ''", source)

    def test_retired_live_prediction_engine_is_not_executed(self):
        source = APP.read_text(encoding="utf-8")
        # No client prediction engine exists to execute: the
        # retired in-browser engine and its mark assignment
        # stay out, and nothing rebuilds a prediction locally.
        self.assertNotIn("function predict(r){", source)
        self.assertNotIn("assignPredictionMarks(", source)
        self.assertNotIn("learnedD1Prediction(r)", source)
        self.assertNotIn("ARVEXQProductionPrediction", source)
        self.assertNotIn("arvexq-true-run-pure-sectional-v2", source)

if __name__ == "__main__":
    unittest.main()
