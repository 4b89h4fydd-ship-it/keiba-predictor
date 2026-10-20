"""No new request paths, 429 fail-closed, bounded response diagnostics."""
import io
from email.message import Message
import urllib.error
import pytest

from arvexq.ingest.d1_day_readback import get_json, read_day
from arvexq.v3.audit.http429 import describe_429
from scripts import arvexq_fact_data_audit as cli


def http429(url="https://example.invalid/api/day?date=2026-10-18"):
    headers = Message()
    headers["Retry-After"] = "120"
    headers["CF-Ray"] = "0123456789abcdef-NRT"
    headers["Server"] = "cloudflare"
    headers["Set-Cookie"] = "must-not-include"
    return urllib.error.HTTPError(url, 429, "Too Many Requests", headers,
                                  io.BytesIO(b"Error 429 Too Many Requests"))


def test_first_429_is_not_retried_and_sanitized():
    calls = []
    def opener(req, timeout):
        calls.append(req.full_url)
        raise http429(req.full_url)
    with pytest.raises(urllib.error.HTTPError):
        get_json("https://example.invalid/api/day?date=2026-10-18",
                 opener=opener, sleeper=lambda _: None)
    assert len(calls) == 1
    diagnostic = describe_429(http429())
    assert diagnostic["httpStatus"] == 429
    assert diagnostic["attribution"] == "unknown-requires-cloudflare-request-log"
    assert diagnostic["responseHeadersObserved"]["retryAfter"] == "120"
    assert "Set-Cookie" not in str(diagnostic)
    assert "example.invalid" not in str(diagnostic)


def test_nested_race_read_429_preserves_record_and_fails_day_gate(monkeypatch,tmp_path):
    from scripts import arvexq_fact_data_audit as fact_cli
    calls = []
    def fetch(url):
        calls.append(url)
        if "/api/day?" in url:
            return {"ok": True, "date": "2026-10-17",
                    "races": [{"id": "nar-2026-10-17-高知-01"}]}
        raise http429(url)
    bundle = read_day("https://example.invalid", "2026-10-17", fetch=fetch, workers=1)
    assert len(bundle["readErrors"]) == 1
    assert bundle["readErrors"][0]["httpStatus"] == 429
    assert bundle["readErrors"][0]["rateLimitEvidence"]["responseBodyClass"] == "too-many-requests-marker"
    assert bundle["details"] == []
    called=[]
    def fake_read_day(_base, day):
        called.append(day)
        return {"date": day, "races": [{"id": "nar-2026-10-17-高知-01"}],
                "details": [], "readErrors": bundle["readErrors"]}
    monkeypatch.setattr(fact_cli, "read_day", fake_read_day)
    monkeypatch.setattr("sys.argv", ["audit", "--days", "2",
                                   "--end-date", "2026-10-18",
                                   "--report", str(tmp_path/"report.json")])
    assert fact_cli.main() == 1
    assert called == ["2026-10-17"]
