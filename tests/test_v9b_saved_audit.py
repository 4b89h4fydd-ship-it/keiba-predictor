import copy
import unittest
from scripts.arvexq_v9b_saved_audit import extract, digest, VERSION, paired_market, receipt_hashes


def fixture():
    f=dict(modelVersion=VERSION,raceId='r',raceDate='2026-11-01',capturedAt='2026-11-01T09:00:00+09:00',
           roster=[dict(horseNumber=n) for n in (1,2,3)],
           diagnosis=[dict(horseNumber=n,winProbability=p) for n,p in [(1,.5),(2,.3),(3,.2)]])
    f['receiptSha256']=digest(f)
    return dict(id='r',date='2026-11-01',startTime='10:00',unifiedForecast=f,
                preparedMeta=dict(rewritePublish=dict(receiptSha256=f['receiptSha256'],publishedAt=f['capturedAt'])),
                result=dict(status='確定',finishers=[dict(horseNumber=n,finish=p) for n,p in [(1,2),(2,1),(3,3)]]))


class SavedV9bTests(unittest.TestCase):
    def test_read_only_and_failure_not_causal(self):
        s=fixture(); before=copy.deepcopy(s); row,status=extract(s)
        self.assertEqual(status,'eligible'); self.assertEqual(s,before)
        self.assertEqual(row['failureCause'],'未特定')
        self.assertEqual(row['metrics']['winnerTop3'],1)
        self.assertEqual(row['metrics']['mrr'],.5)

    def test_tampering_fails(self):
        s=fixture();s['unifiedForecast']['diagnosis'][0]['winProbability']=.6
        self.assertEqual(extract(s)[1],'receipt-mismatch')

    def test_postoff_publication_fails(self):
        s=fixture();s['preparedMeta']['rewritePublish']['publishedAt']='2026-11-01T10:01:00+09:00'
        self.assertEqual(extract(s)[1],'publication-not-preoff')

    def test_duplicate_result_fails(self):
        s=fixture();s['result']['finishers'][1]['horseNumber']=1
        self.assertEqual(extract(s)[1],'incomplete-or-duplicate-roster')

    def test_dead_heat_competition_ranks(self):
        s=fixture()
        for h,p in zip(s['result']['finishers'],[1,1,3]):h['finish']=p
        self.assertEqual(extract(s)[0]['metrics']['top1Win'],1)
        s['result']['finishers'][2]['finish']=2
        self.assertEqual(extract(s)[1],'invalid-competition-ranks')

    def test_day_bootstrap_no_single_day_interval(self):
        row,_=extract(fixture());row['marketMetrics']=dict(row['metrics'])
        one=paired_market([row],draws=100)
        self.assertIsNone(one['paired']['top1Win']['dayCluster95'])
        other=copy.deepcopy(row);other['date']='2026-11-02'
        two=paired_market([row,other],draws=100)
        self.assertEqual(two['paired']['top1Win']['dayCluster95'],[0,0])

    def test_legacy_receipt_is_accepted(self):
        import hashlib,json
        s=fixture();f=s['unifiedForecast'];f.pop('receiptSha256')
        f['beta']=4.0
        sha=hashlib.sha256(json.dumps(f,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        f['beta']=4;f['receiptSha256']=sha
        s['preparedMeta']['rewritePublish']['receiptSha256']=sha
        self.assertIn(sha,receipt_hashes(f))
        self.assertEqual(extract(s)[1],'eligible')

    def test_full_roster_required(self):
        s=fixture();s['result']['finishers'].pop()
        self.assertEqual(extract(s)[1],'incomplete-or-duplicate-roster')


if __name__=='__main__':unittest.main()
