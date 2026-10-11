import csv
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("audit", Path(__file__).resolve().parents[1] / "scripts" / "arvexq_career_odds_audit.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def A(state, acq, reason=None, failed=(), missing=()):
    return {"career_state": state, "acquisition_status": acq, "field_completeness": "x", "missing_fields": list(missing),
            "acquisition_evidence": {"reason": reason, "failedProviders": list(failed)}}


SCEN = {
    "normal": A("complete", "complete", "reported-starts-matched"),
    "zero": A("complete-no-starts", "complete", "reported-starts-matched"),
    "fieldmiss": A("complete-with-missing-fields", "complete", "reported-starts-matched", missing=["finish_position"]),
    "noevidence": A("no-history", "unverified", "no-acquisition-evidence"),
    "datemismatch": A("acquisition-unverified", "unverified", "audit-not-bound-to-this-race-date"),
    "unexpected": A("weird-state", "complete"),
    "partial": A("partially-acquired", "partial", "pagination-incomplete"),
    "failedunverified": A("acquisition-unverified", "unverified", "reported-starts-unknown", failed=["p1"]),
    "noproof": A("acquisition-unverified", "unverified", "audit-not-marked-complete"),
}
FULL_AUDIT = {"failedProviders": [], "paginationComplete": True}


def fake_analysis(horse, race):
    if horse.get("_boom"):
        raise ValueError("boom")
    return SCEN[horse["_scen"]]


def H(no, scen, **kw):
    h = {"horseNumber": no, "name": f"h{no}", "_scen": scen}
    h.update(kw)
    return h


def make_fetch(races, details, odds=None, day_extra=None, fail=()):
    def fetch(url):
        if "/api/day" in url:
            d = {"ok": True, "races": [{"id": r, "circuit": "中央", "track": "東京", "raceNumber": i + 1} for i, r in enumerate(races)], "missing": [], "complete": bool(races)}
            d.update(day_extra or {})
            return d
        rid = url.rsplit("/", 1)[1]
        if rid in fail:
            raise RuntimeError("HTTP 503")
        return {"ok": True, "detail": {"date": "2026-10-11", "circuit": "中央", "track": "東京", "horses": details[rid]}, "odds": (odds or {}).get(rid, [])}
    return fetch


class ClassifyTests(unittest.TestCase):
    def test_table(self):
        exp = {"normal": audit.L_FULL, "zero": audit.L_ZERO, "fieldmiss": audit.L_COUNT_OK_MISSING, "noevidence": audit.L_UNDECIDABLE,
               "datemismatch": audit.L_UNDECIDABLE, "unexpected": audit.L_UNDECIDABLE, "partial": audit.L_INSUFFICIENT,
               "failedunverified": audit.L_INSUFFICIENT, "noproof": audit.L_NO_PROOF}
        for k, v in exp.items():
            self.assertEqual(audit.classify_history(SCEN[k])[0], v, k)

    def test_each_horse_exactly_one_class(self):
        for k in SCEN:
            self.assertIsInstance(audit.classify_history(SCEN[k])[0], str)

    def test_unexpected_keeps_raw_state_and_reason(self):
        cls, why = audit.classify_history(SCEN["unexpected"])
        self.assertEqual(cls, audit.L_UNDECIDABLE)
        self.assertIn("weird-state", why)

    def test_absent_fields_are_unknown(self):
        self.assertEqual(audit.audit_field_states({"_careerHistoryAudit": {"complete": True}}), ("不明(欄なし)", "不明(欄なし)"))
        self.assertEqual(audit.audit_field_states({}), ("不明(取得監査なし)", "不明(取得監査なし)"))
        self.assertEqual(audit.audit_field_states({"_careerHistoryAudit": FULL_AUDIT}), ("なし(欄あり)", "完了"))
        self.assertEqual(audit.audit_field_states({"_careerHistoryAudit": {"failedProviders": ["x"], "paginationComplete": False}}), ("あり", "未完了"))

    def test_odds(self):
        self.assertEqual(audit.classify_odds({}, {"win_odds": 3.4})["odds_state"], "実オッズ取得済み")
        o = audit.classify_odds({"oddsForecast": 5.0, "oddsSource": "x"}, None)
        self.assertEqual(o["odds_state"], "未取得・原因不明")
        self.assertEqual(o["forecast_odds"], 5.0)
        self.assertIsNone(o["real_win_odds"])
        self.assertEqual(audit.classify_odds({"status": "出走取消"}, {"win_odds": None})["odds_state"], "未取得(出走取消・除外の記録あり)")


class RunTests(unittest.TestCase):
    def go(self, fetch, **kw):
        d = tempfile.mkdtemp()
        code = audit.run("2026-10-11", fetch, kw.get("analysis", fake_analysis), d, fetched_at="t")
        summ = json.loads(Path(d, "summary.json").read_text(encoding="utf-8"))
        return code, summ, d

    def test_full_run_consistency(self):
        horses = {"R1": [H(1, "normal", _careerHistoryAudit=FULL_AUDIT), H(2, "zero"), H(3, "fieldmiss"), H(4, "noevidence"), H(5, "datemismatch"), H(6, "unexpected"), H(7, "partial"), H(8, "noproof")]}
        code, s, d = self.go(make_fetch(["R1"], horses, odds={"R1": [{"horse_no": 1, "win_odds": 2.5, "popularity": 1, "updated_at": 1}]}))
        self.assertEqual(code, 0)
        self.assertTrue(s["auditComplete"])
        self.assertTrue(s["consistencyOk"])
        self.assertEqual(sum(s["historyClassCounts"].values()), 8)
        self.assertEqual(sum(s["oddsStateCounts"].values()), 8)
        self.assertEqual(s["oddsStateCounts"]["実オッズ取得済み"], 1)
        self.assertEqual(s["oddsStateCounts"]["未取得・原因不明"], 7)
        with open(Path(d, "horses.csv"), encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 8)
        self.assertEqual(len(json.loads(Path(d, "horses.json").read_text(encoding="utf-8"))), 8)
        self.assertEqual(s["paginationStateCounts"]["完了"], 1)
        self.assertEqual(s["paginationStateCounts"]["不明(取得監査なし)"], 7)
        self.assertEqual(rows[1]["evidence_caveat"] != "", True)

    def test_detail_failure_is_race_level_and_incomplete(self):
        horses = {"R1": [H(1, "normal")], "R2": [H(1, "normal")]}
        code, s, _ = self.go(make_fetch(["R1", "R2"], horses, fail={"R2"}))
        self.assertEqual(code, 0)
        self.assertFalse(s["auditComplete"])
        self.assertEqual((s["targetRaces"], s["detailFetchSucceeded"], s["detailFetchFailed"]), (2, 1, 1))
        self.assertEqual(s["failedRaces"][0]["race_id"], "R2")
        self.assertIsInstance(s["horsesInFailedRaces"], str)
        self.assertIn("欠損0とは判断しない", s["auditStatus"])
        self.assertTrue(s["consistencyOk"])

    def test_api_complete_false_and_missing_reflected(self):
        horses = {"R1": [H(1, "normal")]}
        _, s, _ = self.go(make_fetch(["R1"], horses, day_extra={"complete": False}))
        self.assertFalse(s["auditComplete"])
        _, s, _ = self.go(make_fetch(["R1"], horses, day_extra={"missing": ["R9"]}))
        self.assertFalse(s["auditComplete"])
        self.assertEqual(s["apiMissing"], ["R9"])

    def test_zero_races_is_not_complete(self):
        _, s, _ = self.go(make_fetch([], {}))
        self.assertFalse(s["auditComplete"])

    def test_day_list_failure(self):
        def boom(url):
            raise RuntimeError("down")
        code, s, _ = self.go(boom)
        self.assertEqual(code, 2)
        self.assertFalse(s["auditComplete"])

    def test_horse_analysis_exception_is_undecidable(self):
        code, s, _ = self.go(make_fetch(["R1"], {"R1": [H(1, "normal", _boom=True)]}))
        self.assertEqual(s["historyClassCounts"], {audit.L_UNDECIDABLE: 1})


class TransportTests(unittest.TestCase):
    class Resp:
        def __init__(self, body): self.body = body
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return self.body

    def test_retry_bounded_and_timeout(self):
        calls, sleeps = [], []
        def opener(req, timeout=None):
            calls.append(timeout)
            raise OSError("fail")
        with self.assertRaises(RuntimeError):
            audit.get_json("http://x", opener=opener, sleep=sleeps.append)
        self.assertEqual(len(calls), audit.MAX_RETRIES + 1)
        self.assertTrue(all(t == audit.TIMEOUT for t in calls))
        self.assertEqual(len(sleeps), audit.MAX_RETRIES)

    def test_retry_then_success(self):
        n = []
        def opener(req, timeout=None):
            n.append(1)
            if len(n) < 2:
                raise OSError("once")
            return self.Resp(b'{"ok": true}')
        self.assertEqual(audit.get_json("http://x", opener=opener, sleep=lambda s: None), {"ok": True})

    def test_get_only_and_low_concurrency(self):
        self.assertLessEqual(audit.MAX_WORKERS, 4)
        self.assertGreaterEqual(audit.MAX_WORKERS, 1)
        seen = {}
        def opener(req, timeout=None):
            seen["m"] = req.get_method()
            return self.Resp(b"{}")
        audit.get_json("http://x", opener=opener)
        self.assertEqual(seen["m"], "GET")


class ImportFailureTests(unittest.TestCase):
    def test_import_failure_is_program_failure(self):
        saved = {k: sys.modules.get(k) for k in ("arvexq", "arvexq.career_missing")}
        sys.modules["arvexq"] = None
        sys.modules.pop("arvexq.career_missing", None)
        d = tempfile.mkdtemp()
        old = audit.OUT_DIR
        audit.OUT_DIR = d
        try:
            code = audit.main()
        finally:
            audit.OUT_DIR = old
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        self.assertEqual(code, 3)
        s = json.loads(Path(d, "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(s["runFailure"], "import-failed")
        self.assertFalse(Path(d, "horses.csv").exists())


if __name__ == "__main__":
    unittest.main()
