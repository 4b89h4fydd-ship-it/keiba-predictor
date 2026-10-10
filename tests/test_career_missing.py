import unittest
from arvexq.horse_detail import build_horse_detail
from arvexq.diagnosis import diagnose_horse

RACE = {'date': '2026-02-01'}


def run(**kw):
    r = {'date': '2026-01-01', 'finish': 1, 'fieldSize': 10,
         'surface': 'ダート', 'condition': '良', 'distance': 1200}
    r.update(kw)
    return r


def analyze(rows, race=RACE):
    return build_horse_detail({'recentRaces': rows}, race)['careerAnalysis']


class CareerMissingTests(unittest.TestCase):
    def test_missing_field_is_not_absent_history(self):
        a = analyze([{'date': '2026-01-01', 'finish': 1}])
        self.assertEqual(a['data_limitation'], 'partial')
        self.assertEqual(a['history_status'], 'history-present-but-unusable')
        self.assertIn('field_size', a['missing_fields'])
        self.assertEqual(a['analyzed_runs'], 0)
        self.assertIsNone(a['recent_stats']['top3_rate'])

    def test_empty_history(self):
        a = analyze([])
        self.assertEqual(a['data_limitation'], 'no_runs')
        self.assertEqual(a['history_status'], 'no-runs')

    def test_only_valid_rows_contribute_to_statistics(self):
        a = analyze([run(), run(date='2026-01-02', fieldSize=None)])
        self.assertEqual(a['analyzed_runs'], 1)
        self.assertEqual(a['recent_stats']['top3_rate'], 1)
        self.assertEqual(a['unusable_dated_records'], 1)
        self.assertEqual(a['data_limitation'], 'partial')

    def test_missing_finish(self):
        a = analyze([run(finish=None)])
        self.assertIn('finish_position', a['missing_fields'])
        self.assertEqual(a['analyzed_runs'], 0)

    def test_same_day_future_undated_excluded(self):
        a = analyze([run(date='2026-02-01', fieldSize=None),
                     run(date='2026-02-02', fieldSize=None),
                     run(date=None, fieldSize=None)])
        self.assertEqual(a['analyzed_runs'], 0)
        self.assertEqual(a['unusable_dated_records'], 0)
        self.assertEqual(a['history_status'], 'no-eligible-dated-runs')

    def test_duplicate_invalid_record(self):
        r = run(fieldSize=None)
        h = {'recentRaces': [r], 'allPastRuns': [r]}
        a = build_horse_detail(h, RACE)['careerAnalysis']
        self.assertEqual(a['unusable_dated_records'], 1)

    def test_unknown_target_date(self):
        a = analyze([run()], {})
        self.assertEqual(a['history_status'], 'race-date-unverified')
        self.assertEqual(a['analyzed_runs'], 0)

    def test_diagnosis_exposes_missing_state(self):
        h = {'horseNumber': 1, 'recentRaces': [run(fieldSize=None)]}
        d = diagnose_horse(h, RACE)
        self.assertEqual(d['careerAnalysis']['data_limitation'], 'partial')
        self.assertEqual(d['careerAnalysis'], d['horseDetail']['careerAnalysis'])

    def test_all_eight_runs_and_five_display_preserved(self):
        h = {'recentRaces': [run(date=f'2026-01-{i:02d}') for i in range(1, 9)]}
        d = build_horse_detail(h, RACE)
        self.assertEqual(d['careerAnalysis']['analyzed_runs'], 8)
        self.assertEqual(len(d['recentFive']), 5)


if __name__ == '__main__':
    unittest.main()
