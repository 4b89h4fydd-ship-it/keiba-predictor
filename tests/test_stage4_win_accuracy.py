"""Stage4 archived winner accuracy regression; no forecast/model/product calls.

This test reads the existing retrospective Stage64 report ONLY. It must not
be taken as an independently witnessed pre-off prediction result.
"""
from collections import Counter, defaultdict
import csv
import json
from math import comb
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/research/stage64-results"
ARMS = ("baseline", "recent5", "recent5_shrunk")


def paired_counts(rows, owner):
    table = Counter()
    for (circuit, _), arms in rows.items():
        if circuit != owner or arms["baseline"]["scored"] != "True":
            continue
        b = arms["baseline"]["winnerTop1"] == "True"
        r = arms["recent5"]["winnerTop1"] == "True"
        table[(b, r)] += 1
    return (table[(True, True)], table[(True, False)],
            table[(False, True)], table[(False, False)])


def exact_paired_pvalue(baseline_only, recent_only):
    """Exact two-sided binomial McNemar, used for diagnosis, not adoption."""
    discordant = baseline_only + recent_only
    if not discordant:
        return 1.0
    k = min(baseline_only, recent_only)
    return min(1.0, 2 * sum(comb(discordant, i) for i in range(k + 1)) / 2 ** discordant)


class Stage4ArchiveWinnerAccuracyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (EVIDENCE / "race_metrics.csv").open(encoding="utf-8-sig", newline="") as fh:
            cls.raw_rows = list(csv.DictReader(fh))
        cls.summary = json.loads((EVIDENCE / "summary.json").read_text(encoding="utf-8"))
        cls.races = defaultdict(dict)
        for row in cls.raw_rows:
            owner, rid, arm = row["circuit"], row["raceId"], row["arm"]
            if arm in cls.races[(owner, rid)]:
                raise AssertionError("duplicate archive arm/race")
            cls.races[(owner, rid)][arm] = row

    def test_full_archive_identity_and_circuit_separation(self):
        self.assertEqual((len(self.raw_rows), len(self.races)), (1581, 527))
        self.assertEqual(set(self.summary["byCircuit"]), {"jra", "nar"})
        for (owner, rid), arms in self.races.items():
            self.assertTrue(rid.startswith(owner + "-"), rid)
            self.assertEqual(set(arms), set(ARMS))
            self.assertEqual({r["date"] for r in arms.values()}, {arms["baseline"]["date"]})
            self.assertEqual({r["scored"] for r in arms.values()}, {arms["baseline"]["scored"]})
            self.assertTrue(all(r["circuit"] == owner for r in arms.values()))

    def test_unscored_races_retained_and_never_treated_as_losses(self):
        expected = {"jra": (108, 87, 21), "nar": (419, 332, 87)}
        for owner, (total, eligible, missing) in expected.items():
            cohort = [arms for (c, _), arms in self.races.items() if c == owner]
            self.assertEqual(len(cohort), total)
            self.assertEqual(sum(a["baseline"]["scored"] == "True" for a in cohort), eligible)
            blocked = [a for a in cohort if a["baseline"]["scored"] == "False"]
            self.assertEqual(len(blocked), missing)
            for arms in blocked:
                for arm in ARMS:
                    row = arms[arm]
                    self.assertEqual(row["winnerTop1"], "False")
                    self.assertEqual(row["logloss"], "")
                    self.assertEqual(row["brier"], "")
                    self.assertEqual(row["stakeYen"], "0")
            for arm in ARMS:
                values = self.summary["byCircuit"][owner][arm]
                self.assertEqual((values["cohortRaces"], values["scoredRaces"],
                                  values["unscoredRaces"]), (total, eligible, missing))
                self.assertEqual(sum(a[arm]["winnerTop1"] == "True" for a in cohort),
                                 values["winnerTop1Hits"])

    def test_paired_top1_hits_without_cross_circuit_pooling(self):
        self.assertEqual(paired_counts(self.races, "jra"), (16, 4, 0, 67))
        self.assertEqual(paired_counts(self.races, "nar"), (80, 11, 17, 224))
        self.assertAlmostEqual(exact_paired_pvalue(4, 0), .125)
        self.assertGreater(exact_paired_pvalue(11, 17), .344)
        self.assertLess(exact_paired_pvalue(11, 17), .346)

    def test_leave_one_racing_day_out_retrospective_sensitivity(self):
        daily = {owner: defaultdict(lambda: {"scored": 0, "baseline": 0, "recent5": 0})
                 for owner in ("jra", "nar")}
        for (owner, _), arms in self.races.items():
            if arms["baseline"]["scored"] != "True":
                continue
            date = arms["baseline"]["date"]
            item = daily[owner][date]
            item["scored"] += 1
            for arm in ("baseline", "recent5"):
                item[arm] += arms[arm]["winnerTop1"] == "True"
        self.assertEqual((len(daily["jra"]), len(daily["nar"])), (5, 9))
        self.assertEqual(daily["nar"]["2026-10-12"],
                         {"scored": 35, "baseline": 9, "recent5": 14})
        for owner in daily:
            totals = {k: sum(day[k] for day in daily[owner].values())
                      for k in ("scored", "baseline", "recent5")}
            for day in daily[owner].values():
                remaining = {k: totals[k] - day[k] for k in totals}
                if owner == "jra":
                    self.assertLess(remaining["recent5"], remaining["baseline"])
                elif day == daily["nar"]["2026-10-12"]:
                    self.assertEqual(remaining, {"scored": 297, "baseline": 82, "recent5": 83})

    def test_no_independent_future_or_production_success_claim(self):
        self.assertFalse(self.summary["independentlyVerifiedPreoff"])
        self.assertFalse(self.summary["productionEligible"])
        self.assertIn("byCircuit", self.summary)
        self.assertEqual(set(self.summary["byCircuit"]), {"jra", "nar"})


if __name__ == "__main__":
    unittest.main()
