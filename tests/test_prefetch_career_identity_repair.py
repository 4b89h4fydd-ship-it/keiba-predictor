"""Retain every observed career start even if run counts are unchanged."""
import unittest
from scripts.arvexq_select_prefetch_repairs import repair_reason


def card(runs):
    return {'id': 'jra-test', 'date': '2026-10-17',
            'horses': [{'horseNumber': 1, 'name': 'A', 'allPastRuns': runs},
                       {'horseNumber': 2, 'name': 'B', 'allPastRuns': []}],
            'preparedMeta': {'diagnosisReady': True}}


class CareerIdentityRepairTests(unittest.TestCase):
    def test_same_count_different_observation_is_repaired(self):
        fresh = card([{'date': '2026-09-01', 'track': '東京', 'finish': 1}])
        stored = card([{'date': '2026-08-01', 'track': '東京', 'finish': 1}])
        self.assertEqual(repair_reason(fresh, stored), 'career_history_missing_observations')

    def test_equivalent_history_not_rewritten(self):
        fresh = card([{'date': '2026-09-01', 'track': '東京', 'finish': 1}])
        self.assertEqual(repair_reason(fresh, card([{'date': '2026-09-01', 'track': '東京', 'finish': 1}])), '')

    def test_corrupt_archive_requires_repair(self):
        fresh = card([{'date': '2026-09-01', 'track': '東京', 'finish': 1}])
        stored = card([])
        stored['horses'][0]['careerArchive'] = {'encoding': 'broken'}
        self.assertEqual(repair_reason(fresh, stored), 'career_archive_invalid')


if __name__ == '__main__':
    unittest.main()
