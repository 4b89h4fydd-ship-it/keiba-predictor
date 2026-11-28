from pathlib import Path
import ast
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
  result=subprocess.run(['node','scripts/arvexq_production_boundaries_smoke.cjs'],
                        cwd=root,capture_output=True,text=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_both_circuits_use_observed_evidence_consensus(self):
  # Display side: since the 2026-11-28 rebuild the app only shows the
  # racecard and the marks the publisher put in the pack. It builds no
  # prediction of its own, so it must carry no per-circuit scoring and
  # no retired display-side prediction builder.
  s=S.read_text(encoding='utf-8')
  self.assertNotIn('function narScoreRows(',s)
  self.assertNotIn('function assignObservedPredictionMarks(',s)
  self.assertNotIn('ARVEXQProductionPrediction',s)
  self.assertNotIn('function arvexqFactorValues',s)
  self.assertNotIn('arvexq-true-run-pure-sectional-v2',s)
  # Production side: the marks in every pack are built by the publisher,
  # and since clean-forecast-v2 both circuits (中央・地方) go through the
  # one netkeiba-foundation path — apply_nk_foundation inside the single
  # build function build_publish_detail. There is no circuit branch.
  root=S.parents[3]
  pub=(root/'scripts/arvexq_rewrite_publish.py').read_text(encoding='utf-8')
  self.assertIn('from rewrite.analysis.clean_forecast import',pub)
  self.assertIn('CLEAN_FORECAST_VERSION, apply_nk_foundation)',pub)
  self.assertNotIn('circuit ==',pub)
  self.assertNotIn('is_nar',pub)
  self.assertNotIn('is_jra',pub)
  tree=ast.parse(pub)
  builds=[n for n in tree.body
          if isinstance(n,ast.FunctionDef) and n.name=='build_publish_detail']
  self.assertEqual(len(builds),1)
  calls=[n for n in ast.walk(builds[0])
         if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
         and n.func.id=='apply_nk_foundation']
  self.assertEqual(len(calls),1)
  call=calls[0]
  for node in ast.walk(builds[0]):
   if isinstance(node,ast.If) and any(c is call for c in ast.walk(node)):
    gate=ast.get_source_segment(pub,node.test) or ''
    self.assertNotIn('circuit',gate)
    self.assertNotIn('中央',gate)
    self.assertNotIn('地方',gate)
  # The foundation module itself is the v2 path both circuits share.
  cf=(root/'rewrite/analysis/clean_forecast.py').read_text(encoding='utf-8')
  self.assertIn('CLEAN_FORECAST_VERSION = "clean-forecast-v2"',cf)
  self.assertIn('def nk_foundation_vector(',cf)
  self.assertIn('def apply_nk_foundation(',cf)
if __name__=='__main__':unittest.main()
