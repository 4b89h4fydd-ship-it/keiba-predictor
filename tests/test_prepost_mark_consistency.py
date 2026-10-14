from pathlib import Path
import subprocess
import unittest
S=Path(__file__).resolve().parents[1]/'arvexq/ui/static/app.js'
class PrePostMarkConsistency(unittest.TestCase):
 def test_live_preoff_marks_and_immutable_postoff_original(self):
  # Execute the existing behavior regression against the real display function.
  # Morning originals stay immutable; they must not overwrite newer pre-off
  # inputs, and are the authority once the race has started. The former text
  # assertion required the retired morning-before-post override instead.
  root=S.parents[3]
  result=subprocess.run(['node','scripts/arvexq_frozen_marks_smoke.js'],
                        cwd=root,capture_output=True,text=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_no_sectional_score_in_live_frontend(self):
  s=S.read_text(encoding='utf-8')
  self.assertIn('var jraStrength=Math.min(.12,.04*comparable.length)',s)
  self.assertIn('var narStrength=Math.min(.25,.08*comparable.length)',s)
  self.assertIn('score+=.06*Math.max(-.30,Math.min(.30,momentum))',s)
  self.assertIn('score=.90*score+.10*',s)
  self.assertNotIn('score:.45*(tr===null?.5:tr)+.35*(pure===null?.5:pure)+.20*(sec===null?.5:sec)',s)
if __name__=='__main__':unittest.main()
