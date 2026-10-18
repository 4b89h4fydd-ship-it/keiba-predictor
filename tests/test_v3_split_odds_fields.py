"""Independent, circuit-checked market facts do not become probabilities."""
from copy import deepcopy
from importlib import import_module

import pytest

from arvexq.v3.data.quote_split import FIELDS, read_quotes
from arvexq.v3.transport.api import factual_response
from arvexq.v3.transport.display import factual_screen


def sample(circuit):
    track = "東京" if circuit == "jra" else "川崎"
    return {
        "id": f"{circuit}-2026-10-18-{track}-04", "date": "2026-10-18",
        "circuit": "中央" if circuit == "jra" else "地方", "track": track,
        "horses": [
            {"horseNumber": 1, "name": "候補A", "winOdds": 2.5, "placeOdds": "1.1-1.3",
             "popularity": 1, "oddsUpdatedAt": "2026-10-18T10:20:00",
             "predictedWinRate": 0.8, "mark": "◎"},
            {"horseNumber": 2, "name": "候補B", "winOdds": None,
             "placeOdds": None, "popularity": 0},
            {"horseNumber": 3, "name": "候補C", "winOdds": "nan",
             "placeOdds": "不明", "popularity": None},
        ],
        "preRaceBet": {"tickets": [1]},
    }


@pytest.mark.parametrize("circuit", ["jra", "nar"])
def test_eight_independent_quote_fields_and_missing_timestamps(circuit):
    source = sample(circuit)
    before = deepcopy(source)
    assert len(FIELDS) == 4
    for field in FIELDS:
        m = import_module(f"arvexq.v3.data.{circuit}.quote_fields.{field}")
        assert len(m.read(source)) == 3
    out = read_quotes(source, circuit)
    assert out["fields"]["win_odds"]["observed"] == 1
    assert out["fields"]["win_odds"]["missing"] == 1
    assert out["fields"]["win_odds"]["invalid"] == 1
    assert out["fields"]["place_odds"]["rows"][0]["status"] == "observed-raw-range"
    assert out["fields"]["popularity"]["invalid"] == 1
    assert out["fields"]["quote_time"]["observed"] == 1
    assert out["fields"]["quote_time"]["missing"] == 2
    assert out["quoteFreshness"] == "unknown"
    assert "predictedWinRate" not in str(out) and "'mark'" not in str(out)
    assert "tickets" not in str(out)
    assert source == before
    api = factual_response(source)
    view = factual_screen(api)
    assert view["oddsFields"]["fields"]["quote_time"]["missing"] == 2
    view["oddsFields"]["fields"]["win_odds"]["rows"][0]["value"] = 999
    assert source == before


@pytest.mark.parametrize("circuit,other", [("jra", "nar"), ("nar", "jra")])
def test_cross_circuit_read_refused(circuit, other):
    for field in FIELDS:
        with pytest.raises(ValueError, match="circuit"):
            import_module(f"arvexq.v3.data.{other}.quote_fields.{field}").read(sample(circuit))
    with pytest.raises(ValueError, match="circuit"):
        read_quotes(sample(circuit), other)


def test_absent_observed_quotes_are_not_projections():
    s = sample("jra")
    for row in s["horses"]:
        for k in ("winOdds", "placeOdds", "popularity", "oddsUpdatedAt"):
            row.pop(k, None)
    out = read_quotes(s, "jra")
    for field in FIELDS:
        assert out["fields"][field]["observed"] == 0
        assert out["fields"][field]["missing"] == 3
    assert out["quoteFreshness"] == "unknown"
