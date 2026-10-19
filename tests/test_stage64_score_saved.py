"""Stage64 confirmed D1-result readback: fail closed, never invent payout."""
import unittest

from scripts.arvexq_stage64_score_saved import confirmed_label, assemble_results


def sample(status="確定"):
    return {"id":"nar-2026-10-23-高知-01","circuit":"地方","date":"2026-10-23",
            "result":{"status":status,
                      "finishers":[{"horseNumber":8,"finish":2},{"horseNumber":3,"finish":1},
                                   {"horseNumber":2,"finish":3},{"horseNumber":4,"finish":4}],
                      "payouts":[{"kind":"3連単","combination":"3-8-2","payout":12500}]}}


class SavedResults(unittest.TestCase):
    def test_confirmed_trifecta_exact_and_return(self):
        self.assertEqual(confirmed_label(sample())["orders"], [[3,8,2]])
        self.assertEqual(confirmed_label(sample())["payouts"],
                         [{"order":[3,8,2],"amount":12500}])

    def test_explicit_numeric_strings_from_saved_official_results(self):
        race=sample()
        race["result"]["finishers"][0]["finish"]="2"
        race["result"]["finishers"][1]["horseNumber"]="3"
        race["result"]["payouts"][0]["payout"]="12,500"
        self.assertEqual(confirmed_label(race)["orders"],[[3,8,2]])
        self.assertEqual(confirmed_label(race)["payouts"],
                         [{"order":[3,8,2],"amount":12500}])

    def test_non_numeric_payout_is_unknown_not_zero(self):
        race=sample()
        race["result"]["payouts"][0]["payout"]="払戻不明"
        self.assertIsNone(confirmed_label(race)["payouts"])

    def test_missing_payout_never_zero(self):
        race=sample();race["result"]["payouts"]=[]
        self.assertIsNone(confirmed_label(race)["payouts"])
        race["result"]["payouts"]=[{"kind":"3連単","combination":"3-8-2","payout":None}]
        self.assertIsNone(confirmed_label(race)["payouts"])

    def test_unconfirmed_does_not_score(self):
        for status in ("未確定","予想","",None):
            with self.subTest(status=status),self.assertRaises(ValueError):
                confirmed_label(sample(status))

    def test_ambiguous_dead_heat_is_blocked(self):
        race=sample();race["result"]["finishers"][1]["finish"]=2
        with self.assertRaisesRegex(ValueError,"dead heat"):
            confirmed_label(race)

    def test_missing_podium_is_blocked(self):
        race=sample();race["result"]["finishers"]=race["result"]["finishers"][:2]
        with self.assertRaises(ValueError):
            confirmed_label(race)

    def test_duplicate_result_rejected(self):
        race=sample()
        batch={"cohort":[race["id"]]}
        with self.assertRaisesRegex(ValueError,"duplicate"):
            assemble_results(batch,{"details":[race,race]})

    def test_incomplete_not_cherry_picked(self):
        race=sample()
        labels,audit=assemble_results({"cohort":[race["id"],"nar-2026-10-23-高知-02"]},
                                      {"details":[race]})
        self.assertEqual(len(labels),1)
        self.assertFalse(audit["allConfirmed"])
        self.assertEqual(audit["pendingRaces"][0]["reason"],"missing-saved-detail")

    def test_foreign_result_day_is_not_selected(self):
        race=sample()
        other=sample();other["id"]="nar-2026-10-24-高知-01";other["date"]="2026-10-24"
        batch={"cohort":[race["id"]]}
        labels,audit=assemble_results(batch,{"details":[other]})
        self.assertFalse(labels)
        self.assertEqual(audit["pendingRaces"][0]["reason"],"missing-saved-detail")

    def test_non_final_result_is_retained_as_pending_not_discarded(self):
        race=sample("未確定")
        labels,audit=assemble_results({"cohort":[race["id"]]},{"details":[race]})
        self.assertEqual(labels,[])
        self.assertEqual(audit["frozenRaces"],1)
        self.assertFalse(audit["allConfirmed"])

    def test_bad_payout_combination_never_parsed_as_order(self):
        race=sample();race["result"]["payouts"][0]["combination"]="bad"
        with self.assertRaises(ValueError):
            confirmed_label(race)


if __name__=="__main__":unittest.main()
