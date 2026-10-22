import unittest
from unittest.mock import patch
from scripts.arvexq_rebuild_saved_forecasts import official_training_races

def row(track, day, number):
    out=['']*80
    out[0]=track;out[1]=day;out[2]=str(number);out[21]='ダ';out[26]='3'
    return out

def entry(track,day,n,no):
    r=['']*40
    r[0]=track;r[1]=day;r[2]=str(n);r[5]=str(no);r[6]='馬'+str(no);r[31]=str(no)
    return r

class Archive:
    def __init__(self):
        keys=[('園田','2026-10-16',1),('園田','2026-10-15',1),('園田','2026-10-14',1)]
        self.race_rows={k:row(*k) for k in keys}
        self.entry_rows={(k,i):entry(*k,i) for k in keys for i in range(1,4)}

class RebuildCacheTests(unittest.TestCase):
    def test_same_as_of_training_reuses_enrichment_without_changing_identity(self):
        archive=Archive();calls=[]
        def enrich(detail, source):
            calls.append(detail['id'])
            return detail
        with patch('scripts.arvexq_rebuild_saved_forecasts.enrich_official_history',enrich):
            first=official_training_races(archive,'2026-10-17','flat',2)
            again=official_training_races(archive,'2026-10-17','flat',2)
            earlier=official_training_races(archive,'2026-10-16','flat',2)
        self.assertEqual([d['id'] for d in first],
             ['nar-2026-10-16-園田-01','nar-2026-10-15-園田-01'])
        self.assertEqual([d['id'] for d in earlier],
             ['nar-2026-10-15-園田-01','nar-2026-10-14-園田-01'])
        self.assertEqual([d['id'] for d in first],[d['id'] for d in again])
        self.assertEqual(len(calls),3)
        for target,rows in [('2026-10-17',first),('2026-10-16',earlier)]:
            self.assertTrue(all(d['date']<target for d in rows))

if __name__=='__main__':unittest.main()
