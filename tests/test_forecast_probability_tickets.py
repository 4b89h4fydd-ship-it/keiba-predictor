"""Fail-closed tests for independently generated probability tickets."""
from arvexq.forecast.tickets import generate_tickets


def source():
    return {
        "approvedForProduction": True,
        "orderedTop3": [
            {"horseNumbers": [1, 2, 3], "probability": 0.4},
            {"horseNumbers": [1, 3, 2], "probability": 0.3},
            {"horseNumbers": [2, 1, 3], "probability": 0.2},
            {"horseNumbers": [3, 1, 2], "probability": 0.1},
        ],
    }


def marks():
    return [
        {"horseNumber": 1, "mark": "◎"},
        {"horseNumber": 2, "mark": "○"},
        {"horseNumber": 3, "mark": "▲"},
    ]


def test_builds_three_probabilistic_ticket_types():
    assert generate_tickets(source(), marks()) == [
        {"type": "3連単", "horseNumbers": [1, 2, 3], "probability": 0.4},
        {"type": "3連複", "horseNumbers": [1, 2, 3], "probability": 1.0},
        {"type": "馬連", "horseNumbers": [1, 2], "probability": 0.6},
    ]


def test_unapproved_missing_or_sparse_distribution_returns_empty():
    data = source()
    data["approvedForProduction"] = False
    assert generate_tickets(data, marks()) == []
    data = source()
    data["orderedTop3"].pop()
    assert generate_tickets(data, marks()) == []
    assert generate_tickets(None, marks()) == []
    assert generate_tickets(source(), []) == []


def test_duplicate_or_invalid_probability_returns_empty():
    data = source()
    data["orderedTop3"].append(data["orderedTop3"][0].copy())
    assert generate_tickets(data, marks()) == []
    data = source()
    data["orderedTop3"][0]["probability"] = float("nan")
    assert generate_tickets(data, marks()) == []
    data = source()
    data["orderedTop3"][0]["horseNumbers"] = [1, 1, 3]
    assert generate_tickets(data, marks()) == []
