"""Stage65 research winner ranking regressions; not historical hit-rate evidence."""
import unittest
from arvexq.research.stage65.win_focus import candidates


def race(owner="nar"):
    return {"id": owner+"-2026-10-21-試験場-01", "date":"2026-10-21",
            "circuit":owner,"track":"試験場","surface":"ダート",
            "fieldSize":3,"horses":[
                {"horseNumber":1,"recentRaces":[{"date":"2026-10-18","finish":1,"fieldSize":10},
                    {"date":"2026-10-10","finish":10,"fieldSize":10}]},
                {"horseNumber":2,"recentRaces":[{"date":"2026-10-18","finish":3,"fieldSize":10},
                    {"date":"2026-10-10","finish":3,"fieldSize":10}]},
                {"horseNumber":3,"recentRaces":[{"date":"2026-10-18","finish":8,"fieldSize":10},
                    {"date":"2026-10-10","finish":8,"fieldSize":10}]}]}


class Stage65WinFocus(unittest.TestCase):
    def test_win_and_axis_are_distinct(self):
        p=candidates(race(),expected_circuit="nar")
        self.assertEqual(p["winRole"]["horseNumber"],1)
        self.assertEqual(p["axisRole"]["horseNumber"],2)
        self.assertFalse(p["productionEligible"])
        self.assertFalse(p["independentlyValidated"])

    def test_reject_cross_circuit(self):
        with self.assertRaises(ValueError):
            candidates(race("jra"),expected_circuit="nar")

    def test_no_history_abstains(self):
        r=race()
        r["horses"][0]["recentRaces"]=[]
        p=candidates(r,expected_circuit="nar")
        self.assertEqual(p["status"],"incomplete-evidence")
        self.assertIsNone(p["winRole"])

    def test_postoff_and_odds_not_used(self):
        r=race()
        base=candidates(r,expected_circuit="nar")
        r["result"]={"winner":3}
        for h in r["horses"]:
            h["winOdds"]=0.01
            h["recentRaces"].insert(0,{"date":"2026-10-22","finish":1,"fieldSize":10})
        self.assertEqual(candidates(r,expected_circuit="nar"),base)

    def test_scratched_excluded(self):
        r=race();r["horses"][0]["status"]="競走除外"
        p=candidates(r,expected_circuit="nar")
        self.assertIn("fewer-than-three-active-runners",p["blockers"])

    def test_duplicate_horse_rejected(self):
        r=race();r["horses"][1]["horseNumber"]=1
        with self.assertRaises(ValueError):
            candidates(r,expected_circuit="nar")


if __name__ == "__main__":
    unittest.main()
