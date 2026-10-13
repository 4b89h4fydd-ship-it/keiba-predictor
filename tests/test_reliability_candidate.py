import unittest
from arvexq.research.reliability_candidate import score


class ReliabilityCandidateTests(unittest.TestCase):
    def test_empty_is_unknown(self):
        self.assertIsNone(score({'horseNumber': 1}, {'date': '2026-10-14'}))

    def test_short_history_shrinks(self):
        one = {'recentRaces': [{'date': '2026-10-12', 'fieldSize': 10, 'finish': 1}]}
        five = {'recentRaces': [{'date': f'2026-10-{day:02d}', 'fieldSize': 10, 'finish': 1} for day in (12,10,8,6,4)]}
        race = {'date': '2026-10-14'}
        self.assertGreater(score(five, race), score(one, race))
        self.assertGreater(score(one, race), .5)

    def test_future_result_never_contributes(self):
        horse = {'recentRaces': [{'date': '2026-10-11', 'fieldSize': 10, 'finish': 6}]}
        race = {'date': '2026-10-14'}
        before = score(horse, race)
        horse['recentRaces'].append({'date': '2026-10-16', 'fieldSize': 10, 'finish': 1})
        self.assertEqual(before, score(horse, race))

if __name__ == '__main__':
    unittest.main()
