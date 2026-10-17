"""Regression: a low top-three range must not erase the only research honmei."""
import unittest
from arvexq.prediction.new_forecast import _decide


class HonmeiSelectionTests(unittest.TestCase):
    def test_low_top3_win_leader_still_marked_once(self):
        reports = [
            {'horseNumber': n, 'featureValues': {'closing_gain': 0.0}}
            for n in (1, 2, 3)
        ]
        scenario = {'probabilities': {
            1: {'win': .51, 'top2': .54, 'top3': .56},
            2: {'win': .35, 'top2': .70, 'top3': .86},
            3: {'win': .14, 'top2': .76, 'top3': .90},
        }}
        marks, ranges, reasons = _decide({'reports': reports, 'scenarios': [scenario]})
        self.assertEqual(marks[1], '◎')
        self.assertEqual(list(marks.values()).count('◎'), 1)
        self.assertIn('安定性に懸念', reasons[1])
        self.assertEqual(ranges[1]['win'][0], .51)

    def test_no_model_does_not_invent_honmei(self):
        marks, ranges, reasons = _decide({'reports': [], 'scenarios': []})
        self.assertEqual(marks, {})
        self.assertEqual(ranges, {})
        self.assertEqual(reasons, {})


if __name__ == '__main__':
    unittest.main()
