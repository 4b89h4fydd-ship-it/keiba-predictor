"""Guard result repair and NAR parser failures that left the UI indefinitely pending."""
import io
import unittest
from unittest.mock import patch

from arvexq.results.state import merge_detail, merge_result


class StoredResultMergeTests(unittest.TestCase):
    def test_sparse_update_keeps_final_result_and_payouts(self):
        previous = {
            "status": "確定",
            "finishers": [{"horseNumber": 1, "finish": 1},
                          {"horseNumber": 2, "finish": 2},
                          {"horseNumber": 3, "finish": 3}],
            "payouts": [{"type": "単勝", "amount": 120},
                        {"type": "馬連", "amount": 750}],
        }
        partial = {"status": "速報", "finishers": [{"horseNumber": 1, "finish": 1}],
                   "payouts": [{"type": "単勝", "amount": 120}]}
        after = merge_result(previous, partial)
        self.assertEqual(after["status"], "確定")
        self.assertEqual(after["finishers"], previous["finishers"])
        self.assertEqual(after["payouts"], previous["payouts"])
        detail = merge_detail({"id": "test-1", "result": previous, "horses": [{"horseNumber": 1}]},
                              {"id": "test-1", "result": partial, "horses": []})
        self.assertEqual(detail["result"], previous)
        self.assertEqual(len(detail["horses"]), 1)

    def test_new_complete_payout_supersedes_partial(self):
        initial = {"status": "速報", "finishers": [{"horseNumber": 1, "finish": 1}],
                   "payouts": [{"type": "単勝", "amount": 120}]}
        updated = {"status": "確定",
                   "finishers": [{"horseNumber": 1, "finish": 1},
                                 {"horseNumber": 2, "finish": 2},
                                 {"horseNumber": 3, "finish": 3}],
                   "payouts": [{"type": "単勝", "amount": 120},
                               {"type": "馬連", "amount": 750}]}
        result = merge_result(initial, updated)
        self.assertEqual(result["status"], "確定")
        self.assertEqual(len(result["finishers"]), 3)
        self.assertEqual(len(result["payouts"]), 2)


class SingleResultAcquisitionPathTests(unittest.TestCase):
    def test_realtime_sync_never_polls_result_source_independently(self):
        from pathlib import Path
        import scripts.arvexq_live_sync as live

        realtime = Path("scripts/arvexq_live_sync.py").read_text(encoding="utf-8")
        repair = Path("scripts/arvexq_result_repair.py").read_text(encoding="utf-8")
        self.assertNotIn("app._refresh_result_fast(", realtime)
        self.assertNotIn("def terminal(", realtime)
        self.assertEqual(repair.count("app._refresh_result_fast("), 1,
                         "result repair is the sole external result refresher")

        rid = "nar-2026-10-11-大井-11"
        original = {
            "id": rid, "date": "2026-10-11", "startTime": "11:00",
            "track": "大井", "raceNumber": 11, "circuit": "地方",
            "preparedMeta": {"diagnosisReady": True},
            "horses": [{"horseNumber": 1, "name": "one", "winOdds": 2.5}],
            "preRacePrediction": {"frozen": True, "raceId": rid},
            "preRaceBet": {"fixedAt": "2026-10-11T10:35:00+09:00",
                           "items": [{"kind": "馬連", "combos": [[1, 2]]}]},
            "result": {"status": "確定",
                       "finishers": [{"finish": 1, "horseNumber": 1},
                                     {"finish": 2, "horseNumber": 2},
                                     {"finish": 3, "horseNumber": 3}],
                       "payouts": [{"type": "馬連", "amount": 600}]},
        }
        partial = {"id": rid, "date": original["date"], "track": "大井",
                   "horses": [], "result": {"status": "速報",
                     "finishers": [{"finish": 1, "horseNumber": 1}]}}
        with patch.object(live, "snapshot", return_value=partial), \
             patch.object(live.app, "odds_refresh", return_value={
                 "horses": [{"horseNumber": 1, "winOdds": 3.2}]}), \
             patch.object(live.app, "_refresh_result_fast",
                          side_effect=AssertionError("duplicate result fetch")):
            _, updated, error, _, _ = live.refresh_one(
                rid, 12 * 60, {rid: original}, original)
        self.assertFalse(error, error)
        self.assertEqual(updated["result"], original["result"],
                         "live odds cannot downgrade official results/payouts")
        self.assertEqual(updated["preRacePrediction"], original["preRacePrediction"])
        self.assertEqual(updated["preRaceBet"], original["preRaceBet"])
        self.assertEqual(updated["horses"][0]["winOdds"], 3.2)



