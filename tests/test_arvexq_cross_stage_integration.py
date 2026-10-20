"""Integration-only, read-only contracts joining pre-existing Stage1/2/3 behavior.

This file adds no production route, prediction or provider.  CI runs it on the
isolated #373 candidate; the underlying stage PRs remain separate.
"""
from __future__ import annotations
import urllib.error

from arvexq.databanks.legacy_bridge import _nar_store_adapters
from arvexq.ingest.d1_day_readback import read_day
from arvexq.quality.fact_audit import audit_day

DAY = "2026-10-20"
NAR_ID = "nar-2026-10-20-大井-01"
JRA_ID = "jra-2026-10-20-東京-01"


def test_stage1_age_sex_filter_reaches_stage3_sqlite_bridge():
    requests = []

    class Store:
        def recent_races(self, *args):
            requests.append(args)
            return [{"date": "2026-10-19", "finish": 2}]

        def prize_before(self, name, cutoff):
            return 0

    history, _connections = _nar_store_adapters({"NarStore": Store})
    result = history({"name": "同名馬", "age": 3, "sex": "牝"},
                     {"date": DAY}, limit=5)
    assert requests == [("同名馬", DAY, 5, 3, "牝")]
    assert len(result["recentRaces"]) == 1
    assert result["allPastRuns"] == []


def test_stage3_circuit_isolation_preserves_stage2_missing_history_and_display_evidence():
    details = [
        {"id": JRA_ID, "date": DAY, "circuit": "中央", "track": "東京",
         "raceNumber": 1, "horses": [{"horseNumber": 1, "name": "同名馬"}]},
        {"id": NAR_ID, "date": DAY, "circuit": "地方", "track": "大井",
         "raceNumber": 1, "horses": [{"horseNumber": 1, "name": "同名馬"}]},
    ]
    readback_error = {"raceId": NAR_ID, "reason": "display_fact_mismatch",
                      "fields": ["result.finishers"]}
    result = audit_day({"date": DAY,
                        "races": [{"id": d["id"]} for d in details],
                        "details": details, "readErrors": [],
                        "displayParityErrors": [readback_error]})
    assert result["validationErrors"] == []
    assert len(result["missingHistoryReasons"]) == 2
    assert result["displayParityErrors"] == [readback_error]
    assert all(r["reason"] == "acquisition-unverified"
               for r in result["missingHistoryReasons"])


def test_stage3_http429_fail_closed_even_with_stage2_display_parity_enabled():
    called = []

    def fetch(url):
        called.append(url)
        if "/api/day?" in url:
            return {"ok": True, "date": DAY, "races": [{"id": NAR_ID}]}
        raise urllib.error.HTTPError(url, 429, "throttled", {}, None)

    bundle = read_day("https://unit.invalid", DAY, fetch=fetch,
                      workers=1, verify_display=True)
    assert len(called) == 2  # No display fallback on HTTP 429.
    assert bundle["details"] == []
    assert bundle["displayParityErrors"] == []
    assert len(bundle["readErrors"]) == 1
    assert bundle["readErrors"][0]["httpStatus"] == 429
    assert bundle["readErrors"][0]["error"] == "api-http-429"
