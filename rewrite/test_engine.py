"""Replacement core regression: no leakage, no fabricated forecasts or bets."""
import unittest
from rewrite.engine import forecast, normalize_race

def race():
    return {"id": "nar-2026-10-29-大井-01", "date": "2026-10-29",
            "circuit": "地方", "track": "大井", "surface": "ダート",
            "distance": 1600, "horses": [
                {"horseNumber": i, "name": f"Horse {i}", "recentRaces": [
                    {"date": "2026-10-01", "fieldSize": 8, "finish": i,
                     "cornerPositions": [i, i], "distance": 1600,
                     "track": "大井", "surface": "ダート"}]}
                for i in range(1, 7)]}

class EngineContract(unittest.TestCase):
    def test_complete_race(self):
        prediction = forecast(race())
        self.assertEqual([r["mark"] for r in prediction["rows"]], ["◎", "○", "▲", "△", "☆", ""])
        self.assertEqual(len(prediction["pace"]["start"]), 6)
        self.assertEqual(prediction["bets"], [])
        self.assertEqual(prediction["betDecision"], "見送り")
        self.assertTrue(all(x["winProbability"] is None for x in prediction["rows"]))

    def test_no_history_no_fake_marks(self):
        p = race()
        p["horses"][0]["recentRaces"] = []
        x = forecast(p)
        self.assertEqual(x["status"], "insufficient-horse-evidence")
        self.assertTrue(all(not h["mark"] for h in x["rows"]))
        self.assertEqual(x["missingEvidence"], [1])

    def test_no_lookahead(self):
        p = race()
        p["horses"][0]["recentRaces"].append(
            {"date": "2026-10-30", "fieldSize": 8, "finish": 1})
        self.assertEqual(forecast(p)["rows"][0]["evidenceCount"], 1)

    def test_duplicates_rejected(self):
        p = race()
        p["horses"][1]["horseNumber"] = 1
        with self.assertRaises(ValueError): normalize_race(p)

    def test_banei_rejected(self):
        p = race()
        p["track"] = "帯広"
        with self.assertRaises(ValueError): forecast(p)

    def test_central_separate(self):
        p = race()
        p["circuit"] = "中央"
        self.assertEqual(forecast(p)["circuit"], "中央")

if __name__ == "__main__":
    unittest.main()
