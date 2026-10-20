"""v3 observed-only integration boundary and empty-prediction regression tests."""
from __future__ import annotations

from copy import deepcopy
import importlib

import pytest

from arvexq.v3.data.quality import build_data_status
from arvexq.v3.data.storage import read_existing_snapshot
from arvexq.v3.data.display import factual_display
from arvexq.v3.prediction.status import UNITS, components_status


def sample(circuit="JRA"):
    prefix = "jra" if circuit == "JRA" else "nar"
    return {
        "id": f"{prefix}-2026-10-19-東京-01", "date": "2026-10-19",
        "circuit": circuit, "track": "東京", "fieldSize": 2,
        "startTime": "10:15", "surface": "芝", "distance": 1600,
        "horses": [
            {"horseNumber": 2, "name": "テストB", "jockey": "騎手B",
             "trainer": "厩舎B", "carriedWeight": 55,
             "recentRaces": [{"date": "2026-09-01", "finish": 1}],
             "mark": "◎", "winningProbability": .9, "preRaceBet": {"bets": [1]}},
            {"horseNumber": 1, "name": "テストA", "jockey": "騎手A",
             "trainer": "厩舎A", "carriedWeight": 56,
             "allPastRuns": [{"date": "2026-08-01", "finish": 3}],
             "recentRaces": [{"date": "2026-08-01", "finish": 3}]}
        ],
        "result": {"finishers": [{"horseNumber": 1, "finish": 1}]},
        "preRacePrediction": {"winner": 2},
        "preRaceBet": {"tickets": [[2, 1, 3]]},
    }


@pytest.mark.parametrize("circuit", ["jra", "nar"])
def test_twelve_independently_importable_empty_units(circuit):
    for unit in UNITS:
        module = importlib.import_module(f"arvexq.v3.prediction.{circuit}.{unit}")
        assert module.run(evidence={"horseNumber": 1}, context={"raceId": "X"}) is None
    contract = components_status(circuit)
    assert contract["status"] == "not-implemented"
    assert contract["marks"] is None and contract["tickets"] is None
    assert all(s == "not-implemented" for s in contract["components"].values())


def test_no_guessing_of_circuit_and_no_cross_source_identity():
    race = sample()
    race["id"] = "nar-2026-10-19-東京-01"
    assert "race-circuit-conflict" in build_data_status(race)["warnings"]
    assert build_data_status({"id": "X", "circuit": "invalid"})["circuit"] is None
    with pytest.raises(ValueError):
        components_status("unknown")


def test_canonical_saved_reader_never_mutates_or_falls_back_to_second_provider():
    original = sample()
    calls = []
    def existing_store_getter(race_id):
        calls.append(race_id)
        return original, 123
    copied = read_existing_snapshot(existing_store_getter, original["id"])
    copied["horses"][0]["name"] = "変更"
    assert original["horses"][0]["name"] == "テストB"
    assert calls == [original["id"]]
    assert read_existing_snapshot(lambda _: None, original["id"]) is None
    with pytest.raises(ValueError, match="identity"):
        read_existing_snapshot(lambda _: {"id": "other"}, original["id"])


def test_factual_display_never_leaks_model_marks_or_bets():
    source = sample()
    original = deepcopy(source)
    view = factual_display(source)
    assert source == original
    assert [h["horseNumber"] for h in view["runners"]] == [1, 2]
    for horse in view["runners"]:
        assert "mark" not in horse and "preRaceBet" not in horse
        assert "winningProbability" not in horse
    assert "preRaceBet" not in view and "preRacePrediction" not in view
    assert view["result"] == source["result"]
    assert len(view["runners"][0]["pastRuns"]) == 1


def test_same_day_and_future_history_never_enter_past_runs():
    race = sample("NAR")
    race["horses"][0]["recentRaces"] += [
        {"date": "2026-10-19", "finish": 1},
        {"date": "2026-10-20", "finish": 1},
    ]
    view = factual_display(race)
    assert [r["date"] for r in view["runners"][1]["pastRuns"]] == ["2026-09-01"]
    assert view["quality"]["sameOrFutureHistoryRows"] == 2
    assert "non-prior-history-present" in view["quality"]["warnings"]


def test_missing_evidence_not_fabricated_and_duplicated_runners_flagged():
    race = sample()
    race["horses"][1]["horseNumber"] = 2
    race["horses"][0]["carriedWeight"] = None
    report = build_data_status(race)
    assert "duplicate-runner-number" in report["warnings"]
    assert report["missing"]["horse.carriedWeight"] == 1
    assert report["careerCompleteness"] == "unverified"
    assert report["status"] == "observed-partial"


def test_data_status_separates_observation_from_prediction():
    report = build_data_status(sample())
    assert report["horseCount"] == 2
    assert report["runnersWithPriorRuns"] == 2
    assert report["observedPriorRuns"] == 2
    assert "win" not in report and "model" not in report
    assert report["careerCompleteness"] == "unverified"
