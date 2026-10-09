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

    def test_shadow_stays_as_captured_through_later_result_updates(self):
        d = seal_detail(self.d, forecast(self.d,self.now),self.now)
        self.assertIn("researchShadow",d)
        old_hash = d["researchShadow"]["hash"]
        changed = deepcopy(d)
        changed["horses"][0]["recentRaces"].append({
            "date":"2026-10-10","finish":1,"fieldSize":12,
            "cornerPositions":[1,1,1,1]})
        changed["result"]={"status":"確定","finishers":[
            {"horseNumber":2,"finish":1}]}
        changed["researchShadow"]={"hash":"malicious-post-hoc-recalculation"}
        restored = restore_seal(d,changed)
        self.assertEqual(restored["researchShadow"]["hash"],old_hash)
        self.assertEqual(restored["researchFactorShadow"]["hash"], d["researchFactorShadow"]["hash"])
        self.assertEqual(restored["result"]["status"],"確定")

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
        # A prior sealed snapshot without a ticket is preserved and queued
        # for ticket capture while the race is still in the pre-off window.
        result2 = prepare_seal(result["detail"], now=self.now + timedelta(minutes=1))
        self.assertEqual(result2["status"], "sealed")
        self.assertEqual(result2["detail"]["preRacePrediction"], record)
        complete = deepcopy(result["detail"])
        complete["preRaceBet"] = {"raceId": self.d["id"],
                                  "fixedAt": self.now.isoformat(), "items": []}
        self.assertEqual(prepare_seal(complete,now=self.now+timedelta(minutes=1))["status"],"already-sealed")

    def test_d1_seal_guard_can_insert_new_race_only_with_verified_day(self):
        import io
        import json
        import urllib.error
        from unittest.mock import patch
        from scripts.arvexq_protect_sync import fetch_current

        def from_remote(req, timeout=25):
            url = str(req.full_url)
            if "/api/race/" in url:
                raise urllib.error.HTTPError(url, 404, "race not found", {}, None)
            if "/api/day?" in url:
                return io.BytesIO(json.dumps({
                    "date": "2026-10-09", "races": [],
                }).encode())
            raise AssertionError("unexpected endpoint " + url)

        with patch("urllib.request.urlopen", side_effect=from_remote):
            self.assertIsNone(fetch_current("https://unit.test", "nar-2026-10-09-大井-01"))

        def invalid_remote(req, timeout=25):
            if "/api/race/" in str(req.full_url):
                raise urllib.error.HTTPError(str(req.full_url), 404, "not found", {}, None)
            return io.BytesIO(json.dumps({"date": "2026-10-09", "races": None}).encode())

        with patch("urllib.request.urlopen", side_effect=invalid_remote):
            with self.assertRaisesRegex(RuntimeError, "cannot be confirmed"):
                fetch_current("https://unit.test", "nar-2026-10-09-大井-01")

    def test_d1_empty_day_requires_explicit_cold_start(self):
        import json
        import sys
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from scripts import arvexq_fetch_d1_bundle as bundle

        with TemporaryDirectory() as tmp:
            output = str(Path(tmp) / "day.json")
            report = str(Path(tmp) / "report.json")
            args = ["fetch-d1", "--api-base", "https://unit.test",
                    "--date", "2026-10-09", "--out", output,
                    "--report", report, "--allow-empty-day"]
            with patch.object(sys, "argv", args), patch.object(bundle, "get_json", return_value={
                "date": "2026-10-09", "races": [],
            }):
                self.assertEqual(bundle.main(), 0)
            self.assertEqual(json.loads(Path(output).read_text())["races"], [])
            self.assertTrue(json.loads(Path(report).read_text())["empty_day"])

            args.remove("--allow-empty-day")
            with patch.object(sys, "argv", args), patch.object(bundle, "get_json", return_value={
                "date": "2026-10-09", "races": [],
            }):
                with self.assertRaises(SystemExit):
                    bundle.main()

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

    def test_scratch_excluded_from_core_rank_without_deleting_racecard(self):
        from scripts.arvexq_freeze_predictions import prepare_seal
        d = deepcopy(self.d)
        d["horses"].insert(0,{
            "horseNumber": 4, "name": "CANCELLED", "status": "出走取消",
            "scratched": True, "recentRaces": [{"finish": 1}],
            "integratedEvaluation": {"mark": "◎", "grade": "S"}})
        seen = []
        def assign_core(data):
            seen.extend(h["horseNumber"] for h in data["horses"])
            for h, mark in zip(data["horses"],("◎", "○", "▲")):
                h["integratedEvaluation"]["mark"] = mark
            return data
        def build_active(wd):
            active = deepcopy(wd)
            active["horses"] = [h for h in wd["horses"] if not h.get("scratched")]
            return forecast(active,self.now)
        result = prepare_seal(d, now=self.now, assign=assign_core,
                              build=build_active)
        self.assertEqual(result["status"], "sealed")
        self.assertEqual(seen, [1,2,3])
        self.assertEqual(len(result["detail"]["horses"]),4)
        locked = result["detail"]["preRacePrediction"]["horses"]
        self.assertNotIn(4,[r["horseNumber"] for r in locked])
        self.assertEqual(result["detail"]["horses"][0]["integratedEvaluation"]["mark"],"")

    def test_post_sync_detects_race_condition_erasure(self):
        from scripts.arvexq_protect_sync import verify_published
        original = seal_detail(self.d,forecast(self.d,self.now),self.now)
        good = lambda base,rid: deepcopy(original)
        self.assertEqual(verify_published({"details":[original]},base="test",read=good),
                         [self.d["id"]])
        bad = lambda base,rid: {"id":self.d["id"],"date":self.d["date"],
                                "startTime":self.d["startTime"]}
        with self.assertRaisesRegex(RuntimeError,"POST_VERIFY_MISMATCH"):
            verify_published({"details":[original]},base="test",read=bad)

    def test_existing_sealed_marks_survive_ticket_backfill_before_off(self):
        from scripts.arvexq_freeze_predictions import prepare_seal
        d = seal_detail(self.d, forecast(self.d,self.now),self.now)
        result = prepare_seal(d,now=self.now+timedelta(minutes=1))
        self.assertEqual(result["status"],"sealed")
        self.assertEqual(result["detail"]["preRacePrediction"],d["preRacePrediction"])

    def test_cross_race_id_is_rejected(self):
        d = deepcopy(self.d)
        d["id"] += "-other"
        self.assertFalse(pre_off(forecast(self.d,self.now),d))


    def test_real_payout_audit_and_kind_metrics_are_not_estimated(self):
        from arvexq.prediction.prerace_archive import (
            evaluate_frozen_result, summarize_frozen_ticket_metrics,
        )
        d = seal_detail(self.d, forecast(self.d, self.now), self.now)
        d["preRaceBet"] = {
            "raceId": d["id"], "fixedAt": self.now.isoformat(),
            "items": [
                {"level": "本線", "kind": "馬連", "combos": [[1, 3], [1, 2]]},
                {"level": "3連単チャレンジ", "kind": "3連単",
                 "combos": [[3, 1, 2], [3, 2, 1]]},
                {"level": "保険", "kind": "ワイド", "combos": [[2, 3]]},
            ],
        }
        d["result"] = {"status": "確定",
            "finishers": [
                {"finish": 1, "horseNumber": 3},
                {"finish": 2, "horseNumber": 1},
                {"finish": 3, "horseNumber": 2},
            ],
            "payouts": [
                {"type": "馬連", "combination": "1-3", "amount": 1400},
                {"type": "3連単", "combination": "3→1→2", "amount": 9800},
                {"type": "ワイド", "combination": "2-3", "amount": 300},
            ],
        }
        audit = evaluate_frozen_result(d)
        kinds = {x["kind"]: x for x in audit["ticketEvaluations"]}
        self.assertEqual(kinds["馬連"]["payoutYenAt100"], 1400)
        self.assertEqual(kinds["3連単"]["payoutYenAt100"], 9800)
        self.assertEqual(kinds["ワイド"]["payoutYenAt100"], 300)
        self.assertTrue(all(x["hit"] for x in kinds.values()))
        metrics = summarize_frozen_ticket_metrics([audit])["byKind"]
        self.assertEqual(metrics["3連単"]["averagePoints"], 2.0)
        self.assertEqual(metrics["3連単"]["flatStakeReturnRate"], 49.0)
        self.assertEqual(metrics["馬連"]["observedHitRate"], 1.0)
        self.assertTrue(metrics["3連単"]["completePayouts"])

        unavailable = deepcopy(d)
        unavailable["result"].pop("payouts")
        no_payout = evaluate_frozen_result(unavailable)
        missing = summarize_frozen_ticket_metrics([audit, no_payout])["byKind"]
        self.assertIsNone(missing["3連単"]["flatStakeReturnRate"])
        self.assertIsNone(missing["3連単"]["payoutYenAt100"])
        self.assertEqual(missing["3連単"]["sampleRaces"], 2)
        self.assertEqual(missing["3連単"]["averagePoints"], 2)



if __name__ == "__main__":
    unittest.main()
