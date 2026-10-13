from pathlib import Path
import unittest
S=Path(__file__).resolve().parents[1]/'arvexq/ui/static/app.js'
class PrePostMarkConsistency(unittest.TestCase):
 def test_same_verified_source_is_used_before_and_after(self):
  s=S.read_text(encoding='utf-8')
  a=s[s.index('function applyFrozenMarks('):s.index('function threeFactorMarkInputSignature(')]
  self.assertIn('if(!clock.started&&!server)',a)
  self.assertIn('if(server){',a)
  self.assertIn('z.predMark=scratched?',a)
  archive=s[s.index('function immutableArchivedPrediction('):s.index('function applyFrozenMarks(')]
  self.assertIn('var lock=authorizedPreOffMarks(r)',archive)
  self.assertIn('var clock=raceMarkClock(r),server=authorizedPreOffMarks(r)',a)
 def test_three_factor_weights_are_intact(self):
  s=S.read_text(encoding='utf-8')
  self.assertIn('score:.45*(tr===null?.5:tr)+.35*(pure===null?.5:pure)+.20*(sec===null?.5:sec)',s)
if __name__=='__main__':unittest.main()
