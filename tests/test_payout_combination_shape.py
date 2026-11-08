"""Standing check payout_combination_shape (arvexq.results.state).

Stored payout rows must carry a combination whose shape matches the
bet type. The corrupt rows below are the shape the JRA payout-parser
defect stored on 2026-11-08 (Tokyo 11R): popularity numbers and
neighbouring amounts in the combination field, and one combination
repeated with two amounts.
"""
import unittest

from arvexq.results.state import payout_combination_violations, result_state


CORRUPT = [
    {"type": "単勝", "combination": "6", "amount": 7420},
    {"type": "複勝", "combination": "6", "amount": 1960},
    {"type": "複勝", "combination": "15", "amount": 1020},
    {"type": "複勝", "combination": "15", "amount": 1200},
    {"type": "ワイド", "combination": "6-15", "amount": 29720},
    {"type": "ワイド", "combination": "133", "amount": 35470},
    {"type": "ワイド", "combination": "6-12", "amount": 17450},
    {"type": "3連単", "combination": "6-15-12", "amount": 12065300},
]

CORRECT = [
    {"type": "単勝", "combination": "6", "amount": 7420},
    {"type": "複勝", "combination": "6", "amount": 1960},
    {"type": "複勝", "combination": "15", "amount": 1020},
    {"type": "複勝", "combination": "12", "amount": 1200},
    {"type": "ワイド", "combination": "6-15", "amount": 29720},
    {"type": "ワイド", "combination": "6-12", "amount": 35470},
    {"type": "ワイド", "combination": "12-15", "amount": 17450},
    {"type": "3連単", "combination": "6-15-12", "amount": 12065300},
]


def _detail(payouts):
    return {
        "id": "jra-2026-11-08-東京-11",
        "result": {
            "status": "確定",
            "finishers": [
                {"finish": 1, "horseNumber": 6},
                {"finish": 2, "horseNumber": 15},
                {"finish": 3, "horseNumber": 12},
            ],
            "payouts": payouts,
        },
    }


class PayoutCombinationShapeTests(unittest.TestCase):
    def test_corrupt_rows_are_flagged_with_race_and_type(self):
        violations = payout_combination_violations(_detail(CORRUPT))
        flagged = {(v["type"], v["combination"]) for v in violations}
        self.assertIn(("ワイド", "133"), flagged)
        self.assertIn(("複勝", "15"), flagged)  # duplicate combination
        for v in violations:
            self.assertEqual(v["race_id"], "jra-2026-11-08-東京-11")
            self.assertTrue(v["reason"])

    def test_out_of_range_single_number_is_flagged(self):
        detail = _detail([{"type": "複勝", "combination": "170", "amount": 260}])
        violations = payout_combination_violations(detail)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["type"], "複勝")

    def test_correct_rows_pass(self):
        self.assertEqual(payout_combination_violations(_detail(CORRECT)), [])

    def test_result_state_marks_corrupt_payouts_incomplete(self):
        _, payout_ok, _ = result_state(_detail(CORRUPT))
        self.assertFalse(payout_ok)
        _, payout_ok, _ = result_state(_detail(CORRECT))
        self.assertTrue(payout_ok)

    def test_frame_pair_uses_frame_range(self):
        detail = _detail([{"type": "枠連", "combination": "8-8", "amount": 27980}])
        self.assertEqual(payout_combination_violations(detail), [])
        detail = _detail([{"type": "枠連", "combination": "8-11", "amount": 100}])
        self.assertEqual(len(payout_combination_violations(detail)), 1)


if __name__ == "__main__":
    unittest.main()
