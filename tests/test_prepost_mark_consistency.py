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
 def test_both_circuits_use_observed_evidence_consensus(self):
  s=S.read_text(encoding='utf-8')
  self.assertIn('if(position!==null)observations.push(position);',s)
  self.assertIn('observations.push((rate.winRate+rate.top2Rate+rate.top3Rate)/3)',s)
  self.assertIn('observations.push(.5+rate.transferClassSignal)',s)
  self.assertIn("var ARVEXQ_JRA_MODEL='arvexq-jra-observed-consensus-v2'",s)
  self.assertIn("var ARVEXQ_NAR_MODEL='arvexq-nar-observed-consensus-v2'",s)
  self.assertNotIn('function arvexqFactorValues',s)
  self.assertNotIn('arvexq-true-run-pure-sectional-v2',s)
if __name__=='__main__':unittest.main()