class OfficialNarResultParserTests(unittest.TestCase):
    @staticmethod
    def _html(split_col=False):
        heads = ["着順", "枠", "馬番", "馬名", "馬体重", "タイム"]
        if split_col:
            heads.append("上がり")
        lines = ["<html><body><h2>競走成績　確定</h2>",
                 "<table><tr>" + "".join("<th>" + v + "</th>" for v in heads) + "</tr>"]
        for i in range(1, 4):
            cells = [str(i), str(i), str(i), "競走馬" + str(i),
                     "480(+0)", "1:33.2"]
            if split_col:
                cells.append("37.4")
            lines.append("<tr>" + "".join("<td>" + v + "</td>" for v in cells) + "</tr>")
        lines.append("</table></body></html>")
        return "".join(lines).encode("cp932")

    def test_official_result_without_last3f_column(self):
        import app
        detail = {"id": "nar-2026-10-10-大井-01", "date": "2026-10-10",
                  "track": "大井", "raceNumber": 1,
                  "horses": [{"horseNumber": i, "name": "競走馬" + str(i)} for i in range(1, 4)]}
        with patch.object(app.urllib.request, "urlopen", return_value=io.BytesIO(self._html(False))):
            actual = app._nar_official_result_fast(detail)
        self.assertIsNotNone(actual, "NAR result without 上がり is still usable")
        self.assertEqual(actual["status"], "確定")
        self.assertEqual([x["finish"] for x in actual["finishers"]], [1, 2, 3])
        self.assertEqual([x["last3FSeconds"] for x in actual["finishers"]], [None, None, None])

    def test_official_result_with_last3f_column(self):
        import app
        detail = {"id": "nar-2026-10-10-大井-02", "date": "2026-10-10",
                  "track": "大井", "raceNumber": 2,
                  "horses": [{"horseNumber": i, "name": "競走馬" + str(i)} for i in range(1, 4)]}
        with patch.object(app.urllib.request, "urlopen", return_value=io.BytesIO(self._html(True))):
            actual = app._nar_official_result_fast(detail)
        self.assertIsNotNone(actual)
        self.assertEqual([x["last3FSeconds"] for x in actual["finishers"]], [37.4, 37.4, 37.4])



class ResultIdentityRoutingTests(unittest.TestCase):
    """The existing result fallback must not use a JRA identifier for NAR."""

    def test_nar_uses_existing_nar_race_identity_and_existing_result_url(self):
        import app
        detail = {"id": "nar-2026-10-20-盛岡-01", "date": "2026-10-20",
                  "circuit": "地方", "track": "盛岡", "raceNumber": 1}
        html = OfficialNarResultParserTests._html(False).decode("cp932")
        urls = []
        def supplied_html(url, *args):
            urls.append(url)
            return html
        with patch.object(app, "_netkeiba_get", side_effect=supplied_html), \
             patch.object(app, "_netkeiba_race_id",
                          side_effect=AssertionError("JRA identifier used for NAR")):
            result = app._netkeiba_current_result(detail)
        self.assertEqual(urls, [
            "https://race.netkeiba.com/race/result.html?race_id=202635102001"])
        self.assertIsNotNone(result)
        self.assertEqual([r["horseNumber"] for r in result["finishers"]], [1, 2, 3])

    def test_explicit_saved_nar_identifier_is_preserved(self):
        import app
        detail = {"id": "nar-2026-10-20-盛岡-01",
                  "netkeibaRaceId": "202635102001",
                  "date": "2026-10-20", "circuit": "地方",
                  "track": "盛岡", "raceNumber": 1}
        with patch.object(app, "_nar_netkeiba_race_id",
                          side_effect=AssertionError("must use saved ID")), \
             patch.object(app, "_netkeiba_get", return_value=""):
            self.assertIsNone(app._netkeiba_current_result(detail))

    def test_jra_still_uses_the_original_jra_resolver(self):
        import app
        detail = {"id": "jra-2026-10-18-東京-08", "date": "2026-10-18",
                  "circuit": "中央", "track": "東京", "raceNumber": 8}
        urls = []
        def grab(url, *args):
            urls.append(url)
            return ""
        with patch.object(app, "_netkeiba_race_id", return_value="202605040808") as jra, \
             patch.object(app, "_nar_netkeiba_race_id",
                          side_effect=AssertionError("NAR resolver used for JRA")), \
             patch.object(app, "_netkeiba_get", side_effect=grab):
            self.assertIsNone(app._netkeiba_current_result(detail))
        jra.assert_called_once_with("2026-10-18", "東京", 8)
        self.assertEqual(urls, ["https://race.netkeiba.com/race/result.html?race_id=202605040808"])



