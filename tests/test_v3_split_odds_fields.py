"""Independent observed-only JRA/NAR odds, metadata and missingness."""
from copy import deepcopy
from importlib import import_module

import pytest

from arvexq.v3.data.odds_facts import FIELDS
from arvexq.v3.data.odds_split import read_odds_breakdown
from arvexq.v3.transport.api import factual_response
from arvexq.v3.transport.display import factual_screen


def saved(circuit: str):
    city = "東京" if circuit == "jra" else "高知"
    return {
        "id": f"{circuit}-2026-10-18-{city}-08", "date": "2026-10-18",
        "circuit": "JRA" if circuit == "jra" else "NAR", "track": city,
        "oddsUpdatedAt": "13:09:00", "oddsSource": "現地取得記録",
        "oddsType": "単勝観測値",
        "horses": [
            {"horseNumber": 1, "name": "候補一", "winOdds": 2.3,
             "placeOdds": "1.2-1.4", "popularity": 1,
             "observedWinOddsDelta": -0.4,
             "mark": "◎", "preRaceBet": {"bet": "not-factual"}},
            {"horseNumber": 2, "name": "候補二", "winOdds": 0,
             "placeOdds": None, "popularity": "??",
             "observedWinOddsDelta": None},
            {"horseNumber": 3, "name": "候補三", "winOdds": None,
             "placeOdds": "1.8", "popularity": 3,
             "observedWinOddsDelta": 0},
        ],
        "preRacePrediction": {"favorite": 1},
        "preRaceBet": {"tickets": [1, 2]},
    }


@pytest.mark.parametrize("circuit", ["jra", "nar"])
def test_independent_odds_readers_keep_observed_values_only(circuit):
    source = saved(circuit)
    original = deepcopy(source)
    for name in FIELDS:
        module = import_module(f"arvexq.v3.data.{circuit}.odds_fields.{name}")
        assert module.read(source) is not None
    view = read_odds_breakdown(source, circuit)
    assert len(FIELDS) == 7
    assert view["counts"]["win"] == {"observed": 1, "missing": 1, "invalid": 1}
    assert view["counts"]["place"] == {"observed": 2, "missing": 1, "invalid": 0}
    assert view["counts"]["popularity"] == {"observed": 2, "missing": 0, "invalid": 1}
    assert view["win"][0]["value"] == 2.3
    assert view["win"][1]["value"] is None
    assert view["place"][0]["value"] == "1.2-1.4"
    assert view["delta"][2]["value"] == 0
    assert view["timestamp"]["value"] == "13:09:00"
    assert view["timestamp"]["precision"] == "local-time-of-day-only"
    assert view["timestamp"]["preOffTimeVerified"] is False
    assert view["marketDateAndPreOffVerified"] is False
    assert view["source"]["independentlyConfirmed"] is False
    assert view["predictionsCalculated"] is False
    assert "preRaceBet" not in str(view) and "mark" not in str(view)
    assert source == original


@pytest.mark.parametrize("circuit", ["jra", "nar"])
def test_odds_screen_api_are_read_only_and_do_not_enable_predictions(circuit):
    original = saved(circuit)
    pre = factual_response(original)
    screen = factual_screen(pre)
    assert screen["oddsFields"]["win"][0]["value"] == 2.3
    assert screen["predictionStatus"] == "not-implemented"
    assert screen["marks"] is None and screen["tickets"] is None
    assert pre["results"] is None
    assert pre["oddsFields"]["timestamp"]["preOffTimeVerified"] is False
    screen["oddsFields"]["win"][0]["value"] = 999
    assert original["horses"][0]["winOdds"] == 2.3


@pytest.mark.parametrize("circuit,other", [("jra", "nar"), ("nar", "jra")])
def test_cross_circuit_odds_are_rejected(circuit, other):
    with pytest.raises(ValueError, match="circuit"):
        read_odds_breakdown(saved(circuit), other)
    for name in FIELDS:
        with pytest.raises(ValueError, match="circuit"):
            import_module(f"arvexq.v3.data.{other}.odds_fields.{name}").read(saved(circuit))


def test_no_market_timestamp_fabricated_from_start_time():
    detail = saved("jra")
    del detail["oddsUpdatedAt"]
    detail["startTime"] = "14:00"
    detail["oddsSource"] = ""
    detail["oddsType"] = ""
    view = read_odds_breakdown(detail, "jra")
    assert view["timestamp"]["state"] == "missing"
    assert view["timestamp"]["value"] is None
    assert view["source"]["state"] == "missing"


def test_invalid_quotes_differ_from_missing_and_no_odds_are_guessed():
    detail = saved("nar")
    detail["horses"][0]["winOdds"] = "nan"
    detail["horses"][1]["winOdds"] = None
    detail["horses"][2]["placeOdds"] = "-1-2"
    view = read_odds_breakdown(detail, "nar")
    assert view["counts"]["win"] == {"observed": 0, "missing": 2, "invalid": 1}
    assert view["place"][2]["state"] == "invalid"
    assert view["win"][0]["value"] is None
