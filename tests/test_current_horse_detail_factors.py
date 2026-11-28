"""The minimal app (2026-11-28, user instruction) has no
horse detail view at all: the racecard table is the whole
race screen, and its marks and probabilities are read from
the published pack (unifiedForecast), never computed from
per-horse detail factors in the client. The old live detail
body (runnerDetailBody), its three-factor fallback fields
and its coverage line must stay gone, and no client-side
factor model may come back in their place."""
from pathlib import Path
import unittest
S=Path(__file__).resolve().parents[1]/"arvexq/ui/static/app.js"
class CurrentHorseDetailFactors(unittest.TestCase):
    def test_no_old_fallback_in_live_detail(self):
        s=S.read_text(encoding="utf-8")
        # There is no live detail body to fall back in.
        self.assertNotIn("function runnerDetailBody(",s)
        self.assertNotIn("function horseModal(",s)
        self.assertNotIn("function horseDetailPage(",s)
        for old in ("x.resultsScore","x.levelFit","x.distFit","x.trackFit","x.condFit","x.ability","x.paceScore"):
            self.assertNotIn(old,s)
        self.assertNotIn("var ability=rf.ability,form=rf.form,klass=rf.classLevel",s)
        self.assertNotIn("n(x.threeFactorCoverage,0)/3",s)
    def test_original_three_factor_unchanged(self):
        s=S.read_text(encoding="utf-8")
        self.assertNotIn("score:.45*(tr===null?.5:tr)+.35*(pure===null?.5:pure)+.20*(sec===null?.5:sec)",s)
        self.assertNotIn("function assignPredictionMarks(",s)
        self.assertNotIn("ARVEXQProductionMarks.visible(x)",s)
        # The racecard's marks are the published pack's own,
        # keyed by horse number — nothing is scored locally.
        self.assertIn("function marksByNumber(detail)",s)
        self.assertIn("map[Number(m.horseNumber)] = String(m.markSymbol)",s)
if __name__=="__main__": unittest.main()
