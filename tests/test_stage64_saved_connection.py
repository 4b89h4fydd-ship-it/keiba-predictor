"""Actual immutable 2026-10-17 saved JRA/NAR races through unchanged Stage64."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from arvexq.research.stage64.pipeline import STAGES, predict
from arvexq.research.stage64.protocol import ARMS, clean_input, code_hash
from scripts.arvexq_stage64_saved_connection import (SAVED, run_saved_day,
                                                     compare_archived_coverage)

ROOT = Path(__file__).resolve().parents[1]


class Stage64SavedConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_saved_day("2026-10-17")
        cls.reference = json.loads((ROOT / "docs/research/stage64-results/summary.json")
                                   .read_text(encoding="utf-8"))

    def test_all_original_races_and_three_ability_methods_in_both_circuits(self):
        report = self.report
        self.assertEqual(set(report["byCircuit"]), {"jra", "nar"})
        self.assertEqual([report["byCircuit"][c]["races"] for c in ("jra", "nar")],
                         [36, 34])
        self.assertEqual(len(report["raceRows"]), 70)
        self.assertEqual(tuple(report["abilityMethods"]), ARMS)
        self.assertEqual(tuple(report["stages"]), STAGES)
        self.assertEqual(sum(v["armsExecuted"] for v in report["byCircuit"].values()), 210)
        self.assertFalse(report["productionEligible"])
        self.assertFalse(report["independentlyVerifiedPreoff"])
        self.assertFalse(report["productionChanged"])
        self.assertIsNone(report["productMarks"])
        self.assertIsNone(report["recommendedBets"])

    def test_real_six_stages_and_separate_jra_nar_scenario_counts(self):
        for owner in ("jra", "nar"):
            cohort = [row for row in self.report["raceRows"] if row["circuit"] == owner]
            self.assertTrue(cohort)
            scored = 0
            for row in cohort:
                self.assertTrue(row["rosterVerified"])
                self.assertTrue(row["savedSourceSha256"])
                self.assertEqual(set(row["predictions"]), set(ARMS))
                for arm, p in row["predictions"].items():
                    self.assertEqual(p["abilityMethod"], arm)
                    self.assertEqual(tuple(p["stages"]), STAGES)
                    self.assertFalse(p["productionEligible"])
                    if p["sixStageCalculated"]:
                        scored += 1
                        six = p["stages"]
                        self.assertEqual(len(six["pace"]["value"]), 1 if owner == "jra" else 4)
                        self.assertAlmostEqual(sum(six["probability"]["value"]["win"].values()), 1.)
                        self.assertAlmostEqual(sum(six["probability"]["value"]["top3"].values()), 3.)
                        self.assertIsNone(six["marks"]["value"]["productMarks"])
                        self.assertIsNone(six["tickets"]["value"]["recommendedBets"])
                        self.assertLessEqual(
                            len(six["tickets"]["value"]["hypotheticalTrifectaTop10"]), 10)
                    else:
                        self.assertFalse(p["stages"]["tickets"]["value"])
            self.assertGreater(scored, 0, owner + " should compute real saved six-stage races")
            self.assertEqual(scored, self.report["byCircuit"][owner]["sixStageCalculated"])
            self.assertEqual(scored + self.report["byCircuit"][owner]["unscoredArms"],
                             len(cohort) * 3)

    def test_no_comparability_claim_with_prior_527_race_study(self):
        self.assertIn("different-saved-cohort", self.report["historical527Comparison"])
        self.assertFalse(self.reference["productionEligible"])
        self.assertFalse(self.reference["independentlyVerifiedPreoff"])
        self.assertEqual(set(self.reference["byCircuit"]), {"jra", "nar"})
        for circuit, historical_count in (("jra", 108), ("nar", 419)):
            self.assertEqual(set(self.reference["byCircuit"][circuit]), set(ARMS))
            for arm in ARMS:
                self.assertEqual(
                    self.reference["byCircuit"][circuit][arm]["cohortRaces"],
                    historical_count)

    def test_outcomes_odds_and_product_bets_cannot_change_stage64(self):
        sample = {"id": "nar-2026-10-17-高知-01", "date": "2026-10-17",
                  "circuit": "地方", "fieldSize": 3,
                  "horses": [{"horseNumber": n, "recentRaces": [
                      {"date": "2026-10-10", "finish": n, "fieldSize": 6,
                       "cornerPositions": [n]}]} for n in (1, 2, 3)]}
        baseline = clean_input(sample)
        expected = {arm: predict(baseline, expected_circuit="nar", ability_method=arm)
                    for arm in ARMS}
        sample.update(result={"status": "確定", "finishers": [{"finish": 1}]},
                      payouts=[{"kind": "3連単", "amount": 99999}],
                      preRaceBet={"items": [{"kind": "おすすめ買い目"}]},
                      morningMarkSnapshot={"horses": [{"mark": "◎"}]})
        for horse in sample["horses"]:
            horse["winOdds"] = 1.1
        # Original prospective guard still rejects result-bearing input.
        with self.assertRaisesRegex(ValueError, "target outcome present"):
            clean_input(sample)
        projected = {k: v for k, v in sample.items()
                     if k not in ("result", "results", "payouts")}
        self.assertEqual(clean_input(projected), baseline)
        for arm in ARMS:
            self.assertEqual(predict(clean_input(projected),
                                     expected_circuit="nar", ability_method=arm),
                             expected[arm])

    def test_future_date_or_mismatched_horses_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "retrospective"):
            run_saved_day("2999-01-01")
        with self.assertRaisesRegex(ValueError, "retrospective"):
            run_saved_day("2026-10-20")

    def test_same_race_archive_baseline_coverage_reconciliation(self):
        # 2026-10-11 has 80 identical race IDs in the original 527R report.
        # Compare readiness AND per-horse blockers for every ability arm;
        # no unverified numeric probability-equivalence claim is made.
        day = run_saved_day("2026-10-11")
        archived = json.loads((ROOT / "docs/research/stage64-results/coverage.json")
                              .read_text(encoding="utf-8"))
        joined = compare_archived_coverage(day, archived)
        self.assertEqual(day["byCircuit"]["jra"]["races"], 24)
        self.assertEqual(day["byCircuit"]["nar"]["races"], 56)
        self.assertEqual(sum(v["overlappingRaces"]
                             for v in joined["byCircuit"].values()), 80)
        self.assertEqual(sum(v["notInArchivedResearch"]
                             for v in joined["byCircuit"].values()), 0)
        for owner in ("jra", "nar"):
            counted = joined["byCircuit"][owner]
            self.assertEqual(counted["fullyMatchedRaces"] + counted["disagreedRaces"],
                             counted["overlappingRaces"])
            self.assertLessEqual(counted["fullyMatchedRaces"],
                                 counted["statusMatchedRaces"])
            self.assertLessEqual(counted["fullyMatchedRaces"],
                                 counted["blockersMatchedRaces"])
        self.assertEqual(sum(v["disagreedRaces"]
                             for v in joined["byCircuit"].values()),
                         len(joined["differences"]))
        self.assertFalse(joined["sameInputByteEqualityVerified"])
        self.assertFalse(joined["probabilityOrTicketNumericalEqualityVerified"])
        self.assertFalse(joined["productionEligible"])

    def test_nar_only_actual_saved_day_preserves_circuit_isolation(self):
        # 2026-10-13 has 58 NAR races and no JRA race. The trial may not
        # fabricate JRA observations merely to fill a per-day cohort.
        report = run_saved_day("2026-10-13")
        self.assertEqual(report["byCircuit"]["jra"].get("races", 0), 0)
        self.assertEqual(report["byCircuit"]["nar"]["races"], 58)
        self.assertEqual(len(report["raceRows"]), 58)
        self.assertTrue(all(row["circuit"] == "nar" for row in report["raceRows"]))
        self.assertEqual(report["byCircuit"]["nar"]["armsExecuted"], 174)
        archived = json.loads((ROOT / "docs/research/stage64-results/coverage.json")
                              .read_text(encoding="utf-8"))
        comparison = compare_archived_coverage(report, archived)
        self.assertEqual(comparison["byCircuit"]["nar"]["overlappingRaces"], 58)
        self.assertEqual(comparison["byCircuit"]["jra"]["overlappingRaces"], 0)
        self.assertFalse(comparison["productionEligible"])

    def test_archived_coverage_identity_and_duplicates_fail_closed(self):
        day = {"raceRows": [{"raceId": "jra-2026-10-11-京都-01",
                            "date": "2026-10-11", "circuit": "jra",
                            "predictions": {}}]}
        archived = [{"raceId": "jra-2026-10-11-京都-01",
                     "date": "2026-10-11", "circuit": "nar",
                     "stageStatus": {}, "blockers": []}]
        with self.assertRaisesRegex(ValueError, "circuit/date"):
            compare_archived_coverage(day, archived)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            compare_archived_coverage(day, archived + archived)

    def test_readonly_saved_history_diagnostic_categories(self):
        for owner, expected in (("jra", (1, 6)), ("nar", (12, 6))):
            diag = self.report["byCircuit"][owner]
            self.assertEqual(diag["blockedUnsupportedDisciplineRaces"], expected[0])
            self.assertEqual(diag["blockedInsufficientHistoryRaces"], expected[1])
            self.assertEqual(diag.get("blockedOtherRaces", 0), 0)
            self.assertEqual(diag["races"],
                             diag["sixStageCalculated"] // 3 + sum(expected))

    def test_same_status_with_changed_runner_blocker_is_not_called_full_match(self):
        rid = "nar-2026-10-12-佐賀-11"
        status = {stage: "research-only" for stage in STAGES}
        now = [{"horseNumber": 11, "date": "2026-04-26",
                "reason": "incompatible-history-discipline"},
               {"horseNumber": 11, "date": "2026-06-28",
                "reason": "incompatible-history-discipline"}]
        old = [now[0]]
        row = {"raceId": rid, "circuit": "nar", "date": "2026-10-12",
               "predictions": {arm: {
                   "stages": {stage: {"status": value}
                              for stage, value in status.items()},
                   "blockers": now} for arm in ARMS}}
        report = {"raceRows": [row]}
        archived = [{"raceId": rid, "circuit": "nar",
                     "date": "2026-10-12", "stageStatus": status,
                     "blockers": old}]
        compare = compare_archived_coverage(report, archived)
        nar = compare["byCircuit"]["nar"]
        self.assertEqual(nar["overlappingRaces"], 1)
        self.assertEqual(nar["statusMatchedRaces"], 1)
        self.assertEqual(nar["blockersMatchedRaces"], 0)
        self.assertEqual(nar["fullyMatchedRaces"], 0)
        self.assertEqual(nar["disagreedRaces"], 1)
        self.assertEqual(len(compare["differences"]), 1)
        self.assertEqual(set(compare["differences"][0]["armDifferences"]), set(ARMS))
        self.assertFalse(compare["probabilityOrTicketNumericalEqualityVerified"])

    def test_stage4_archived_misses_join_existing_saved_card_context_without_leakage(self):
        # Contextual failure audit only. The archived 527R forecast inputs differ
        # from today's saved static originals; no arm selection or accuracy promotion.
        import csv
        with (ROOT / "docs/research/stage64-results/race_metrics.csv").open(
                encoding="utf-8-sig", newline="") as stream:
            metrics = list(csv.DictReader(stream))
        self.assertEqual(len(metrics), 527 * 3)
        by_id = {}
        for row in metrics:
            arms = by_id.setdefault(row["raceId"], {})
            self.assertNotIn(row["arm"], arms)
            arms[row["arm"]] = row
        self.assertEqual(len(by_id), 527)
        self.assertTrue(all(set(arms) == set(ARMS) for arms in by_id.values()))

        cards = {}
        for day in range(10, 16):
            date = "2026-10-%02d" % day
            data = json.loads((SAVED / "racecards" / (date + ".json"))
                              .read_text(encoding="utf-8"))
            self.assertEqual(data["date"], date)
            for card in data["races"]:
                self.assertNotIn(card["id"], cards)
                cards[card["id"]] = card
        self.assertEqual(len(cards), 364)
        overlaps = set(cards) & set(by_id)
        self.assertEqual(len(overlaps), 362)
        self.assertEqual(set(cards) - overlaps,
                         {"jra-2026-10-10-京都-07", "jra-2026-10-10-京都-10"})

        scored = {"jra": [], "nar": []}
        for rid in sorted(overlaps):
            baseline, recent = by_id[rid]["baseline"], by_id[rid]["recent5"]
            self.assertEqual(baseline["circuit"], recent["circuit"])
            self.assertEqual(baseline["date"], cards[rid]["date"])
            self.assertEqual(recent["date"], cards[rid]["date"])
            self.assertEqual(baseline["scored"], recent["scored"])
            if baseline["scored"] == "True":
                scored[baseline["circuit"]].append((
                    rid, baseline["winnerTop1"] == "True",
                    recent["winnerTop1"] == "True",
                    cards[rid]["distance"]))

        self.assertEqual([len(scored[owner]) for owner in ("jra", "nar")], [51, 230])
        jra_losses = {rid for rid, b, r, _ in scored["jra"] if b and not r}
        jra_gains = {rid for rid, b, r, _ in scored["jra"] if r and not b}
        self.assertFalse(jra_gains)
        self.assertEqual(jra_losses, {
            "jra-2026-10-10-京都-12",
            "jra-2026-10-12-東京-07",
            "jra-2026-10-12-東京-10",
        })
        nar_gains = [rid for rid, b, r, _ in scored["nar"] if r and not b]
        nar_losses = [rid for rid, b, r, _ in scored["nar"] if b and not r]
        self.assertEqual((len(nar_gains), len(nar_losses)), (13, 8))
        nar_1400 = [(b, r) for _, b, r, distance in scored["nar"]
                    if distance == 1400]
        self.assertEqual((len(nar_1400), sum(b for b, r in nar_1400),
                          sum(r for b, r in nar_1400)), (83, 23, 29))
        self.assertEqual((sum(not b and r for b, r in nar_1400),
                          sum(b and not r for b, r in nar_1400)), (7, 1))
        # The lack of the 2026-09-27 original saved card must remain explicit.
        self.assertNotIn("jra-2026-09-27-阪神-11", cards)
        self.assertFalse(self.reference["independentlyVerifiedPreoff"])
        self.assertFalse(self.reference["productionEligible"])

    def test_stage4_leave_one_day_out_accuracy_concentration_is_retrospective_only(self):
        # Fixed Stage64 archived outcomes: diagnose date concentration, NEVER
        # choose a production method or treat reused outcomes as forward proof.
        import csv
        from collections import defaultdict
        path = ROOT / "docs/research/stage64-results/race_metrics.csv"
        with path.open(encoding="utf-8-sig", newline="") as stream:
            source = list(csv.DictReader(stream))
        self.assertEqual(len(source), 1581)
        keyed = {}
        for row in source:
            key = (row["raceId"], row["arm"])
            self.assertNotIn(key, keyed)
            keyed[key] = row
        self.assertEqual(len(keyed), 1581)

        days = {"jra": defaultdict(lambda: {"total": 0, "eligible": 0,
                                             "baseline": 0, "recent5": 0}),
                "nar": defaultdict(lambda: {"total": 0, "eligible": 0,
                                             "baseline": 0, "recent5": 0})}
        for (rid, arm), base in keyed.items():
            if arm != "baseline":
                continue
            recent = keyed[(rid, "recent5")]
            shrunk = keyed[(rid, "recent5_shrunk")]
            owner = base["circuit"]
            self.assertIn(owner, days)
            self.assertTrue(rid.startswith(owner + "-"))
            self.assertEqual({v["date"] for v in (base, recent, shrunk)},
                             {base["date"]})
            self.assertEqual({v["scored"] for v in (base, recent, shrunk)},
                             {base["scored"]})
            record = days[owner][base["date"]]
            record["total"] += 1
            if base["scored"] != "True":
                continue
            record["eligible"] += 1
            for label, row in (("baseline", base), ("recent5", recent)):
                record[label] += row["winnerTop1"] == "True"

        totals = {}
        for owner in ("jra", "nar"):
            owner_totals = {k: sum(day[k] for day in days[owner].values())
                            for k in ("total", "eligible", "baseline", "recent5")}
            totals[owner] = owner_totals
            self.assertEqual(owner_totals["total"],
                             self.reference["byCircuit"][owner]["baseline"]["cohortRaces"])
            self.assertEqual(owner_totals["eligible"],
                             self.reference["byCircuit"][owner]["baseline"]["scoredRaces"])
            self.assertEqual(owner_totals["baseline"],
                             self.reference["byCircuit"][owner]["baseline"]["winnerTop1Hits"])
            self.assertEqual(owner_totals["recent5"],
                             self.reference["byCircuit"][owner]["recent5"]["winnerTop1Hits"])

        self.assertEqual(totals["jra"],
                         {"total": 108, "eligible": 87, "baseline": 20, "recent5": 16})
        self.assertEqual(totals["nar"],
                         {"total": 419, "eligible": 332, "baseline": 91, "recent5": 97})
        self.assertEqual((len(days["jra"]), len(days["nar"])), (5, 9))
        self.assertEqual(days["nar"]["2026-10-12"],
                         {"total": 47, "eligible": 35, "baseline": 9, "recent5": 14})

        # No one-day deletion rescues JRA recent5; NAR's +6R advantage
        # shrinks to +1R when the Oct 12 gain of +5R is omitted.
        for day in days["jra"].values():
            others_baseline = totals["jra"]["baseline"] - day["baseline"]
            others_recent = totals["jra"]["recent5"] - day["recent5"]
            self.assertLess(others_recent, others_baseline)
        nar_deltas = set()
        for day in days["nar"].values():
            others_base = totals["nar"]["baseline"] - day["baseline"]
            others_recent = totals["nar"]["recent5"] - day["recent5"]
            nar_deltas.add(others_recent - others_base)
        self.assertEqual(nar_deltas, {1, 4, 5, 7, 8})
        dec12 = days["nar"]["2026-10-12"]
        remaining = totals["nar"]["eligible"] - dec12["eligible"]
        self.assertEqual((remaining,
                          totals["nar"]["baseline"] - dec12["baseline"],
                          totals["nar"]["recent5"] - dec12["recent5"]),
                         (297, 82, 83))
        self.assertFalse(self.reference["independentlyVerifiedPreoff"])
        self.assertFalse(self.reference["productionEligible"])

    def test_pipeline_and_protocol_source_not_modified_by_connector(self):
        self.assertTrue(code_hash())
        ui = (SAVED / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("arvexq_stage64_saved_connection", ui)


if __name__ == "__main__":
    unittest.main()
