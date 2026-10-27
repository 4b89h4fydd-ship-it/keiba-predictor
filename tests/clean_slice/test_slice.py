"""Real source captures, plus corruptions which must fail closed."""
import ast
import copy
import importlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from rewrite.slice.analyze import analyze, validate
from rewrite.slice.store import Store, digest

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures/clean_slice'
CASES=[json.loads(p.read_text()) for p in sorted(FIXTURES.glob('*.input.json'))]


class SliceTests(unittest.TestCase):
    def test_real_complete_fields_and_temporal_cutoff(self):
        self.assertEqual([len(r['horses']) for r in CASES],[18,10])
        self.assertEqual([sum(len(h['histories']) for h in r['horses']) for r in CASES],[118,49])
        for race in CASES:
            validate(race)
            self.assertTrue(all(h['histories'] for h in race['horses']))
            self.assertTrue(all(p['date']<race['date'] for h in race['horses'] for p in h['histories']))
            self.assertTrue(all(h['odds'] is not None for h in race['horses']))
        self.assertTrue(any(h.get('unscored_history') for h in CASES[1]['horses']))
        for horse in CASES[1]['horses']:
            self.assertTrue(horse['pedigree'][0].startswith('父：'))
            self.assertTrue(horse['pedigree'][1].startswith('母：'))
            self.assertTrue(horse['pedigree'][2].startswith('母父：'))
            self.assertNotIn(horse['name'], ' '.join(horse['pedigree']))

    def test_four_stages_all_horses_every_scenario(self):
        for race in CASES:
            a=analyze(race)
            expected={h['number'] for h in race['horses']}
            for scenario in a['scenarios']:
                self.assertEqual(set(scenario['stages']),{'start','thirdCorner','fourthCorner','straight'})
                for positions in scenario['stages'].values():
                    self.assertEqual({x['number'] for x in positions},expected)
                    self.assertEqual(sorted(x['position'] for x in positions),list(range(1,len(expected)+1)))
            self.assertTrue(a['stage_limitations']['start'])
            self.assertTrue(a['stage_limitations']['straight'])
            self.assertNotEqual(a['rows'][0]['position_basis']['start'],a['rows'][0]['position_basis']['straight'])

    def test_marks_and_no_invented_probability_or_bets(self):
        for race in CASES:
            a=analyze(race)
            self.assertEqual([r['mark'] for r in a['rows'][:5]],list('◎○▲△☆'))
            self.assertEqual(sum(r['mark']=='◎' for r in a['rows']),1)
            self.assertTrue(all(r['win_probability'] is None and r['top2_probability'] is None and r['top3_probability'] is None for r in a['rows']))
            self.assertEqual(a['bets'],[])
            self.assertEqual(a['bet_decision'],'見送り')
            self.assertFalse(a['production_eligible'])
            self.assertGreater(a['quality']['missing_rate'],0)
            self.assertEqual(a['quality']['extended_missing_rate'],1)

    def test_target_outcome_and_odds_do_not_drive_predictions(self):
        for original in CASES:
            changed=copy.deepcopy(original)
            changed['result']={'winner':999}
            for h in changed['horses']:
                h['odds']=9999
                h['predictionMark']='◎'
                h['legacy_score']=10**9
            a,b=analyze(original),analyze(changed)
            self.assertEqual(a['rows'],b['rows'])
            self.assertEqual(a['scenarios'],b['scenarios'])

    def test_missing_future_duplicate_and_bad_positions_fail(self):
        for mutation in ('missing','future','duplicate','corner','no_positions'):
            r=copy.deepcopy(CASES[0])
            if mutation=='missing':r['horses'].pop()
            elif mutation=='future':r['horses'][0]['histories'][0]['date']=r['date']
            elif mutation=='duplicate':r['horses'][0]['number']=r['horses'][1]['number']
            elif mutation=='corner':r['horses'][0]['histories'][0]['corners']=[999]
            else:
                for p in r['horses'][0]['histories']:p['corners']=None
            with self.assertRaises(ValueError):analyze(r)

    def test_storage_reopen_preserves_exact_api_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'research.db'
            store=Store(path)
            expected={}
            for race in CASES:
                output=analyze(race)
                expected[race['id']]=store.save(race,output)
                self.assertEqual(store.save(race,output),expected[race['id']])
                changed=copy.deepcopy(output);changed['rows'][0]['mark']='○'
                with self.assertRaises(ValueError):store.save(race,changed)
            for sql in ('DELETE FROM runs',"UPDATE runs SET output_sha256='bad'"):
                with self.assertRaises(sqlite3.IntegrityError):
                    with store.db:store.db.execute(sql)
            store.close()
            store=Store(path)
            for rid,document in expected.items():self.assertEqual(store.read(rid),document)
            store.close()

    def test_new_runtime_does_not_import_old_engine(self):
        root=Path(importlib.import_module('rewrite.slice').__file__).parent
        for path in root.glob('*.py'):
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    for alias in node.names:self.assertFalse(alias.name=='app' or alias.name.startswith('arvexq') or alias.name=='rewrite.engine')
                elif isinstance(node,ast.ImportFrom):
                    self.assertFalse((node.module or '').startswith(('arvexq','app','rewrite.engine')))


if __name__=='__main__':unittest.main()
