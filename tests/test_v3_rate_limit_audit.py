"""Live fact auditor must stop repeated API reads on first 429."""
from pathlib import Path
import json
import urllib.error

from scripts import arvexq_fact_data_audit as cli


def test_first_api_429_aborts_remaining_day_requests(monkeypatch, tmp_path):
    calls = []
    def unavailable(_base, day):
        calls.append(day)
        raise urllib.error.HTTPError("https://example.invalid/api/day", 429,
                                     "Too Many Requests", {}, None)
    monkeypatch.setattr(cli, "read_day", unavailable)
    report_file = tmp_path / "limited.json"
    monkeypatch.setattr("sys.argv", [
        "audit", "--days", "7", "--end-date", "2026-10-18",
        "--report", str(report_file)])
    assert cli.main() == 1
    report = json.loads(report_file.read_text())
    assert calls == ["2026-10-12"]
    assert report["days"][0]["readErrors"][0]["error"] == "api-http-429"
    assert all(day["readErrors"][0]["error"] == "skipped-after-api-http-429"
               for day in report["days"][1:])
    assert all(day["allRaceReadsVerified"] is False for day in report["days"])


def test_regular_http_failure_does_not_masquerade_as_rate_limit(monkeypatch, tmp_path):
    calls = []
    def unavailable(_base, day):
        calls.append(day)
        raise urllib.error.HTTPError("https://example.invalid/api/day", 503,
                                     "Unavailable", {}, None)
    monkeypatch.setattr(cli, "read_day", unavailable)
    report_file = tmp_path / "unavailable.json"
    monkeypatch.setattr("sys.argv", [
        "audit", "--days", "2", "--end-date", "2026-10-18",
        "--report", str(report_file)])
    assert cli.main() == 1
    report = json.loads(report_file.read_text())
    assert calls == ["2026-10-17", "2026-10-18"]
    assert report["days"][0]["readErrors"][0]["status"] == "read-error-not-verified"
