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
