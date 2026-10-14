"""Identical five-race Mineta research comparator; missing inputs are not hits."""
import unittest
from scripts.arvexq_sequential_candidate_audit import summarize_five

METHODS=("mineta_field_proxy","mineta_current_60_40",
         "mineta_margin_60_40","mineta_current_margin_60_20_20")

class SameFiveMinetaComparison(unittest.TestCase):
    def test_all_four_models_on_same_two_jra_three_nar(self):
        races=[]
        for i in range(5):
            races.append({"raceId":str(i),"circuit":"中央" if i<2 else "地方",
                          "currentWinnerRank":1 if i<2 else 3,
                          "mixedForecasts":{m:{"topHorse":i+1,
                              "winnerRank":1 if i<2 else 3} for m in METHODS}})
        comp,coverage=summarize_five(races)
        self.assertTrue(coverage["allThreeCombinationsComparableOnFive"])
        self.assertEqual(coverage["fullyComparableRaces"],5)
        for name in ("current",)+METHODS:
            self.assertEqual(comp[name]["eligible"],5)
            self.assertEqual(comp[name]["top1Hits"],2)
            self.assertEqual(comp[name]["winnerTop3Hits"],5)
            self.assertEqual(comp[name]["byCircuit"]["中央"]["eligible"],2)
            self.assertEqual(comp[name]["byCircuit"]["地方"]["eligible"],3)

    def test_missing_margin_does_not_count_as_defeat_or_win(self):
        rows=[{"raceId":str(i),"circuit":"地方","currentWinnerRank":1,
               "mixedForecasts":{name:({"status":"missing-required-evidence"}
                    if name=="mineta_margin_60_40" else
                    {"winnerRank":1}) for name in METHODS}} for i in range(5)]
        comp,coverage=summarize_five(rows)
        self.assertEqual(comp["mineta_margin_60_40"]["eligible"],0)
        self.assertIsNone(comp["mineta_margin_60_40"]["top1Rate"])
        self.assertFalse(coverage["allThreeCombinationsComparableOnFive"])
        self.assertEqual(coverage["fullyComparableRaces"],0)
        self.assertEqual(comp["mineta_current_60_40"]["top1Hits"],5)

if __name__=="__main__":
    unittest.main()
