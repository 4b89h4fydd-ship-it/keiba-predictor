"""Named result audit checks (arvexq.results.audit, item 2 2026-11-08).

The old workflow verify gate was monolithic: one anonymous
"result repair incomplete" failure for the whole day.  These tests
pin the restructured behaviour: five independent named checks, every
failure carrying race_id / failure_class / expected / actual /
timestamp / retry_state, finisher completeness counting aligned with
result_state's scratch handling, and the Kochi 5R (2026-11-07)
counting question.
"""
import copy
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from arvexq.results import JST
from arvexq.results.audit import (
    ALL_CHECKS,
    audit_detail,
    audit_race,
    summarise,
)
from arvexq.results.state import result_state

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=JST)


def _detail(race_id="nar-2026-11-07-高知-05", n_card=10, finishers=None,
            payouts=None, scratches=(), non_finishers=()):
    """A Kochi-5R-shaped detail: 10 card horses, official payouts."""
    if finishers is None:
        finishers = [(1, 7), (2, 10), (3, 1), (4, 3), (5, 4),
                     (6, 5), (7, 8), (8, 9), (9, 6)]
    if payouts is None:
        payouts = [
            {"type": "単勝", "combination": "7", "amount": 1030},
            {"type": "複勝", "combination": "7", "amount": 130},
            {"type": "複勝", "combination": "10", "amount": 140},
            {"type": "複勝", "combination": "1", "amount": 120},
            {"type": "枠連", "combination": "7-8", "amount": 930},
            {"type": "馬連", "combination": "7-10", "amount": 1480},
            {"type": "馬単", "combination": "7-10", "amount": 3280},
            {"type": "ワイド", "combination": "7-10", "amount": 320},
            {"type": "ワイド", "combination": "1-7", "amount": 190},
            {"type": "ワイド", "combination": "1-10", "amount": 300},
            {"type": "3連複", "combination": "1-7-10", "amount": 1010},
            {"type": "3連単", "combination": "7-10-1", "amount": 12080},
        ]
    horses = []
    for no in range(1, n_card + 1):
        horse = {"horseNumber": no, "name": f"馬{no}", "scratched": False}
        if no in scratches:
            horse["status"] = "競走除外"
        horses.append(horse)
    fin_rows = [{"finish": fin, "horseNumber": no} for fin, no in finishers]
    result = {"status": "確定", "finishers": fin_rows, "payouts": payouts}
    if non_finishers:
        result["nonFinishers"] = [
            {"horseNumber": no, "finishLabel": label}
            for no, label in non_finishers
        ]
    return {
        "id": race_id, "date": "2026-11-07", "track": "高知",
        "raceNumber": 5, "horses": horses, "result": result,
    }


def _classes(failures):
    return {(f["check"], f["failure_class"]) for f in failures}


class KochiCountingTests(unittest.TestCase):
    """高知5R 2026-11-07: card 10, finishers 9, horse 2 unaccounted.

    Officially (keiba.go.jp RaceMarkTable) horse 2 ゲクウ is 中止 —
    the 9 stored finishers are the full official finisher list, but
    the stored detail carries no accounting of the non-finisher and
    no scratch marker, so result_state judges it incomplete.
    The audit must agree with result_state (not the old podium-only
    verify, which passed this race silently).
    """

    def test_stored_kochi_shape_fails_completeness_by_name(self):
        detail = _detail()
        self.assertFalse(result_state(detail)[0])
        failures = audit_detail(detail, expected_race_id=detail["id"], now=NOW)
        short = [f for f in failures
                 if f["failure_class"] == "finisher_count_short"]
        self.assertEqual(len(short), 1)
        self.assertEqual(short[0]["check"], "finisher_completeness")
        self.assertEqual(short[0]["race_id"], "nar-2026-11-07-高知-05")
        self.assertEqual(short[0]["expected"], 10)
        self.assertEqual(short[0]["actual"], 9)
        self.assertEqual(short[0]["missing_horse_numbers"], [2])
        self.assertTrue(short[0]["timestamp"])
        self.assertIn("retry_state", short[0])

    def test_kochi_passes_when_non_finisher_is_accounted(self):
        detail = _detail(non_finishers=[(2, "中止")])
        failures = audit_detail(detail, expected_race_id=detail["id"], now=NOW)
        self.assertNotIn(("finisher_completeness", "finisher_count_short"),
                         _classes(failures))

    def test_scratched_horse_is_not_expected_to_finish(self):
        # Same 9 finishers, but horse 2 marked 競走除外 on the card:
        # result_state's scratch handling removes it from the roster.
        detail = _detail(scratches=(2,))
        self.assertTrue(result_state(detail)[0])
        failures = audit_detail(detail, expected_race_id=detail["id"], now=NOW)
        self.assertEqual(failures, [])


