import unittest

from arvexq.prediction.mass_training_dataset import split_walk_forward


class FrozenMassTrainingInputTests(unittest.TestCase):
    def test_fractional_and_boolean_runner_id_or_result_rank_rejected(self):
        from copy import deepcopy
        from arvexq.prediction.mass_training_dataset import rows_from_frozen_snapshot

        snapshot = {
            "raceId": "jra-2026-10-01-test-01",
            "date": "2026-10-01",
            "circuit": "中央",
            "horseCount": 3,
            "rows": [
                {"horseNumber": 1, "name": "一", "features": {"history::win": 0.1}},
                {"horseNumber": 2, "name": "二", "features": {"history::win": 0.2}},
                {"horseNumber": 3, "name": "三", "features": {"history::win": 0.3}},
            ],
        }
        result = {"finishers": [
            {"horseNumber": 1, "finish": 1},
            {"horseNumber": 2, "finish": 2},
            {"horseNumber": 3, "finish": 3},
        ]}
        self.assertEqual(len(rows_from_frozen_snapshot(snapshot, result)), 3)
        for bad in (2.5, True, float("nan"), float("inf")):
            with self.subTest(bad=bad):
                broken = deepcopy(result)
                broken["finishers"][1]["finish"] = bad
                self.assertEqual(rows_from_frozen_snapshot(snapshot, broken), [])
                broken = deepcopy(result)
                broken["finishers"][1]["horseNumber"] = bad
                self.assertEqual(rows_from_frozen_snapshot(snapshot, broken), [])
                broken_snapshot = deepcopy(snapshot)
                broken_snapshot["rows"][1]["horseNumber"] = bad
                self.assertEqual(rows_from_frozen_snapshot(broken_snapshot, result), [])


class TemporalSplitTests(unittest.TestCase):
    def test_one_day_is_not_three_independent_periods(self):
        rows = [{"raceId": f"r{i}", "date": "2026-10-10"} for i in range(20)]
        split = split_walk_forward(rows)
        self.assertFalse(split["valid"])
        self.assertFalse(split["test"])

    def test_days_and_races_stay_together(self):
        rows = [{"raceId": f"d{d}r{r}", "date": f"2026-10-{d:02d}", "horseNumber": h}
                for d in range(1, 11) for r in range(3) for h in (1, 2)]
        split = split_walk_forward(rows)
        dates = {k: {r["date"] for r in v} for k, v in split.items()}
        self.assertLess(max(dates["train"]), min(dates["valid"]))
        self.assertLess(max(dates["valid"]), min(dates["test"]))
        self.assertEqual(sum(map(len, split.values())), len(rows))

    def test_invalid_or_conflicting_race_dates_fail_closed(self):
        for rows in ([{"raceId": "r", "date": ""}],
                     [{"raceId": "r", "date": "2026-10-01"},
                      {"raceId": "r", "date": "2026-10-02"}]):
            with self.assertRaises(ValueError):
                split_walk_forward(rows)

    def test_invalid_ratios_rejected(self):
        with self.assertRaises(ValueError):
            split_walk_forward([], train_ratio=.9, valid_ratio=.2)


if __name__ == "__main__":
    unittest.main()
