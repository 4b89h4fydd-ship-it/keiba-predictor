"""Regression guards: retired v345 device marks cannot influence current UI."""
from pathlib import Path
import unittest

APP_JS = Path(__file__).resolve().parents[1] / "arvexq" / "ui" / "static" / "app.js"

class RetiredLocalMarkFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP_JS.read_text(encoding="utf-8")

    def test_old_device_mark_loader_removed(self):
        self.assertNotIn("loadFrozenMarks", self.source)
        self.assertNotIn("saveFrozenMarks", self.source)

    def test_old_device_mark_display_and_override_removed(self):
        self.assertNotIn("local-prepost", self.source)
        self.assertNotIn("端末の発走前印・固定済み", self.source)

    def test_archived_original_is_not_republished_by_legacy_view(self):
        # Original immutable audit data stays in storage; the
        # minimal app (2026-11-28, user instruction) has no
        # legacy view that could republish it: no
        # frozen-prediction view, no saved-revision panels and
        # no pre-off mark authoriser remain. The only marks on
        # screen are the published pack's unifiedForecast.marks.
        self.assertNotIn("function serverFrozenPrediction(r)", self.source)
        self.assertNotIn("function savedRevisionDiagnosisPanel(r,p)", self.source)
        self.assertNotIn("function savedRevisionHorseDetail(r,x)", self.source)
        self.assertNotIn("function authorizedPreOffMarks(r)", self.source)
        self.assertNotIn("function applyFrozenMarks(r,p)", self.source)
        self.assertNotIn("ARVEXQProductionMarks.visible(x)", self.source)
        self.assertIn("function marksByNumber(detail)", self.source)
        self.assertIn("map[Number(m.horseNumber)] = String(m.markSymbol)", self.source)

if __name__ == "__main__":
    unittest.main()
