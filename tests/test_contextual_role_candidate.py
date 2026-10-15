import copy
import unittest
from arvexq.research.contextual_role_candidate import predict,context_weight,comparable
from tests.test_nar_mineta_margin_authority import race
from scripts.arvexq_contextual_role_comparison import evaluate


class ContextualRoleTests(unittest.TestCase):
    def test_separate_roles_and_normalized_joint(self):
        r=race();original=copy.deepcopy(r);p=predict(r)
        self.assertEqual(r,original)
        self.assertTrue(p['fullyObserved'])
        self.assertAlmostEqual(sum(t[3] for t in p['joint']),1)
        for slot in range(3):
            self.assertAlmostEqual(sum(z['relativeSlotProbabilities'][slot] for z in p['rows']),1)
        for i,j,k,_ in p['joint']:self.assertEqual(len({i,j,k}),3)
        for z in p['rows']:
            self.assertAlmostEqual(z['roleEvidence']['positionWeight']+z['roleEvidence']['marginWeight'],1)
            self.assertEqual(set(z['roles']),{'win','second','third','axis'})

    def test_context_changes_blend_without_odds(self):
        r=race();p=predict(r)
        r['distance']=2200;q=predict(r)
        self.assertNotEqual(p['rows'][0]['roleEvidence']['positionWeight'],q['rows'][0]['roleEvidence']['positionWeight'])
        before=predict(r)
        for h in r['horses']:h['winOdds']=999;h['popularity']=1
        self.assertEqual(before['marks'],predict(r)['marks'])

    def test_result_and_future_history_cannot_change_decisions(self):
        r=race();p=predict(r)
        r['result']={'finishers':[{'horseNumber':6,'finish':1}]}
        for h in r['horses']:
            h['recentRaces'].append({'date':'2027-01-01','finish':1,'fieldSize':10,'cornerPositions':[1,1],'timeBehindWinner':0})
        q=predict(r)
        self.assertEqual(p['marks'],q['marks'])
        self.assertEqual([z['roles'] for z in p['rows']],[z['roles'] for z in q['rows']])

    def test_missing_proof_cannot_create_joint_or_axis(self):
        r=race()
        for q in r['horses'][0]['recentRaces']:q.pop('timeBehindWinner')
        p=predict(r)
        self.assertFalse(p['fullyObserved']);self.assertEqual(p['joint'],[]);self.assertEqual(p['axisHorseNumber'],0)

    def test_context_never_matches_unknown_surface(self):
        r=race();run=r['horses'][0]['recentRaces'][0]
        self.assertTrue(comparable(run,r));run['surface']=''
        self.assertFalse(comparable(run,r))

    def test_special_marks_require_current_distance_and_surface_proof(self):
        from tests.test_optional_star_marks import make_race
        r=make_race();r['distance']=2400
        p=predict(r)
        self.assertFalse(any(m in ('☆','注') for m in p['marks'].values()))
        self.assertTrue(all(row['roleEvidence']['reproductionRuns']==0 for row in p['rows']))

    def test_going_and_opposition_change_context_weight(self):
        r=race();r['condition']='重'
        q=copy.deepcopy(r['horses'][0]['recentRaces'][0]);q['condition']='重'
        matched=context_weight(q,r,0);q['condition']='良'
        self.assertGreater(matched,context_weight(q,r,0))
        q['opponentLevel']=1;strong=context_weight(q,r,0)
        q['opponentLevel']=0
        self.assertGreater(strong,context_weight(q,r,0))

    def test_insufficient_comparison_cannot_approve_production(self):
        report=evaluate([])
        self.assertEqual(report['status'],'blocked');self.assertFalse(report['productionChanged'])

    def test_changed_finish_tendency_changes_role_scores(self):
        r=race()
        for q in r['horses'][0]['recentRaces']:q['finish']=2
        p=predict(r);row=next(z for z in p['rows'] if z['horse']['horseNumber']==1)
        self.assertGreater(row['roles']['second'],row['roles']['win'])


if __name__=='__main__':unittest.main()
