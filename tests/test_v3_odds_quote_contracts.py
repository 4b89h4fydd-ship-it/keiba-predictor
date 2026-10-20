"""Regression: stage-9 quote and odds contracts must not overwrite each other."""
from copy import deepcopy

import pytest

from arvexq.v3.transport.api import factual_response
from arvexq.v3.transport.display import factual_screen


@pytest.mark.parametrize("circuit,track", [("JRA", "東京"), ("NAR", "高知")])
def test_odds_and_quote_contracts_are_independent(circuit, track):
    source = {
        "id": f"{circuit.lower()}-2026-10-18-{track}-08",
        "date": "2026-10-18",
        "circuit": circuit,
        "track": track,
        "oddsUpdatedAt": "12:34:00",
        "horses": [
            {"horseNumber": 1, "name": "一号", "winOdds": 2.4,
             "placeOdds": "1.2-1.4", "popularity": 1, "mark": "◎"},
            {"horseNumber": 2, "name": "二号", "winOdds": None,
             "popularity": None, "predictionScore": 99},
        ],
        "result": {
            "finishers": [{"horseNumber": 1, "finish": 1}],
            "payouts": [{"kind": "単勝", "payout": 240}],
        },
    }
    frozen = deepcopy(source)
    response = factual_response(source)

    assert response["oddsFields"]["schema"] == "arvexq-v3-observed-odds-fields-1"
    assert response["quoteFields"]["schema"] == "arvexq-v3-observed-quote-fields-1"
    assert response["oddsFields"]["win"][0]["value"] == 2.4
    assert response["oddsFields"]["timestamp"]["value"] == "12:34:00"
    assert response["quoteFields"]["fields"]["win_odds"]["rows"][0]["value"] == 2.4
    assert response["quoteFields"]["fields"]["quote_time"]["missing"] == 2
    assert response["quoteFields"]["quoteFreshness"] == "unknown"

    assert response["results"] is None
    assert response["resultFields"] is None
    assert response["prediction"] is None
    assert response["marks"] is None
    assert response["tickets"] is None
    assert "predictionScore" not in str(response) and "'mark':" not in str(response)

    view = factual_screen(response)
    assert view["oddsFields"] == response["oddsFields"]
    assert view["quoteFields"] == response["quoteFields"]
    view["oddsFields"]["win"][0]["value"] = 500
    view["quoteFields"]["fields"]["win_odds"]["rows"][0]["value"] = 600
    assert response["oddsFields"]["win"][0]["value"] == 2.4
    assert response["quoteFields"]["fields"]["win_odds"]["rows"][0]["value"] == 2.4
    assert source == frozen
