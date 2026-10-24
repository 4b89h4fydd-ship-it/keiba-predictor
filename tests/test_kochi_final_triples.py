"""Kochi final race: tri-only pre-off candidates must not discard unmarked horses."""
from copy import deepcopy
from unittest import TestCase
from arvexq.forecast.tickets import generate_tickets


class KochiFinalTripleCoverageTests(TestCase):
    def setUp(self):
        self.probabilities = {
            (1, 2, 6): .42,
            (6, 1, 2): .28,
            (1, 3, 4): .15,
            (2, 3, 6): .08,
            (1, 2, 3): .07,
        }
        self.prediction = {'predictionStatus': 'ready',
                           'stages': {'probability': {'value': {'trifecta': self.probabilities}}}}
        self.marks = [{'horseNumber': n, 'mark': m}
                      for n, m in zip((1, 2, 3, 4, 5), ('◎', '○', '▲', '△', '☆'))]
        self.race = {'id': 'nar-2026-10-24-高知-12', 'track': '高知',
                     'title': 'ファイナルレースＣ３－１９記者選抜'}

    def test_unmarked_third_candidate_is_eligible(self):
        previous = deepcopy((self.prediction, self.marks, self.race))
        bets = generate_tickets(self.prediction, self.marks, race=self.race)
        self.assertEqual([b['kind'] for b in bets], ['3連複', '3連単'])
        self.assertEqual(sum(b['points'] for b in bets), 5)
        self.assertIn([1, 2, 6], bets[0]['combos'])
        self.assertTrue(any(6 in combo for bet in bets for combo in bet['combos']))
        self.assertEqual(previous, (self.prediction, self.marks, self.race))

    def test_historical_outcome_is_never_used_to_reorder_candidates(self):
        before = generate_tickets(self.prediction, self.marks, race=self.race)
        result_detail = {**self.race, 'result': {'finishers': [
            {'horseNumber': 5, 'finish': 1},
            {'horseNumber': 4, 'finish': 2},
            {'horseNumber': 3, 'finish': 3}]}}
        self.assertEqual(before, generate_tickets(self.prediction, self.marks, race=result_detail))

    def test_other_circuits_and_nonfinal_races_keep_existing_mix(self):
        for race in ({'track': '高知', 'title': '通常レース'},
                     {'track': '大井', 'title': 'ファイナルレース'},
                     {'track': '東京', 'title': 'ファイナルレース'}):
            bets = generate_tickets(self.prediction, self.marks, race=race)
            self.assertTrue(bets)
            self.assertNotEqual({x['kind'] for x in bets}, {'3連複', '3連単'})
            self.assertLessEqual(sum(x['points'] for x in bets), 5)

    def test_fail_closed_on_missing_or_invalid_joint(self):
        bad = deepcopy(self.prediction)
        bad['stages']['probability']['value']['trifecta'] = {(1, 2, 6): float('nan')}
        self.assertEqual(generate_tickets(bad, self.marks, race=self.race), [])
        bad['stages']['probability']['value']['trifecta'] = {}
        self.assertEqual(generate_tickets(bad, self.marks, race=self.race), [])
