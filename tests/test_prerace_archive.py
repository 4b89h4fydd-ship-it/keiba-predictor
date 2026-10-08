import unittest
from copy import deepcopy
from datetime import datetime, timedelta
from arvexq.prediction.prerace_archive import (
    JST, SEALED_VERSION, post_at, pre_off, seal_detail, sealed_lock, restore_seal,
)
from scripts.arvexq_freeze_predictions import prepare_seal


def race(now, minutes=20):
    post = now + timedelta(minutes=minutes)
    return {"id": "nar-2026-10-08-大井-11", "date": post.strftime("%Y-%m-%d"),
            "startTime": post.strftime("%H:%M"), "circuit": "地方",
            "horses": [{"horseNumber": no, "name": f"H{no}",
                        "recentRaces": [{"finish": 2, "fieldSize": 10}],
                        "integratedEvaluation": {"mark": mark, "grade": "A", "score": 80}}
                       for no, mark in ((1, "○"), (2, "◎"), (3, "▲"))]}


def forecast(d, now):
    return {
        "raceId": d["id"], "raceDate": d["date"], "capturedAtEpoch": int(now.timestamp()),
        "markCount": 3, "horses": [
            {"horseNumber": h["horseNumber"], "mark": h["integratedEvaluation"]["mark"]}
            for h in d["horses"]
        ],
    }


class ServerSealTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 8, 19, 50, tzinfo=JST)
        self.d = race(self.now)

    def test_seal_is_immutable_across_rerun_and_result(self):
        d = seal_detail(self.d, forecast(self.d, self.now), self.now)
        self.assertTrue(sealed_lock(d))
        self.assertEqual(d["preRacePrediction"]["horses"][1]["mark"], "◎")
        changed = deepcopy(d)
        changed["horses"][1]["integratedEvaluation"]["mark"] = "注"
        changed["result"] = {"status": "確定", "finishers": [{"finish": 1, "horseNumber": 3}]}
        other_lock = forecast(changed, self.now + timedelta(minutes=1))
        changed["preRacePrediction"] = other_lock
        preserved = restore_seal(d, changed)
        self.assertEqual(preserved["preRacePrediction"], d["preRacePrediction"])
        self.assertEqual(preserved["result"]["status"], "確定")

    def test_no_post_start_creation(self):
        d = race(self.now, minutes=-1)
        with self.assertRaises(ValueError):
            seal_detail(d, forecast(d, self.now - timedelta(minutes=2)), self.now)
        result = prepare_seal(d, now=self.now, build=lambda x:forecast(x,self.now))
        self.assertEqual(result["status"], "started-no-new-lock")

    def test_no_fabricated_legacy_post_lock(self):
        d = deepcopy(self.d)
        lock = forecast(d, self.now + timedelta(minutes=30))
        self.assertFalse(pre_off(lock, d))
        self.assertFalse(sealed_lock(dict(d, preRacePrediction=lock)))

    def test_no_mark_if_missing_evidence(self):
        d = deepcopy(self.d)
        for h in d["horses"]:
            h["recentRaces"] = []
        result = prepare_seal(d, now=self.now, assign=lambda x:x,
                              build=lambda x:forecast(x,self.now))
        self.assertEqual(result["status"], "missing-historical-evidence")

    def test_evaluation_and_marks_are_as_captured(self):
        result = prepare_seal(self.d, now=self.now, assign=lambda x:x,
                              build=lambda x:forecast(x,self.now))
        self.assertEqual(result["status"], "sealed")
        record = result["detail"]["preRacePrediction"]
        self.assertEqual(record["horses"][1]["lockedEvaluation"]["score"], 80)
        self.assertEqual(record["freezePolicy"], SEALED_VERSION)
        result2 = prepare_seal(result["detail"], now=self.now + timedelta(minutes=1))
        self.assertEqual(result2["status"], "already-sealed")

    def test_sync_guard_never_erases_server_lock(self):
        from scripts.arvexq_protect_sync import guard
        d = seal_detail(self.d, forecast(self.d, self.now), self.now)
        update = deepcopy(d)
        update.pop("preRacePrediction")
        update["result"] = {"status": "確定"}
        protected = guard({"details": [update]}, base="test",
                          read=lambda base, rid: deepcopy(d))
        self.assertEqual(protected["details"][0]["preRacePrediction"],d["preRacePrediction"])
        self.assertEqual(protected["details"][0]["result"]["status"],"確定")

    def test_same_js_betting_core_is_archiveable(self):
        from scripts.arvexq_freeze_predictions import capture_original_bet
        import shutil
        if shutil.which("node") is None:
            self.skipTest("Node unavailable")
        d = seal_detail(self.d, forecast(self.d, self.now), self.now)
        bet = capture_original_bet(d, self.now)
        self.assertEqual(bet["raceId"], self.d["id"])
        self.assertTrue(bet["fixedBeforePost"])
        self.assertIsInstance(bet["items"], list)
        self.assertIn("jsHash", bet)
        with self.assertRaises(ValueError):
            capture_original_bet(d, self.now + timedelta(minutes=21))

    def test_result_audit_preserves_podium_vs_trifecta_distinction(self):
        from arvexq.prediction.prerace_archive import evaluate_frozen_result
        d = seal_detail(self.d, forecast(self.d,self.now),self.now)
        d["result"]={"status":"確定","finishers":[
            {"finish":1,"horseNumber":3},{"finish":2,"horseNumber":1},
            {"finish":3,"horseNumber":2}]}
        d["preRaceBet"]={"items":[{"kind":"3連単","combos":[[2,1,3]]},
                                        {"kind":"ワイド","combos":[[1,2]]}]}
        a=evaluate_frozen_result(d)
        self.assertTrue(a["honmeiTop3Hit"])
        self.assertFalse(a["honmeiWinHit"])
        self.assertTrue(a["allThreeMarked"])
        self.assertFalse(a["trifectaHit"])
        self.assertTrue(a["ticketsHit"])
        self.assertEqual(a["markedPodiumCount"],3)

    def test_server_sync_roundtrip_before_post_and_no_second_archive(self):
        """The scheduled job sends a pre-off lock and rereads the exact D1 revision."""
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        from pathlib import Path
        import json
        import os
        import sys
        from scripts import arvexq_freeze_predictions as runner
        now = datetime.now(JST)
        current = race(now, minutes=20)
        stored = {"detail": deepcopy(current), "posts": 0, "queries": 0}
        def fake_http(url, *, payload=None, token="", retries=3):
            if "/api/day?" in url:
                return {"races": [current]}
            if "/api/race/" in url:
                stored["queries"] += 1
                return {"ok": True, "detail": deepcopy(stored["detail"])}
            if url.endswith("/api/sync"):
                self.assertEqual(token, "secret-for-test")
                self.assertEqual(len(payload["details"]), 1)
                stored["posts"] += 1
                stored["detail"] = deepcopy(payload["details"][0])
                return {"ok": True}
            raise AssertionError(url)
        def fake_prepare(d, now):
            sealed = seal_detail(d, forecast(d, now), now)
            return {"status": "sealed", "detail": sealed,
                    "revision": sealed["preRacePrediction"]["sealRevision"]}
        with TemporaryDirectory() as td:
            dest = str(Path(td) / "audit.json")
            with patch.dict(os.environ, {"SYNC_TOKEN": "secret-for-test"}), \
                 patch.object(runner, "request_json", side_effect=fake_http), \
                 patch.object(runner, "prepare_seal", side_effect=fake_prepare), \
                 patch.object(runner, "capture_original_bet", return_value={
                     "raceId": current["id"], "fixedAt": now.isoformat(),
                     "decision": "見送り", "items": []}), \
                 patch.object(sys, "argv", ["runner", "--audit", dest]):
                self.assertEqual(runner.main(), 0)
                report = json.loads(Path(dest).read_text(encoding="utf-8"))
        self.assertEqual(stored["posts"], 1)
        self.assertEqual(report["sealed"], [current["id"]])
        before = deepcopy(stored["detail"]["preRacePrediction"])
        modified = deepcopy(stored["detail"])
        modified["horses"][1]["integratedEvaluation"]["mark"] = "△"
        result = restore_seal(stored["detail"], modified)
        self.assertEqual(result["preRacePrediction"], before)

    def test_cross_race_id_is_rejected(self):
        d = deepcopy(self.d)
        d["id"] += "-other"
        self.assertFalse(pre_off(forecast(self.d,self.now),d))


if __name__ == "__main__":
    unittest.main()
