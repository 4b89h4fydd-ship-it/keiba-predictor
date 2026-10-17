"""Research candidate must never silently become a betting recommendation."""
from unittest import TestCase
from arvexq.betting.scenario_tickets import compare_tickets


class ResearchTicketLeaderTests(TestCase):
    def test_candidate_is_visible_without_recommendation(self):
        horses = [
            {'horseNumber': n, 'frameNumber': n,
             'integratedEvaluation': {'mark': mark}}
            for n, mark in [(1, '◎'), (2, '○'), (3, '▲')]]
        scenario = {
            'id': 'usual',
            'orders': [
                {'order': [1, 2, 3], 'probability': .6},
                {'order': [2, 1, 3], 'probability': .3},
                {'order': [3, 1, 2], 'probability': .1},
            ],
        }
        detail = {'id': 'fixture', 'horses': horses,
                  'availableBetTypes': ['単勝', '馬連', '3連単']}
        report = compare_tickets(detail, [scenario], model_version='fixture')
        self.assertEqual(report['decision'], '見送り')
        self.assertEqual(report['items'], [])
        self.assertGreater(report['eligibleCandidateKinds'], 0)
        leader = report['researchLeader']
        self.assertIsNotNone(leader)
        self.assertEqual(leader['status'], 'research-only-not-a-recommendation')
        self.assertIn(leader['kind'], ('単勝', '馬連', '3連単'))
        self.assertLessEqual(leader['points'], 10)
        self.assertLessEqual(leader['conditionalProbabilityRange'][0], 1)

    def test_missing_official_sales_evidence_has_no_candidate(self):
        horses = [
            {'horseNumber': n, 'integratedEvaluation': {'mark': mark}}
            for n, mark in [(1, '◎'), (2, '○'), (3, '▲')]]
        scenario = {'id': 'usual', 'orders': [
            {'order': [1, 2, 3], 'probability': 1.0}]}
        report = compare_tickets(
            {'id': 'fixture', 'horses': horses}, [scenario],
            model_version='fixture')
        self.assertIsNone(report['researchLeader'])
        self.assertEqual(report['eligibleCandidateKinds'], 0)
        self.assertEqual(report['decision'], '見送り')
