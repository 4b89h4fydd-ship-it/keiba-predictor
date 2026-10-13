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

    def test_server_original_retained_for_audit(self):
        self.assertIn("function serverFrozenPrediction(r)", self.source)
        self.assertIn("function authorizedPreOffMarks(r)", self.source)
        self.assertIn("function applyFrozenMarks(r,p)", self.source)

if __name__ == "__main__":
    unittest.main()
