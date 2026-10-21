"""Regression coverage for evidence-complete winner-top1 research training.

No production prediction, network access or score weighting is activated.
"""
import unittest

from arvexq.prediction.mass_training_dataset import rows_from_frozen_snapshot
from arvexq.prediction.mass_model_training import _race_winner_top1, _training_circuit


class RebuiltWinnerTop1TrainingTests(unittest.TestCase):
    def snapshot(self):
        return {
            "raceId": "nar-2026-10-21-門別-12",
            "date": "2026-10-21",
            "circuit": "地方",
            "track": "門別",
            "raceNumber": 12,
            "horseCount": 3,
            "rows": [
                {"horseNumber": n, "name": str(n), "features": {"static::age": 5.0 + n}}
                for n in (1, 2, 3)
            ],
        }

    def result(self):
        return {"finishers": [
            {"horseNumber": 1, "finish": 2},
            {"horseNumber": 2, "finish": 1},
            {"horseNumber": 3, "finish": 3},
        ]}

    def test_complete_frozen_field_yields_exact_labels(self):
        rows = rows_from_frozen_snapshot(self.snapshot(), self.result())
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(row["labelWin"] for row in rows), 1)
        self.assertEqual(_race_winner_top1(rows, [0.2, 0.8, 0.1])["winnerTop1Rate"], 1.0)

    def test_incomplete_result_does_not_create_easier_training_race(self):
        incomplete = {"finishers": self.result()["finishers"][:2]}
        self.assertEqual(rows_from_frozen_snapshot(self.snapshot(), incomplete), [])

    def test_duplicate_or_ambiguous_frozen_field_does_not_train(self):
        snap = self.snapshot()
        snap["rows"][2]["horseNumber"] = 2
        self.assertEqual(rows_from_frozen_snapshot(snap, self.result()), [])
        snap2 = self.snapshot()
        snap2["horseCount"] = 4
        self.assertEqual(rows_from_frozen_snapshot(snap2, self.result()), [])

    def test_unresolved_winner_does_not_train(self):
        results = self.result()
        results["finishers"][1]["finish"] = 2
        self.assertEqual(rows_from_frozen_snapshot(self.snapshot(), results), [])

    def test_central_local_training_isolated(self):
        self.assertEqual(_training_circuit([{"circuit": "中央"}, {"circuit": "jra"}]), "jra")
        self.assertEqual(_training_circuit([{"circuit": "地方"}, {"circuit": "nar"}]), "nar")
        with self.assertRaises(ValueError):
            _training_circuit([{"circuit": "中央"}, {"circuit": "地方"}])
        with self.assertRaises(ValueError):
            _training_circuit([{"circuit": "unknown"}])

    def test_winner_top1_has_explicit_coverage_and_tie_exclusion(self):
        rows = rows_from_frozen_snapshot(self.snapshot(), self.result())
        metrics = _race_winner_top1(rows, [0.2, 0.8, 0.1])
        self.assertEqual((metrics["cohortRaces"], metrics["scoredRaces"], metrics["winnerTop1Hits"]), (1, 1, 1))
        self.assertEqual(metrics["byCircuit"]["地方"]["hits"], 1)
        tied = _race_winner_top1(rows, [0.8, 0.8, 0.1])
        self.assertEqual(tied["scoredRaces"], 0)
        self.assertEqual(tied["tiedPredictionRaces"], 1)
        self.assertIsNone(tied["winnerTop1Rate"])
        with self.assertRaises(ValueError):
            _race_winner_top1(rows, [0.2, 0.8])

    def test_invalid_labelled_holdout_is_not_scored(self):
        rows = rows_from_frozen_snapshot(self.snapshot(), self.result())
        rows[0]["horseNumber"] = rows[1]["horseNumber"]
        metrics = _race_winner_top1(rows, [0.1, 0.8, 0.1])
        self.assertEqual(metrics["scoredRaces"], 0)
        self.assertEqual(metrics["incompleteOrInvalidRaces"], 1)


if __name__ == "__main__":
    unittest.main()
