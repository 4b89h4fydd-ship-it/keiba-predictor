"""Readback regression: legacy 404 must not conceal verified D1 detail."""
import json
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import arvexq_fetch_d1_bundle as hydrator

RID = "jra-2026-10-18-東京-08"
BASE = "https://kraiz-api.4b89h4fydd.workers.dev"


def run(tmp_path, responder, *, allow_missing=False):
    out = tmp_path / "d1.json"
    report = tmp_path / "audit.json"
    args = ["fetch", "--api-base", BASE, "--date", "2026-10-18",
            "--out", str(out), "--report", str(report), "--workers", "1",
            "--retries", "1"]
    if allow_missing:
        args.append("--allow-missing-details")
    with patch.object(sys, "argv", args), patch.object(hydrator, "get_json", side_effect=responder):
        outcome = hydrator.main()
    return outcome, json.loads(out.read_text()), json.loads(report.read_text())


def test_legacy_404_display_route_recovers_correct_stored_race(tmp_path):
    calls = []
    def fetch(url, timeout, retries):
        calls.append(url)
        if "/api/day?" in url:
            return {"ok": True, "date": "2026-10-18", "races": [{"id": RID}]}
        if "view=display" in url:
            return {"ok": True, "detail": {"id": RID, "horses": [
                {"horseNumber": 1, "name": "A", "recentRaces": [{"finish": 1}]}]}}
        raise HTTPError(url, 404, "not found", {}, None)
    code, bundle, audit = run(tmp_path, fetch)
    assert code == 0
    assert audit["missing_detail_count"] == 0
    assert bundle["details"][0]["id"] == RID
    assert len(calls) == 3
    assert "view=display" in calls[-1]


def test_display_wrong_identity_rejected_and_reported_not_relabelled(tmp_path):
    def fetch(url, timeout, retries):
        if "/api/day?" in url:
            return {"ok": True, "date": "2026-10-18", "races": [{"id": RID}]}
        return {"ok": True, "detail": {"id": "different-race", "horses": []}}
    code, bundle, audit = run(tmp_path, fetch, allow_missing=True)
    assert code == 0
    assert bundle["details"] == []
    assert audit["missing_detail_count"] == 1


def test_display_fallback_not_needed_when_original_is_complete(tmp_path):
    calls = []
    def fetch(url, timeout, retries):
        calls.append(url)
        if "/api/day?" in url:
            return {"ok": True, "date": "2026-10-18", "races": [{"id": RID}]}
        assert "view=display" not in url
        return {"ok": True, "detail": {"id": RID, "horses": [
            {"horseNumber": 1, "name": "A"}]}}
    code, bundle, audit = run(tmp_path, fetch)
    assert code == 0
    assert len(calls) == 2
    assert audit["detail_count"] == 1
