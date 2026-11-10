import copy
import unittest
from rewrite.selection.models import fit,predict,partner_pool
from scripts.arvexq_separate_targets import valid_payouts


def records():
    # Winner and podium labels deliberately encode different conditional roles.
    return [{'id':f'r{i}','date':'2026-11-05','segment':'nar','winner':1,'partners':[2,3],
             'rows':[{'number':n,'baseWin':p,'x':[a,a-.5,p,(n-1)/4,5/18]}
                     for n,p,a in [(1,.4,.9),(2,.3,.5),(3,.15,.3),(4,.1,.2),(5,.05,.1)]]}
            for i in range(25)]


class SeparateTargetsTest(unittest.TestCase):
    def test_winner_and_partner_have_distinct_objectives(self):
        rs=records();winner=fit(rs,target='winner',segment='nar',iterations=100)
        partner=fit(rs,target='partner',segment='nar',iterations=100)
        test=copy.deepcopy(rs[0]);test['date']='2026-11-06'
        wp,pp=predict(winner,test),predict(partner,test)
        self.assertAlmostEqual(sum(wp.values()),1)
        self.assertEqual(max(wp,key=wp.get),1)
        self.assertNotEqual(winner['weights'],partner['weights'])
        self.assertEqual(partner['status'],'research-only-not-approved')
        self.assertTrue(all(0<p<1 for p in pp.values()))

    def test_no_same_day_fit_and_no_cross_circuit_or_tampered_artifact(self):
        rs=records();m=fit(rs,target='partner',segment='nar',iterations=5)
        for mutate in ('same-day','circuit','tampered'):
            candidate=copy.deepcopy(m);r=copy.deepcopy(rs[0]);r['date']='2026-11-06'
            if mutate=='same-day':r['date']='2026-11-05'
            if mutate=='circuit':r['segment']='jra_flat'
            if mutate=='tampered':candidate['weights'][0]+=1
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):predict(candidate,r)

    def test_partner_arm_preserves_heads_and_budget(self):
        r=records()[0];pool=partner_pool(r,{1:.1,2:.2,3:.3,4:.9,5:.8})
        self.assertEqual(pool[:2],[1,2]);self.assertEqual(len(set(pool)),5)

    def test_refuse_malformed_payouts_instead_of_zero_return(self):
        self.assertFalse(valid_payouts({'payouts':[{'type':'3連単','combination':'8','amount':10000}]}))
        self.assertFalse(valid_payouts({'payouts':None}))
        self.assertTrue(valid_payouts({'payouts':[{'type':'3連単','combination':'8-2-3','amount':10000}]}))

    def test_duplicate_training_ids_refused(self):
        r=records();r[1]['id']=r[0]['id']
        with self.assertRaisesRegex(ValueError,'duplicate'):fit(r,target='winner',segment='nar')


if __name__=='__main__':unittest.main()
