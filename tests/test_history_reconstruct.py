import unittest
from scripts.arvexq_history_reconstruct import normalize, roster

class IdentityContracts(unittest.TestCase):
    def test_conflicts_and_missing_identity_never_merge(self):
        p=dict(date='2026-01-01',track='浦和',raceNumber=1,raceId='nar-2026-01-01-浦和-01')
        self.assertIsNotNone(normalize('123','同名',p)['entry_key'])
        self.assertIsNone(normalize('name:同名','同名',p)['entry_key'])
        self.assertIsNone(normalize('123','同名',dict(p,date='2026-01-02'))['entry_key'])
        self.assertIsNone(normalize('123','同名',dict(p,raceNumber=None))['entry_key'])
        self.assertNotEqual(normalize('123','同名',p)['entry_key'],normalize('456','同名',p)['entry_key'])
    def test_dead_heat_competition_ranking(self):
        def snap(pos):
            return dict(horses=[dict(horseNumber=i+1) for i in range(len(pos))],result=dict(finishers=[dict(horseNumber=i+1,finish=x) for i,x in enumerate(pos)]))
        self.assertEqual(roster(snap([1,1,3])),([],True))
        self.assertEqual(roster(snap([1,2,2,4])),([],True))
        self.assertIn('invalid_competition_ranks',roster(snap([1,1,2]))[0])
        self.assertIn('unresolved_nonfinish_status',roster(snap([1,2,'中止']))[0])
    def test_raw_and_missing_fields_preserved(self):
        p={'date':'2026-01-01'}
        v=normalize('123','horse',p)
        self.assertEqual(v['raw'],p)
        self.assertIsNone(v['acquired_at'])
        self.assertIsNone(v['last3f'])

if __name__=='__main__': unittest.main()

class RetrospectiveExtraction(unittest.TestCase):
    @staticmethod
    def extract(snap):
        # Exercise the actual extraction functions without optional ML runtimes.
        import ast, datetime, hashlib, json, math, statistics, types
        from pathlib import Path
        tree=ast.parse(Path('scripts/arvexq_retro_comparison_v2.py').read_text())
        funcs=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('fl','extract')],type_ignores=[])
        ns=dict(datetime=datetime,hashlib=hashlib,json=json,math=math,statistics=statistics,np=types.SimpleNamespace(nan=float('nan')))
        exec(compile(funcs,'retrospective-extract','exec'),ns)
        return ns['extract']('nar-2026-01-03-浦和-01',snap,'2026-01-03')
    def test_ties_and_future_history(self):
        snap={'horses':[{'horseNumber':i+1,'allPastRuns':[{'date':'2026-01-04','finish':1},{'date':'2026-01-03','finish':1},{'date':'2026-01-01','finish':4}]} for i in range(4)],'result':{'status':'確定','finishers':[{'horseNumber':i+1,'finish':p} for i,p in enumerate([1,1,3,4])]}}
        rows,status=self.extract(snap)
        self.assertEqual(status,'eligible')
        self.assertEqual([r['label'] for r in rows],[3,3,1,0])
        self.assertEqual(rows[0]['features'][6],1)
        snap['result']['finishers'].append(snap['result']['finishers'][0])
        self.assertEqual(self.extract(snap)[1],'duplicate_result_number')
