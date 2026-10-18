"""Live cards may show new pre-off provisional marks, never retired predictions."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from arvexq.forecast.publication import public_race

JST = ZoneInfo("Asia/Tokyo")


def _future_race():
    tomorrow = (datetime.now(JST) + timedelta(days=1)).date().isoformat()
    return {
        "id": "nar-provisional-smoke", "date": tomorrow, "startTime": "23:59",
        "circuit": "地方", "track": "園田",
        "predictionMarks": [{"horseNumber": 1, "mark": "☆"}],  # retired, not authoritative
        "horses": [
            {"horseNumber": 1, "name": "A",
             "mark": "注", "recentRaces": [{"finish": 1}, {"finish": 2}, {"finish": 1}]},
            {"horseNumber": 2, "name": "B",
             "mark": "◎", "recentRaces": [{"finish": 2}, {"finish": 1}, {"finish": 3}]},
            {"horseNumber": 3, "name": "C",
             "mark": "△", "recentRaces": [{"finish": 3}, {"finish": 3}, {"finish": 2}]},
        ],
    }


def test_live_projection_replaces_archived_marks():
    source = _future_race()
    out = public_race(source)
    assert out["predictionStatus"] == "provisional"
    assert out["predictionModelVersion"].startswith("arvexq-observed-history-baseline-")
    assert len(out["predictionMarks"]) == 3
    assert {m["mark"] for m in out["predictionMarks"]} == {"◎", "○", "▲"}
    assert {h["mark"] for h in out["horses"]} == {"◎", "○", "▲"}
    assert source["horses"][0]["mark"] == "注"
    assert out["recommendedBetsStatus"] == "not_evaluated_without_verified_odds"


def test_stale_payloads_do_not_reappear_without_evidence():
    source = _future_race()
    source["horses"][2]["recentRaces"] = [{"finish": 1}]
    out = public_race(source)
    assert out["predictionStatus"] == "disabled"
    assert "predictionMarks" not in out
    assert "mark" not in out["horses"][0]
    assert "predictionEvidence" not in out