class NamedCheckTests(unittest.TestCase):
    def test_clean_race_passes_all_five_checks(self):
        detail = _detail(scratches=(2,))
        failures = audit_race(detail, copy.deepcopy(detail),
                              expected_race_id=detail["id"], now=NOW,
                              retry_state="repaired_this_run")
        self.assertEqual(failures, [])
        self.assertEqual(set(summarise(failures)), set(ALL_CHECKS))

    def test_wrong_identity_result_is_named(self):
        detail = _detail(scratches=(2,))
        detail["id"] = "nar-2026-11-07-高知-06"
        failures = audit_detail(detail,
                                expected_race_id="nar-2026-11-07-高知-05",
                                now=NOW)
        self.assertIn(("race_identity", "race_id_mismatch"), _classes(failures))

    def test_foreign_result_cname_is_named(self):
        # Fukushima 7R shape: token naming 2026-09-20 race 8.
        detail = _detail(scratches=(2,))
        detail["resultCname"] = "pw01sde1009202604060820260920/F0"
        failures = audit_detail(detail, expected_race_id=detail["id"], now=NOW)
        self.assertIn(("race_identity", "result_cname_identity_conflict"),
                      _classes(failures))

    def test_short_finisher_list_is_named(self):
        detail = _detail(finishers=[(1, 7), (2, 10), (3, 1), (4, 3), (5, 4)])
        failures = audit_detail(detail, expected_race_id=detail["id"], now=NOW)
        short = [f for f in failures
                 if f["failure_class"] == "finisher_count_short"]
        self.assertEqual(len(short), 1)
        self.assertEqual(short[0]["expected"], 10)
        self.assertEqual(short[0]["actual"], 5)
        self.assertEqual(short[0]["missing_horse_numbers"], [2, 5, 6, 8, 9])

    def test_bad_payout_shape_keeps_item1_check_name(self):
        payouts = [
            {"type": "単勝", "combination": "7", "amount": 1030},
            {"type": "ワイド", "combination": "133", "amount": 35470},
        ]
        detail = _detail(scratches=(2,), payouts=payouts)
        failures = audit_detail(detail, expected_race_id=detail["id"], now=NOW)
        shape = [f for f in failures
                 if f["failure_class"] == "payout_combination_shape"]
        self.assertEqual(len(shape), 1)
        self.assertEqual(shape[0]["check"], "payout_cross_check")
        self.assertEqual(shape[0]["actual"], "133")

    def test_missing_payouts_are_named(self):
        detail = _detail(scratches=(2,), payouts=[])
        failures = audit_detail(detail, expected_race_id=detail["id"], now=NOW)
        self.assertIn(("payout_cross_check", "payout_missing"),
                      _classes(failures))

    def test_fetch_failure_is_named(self):
        failures = audit_detail(None, expected_race_id="nar-2026-11-07-高知-05",
                                fetched=False, fetch_error="HTTPError: 503",
                                now=NOW)
        self.assertEqual(_classes(failures),
                         {("result_fetch", "result_not_fetched")})
        self.assertEqual(failures[0]["actual"], "HTTPError: 503")

    def test_read_back_mismatch_is_named(self):
        source = _detail(scratches=(2,))
        read_back = copy.deepcopy(source)
        read_back["result"]["payouts"] = []
        failures = audit_race(source, read_back,
                              expected_race_id=source["id"], now=NOW)
        self.assertIn(("save_read_back", "save_read_back_mismatch"),
                      _classes(failures))

    def test_read_back_missing_is_named(self):
        source = _detail(scratches=(2,))
        failures = audit_race(source, None, expected_race_id=source["id"],
                              now=NOW, read_back_error="HTTPError: 404")
        self.assertIn(("save_read_back", "save_read_back_missing"),
                      _classes(failures))


