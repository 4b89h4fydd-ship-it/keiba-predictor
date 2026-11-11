import unittest
from unittest.mock import patch
from arvexq.prediction.condition_records_v3 import record_splits

class ConditionRecordV3Tests(unittest.TestCase):
    def setUp(self):
        self.race={"date":"2026-10-16","track":"園田","distance":1400,"surface":"ダート","direction":"右","going":"良"}
        self.horse={"horseNumber":1}
        self.rows=[
            {"finish":1,"track":"園田","distance":1400,"surface":"ダート","direction":"右","condition":"良"},
            {"finish":2,"track":"園田","distance":1400,"surface":"ダート","direction":"右","condition":"稍重"},
            {"finish":3,"track":"園田","distance":1200,"surface":"ダート","direction":"右","condition":"良"},
            {"finish":8,"track":"大井","distance":1400,"surface":"ダート","direction":"右","condition":"良"},
        ]
    def test_exact_distance_rates(self):
        with patch("arvexq.prediction.condition_records_v3.observed_runs",return_value=self.rows):
            x=record_splits(self.horse,self.race)["splits"]
        self.assertEqual(x["career"]["starts"],4)
        self.assertEqual(x["career"]["winRate"],.25)
        self.assertEqual(x["career"]["top2Rate"],.5)
        self.assertEqual(x["career"]["top3Rate"],.75)
        self.assertEqual(x["sameDistance"]["starts"],3)
        self.assertEqual(x["sameDistance"]["winRate"],1/3)
        self.assertEqual(x["trackDistance"]["starts"],2)
        self.assertEqual(x["trackDistance"]["top3Rate"],1)
        self.assertEqual(x["sameGoing"]["starts"],3)
    def test_unknown_not_fabricated(self):
        with patch("arvexq.prediction.condition_records_v3.observed_runs",return_value=[]):
            x=record_splits(self.horse,self.race)["splits"]
        self.assertIsNone(x["sameDistance"]["winRate"])
        self.assertEqual(x["sameDistance"]["starts"],0)
