import unittest

from arvexq.prediction.mass_training_dataset import split_walk_forward


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
