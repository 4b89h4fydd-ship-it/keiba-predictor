"""Stage64 research integration on the existing API projection / D1 seal lane."""
import copy
from datetime import datetime, timedelta, timezone
import unittest

from arvexq.forecast.engine import build_prediction
from arvexq.forecast.publication import public_race
from arvexq.prediction.prerace_archive import restore_seal
from scripts.arvexq_freeze_predictions import prepare_seal

JST = timezone(timedelta(hours=9))
BEFORE = datetime(2098, 12, 31, 10, 0, tzinfo=JST)


def race(owner="nar"):
    track = "高知" if owner == "nar" else "京都"
    return {"id": f"{owner}-2099-01-01-{track}-01",
            "date": "2099-01-01", "circuit": "地方" if owner == "nar" else "中央",
            "track": track, "surface": "ダート" if owner == "nar" else "芝",
            "analysisMode": "平地", "startTime": "12:00", "fieldSize": 4,
            "horses": [{"horseNumber": no, "name": f"馬{no}",
                        "recentRaces": [{"date": "2098-10-15", "finish": no,
                                         "fieldSize": 4, "passing": [no], "track": track}]}
                       for no in (1, 2, 3, 4)]}


class LiveResearchTrial(unittest.TestCase):
    def test_existing_freeze_lane_preserves_all_six_stages_without_official_seal(self):
        for owner in ("jra", "nar"):
            detail = race(owner)
            original = copy.deepcopy(detail)
            result = prepare_seal(detail, now=BEFORE)
            self.assertEqual(result["status"], "research-ready")
            self.assertEqual(detail, original)
            saved = result["detail"]
            self.assertNotIn("preRacePrediction", saved)
            self.assertNotIn("preRaceBet", saved)
            forecast = saved["researchShadow"]["stage64"]
            self.assertEqual(forecast["circuit"], owner)
            self.assertEqual(len(forecast["stages"]), 6)
            self.assertIsNone(forecast["stages"]["marks"]["value"]["productMarks"])
            self.assertIsNone(forecast["stages"]["tickets"]["value"]["recommendedBets"])

    def test_projection_preserves_only_current_stage64_tickets_not_retired_bets(self):
        detail = race()
        forecast = build_prediction(detail, now=BEFORE)
        detail["researchShadow"] = {"priorResearch": {"meaning": "keep"}, "stage64": forecast}
        detail["preRacePrediction"] = {"horses": [{"mark": "◎"}]}
        detail["betRecommendations"] = ["retired"]
        displayed = public_race(detail)
        self.assertEqual(displayed["predictionStatus"], "research-provisional")
        self.assertEqual(displayed["researchShadow"]["priorResearch"], {"meaning": "keep"})
        self.assertIn("tickets", displayed["researchShadow"]["stage64"]["stages"])
        self.assertNotIn("preRacePrediction", displayed)
        self.assertNotIn("betRecommendations", displayed)

    def test_postoff_or_wrong_circuit_does_not_publish_trial(self):
        detail = race()
        detail["researchShadow"] = {"stage64": build_prediction(detail, now=BEFORE)}
        detail["date"] = "2020-01-01"
        expired = public_race(detail)
        self.assertEqual(expired["predictionStatus"], "disabled")
        self.assertNotIn("tickets", expired["researchShadow"]["stage64"]["stages"])
        mismatch = race("jra")
        mismatch["researchShadow"] = {"stage64": build_prediction(race("nar"), now=BEFORE)}
        self.assertEqual(public_race(mismatch)["predictionStatus"], "disabled")

    def test_stage64_d1_evidence_survives_regular_detail_update(self):
        old = race()
        source = build_prediction(old, now=BEFORE)
        old["researchShadow"] = {"priorResearch": {"retain": True}, "stage64": source}
        updated = race()
        projected = restore_seal(old, updated, now=BEFORE)
        self.assertEqual(projected["researchShadow"], old["researchShadow"])
        self.assertNotIn("preRacePrediction", projected)
        # A different race must not inherit the previous forecast.
        updated["id"] = "nar-2099-01-01-高知-02"
        self.assertNotIn("researchShadow", restore_seal(old, updated, now=BEFORE))


if __name__ == "__main__":
    unittest.main()
