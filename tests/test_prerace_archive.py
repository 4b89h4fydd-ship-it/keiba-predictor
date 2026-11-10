import unittest
from copy import deepcopy
from datetime import datetime, timedelta
from arvexq.prediction.prerace_archive import (
    JST, SEALED_VERSION, post_at, pre_off, seal_detail, sealed_lock, restore_seal,
)


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

    def test_server_seals_original_honmei_role_without_posthoc_relabel(self):
        d = deepcopy(self.d)
        honmei = d["horses"][1]["integratedEvaluation"]
        honmei.update({"mark": "◎", "honmeiRole": "axis",
                       "honmeiGrade": "A", "honmeiEligible": True})
        saved = seal_detail(d, forecast(d, self.now), self.now)
        record = saved["preRacePrediction"]
        q = record["horses"][1]
        self.assertEqual(q["honmeiRole"], "axis")
        self.assertEqual(q["honmeiGrade"], "A")
        self.assertTrue(q["podiumAxisEligible"])
        changed = deepcopy(saved)
        changed["horses"][1]["integratedEvaluation"].update({
            "mark": "◎", "honmeiRole": "win", "honmeiGrade": "C",
            "honmeiEligible": False,
        })
        changed["result"] = {"status": "確定", "finishers": [{"finish": 1, "horseNumber": 3}]}
        self.assertEqual(restore_seal(saved, changed)["preRacePrediction"], record)

    def test_seal_does_not_derive_grade_from_generic_ability_grade(self):
        d = deepcopy(self.d)
        d["horses"][1]["integratedEvaluation"] = {
            "mark": "◎", "grade": "S", "score": 92,
        }
        saved = seal_detail(d, forecast(d, self.now), self.now)
        q = saved["preRacePrediction"]["horses"][1]
        self.assertEqual(q["lockedEvaluation"]["grade"], "S")
        self.assertNotIn("honmeiGrade", q)
        self.assertNotIn("honmeiRole", q)


    def test_no_fabricated_legacy_post_lock(self):
        d = deepcopy(self.d)
        lock = forecast(d, self.now + timedelta(minutes=30))
        self.assertFalse(pre_off(lock, d))
        self.assertFalse(sealed_lock(dict(d, preRacePrediction=lock)))




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

    def test_retired_server_betting_capture_is_disabled(self):
        from pathlib import Path
        source=Path("scripts/arvexq_capture_prerace_bet.js").read_text(encoding="utf-8")
        self.assertIn("RETIRED_BET_ENGINE_DISABLED", source)
        self.assertNotIn("vm.runInContext", source)


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





def test_rescue_entrypoint_registers_only_existing_production_sources():
    from pathlib import Path
    source = Path("scripts/arvexq_preoff_history_rescue.py").read_text(encoding="utf-8")
    assert "from arvexq.databanks.legacy_bridge import register_legacy_sources" in source
    assert "register_legacy_sources(vars(app))" in source
    assert "arvexq.databanks.authorized_feeds" not in source
