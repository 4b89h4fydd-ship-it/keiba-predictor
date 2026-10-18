"""D1 rich history recovery before post with strict identity and roster checks."""
from datetime import datetime, timezone, timedelta
import pytest

from scripts.arvexq_freeze_predictions import fetch_existing_d1_detail, _history_count

JST = timezone(timedelta(hours=9))
NOW = datetime(2026, 10, 18, 14, 45, tzinfo=JST)
RID = "jra-2026-10-18-京都-11"
BASE = "https://example.invalid"


def detail(*, history=False, horses=(1, 2, 3)):
    return {
        "id": RID, "date": "2026-10-18", "startTime": "15:40",
        "horses": [{"horseNumber": no, "name": str(no),
                    "recentRaces": ([{"date": "2026-09-20", "finish": 2}]
                                    if history else [])} for no in horses]
    }


def test_missing_legacy_history_recovers_existing_d1_display():
    legacy, rich = detail(), detail(history=True)
    calls = []
    def reader(url):
        calls.append(url)
        return {"detail": rich if "view=display" in url else legacy}
    saved = fetch_existing_d1_detail(BASE, RID, now=NOW, reader=reader)
    assert saved is rich
    assert _history_count(saved) == 3
    assert len(calls) == 2


def test_preserves_rich_legacy_without_secondary_request():
    rich = detail(history=True)
    urls = []
    def reader(url):
        urls.append(url)
        return {"detail": rich}
    assert fetch_existing_d1_detail(BASE, RID, now=NOW, reader=reader) is rich
    assert len(urls) == 1


def test_rejects_mismatched_roster_before_sealing():
    legacy = detail()
    wrong = detail(history=True, horses=(1, 2, 4))
    def reader(url):
        return {"detail": wrong if "view=display" in url else legacy}
    with pytest.raises(ValueError, match="active field"):
        fetch_existing_d1_detail(BASE, RID, now=NOW, reader=reader)


def test_wrong_race_or_started_race_is_never_used():
    legacy = detail()
    wrong = detail(history=True)
    wrong["id"] = "not-the-requested-race"
    def reader(url):
        return {"detail": wrong if "view=display" in url else legacy}
    assert fetch_existing_d1_detail(BASE, RID, now=NOW, reader=reader) is legacy
    assert fetch_existing_d1_detail(BASE, RID,
                                    now=datetime(2026, 10, 18, 15, 41, tzinfo=JST),
                                    reader=lambda url: {"detail": detail(history=True)}) is not None


def test_both_sources_fail_closed_without_faking_history():
    def reader(url):
        raise RuntimeError("D1 outage")
    with pytest.raises(RuntimeError, match="outage"):
        fetch_existing_d1_detail(BASE, RID, now=NOW, reader=reader)


def test_display_empty_does_not_synthesize_runs():
    legacy = detail()
    result = fetch_existing_d1_detail(BASE, RID, now=NOW,
                                      reader=lambda url: {"detail": legacy})
    assert _history_count(result) == 0
