from pathlib import Path
import unittest
SOURCE=Path(__file__).resolve().parents[1]/"arvexq/ui/static/app.js"
class LegacyDetailRemoval(unittest.TestCase):
    def test_unused_old_detail_removed(self):
        s=SOURCE.read_text(encoding='utf-8')
        self.assertNotIn('function detailPanel(r,p)',s)
        self.assertNotIn('sevenAxisScore',s)
        self.assertNotIn('v239Composite',s)
    def test_live_detail_and_model_remain(self):
        s=SOURCE.read_text(encoding='utf-8')
        self.assertIn('function horseDetailPage(r,p)',s)
        self.assertIn('runnerDetailBody(r,p,x)',s)
        self.assertIn('score:.45*(tr===null?.5:tr)+.35*(pure===null?.5:pure)+.20*(sec===null?.5:sec)',s)
