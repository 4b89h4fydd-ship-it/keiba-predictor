"""Provenance and label-isolation tests for archived pre-race feature inputs."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import pytest

from arvexq.forecast.frozen_research_input import from_frozen_snapshot
from arvexq.prediction.mass_feature_snapshot import build_mass_feature_snapshot


def frozen():
    detail = {
        "id": "jra-2026-08-01-東京-01", "date": "2026-08-01",
        "track": "東京", "circuit": "中央", "raceNumber": 1,
        "surface": "ダート", "distance": 1400, "condition": "良",
        "horses": [
            {"horseNumber": n, "age": 3, "carriedWeight": 55,
             "winOdds": 2.0 * n,
             "recentRaces": [{"date": "2026-07-16", "finish": n,
                              "fieldSize": 10, "distance": 1400,
                              "surface": "ダート", "track": "東京"}]}
            for n in range(1, 5)
        ],
    }
    snapshot = build_mass_feature_snapshot(detail)
    jst = timezone(timedelta(hours=9))
    post = int(datetime(2026, 8, 1, 12, tzinfo=jst).timestamp())
    receipt = {
        "raceId": detail["id"], "featureHash": snapshot["featureHash"],
        "source": "preoff-acquisition-log", "attestedPreOff": True,
        "capturedAtEpoch": post - 3600, "postAtEpoch": post,
        "activeHorseNumbers": [1, 2, 3, 4],
    }
    labels = [{"horseNumber": i, "finish": i} for i in range(1, 5)]
    return snapshot, receipt, labels


def test_verified_snapshot_does_not_use_market_or_outcome_features():
    snapshot, receipt, finishes = frozen()
    untouched = deepcopy(snapshot)
    race = from_frozen_snapshot(snapshot, receipt, finishes)
    assert race["horses"][0]["finish"] == 1
    assert "market::win_odds" not in race["horses"][0]["features"]
    assert "static::age" in race["horses"][0]["features"]
    assert race["snapshotHash"] == snapshot["featureHash"]
    assert snapshot == untouched
    live = from_frozen_snapshot(snapshot, receipt)
    assert all("finish" not in row for row in live["horses"])


def test_fail_closed_on_unverified_or_changed_original():
    snapshot, receipt, finishes = frozen()
    bad = deepcopy(snapshot)
    bad["rows"][0]["features"]["static::age"] = 99
    with pytest.raises(ValueError, match="hash"):
        from_frozen_snapshot(bad, receipt, finishes)
    badreceipt = dict(receipt, attestedPreOff=False)
    with pytest.raises(ValueError, match="receipt"):
        from_frozen_snapshot(snapshot, badreceipt, finishes)
    badreceipt = dict(receipt, capturedAtEpoch=receipt["postAtEpoch"])
    with pytest.raises(ValueError, match="pre-off"):
        from_frozen_snapshot(snapshot, badreceipt, finishes)
    badreceipt = dict(receipt, activeHorseNumbers=[1, 2, 3, 5])
    with pytest.raises(ValueError, match="absent"):
        from_frozen_snapshot(snapshot, badreceipt, finishes)
    with pytest.raises(ValueError, match="match"):
        from_frozen_snapshot(snapshot, receipt, finishes[:-1])
