from datetime import datetime
from zoneinfo import ZoneInfo

from arvexq.forecast.engine import build_prediction
from arvexq.forecast.marks import generate_marks
from arvexq.forecast.tickets import generate_tickets
from arvexq.forecast.publication import public_race

JST = ZoneInfo("Asia/Tokyo")
BEFORE = datetime(2026, 10, 19, 10, tzinfo=JST)


def example():
    return {"id": "test-2026-10-19", "date": "2026-10-19",
            "startTime": "12:00", "circuit": "地方",
            "horses": [
                {"horseNumber": 1, "name": "A",
                 "recentRaces": [{"finish": 1}, {"finish": 2}, {"finish": 1}, {"finish": 3}]},
                {"horseNumber": 2, "name": "B",
                 "recentRaces": [{"finish": 2}, {"finish": 2}, {"finish": 3}, {"finish": 1}]},
                {"horseNumber": 3, "name": "C",
                 "recentRaces": [{"finish": 5}, {"finish": 3}, {"finish": 3}, {"finish": 4}]},
            ]}


def test_preoff_prediction_and_marks_deterministic():
    a = build_prediction(example(), now=BEFORE)
    b = build_prediction(example(), now=BEFORE)
    assert a == b
    assert a["evidence"]["calibrated"] is False
    assert abs(sum(p for _, p in a["scenarios"]) - 1) < 1e-9
    assert len(generate_marks(a)) == 3
    assert generate_marks(a)[0]["mark"] in ("◎", "○", "▲")


def test_no_hindsight_or_missing_observation_fallback():
    facts = example()
    assert build_prediction(facts, now=datetime(2026, 10, 19, 12, tzinfo=JST)) is None
    facts["horses"][2]["recentRaces"] = [{"finish": 1}]
    assert build_prediction(facts, now=BEFORE) is None


def test_no_odds_means_no_recommended_purchases():
    prediction = build_prediction(example(), now=BEFORE)
    assert generate_tickets(prediction, generate_marks(prediction)) == []


def test_no_leakage_from_saved_result():
    facts = example()
    facts["result"] = {"finishers": [{"horseNumber": 3, "finish": 1}]}
    facts["preRacePrediction"] = {"marks": [{"horseNumber": 3, "mark": "◎"}]}
    a = build_prediction(facts, now=BEFORE)
    facts.pop("result")
    facts.pop("preRacePrediction")
    assert build_prediction(facts, now=BEFORE) == a


def test_historical_projection_still_purges_retired_marks():
    detail = example()
    detail["date"] = "2026-09-01"
    detail["horses"][0]["mark"] = "◎"
    result = public_race(detail)
    assert result["predictionStatus"] == "disabled"
    assert "mark" not in result["horses"][0]
