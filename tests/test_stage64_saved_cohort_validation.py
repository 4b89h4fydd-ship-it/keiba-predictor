"""Validate the 527-race Stage64 saved-data report, not future performance.

Regression gate catches accidental fabricated return rates, cohort deletion,
and copying the most attractive NAR arm into JRA production decisions.
"""
import json
from pathlib import Path
import unittest

RESULTS = Path(__file__).resolve().parents[1] / "docs/research/stage64-results/summary.json"


class ArchivedRaceValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(RESULTS.read_text(encoding="utf-8"))

    def test_all_527_saved_races_and_three_variants_remain(self):
        circuits = self.report["byCircuit"]
        self.assertEqual(set(circuits), {"jra", "nar"})
        for owner, cohort in (("jra",108),("nar",419)):
            self.assertEqual(set(circuits[owner]), {"baseline","recent5","recent5_shrunk"})
            for arm in circuits[owner].values():
                self.assertEqual(arm["cohortRaces"],cohort)
                self.assertEqual(arm["scoredRaces"]+arm["unscoredRaces"],cohort)
                self.assertEqual(arm["winnerTop1Hits"] <= arm["scoredRaces"], True)
                self.assertEqual(arm["trifectaHits"] <= arm["scoredRaces"], True)
                self.assertAlmostEqual(arm["coverage"],arm["scoredRaces"]/cohort)
                self.assertAlmostEqual(arm["trifectaHitRateScored"],
                                       arm["trifectaHits"]/arm["scoredRaces"])
                self.assertFalse(arm["target80Observed"])
                self.assertFalse(arm["target90Observed"])

    def test_jra_roi_not_invented(self):
        for arm in self.report["byCircuit"]["jra"].values():
            self.assertIsNone(arm["roiPct"])
            self.assertIsNone(arm["returnYen"])
            self.assertLess(arm["payoutCoveredScoredRaces"],arm["scoredRaces"])

    def test_nar_return_concentration_must_be_exposed(self):
        circuits=self.report["byCircuit"]["nar"]
        for name in ("recent5","recent5_shrunk"):
            arm=circuits[name]
            self.assertGreater(arm["roiPct"],100)
            self.assertGreater(arm["top2ReturnShare"],.75)
            self.assertLess(arm["roiWithoutTwoLargestReturnsPct"],40)
            self.assertEqual(arm["payoutCoveredScoredRaces"],arm["scoredRaces"])

    def test_do_not_promote_retrospective_results_as_independent(self):
        self.assertFalse(self.report.get("independentlyVerifiedPreoff", False))
        self.assertFalse(self.report.get("productionEligible", False))


if __name__=="__main__":
    unittest.main()