class OfficialNarResultFailureReasonTests(unittest.TestCase):
    """Track source/parser misses without fabricating a result or switching routes."""

    def test_source_has_no_published_result_marker(self):
        import app
        detail = {"id": "nar-2026-10-20-盛岡-01", "date": "2026-10-20",
                  "track": "盛岡", "raceNumber": 1, "horses": []}
        calls = []
        def no_result(_request, timeout=None):
            calls.append("existing NAR endpoint")
            return io.BytesIO("<html><body>現在未公開</body></html>".encode("cp932"))
        with patch.object(app.urllib.request, "urlopen", side_effect=no_result), \
             patch("builtins.print") as printed:
            result = app._nar_official_result_fast(detail)
        self.assertIsNone(result)
        self.assertEqual(len(calls), 2)
        self.assertTrue(any("result_marker_missing" in str(c)
                            for c in printed.call_args_list))
        self.assertTrue(any("NAR_RESULT_UNRESOLVED" in str(c)
                            for c in printed.call_args_list))

    def test_unrecognized_official_table_is_not_saved_as_confirmed_result(self):
        import app
        detail = {"id": "nar-2026-10-20-盛岡-02", "date": "2026-10-20",
                  "track": "盛岡", "raceNumber": 2, "horses": []}
        html = ("<html><body>競走成績<table>"
                "<tr><th>着順</th><th>馬番</th><th>馬名</th></tr>"
                "<tr><td>1</td><td>1</td><td>検証馬</td></tr>"
                "</table></body></html>").encode("cp932")
        with patch.object(app.urllib.request, "urlopen",
                          side_effect=lambda *_a, **_k: io.BytesIO(html)), \
             patch("builtins.print") as printed:
            result = app._nar_official_result_fast(detail)
        self.assertIsNone(result)
        self.assertTrue(any("result_table_unrecognized" in str(c)
                            for c in printed.call_args_list))


class RealtimeResultRetentionTests(unittest.TestCase):
    def test_live_merge_does_not_shrink_confirmed_placings_or_payouts(self):
        import copy
        from scripts.arvexq_live_sync import merge_live
        saved_result = {
            "status": "確定",
            "finishers": [{"horseNumber": 1, "finish": 1},
                          {"horseNumber": 2, "finish": 2},
                          {"horseNumber": 3, "finish": 3}],
            "payouts": [{"type": "単勝", "amount": 200},
                        {"type": "馬連", "amount": 1100}],
        }
        for circuit, race_id in (
            ("地方", "nar-2026-10-20-盛岡-03"),
            ("中央", "jra-2026-10-18-東京-08"),
        ):
            with self.subTest(circuit=circuit):
                original = {"id": race_id, "circuit": circuit,
                            "date": "2026-10-20" if circuit == "地方" else "2026-10-18",
                            "horses": [{"horseNumber": 1, "name": "馬A"}],
                            "result": copy.deepcopy(saved_result),
                            "preRacePrediction": {"frozen": True}}
                saved = copy.deepcopy(original)
                sparse_final = {
                    "id": race_id, "circuit": circuit,
                    "result": {
                        "status": "確定",
                        "finishers": [{"horseNumber": 1, "finish": 1}],
                        "payouts": [{"type": "単勝", "amount": 200}],
                    },
                }
                merged = merge_live(original, sparse_final, {})
                self.assertEqual(merged["result"], saved_result)
                self.assertEqual(merged["horses"], saved["horses"])
                self.assertEqual(merged["preRacePrediction"], saved["preRacePrediction"])
                self.assertEqual(original, saved)

    def test_live_merge_accepts_richer_confirmed_result(self):
        from scripts.arvexq_live_sync import merge_live
        initial = {"id": "nar-2026-10-20-盛岡-03", "result": {
            "status": "速報",
            "finishers": [{"horseNumber": 1, "finish": 1}],
        }}
        confirmed = {"result": {
            "status": "確定",
            "finishers": [{"horseNumber": 1, "finish": 1},
                          {"horseNumber": 2, "finish": 2},
                          {"horseNumber": 3, "finish": 3}],
            "payouts": [{"type": "単勝", "amount": 180}],
        }}
        merged = merge_live(initial, confirmed, {})
        self.assertEqual(merged["result"], confirmed["result"])


