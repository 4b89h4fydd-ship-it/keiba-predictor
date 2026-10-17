from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from arvexq.forecast.preoff_capture import capture_preoff_features
from arvexq.forecast.frozen_research_input import from_frozen_snapshot

JST = timezone(timedelta(hours=9))


def card():
    return {"id": "jra-2026-08-01-東京-01", "date": "2026-08-01",
            "startTime": "12:00", "circuit": "中央", "track": "東京",
            "surface": "芝", "distance": 1600, "condition": "良",
            "preRacePrediction": {"mark": "◎", "score": 99},
            "horses": [
                {"horseNumber": i, "age": 3, "carriedWeight": 55.,
                 "integratedEvaluation": {"score": 99, "mark": "◎"},
                 "recentRaces": [{"date": "2026-07-20", "finish": i, "fieldSize": 10,
                                  "track": "東京", "surface": "芝", "distance": 1600}]}
                for i in (1, 2, 3, 4)
            ]}


def test_capture_does_not_use_predictions_or_mutate_source():
    race = card()
    saved = deepcopy(race)
    before = datetime(2026, 8, 1, 11, 15, tzinfo=JST)
    snapshot, receipt = capture_preoff_features(race, [1, 2, 3, 4], now=before)
    assert race == saved
    assert receipt["capturedAtEpoch"] < receipt["postAtEpoch"]
    assert len(receipt["receiptHash"]) == 64
    assert "integratedEvaluation" not in str(snapshot)
    assert "preRacePrediction" not in str(snapshot)
    rows = from_frozen_snapshot(snapshot, receipt)
    assert len(rows["horses"]) == 4
    assert all("finish" not in h for h in rows["horses"])


def test_capture_rejects_post_off_result_scratched_and_incomplete_roster():
    race = card()
    with pytest.raises(ValueError, match="already started"):
        capture_preoff_features(race, [1, 2, 3, 4],
                                now=datetime(2026, 8, 1, 12, tzinfo=JST))
    race["result"] = {"status": "確定"}
    with pytest.raises(ValueError, match="post-race"):
        capture_preoff_features(race, [1, 2, 3, 4],
                                now=datetime(2026, 8, 1, 11, tzinfo=JST))
    race = card()
    race["horses"][1]["scratched"] = True
    with pytest.raises(ValueError, match="inactive"):
        capture_preoff_features(race, [1, 2, 3, 4],
                                now=datetime(2026, 8, 1, 11, tzinfo=JST))
    with pytest.raises(ValueError, match="missing"):
        capture_preoff_features(card(), [1, 2, 3, 5],
                                now=datetime(2026, 8, 1, 11, tzinfo=JST))
