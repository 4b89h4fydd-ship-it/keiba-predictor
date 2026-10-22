from copy import deepcopy
from itertools import permutations
from unittest import TestCase

from arvexq.betting.scenario_tickets import KINDS, canonical, compare_tickets, ticket_hit


def race():
    return {'id': 'nar-test', 'placePlaces': 2, 'availableBetTypes': list(KINDS),
            'horses': [{'horseNumber': n, 'frameNumber': (n+1)//2,
                        'integratedEvaluation': {'mark': m}}
                       for n, m in enumerate(['◎', '○', '▲', '△', '☆'], 1)]}


def distribution(order=(1, 2, 3, 4, 5), second=(1, 3, 2, 4, 5)):
    return [{'id': 'solo', 'orders': [{'order': list(order), 'probability': .6},
                                     {'order': list(second), 'probability': .4}]},
            {'id': 'contested', 'orders': [{'order': list(second), 'probability': 1.}]}]


class ScenarioTicketsTests(TestCase):
    def test_all_eight_rules_and_same_frame(self):
        order = (2, 1, 3, 4, 5)
        frames = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3}
        for kind, combo in [('単勝', [2]), ('複勝', [1]), ('枠連', [1, 1]),
                            ('馬連', [1, 2]), ('馬単', [2, 1]), ('ワイド', [1, 3]),
                            ('3連複', [3, 2, 1]), ('3連単', [2, 1, 3])]:
            with self.subTest(kind=kind):
                self.assertTrue(ticket_hit(kind, combo, order, frames=frames, place_places=2))
        self.assertFalse(ticket_hit('複勝', [3], order, place_places=2))
        self.assertFalse(ticket_hit('馬単', [1, 2], order))
        self.assertFalse(ticket_hit('ワイド', [2, 5], order))
        with self.assertRaises(ValueError):
            canonical('馬連', [1, 1])

    def test_all_kinds_compared_without_inventing_accuracy(self):
        detail = race()
        original = deepcopy(detail)
        result = compare_tickets(detail, distribution(), model_version='candidate')
        self.assertEqual(detail, original)
        self.assertEqual([c['kind'] for c in result['comparisons']], list(KINDS))
        self.assertEqual(result['decision'], '見送り')
        self.assertEqual(result['items'], [])
        for c in result['comparisons']:
            self.assertLessEqual(c['points'], 10)
            self.assertIsNone(c['expectedReturnRange'])
            self.assertTrue(c['reason'])

    def test_union_of_overlapping_wide_events_cannot_exceed_one(self):
        rows = [{'order': list(o), 'probability': 1/120} for o in permutations(range(1, 6))]
        result = compare_tickets(race(), [{'id': 'all', 'orders': rows}], model_version='candidate')
        wide = next(c for c in result['comparisons'] if c['kind'] == 'ワイド')
        self.assertAlmostEqual(wide['conditionalProbabilityRange'][0], .6)
        self.assertLessEqual(wide['conditionalProbabilityRange'][1], 1 + 1e-12)
        self.assertEqual(wide['points'], 3)

    def test_scenario_range_not_arbitrary_average(self):
        scenarios = [{'id': 'forward', 'orders': [{'order': [1, 2, 3, 4, 5], 'probability': .9},
                                                {'order': [2, 1, 3, 4, 5], 'probability': .1}]},
                     {'id': 'reverse', 'orders': [{'order': [1, 2, 3, 4, 5], 'probability': .2},
                                                {'order': [2, 1, 3, 4, 5], 'probability': .8}]}]
        result = compare_tickets(race(), scenarios, model_version='candidate')
        win = result['comparisons'][0]
        self.assertEqual(win['conditionalProbabilityRange'], [.2, .9])

    def test_expectation_only_uses_verified_market(self):
        d = race()
        d['preOffMarket'] = {'provenanceVerified': True, 'odds': {'単勝': {'1': 2.5}}}
        result = compare_tickets(d, distribution(), model_version='candidate')
        self.assertEqual(result['comparisons'][0]['expectedReturnRange'], [2.5, 2.5])
        d['preOffMarket']['provenanceVerified'] = False
        self.assertIsNone(compare_tickets(d, distribution(), model_version='candidate')['comparisons'][0]['expectedReturnRange'])

    def test_launch_and_place_terms_are_not_guessed(self):
        d = race()
        d.pop('availableBetTypes')
        result = compare_tickets(d, distribution(), model_version='candidate')
        self.assertTrue(all(c['points'] == 0 for c in result['comparisons']))
        d = race()
        d.pop('placePlaces')
        result = compare_tickets(d, distribution(), model_version='candidate')
        self.assertIn('未確認', result['comparisons'][1]['reason'])

    def test_partial_fields_nan_bad_mass_duplicate_scenarios_rejected(self):
        for scenarios in [[], [{'id': 'x', 'orders': [{'order': [1, 2, 3], 'probability': 1}]}],
                          [{'id': 'x', 'orders': [{'order': [1, 2, 3, 4, 5], 'probability': float('nan')}]}],
                          [{'id': 'x', 'orders': [{'order': [1, 2, 3, 4, 5], 'probability': .5}]}],
                          distribution() * 2]:
            with self.subTest(scenarios=scenarios):
                with self.assertRaises(ValueError):
                    compare_tickets(race(), scenarios, model_version='candidate')

    def test_joint_orders_reject_fractional_and_boolean_horse_ids(self):
        for bad in (1.5, True, float('nan'), float('inf')):
            with self.subTest(bad=bad):
                scenarios = distribution()
                scenarios[0]['orders'][0]['order'][0] = bad
                with self.assertRaises(ValueError):
                    compare_tickets(race(), scenarios, model_version='candidate')

    def test_one_axis_and_budget_enforced(self):
        d = race()
        d['horses'][1]['integratedEvaluation']['mark'] = '◎'
        with self.assertRaises(ValueError):
            compare_tickets(d, distribution(), model_version='candidate')
        for points in (0, 11, True):
            with self.assertRaises(ValueError):
                compare_tickets(race(), distribution(), model_version='candidate', max_points=points)
        result = compare_tickets(race(), distribution(), model_version='candidate', max_points=2)
        self.assertTrue(all(c['points'] <= 2 for c in result['comparisons']))