class LiveD1BaseReadbackTests(unittest.TestCase):
    """The existing live fallback must seed verified full data, not a thin shell."""

    def test_packed_d1_race_rehydrates_all_facts_and_frozen_originals(self):
        import json
        from arvexq.ingest.full_snapshot_codec import pack_detail
        from scripts import arvexq_live_sync as live
        for rid, circuit, track in (
            ("nar-2026-10-20-盛岡-01", "地方", "盛岡"),
            ("jra-2026-10-18-東京-08", "中央", "東京"),
        ):
            with self.subTest(circuit=circuit):
                day = "2026-10-20" if circuit == "地方" else "2026-10-18"
                full = {"id": rid, "date": day, "circuit": circuit,
                        "track": track, "raceNumber": 1 if circuit == "地方" else 8,
                        "horses": [{"horseNumber": 1, "name": "検証馬",
                                    "allPastRuns": [{"date": "2026-09-01", "finish": 2}]}],
                        "preRaceBet": {"frozen": True, "tickets": [[1, 2, 3]]},
                        "result": {"status": "確定",
                                   "finishers": [{"finish": 1, "horseNumber": 1}]}}
                response = json.dumps({"ok": True, "detail": pack_detail(full)},
                                      ensure_ascii=False).encode("utf-8")
                with patch.object(live.urllib.request, "urlopen",
                                  return_value=io.BytesIO(response)) as opened:
                    actual = live.fetch_d1_detail(rid, day)
                self.assertEqual(actual, full)
                url = opened.call_args.args[0].full_url
                self.assertIn("/api/race/", url)
                self.assertNotIn("view=display", url)

    def test_unmatched_race_wrong_day_and_bad_digest_fail_closed(self):
        import copy
        import json
        from arvexq.ingest.full_snapshot_codec import pack_detail
        from scripts import arvexq_live_sync as live
        rid = "nar-2026-10-20-盛岡-01"
        right = {"id": rid, "date": "2026-10-20",
                 "horses": [{"horseNumber": 1, "name": "検証馬"}]}
        mismatched = copy.deepcopy(right)
        mismatched["id"] = "nar-2026-10-20-盛岡-02"
        wrong_day = copy.deepcopy(right)
        wrong_day["date"] = "2026-10-19"
        damaged = pack_detail(right)
        damaged["arvexqFullPayload"]["sha256"] = "0" * 64
        cases = (
            {"ok": False, "detail": right},
            {"ok": True, "detail": mismatched},
            {"ok": True, "detail": wrong_day},
            {"ok": True, "detail": damaged},
        )
        for data in cases:
            with self.subTest(data=data.get("detail", {}).get("id")):
                response = json.dumps(data, ensure_ascii=False).encode("utf-8")
                with patch.object(live.urllib.request, "urlopen",
                                  return_value=io.BytesIO(response)), \\
                     patch("builtins.print") as recorded:
                    actual = live.fetch_d1_detail(rid, "2026-10-20")
                self.assertIsNone(actual)
                self.assertTrue(any("D1_BASE_FETCH_ERROR" in str(call)
                                    for call in recorded.call_args_list))


if __name__ == "__main__":
    unittest.main()
