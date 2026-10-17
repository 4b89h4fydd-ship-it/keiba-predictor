"""Complementary scenario tickets must not be filtered before union coverage."""
import unittest

from arvexq.betting.scenario_tickets import compare_tickets


class ResearchScenarioTicketTests(unittest.TestCase):
    def test_two_complementary_pairs_cover_both_scenarios(self):
        detail = {
            'id': 'test-race',
            'availableBetTypes': ['馬連'],
            'horses': [
                {'horseNumber': 1, 'integratedEvaluation': {'mark': '◎'}},
                {'horseNumber': 2, 'integratedEvaluation': {'mark': '○'}},
                {'horseNumber': 3, 'integratedEvaluation': {'mark': '▲'}},
            ],
        }
        scenarios = [
            {'id': 'front', 'orders': [{'order': [1, 2, 3], 'probability': 1.0}]},
            {'id': 'back', 'orders': [{'order': [1, 3, 2], 'probability': 1.0}]},
        ]
        plan = compare_tickets(detail, scenarios, model_version='test-model', max_points=2)
        pairs = next(r for r in plan['comparisons'] if r['kind'] == '馬連')
        self.assertEqual(pairs['points'], 2)
        self.assertEqual({tuple(c) for c in pairs['combos']}, {(1, 2), (1, 3)})
        self.assertEqual(pairs['conditionalProbabilityRange'], [1.0, 1.0])
        self.assertEqual(plan['researchLeader']['kind'], '馬連')
        self.assertEqual(plan['decision'], '見送り')
        self.assertEqual(plan['items'], [])

    def test_single_point_cannot_claim_robust_coverage(self):
        detail = {
            'id': 'test-race',
            'availableBetTypes': ['馬連'],
            'horses': [
                {'horseNumber': 1, 'integratedEvaluation': {'mark': '◎'}},
                {'horseNumber': 2, 'integratedEvaluation': {'mark': '○'}},
                {'horseNumber': 3, 'integratedEvaluation': {'mark': '▲'}},
            ],
        }
        scenarios = [
            {'id': 'front', 'orders': [{'order': [1, 2, 3], 'probability': 1.0}]},
            {'id': 'back', 'orders': [{'order': [1, 3, 2], 'probability': 1.0}]},
        ]
        plan = compare_tickets(detail, scenarios, model_version='test-model', max_points=1)
        pairs = next(r for r in plan['comparisons'] if r['kind'] == '馬連')
        self.assertEqual(pairs['points'], 1)
        self.assertEqual(pairs['conditionalProbabilityRange'], [0.0, 1.0])
        self.assertEqual(plan['decision'], '見送り')


if __name__ == '__main__':
    unittest.main()
