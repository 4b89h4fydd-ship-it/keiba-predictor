"""Keep research priority on ◎【単】 / ◎【軸】 without selecting by archived luck."""
import unittest
from pathlib import Path
import json
from scripts.arvexq_stage64_honmei_review import report,wilson


class HonmeiReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src=json.loads((Path(__file__).parents[1]/"docs/research/stage64-results/summary.json").read_text())
        cls.data=report(cls.src)

    def test_winner_first_axis_second_and_never_promote(self):
        self.assertFalse(self.data["productionEligible"])
        self.assertTrue(self.data["bettingIsDownstream"])
        for owner in ("jra","nar"):
            self.assertFalse(self.data["circuits"][owner]["selectionPermitted"])
            self.assertEqual(len(self.data["circuits"][owner]["arms"]),3)

    def test_saved_winner_counts_match(self):
        j=self.data["circuits"]["jra"]["arms"]["baseline"]
        n=self.data["circuits"]["nar"]["arms"]["recent5"]
        self.assertEqual((j["winHits"],j["eligible"],j["totalRaces"]),(20,87,108))
        self.assertEqual((n["winHits"],n["eligible"],n["totalRaces"]),(97,332,419))
        self.assertEqual(n["axisTop3Hits"],208)
        self.assertAlmostEqual(n["winHitRateScored"],97/332)
        self.assertAlmostEqual(j["winHitRateAllRaces"],20/108)

    def test_uncertainty_and_coverage(self):
        lo,hi=wilson(97,332)
        self.assertLess(lo,97/332)
        self.assertGreater(hi,97/332)
        self.assertIsNone(wilson(0,0))
        for owner in ("jra","nar"):
            for v in self.data["circuits"][owner]["arms"].values():
                self.assertEqual(v["eligible"]+v["unscored"],v["totalRaces"])
                self.assertLess(v["coverage"],1)
                self.assertGreaterEqual(v["axisTop3HitRateAllRaces"],0)

    def test_reject_unverified_change_of_source_status(self):
        d=dict(self.src,independentlyVerifiedPreoff=True)
        with self.assertRaises(ValueError):report(d)


if __name__=="__main__":unittest.main()