class RunnerTests(unittest.TestCase):
    """The workflow runner: clean bundle succeeds, planted bad fails named."""

    def _bundle(self, detail):
        return {
            "date": "2026-11-07",
            "races": [{"id": detail["id"], "date": "2026-11-07",
                       "track": "高知", "raceNumber": 5,
                       "startTime": "17:10"}],
            "details": [detail],
        }

    def test_clean_bundle_reports_success(self):
        from scripts.arvexq_result_audit import run_audit
        detail = _detail(scratches=(2,))
        audit = run_audit(self._bundle(detail), {"date": "2026-11-07"},
                          now=NOW)
        self.assertTrue(audit["success"], audit["failures"])
        self.assertEqual(audit["started_race_count"], 1)

    def test_planted_bad_bundle_fails_with_check_named(self):
        from scripts.arvexq_result_audit import run_audit
        detail = _detail(finishers=[(1, 7), (2, 10), (3, 1)])
        audit = run_audit(self._bundle(detail), {"date": "2026-11-07"},
                          now=NOW)
        self.assertFalse(audit["success"])
        self.assertGreaterEqual(
            audit["checks"]["finisher_completeness"]["failure_count"], 1)
        self.assertEqual(
            audit["checks"]["finisher_completeness"]["race_ids"],
            ["nar-2026-11-07-高知-05"])

    def test_payload_is_the_read_back_comparison_source(self):
        # A genuine repair grows the finisher list (partial 3 -> full
        # 9 with one scratch).  Comparing the read-back against the
        # pre-repair bundle would flag the repair itself as a
        # save_read_back mismatch; the payload detail is the source.
        from scripts.arvexq_result_audit import run_audit
        bundle_detail = _detail(finishers=[(1, 7), (2, 10), (3, 1)])
        fixed_detail = _detail(scratches=(2,))
        bundle = self._bundle(bundle_detail)
        audit = run_audit(bundle, {"date": "2026-11-07", "repaired": [fixed_detail["id"]]},
                          read_back_details={fixed_detail["id"]: copy.deepcopy(fixed_detail)},
                          payload={"details": [fixed_detail]}, now=NOW)
        self.assertTrue(audit["success"], audit["failures"])

    def test_cli_exit_codes_and_message(self):
        import subprocess
        import sys
        detail = _detail(finishers=[(1, 7), (2, 10), (3, 1)])
        with tempfile.TemporaryDirectory() as tmp:
            bundle_path = Path(tmp) / "bundle.json"
            bundle_path.write_text(json.dumps(self._bundle(detail),
                                              ensure_ascii=False),
                                   encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "scripts/arvexq_result_audit.py",
                 "--bundle", str(bundle_path), "--report", str(Path(tmp) / "none.json"),
                 "--out", str(Path(tmp) / "audit.json"),
                 "--now", "2026-11-08T12:00:00+09:00"],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("finisher_completeness", proc.stderr + proc.stdout)
            self.assertIn("nar-2026-11-07-高知-05", proc.stderr + proc.stdout)
            audit = json.loads((Path(tmp) / "audit.json").read_text(encoding="utf-8"))
            self.assertFalse(audit["success"])
            self.assertTrue(audit["failures"][0]["timestamp"])


if __name__ == "__main__":
    unittest.main()
