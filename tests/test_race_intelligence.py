"""Independent evidence, review, provenance and betting-value regressions."""
import copy
import unittest

from arvexq.prediction.race_intelligence import attach_evidence
from arvexq.prediction.factor_cards import evidence_card, weighted_experiment
from arvexq.prediction.sectional_profile import profile
from arvexq.prediction.bias_provenance import provenance
from arvexq.results.auto_recap import build_race_recap
from arvexq.databanks.horse_review_bank import build_horse_review_bank
from arvexq.backtest.expected_value import value_matrix


class RaceIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.horse = {
            "horseNumber": 3, "horseId": "horse-unique-3", "name": "検証馬",
            "integratedEvaluation": {"components": {"distanceFit": .7}},
            "recentRaces": [
                {"date": "2026-09-25", "finish": 2, "fieldSize": 10,
                 "distance": 1400, "track": "園田", "timeSeconds": 86.3,
                 "first3FSeconds": 35.6, "last3FSeconds": 38.1,
                 "last3FPercentile": .77, "cornerPositions": [2, 2, 3, 2]},
                {"date": "2026-10-11", "finish": 1, "fieldSize": 8,
                 "first3FSeconds": 33.4, "last3FSeconds": 35.2},
            ],
        }
        self.race = {"id": "nar-2026-10-09-園田-03", "date": "2026-10-09",
                     "track": "園田", "circuit": "地方", "distance": 1400,
                     "condition": "良", "horses": [copy.deepcopy(self.horse)],
                     "preRaceBet": {"fixedAt": "2026-10-09T08:00:00+09:00",
                                    "items": [{"kind": "馬連", "combos": [[3, 4]]}]},
                     "officialCourseReport": {"condition": "良", "issuedAt": "2026-10-09T08:00+09:00"},
                     "aiTrackBias": {"frontBack": "前寄り", "sampleRaces": 2}}

    def test_evidence_only_already_available_and_preoff(self):
        original = copy.deepcopy(self.race)
        attach_evidence(self.race)
        h = self.race["horses"][0]
        factors = h["researchEvidence"]["factors"]
        self.assertEqual(len(factors["items"]), 14)
        self.assertGreater(factors["evidenceCoverage"], 0)
        self.assertIsNone(next(x for x in factors["items"] if x["key"] == "pedigree")["measurements"] or None)
        sectionals = h["researchEvidence"]["sectionals"]
        self.assertEqual(len(sectionals["runs"]), 1, "future runs must never leak")
        self.assertEqual(sectionals["runs"][0]["early3FSeconds"], 35.6)
        self.assertEqual(sectionals["measuredMiddle"], 0)
        self.assertIn("実測値", sectionals["note"])
        self.assertEqual(self.race["preRaceBet"], original["preRaceBet"])
        self.assertEqual(self.race["horses"][0]["recentRaces"], original["horses"][0]["recentRaces"])
        self.assertEqual(self.race["biasProvenance"]["official"]["source"], "official-announcement")
        self.assertEqual(self.race["biasProvenance"]["estimated"]["source"], "ai-inference-not-official")
        self.assertFalse(self.race["biasProvenance"]["changesMorningMarks"])

    def test_unverified_card_is_never_a_probability(self):
        card = evidence_card(self.horse, self.race)
        result = weighted_experiment(card, {"speed": .2, "early": .8})
        self.assertIsNone(result["predictiveScore"])
        self.assertFalse(card["calibrated"])
        with self.assertRaises(ValueError):
            weighted_experiment(card, {"pace": -1})
        with self.assertRaises(ValueError):
            weighted_experiment(card, {"unknown": 1})

    def test_fourteen_factor_shadow_sealed_only_and_never_recomputed(self):
        from arvexq.prediction.factor_challenger import build_factor_shadow
        from arvexq.backtest.factor_challenger_evaluation import evaluate, aggregate
        from arvexq.prediction.prerace_archive import seal_detail, JST
        from datetime import datetime, timedelta
        now = datetime(2026, 10, 9, 10, 30, tzinfo=JST)
        race = copy.deepcopy(self.race)
        race["startTime"] = "11:00"
        race["horses"] = []
        for no in range(1, 6):
            h = copy.deepcopy(self.horse)
            h["horseNumber"] = no
            h["horseId"] = f"unique-{no}"
            h["recentRaces"][0]["finish"] = no
            race["horses"].append(h)
        base = build_factor_shadow(race)
        self.assertEqual(base["mode"], "frozen-shadow-only-not-for-betting")
        self.assertIsNone(base["winnerProbability"])
        lock = {"raceId": race["id"], "raceDate": race["date"],
                "capturedAtEpoch": int(now.timestamp()),
                "horses": [{"horseNumber": no, "mark": {"1":"◎","2":"○","3":"▲"}.get(str(no),"△")}
                           for no in range(1, 6)]}
        locked = seal_detail(race, lock, now)
        self.assertIn("researchFactorShadow", locked)
        original = copy.deepcopy(locked["researchFactorShadow"])
        locked["horses"][0]["recentRaces"].append({
            "date": "2026-10-11", "finish": 1, "fieldSize": 8})
        self.assertEqual(original, locked["researchFactorShadow"])
        locked["result"] = {"status": "確定", "finishers": [
            {"horseNumber": 1, "finish": 1}, {"horseNumber": 2, "finish": 2},
            {"horseNumber": 3, "finish": 3}]}
        report = evaluate(locked)
        # Sparse evidence may produce a withheld shadow, which is correct.
        if not original["sufficient"]:
            self.assertIsNone(report)
        if original["sufficient"]:
            self.assertFalse(report["usedPostoffRecalculation"])
            self.assertEqual(aggregate([report, report])["raceCount"], 1)
            locked["researchFactorShadow"]["rows"][0]["researchRankScore"] = .999
            self.assertIsNone(evaluate(locked), "tampering must fail the original hash")

    def test_review_only_after_official_confirmation(self):
        detail = copy.deepcopy(self.race)
        result = {"status": "確定", "finishers": [
            {"horseNumber": 4, "finish": 1},
            {"horseNumber": 3, "finish": 2, "cornerPositions": [2, 2, 3, 2]},
            {"horseNumber": 2, "finish": 3},
        ]}
        detail["result"] = result
        self.assertIsNone(build_race_recap(self.race))
        original_bet = copy.deepcopy(detail["preRaceBet"])
        recap = build_race_recap(detail)
        self.assertEqual(len(recap["finishers"]), 3)
        self.assertFalse(recap["videoVerified"])
        self.assertEqual(detail["preRaceBet"], original_bet)
        bank = build_horse_review_bank([recap, recap])
        self.assertEqual(len(bank["horses"]["horse-unique-3"]), 1)
        self.assertNotIn("4", bank["horses"], "horse-number-only must not identify a horse globally")
        detail["result"]["status"] = "速報"
        self.assertIsNone(build_race_recap(detail))

    def test_ticket_value_requires_verified_calibration_and_preoff_odds(self):
        items = [{"kind": "馬連", "combos": [[3, 4]]}]
        kwargs = {"items": items, "odds_captured_at": "2026-10-09T10:00:00+09:00",
                  "scheduled_post_at": "2026-10-09T11:00:00+09:00",
                  "offered_odds": {"馬連:3-4": 6.0}}
        self.assertEqual(value_matrix(calibration={}, **kwargs)["status"], "not-estimable")
        calibrated = {"method": "out-of-sample", "validated": True,
                      "ticketProbabilities": {"馬連:3-4": .20}}
        ready = value_matrix(calibration=calibrated, **kwargs)
        self.assertEqual(ready["status"], "ready")
        self.assertEqual(ready["rows"][0]["expectedNetRatio"], .2)
        kwargs["odds_captured_at"] = "2026-10-09T12:00:00+09:00"
        self.assertEqual(value_matrix(calibration=calibrated, **kwargs)["status"], "not-estimable")


if __name__ == "__main__":
    unittest.main()
