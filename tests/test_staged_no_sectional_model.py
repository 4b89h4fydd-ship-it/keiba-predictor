import unittest
from arvexq.prediction.factor_model import rank_factor_model,PRIMARY_PILLARS

class StageModelTest(unittest.TestCase):
    def test_no_inert_sectional_factor(self):
        race={"date":"2026-10-14","distance":1400,"surface":"ダート"}
        horses=[{"horseNumber":i,"recentRaces":[{"date":"2026-10-10","finish":i,"fieldSize":10,
          "distance":1400,"surface":"ダート"}]} for i in (1,2,3)]
        rows=rank_factor_model(horses,race)
        self.assertEqual(PRIMARY_PILLARS,("recentForm","conditionForm"))
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]["horse"]["horseNumber"],1)
        self.assertNotIn("sectional",rows[0]["factors"])

if __name__=="__main__":
    unittest.main()
