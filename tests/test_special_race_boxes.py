"""Regression contract: evidence boxes cannot become a stealth predictor."""
import copy
import unittest

from arvexq.prediction.special_races import build_special_race_box, special_race_type


class SpecialRaceBoxesTests(unittest.TestCase):
    def test_debut_distinct_and_missing_not_fabricated(self):
        race = {"circuit": "中央", "id": "jra-2026-10-25-東京-05", "date": "2026-10-25",
                "title": "メイクデビュー東京", "surface": "芝", "horses": [
                    {"horseNumber": 1, "name": "A", "jockey": "騎手", "sire": "父"},
                    {"horseNumber": 2, "name": "B"}]}
        original = copy.deepcopy(race)
        self.assertEqual(special_race_type(race), "debut")
        box = build_special_race_box(race)
        self.assertEqual(box["box"], "jra-debut")
        self.assertEqual(box["horseCount"], 2)
        self.assertFalse(box["predictionApproved"])
        self.assertIn("workout", box["horses"][0]["missingFields"])
        self.assertIsNone(box["horses"][0]["visiblePriorStarts"])
        self.assertFalse(box["horses"][0]["firstStartConfirmed"])
        self.assertEqual(race, original)

    def test_nested_pedigree_is_observed(self):
        race = {"circuit": "中央", "title": "2歳新馬", "horses": [
            {"horseNumber": 1, "pedigree": {"sire": "父", "dam": "母", "damsire": "母父"}}]}
        row = build_special_race_box(race)["horses"][0]
        self.assertTrue({"sire", "dam", "damSire"}.issubset(row["observedFields"]))
        self.assertNotIn("sire", row["missingFields"])

    def test_jump_priority_with_flat_surface_and_no_mixed_ability(self):
        race = {"circuit": "中央", "id": "jra-2026-10-17-京都-04", "date": "2026-10-17",
                "surface": "芝", "title": "障害3歳以上未勝利", "horses": [{
                    "horseNumber": 5, "name": "A", "careerTransport": {"packedOlderRuns": 10},
                    "recentRaces": [
                        {"date": "2026-09-02", "title": "障害3歳以上未勝利", "finish": 1},
                        {"date": "2026-09-10", "title": "3歳以上1勝クラス", "finish": 2},
                        {"date": "2026-10-17", "title": "障害3歳以上未勝利", "finish": 1},
                        {"date": "2026-11-01", "title": "障害3歳以上未勝利", "finish": 1},
                    ]}]}
        self.assertEqual(special_race_type(race), "jumps")
        box = build_special_race_box(race)
        self.assertEqual(box["box"], "jra-jumps")
        self.assertEqual(box["horses"][0]["jumpRunsDatedBeforeRace"], 1)
        self.assertEqual(box["horses"][0]["flatOrUnknownRunsDatedBeforeRace"], 1)
        self.assertNotIn("score", box)

    def test_no_debut_legacy_and_unnamed_unknown_history(self):
        nar = {"circuit": "地方", "title": "新馬", "horses": []}
        self.assertIsNone(build_special_race_box(nar))
        flat = {"circuit": "中央", "title": "3歳未勝利", "horses": []}
        self.assertIsNone(build_special_race_box(flat))
        jump = {"circuit": "中央", "title": "東京HJ", "horses": [
            {"horseNumber": 1, "careerTransport": {"packedOlderRuns": 5}}]}
        box = build_special_race_box(jump)
        self.assertEqual(box["horses"][0]["historyState"], "packed-not-decoded")
        self.assertIsNone(box["horses"][0]["jumpRunsDatedBeforeRace"])

    def test_historical_high_jump_and_decoration_integration(self):
        from arvexq.prediction.race_intelligence import attach_evidence
        detail = {"circuit": "中央", "id": "jra-2026-10-18-東京-09",
                  "date": "2026-10-18", "track": "東京", "title": "東京HJ",
                  "horses": [{"horseNumber": 1, "name": "検証馬",
                              "recentRaces": [
                                  {"date": "2026-09-01", "title": "東京HJ", "finish": 3}],
                              "integratedEvaluation": {"mark": "◎"}}],
                  "preRaceBet": {"items": [{"kind": "単勝", "combos": [[1]]}]}}
        original_bet = copy.deepcopy(detail["preRaceBet"])
        attach_evidence(detail)
        box = detail["specialRaceBox"]
        self.assertEqual(box["box"], "jra-jumps")
        self.assertEqual(box["horses"][0]["jumpRunsDatedBeforeRace"], 1)
        self.assertEqual(detail["horses"][0]["integratedEvaluation"]["mark"], "◎")
        self.assertEqual(detail["preRaceBet"], original_bet)

    def test_post_race_results_do_not_change_evidence_box(self):
        race = {"circuit": "中央", "date": "2026-10-25", "title": "2歳新馬", "horses": [
            {"horseNumber": 1, "sire": "父"}]}
        before = build_special_race_box(race)
        race["result"] = {"status": "確定", "finishers": [{"horseNumber": 1, "finish": 1}]}
        race["recommendedBetPlan"] = {"items": ["secret"]}
        self.assertEqual(before, build_special_race_box(race))


if __name__ == "__main__":
    unittest.main()
