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
        # The "live detail" of the minimal app is the racecard
        # table itself (2026-11-28, user instruction): the old
        # per-horse detail page and its mark model are removed
        # with the legacy panel, and the marks on the card are
        # the published pack's own.
        s=SOURCE.read_text(encoding='utf-8')
        self.assertNotIn('function horseDetailPage(r,p)',s)
        self.assertNotIn('runnerDetailBody(r,p,x)',s)
        self.assertNotIn('function visiblePredictionMark(x)',s)
        self.assertNotIn('score:.45*(tr===null?.5:tr)+.35*(pure===null?.5:pure)+.20*(sec===null?.5:sec)',s)
        self.assertNotIn("function assignPredictionMarks(",s)
        self.assertIn("function marksByNumber(detail)",s)
        self.assertIn("map[Number(m.horseNumber)] = String(m.markSymbol)",s)
