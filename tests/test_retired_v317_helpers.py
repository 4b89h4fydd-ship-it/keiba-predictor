from pathlib import Path
import unittest
S=Path(__file__).resolve().parents[1]/'arvexq/ui/static/app.js'
class RemovedV317Helpers(unittest.TestCase):
    def test_old_helpers_are_absent(self):
        s=S.read_text(encoding='utf8')
        self.assertNotIn('v317NormComponent',s)
        self.assertNotIn('v317Audit',s)
    def test_current_model_unchanged(self):
        s=S.read_text(encoding='utf8')
        self.assertIn('function arvexqFactorValues(z,r)',s)
        self.assertIn('score:.45*(tr===null?.5:tr)+.35*(pure===null?.5:pure)+.20*(sec===null?.5:sec)',s)
