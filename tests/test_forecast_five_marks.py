"""Contracts for new isolated five-symbol marking; no production enablement."""
from arvexq.forecast.marks import generate_marks


def forecast():
    return {
        "approvedForProduction": True,
        "horses": [
            {"horseNumber": 4, "winProbability": 0.35, "top3Probability": 0.75},
            {"horseNumber": 2, "winProbability": 0.25, "top3Probability": 0.65},
            {"horseNumber": 5, "winProbability": 0.20, "top3Probability": 0.55},
            {"horseNumber": 3, "winProbability": 0.12, "top3Probability": 0.40},
            {"horseNumber": 1, "winProbability": 0.08, "top3Probability": 0.30},
        ],
    }


def test_approved_pre_race_probabilities_get_five_distinct_marks():
    assert generate_marks(forecast()) == [
        {"horseNumber": 4, "mark": "◎"},
        {"horseNumber": 2, "mark": "○"},
        {"horseNumber": 5, "mark": "▲"},
        {"horseNumber": 3, "mark": "△"},
        {"horseNumber": 1, "mark": "☆"},
    ]


def test_research_only_and_unapproved_forecast_return_empty():
    data = forecast()
    data.pop("approvedForProduction")
    assert generate_marks(data) == []
    data["approvedForProduction"] = False
    assert generate_marks(data) == []
    assert generate_marks(None) == []


def test_missing_invalid_or_duplicate_forecast_fails_closed():
    data = forecast()
    data["horses"][0]["top3Probability"] = None
    assert generate_marks(data) == []
    data = forecast()
    data["horses"][0]["horseNumber"] = 2
    assert generate_marks(data) == []
    data = forecast()
    data["horses"][0]["winProbability"] = 0.9
    assert generate_marks(data) == []
    data = forecast()
    data["horses"][0]["winProbability"] = float("nan")
    assert generate_marks(data) == []


def test_ties_break_deterministically_with_podium_then_horse_number():
    data = {"approvedForProduction": True, "horses": [
        {"horseNumber": 8, "winProbability": 0.5, "top3Probability": 0.8},
        {"horseNumber": 1, "winProbability": 0.5, "top3Probability": 0.9},
    ]}
    assert generate_marks(data) == [
        {"horseNumber": 1, "mark": "◎"}, {"horseNumber": 8, "mark": "○"}
    ]
