"""Static API pack builder: --input shapes, Banei exclusion, merge mode.

Migration block A (GitHub-only): packs must be buildable from the lane
payloads alone (sync payload / official snapshot / day response), with
no API read-back, and delta payloads must overlay existing packs via
--merge-existing without shrinking the day.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import arvexq_static_api_build as b

DATE = "2026-11-21"
RID1 = f"jra-{DATE}-東京-01"
RID2 = f"jra-{DATE}-東京-02"
BANEI_ID = f"nar-{DATE}-帯広-01"


def detail(rid, track="東京", mark="◎"):
    return {
        "id": rid, "date": DATE, "track": track, "raceNumber": 1,
        "horses": [{"horseNumber": 1, "name": "甲"},
                   {"horseNumber": 2, "name": "乙"}],
        "predictionMarks": [{"mark": mark, "horseNumber": 1}],
        "recommendedBets": [{"type": "単勝", "horseNumbers": [1]}],
        "preparedMeta": {"diagnosisReady": True},
        "massFeatureSnapshot": {"should": "be stripped"},
    }


def summary(rid, track="東京"):
    return {"id": rid, "date": DATE, "circuit": "中央", "track": track,
            "raceNumber": 1, "startTime": "10:00", "title": "1R",
            "surface": "芝", "distance": 1600, "weather": "晴",
            "condition": "良", "volatility": {"label": "", "score": None},
            "raceStatus": "", "updatedAtEpoch": 0}


def sync_payload():
    return {
        "summaries": [summary(RID1), summary(RID2), summary(BANEI_ID, "帯広")],
        "details": [detail(RID1), detail(RID2), detail(BANEI_ID, "帯広")],
        "odds_current": [{"race_id": RID1, "horse_no": 1, "win_odds": 2.4}],
        "meta": {"race_count": 3, "sync_date": DATE},
    }


def build_to(payload, out, **kw):
    model = b.detect_model(payload)
    return b.build(model, Path(out), "2026-11-23T00:00:00+09:00", **kw)


class StaticApiBuildTests(unittest.TestCase):
    def test_sync_payload_builds_day_and_race_packs(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_to(sync_payload(), td)
            self.assertEqual(result["races"], 2)
            self.assertEqual(result["details"], 2)
            self.assertEqual(result["missing"], [])
            day = json.loads((Path(td) / "day" / f"{DATE}.json").read_text())
            self.assertEqual(day["raceCount"], 2)
            body = json.loads((Path(td) / "race" / f"{RID1}.json").read_text())
            self.assertEqual(body["detail"]["predictionMarks"][0]["mark"], "◎")
            self.assertTrue(body["detail"]["recommendedBets"])
            self.assertNotIn("massFeatureSnapshot", body["detail"])
            # odds rows lose their race_id, mirroring the API shape
            self.assertEqual(body["odds"], [{"horse_no": 1, "win_odds": 2.4}])
            self.assertTrue(body["analysis_ready"])

    def test_banei_excluded_everywhere(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_to(sync_payload(), td)
            self.assertEqual(result["skippedBanei"], 2)  # summary + detail
            self.assertFalse((Path(td) / "race" / f"{BANEI_ID}.json").exists())
            day = json.loads((Path(td) / "day" / f"{DATE}.json").read_text())
            self.assertNotIn(BANEI_ID, [r["id"] for r in day["races"]])

    def test_wrapped_sync_rows_propagate_updated_at(self):
        payload = sync_payload()
        payload["details"] = [
            {"race_id": d["id"], "payload": d, "updated_at": 123,
             "analysis_ready": True} for d in payload["details"]]
        with tempfile.TemporaryDirectory() as td:
            build_to(payload, td)
            body = json.loads((Path(td) / "race" / f"{RID1}.json").read_text())
            self.assertEqual(body["detail_updated_at"], 123)

    def test_official_snapshot_shape_detected(self):
        payload = {"date": DATE, "results": [
            {"id": RID1, "detail": {
                "summary": {"race_id": RID1, "race_date": DATE,
                            "circuit": "中央", "track": "東京", "race_no": 1,
                            "start_time": "10:00", "title": "1R",
                            "surface": "芝", "distance": 1600,
                            "weather": "晴", "condition": "良",
                            "volatility_label": "", "volatility_score": None,
                            "race_status": "", "updated_at": 0},
                "detail": detail(RID1), "odds": [],
                "analysis_ready": True, "detail_updated_at": 7}}]}
        with tempfile.TemporaryDirectory() as td:
            result = build_to(payload, td)
            self.assertEqual((result["races"], result["details"]), (1, 1))
            body = json.loads((Path(td) / "race" / f"{RID1}.json").read_text())
            self.assertEqual(body["detail_updated_at"], 7)

    def test_day_response_shape_detected(self):
        payload = {"date": DATE, "races": [summary(RID1)],
                   "details": [detail(RID1)]}
        with tempfile.TemporaryDirectory() as td:
            result = build_to(payload, td)
            self.assertEqual((result["races"], result["details"]), (1, 1))

    def test_merge_existing_overlays_delta_without_shrinking_day(self):
        with tempfile.TemporaryDirectory() as td:
            build_to(sync_payload(), td)
            # Delta: only race 2 changed (new mark), plus odds-only rows
            # for race 1 whose detail is not in the delta.
            delta = {"summaries": [summary(RID1), summary(RID2)],
                     "details": [detail(RID2, mark="○")],
                     "odds_current": [{"race_id": RID1, "horse_no": 2,
                                       "win_odds": 9.9}],
                     "meta": {"sync_date": DATE, "live_delta": True}}
            model = b.detect_model(delta)
            base = b.model_from_existing_packs(Path(td), DATE)
            merged = b.merge_models(base, model)
            result = b.build(merged, Path(td), "2026-11-23T01:00:00+09:00")
            self.assertEqual(result["races"], 2)
            self.assertEqual(result["details"], 2)
            body2 = json.loads((Path(td) / "race" / f"{RID2}.json").read_text())
            self.assertEqual(body2["detail"]["predictionMarks"][0]["mark"], "○")
            body1 = json.loads((Path(td) / "race" / f"{RID1}.json").read_text())
            self.assertEqual(body1["detail"]["predictionMarks"][0]["mark"], "◎")
            self.assertEqual(body1["odds"], [{"horse_no": 2, "win_odds": 9.9}])

    def test_unrecognized_shape_rejected(self):
        with self.assertRaises(ValueError):
            b.detect_model({"hello": "world"})


if __name__ == "__main__":
    unittest.main()
