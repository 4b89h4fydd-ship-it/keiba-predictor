"""Chronological model fitting is research-only until verified pace/video acceptance."""
from unittest import TestCase
from arvexq.forecast.training import train, test_holdout as evaluate_holdout


def labeled(day):
    race_date="2098-01-"+str(day).zfill(2)
    return {
        "id":f"nar-{race_date}-園田-01","date":race_date,
        "circuit":"地方","track":"園田","surface":"ダート","distance":1400,
        "horses":[
            {"horseNumber":n,"id":100+n,"frameNumber":n,
             "recentRaces":[{"date":"2097-12-15","track":"園田","surface":"ダート",
                             "distance":1400,"fieldSize":3,"finish":n,"cornerPositions":[n]}]}
            for n in (1,2,3)],
        "result":{"status":"確定","finishers":[{"horseNumber":n,"finish":n} for n in (1,2,3)]},
    }


class ChronologicalTrainingTests(TestCase):
    def test_isolated_fit_validation_and_holdout(self):
        races=[labeled(n) for n in range(1,29)]
        model=train(races,circuit="地方",train_before="2098-01-17",
                    validate_before="2098-01-24",min_train=8,min_validation=4,iterations=80)
        self.assertEqual(model["trainingRaceCount"],16)
        self.assertEqual(model["validationRaceCount"],7)
        self.assertEqual(model["trainedThrough"],"2098-01-16")
        self.assertEqual(model["calibratedThrough"],"2098-01-23")
        self.assertFalse(model["scenarioWeightsValidated"])
        self.assertFalse(model["outOfSampleValidated"])
        results=evaluate_holdout(model,races)
        self.assertEqual(results["raceCount"],5)
        self.assertIsNone(results["returnRate"])
        self.assertIsNone(results["videoLift"])

    def test_reject_not_enough_actual_races(self):
        races=[labeled(n) for n in range(1,9)]
        with self.assertRaises(ValueError):
            train(races,circuit="地方",train_before="2098-01-06",
                  validate_before="2098-01-09")
