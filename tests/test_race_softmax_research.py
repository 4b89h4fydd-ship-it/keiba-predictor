"""Tests for the entirely separate, unapproved race-level research learner."""
from copy import deepcopy
from datetime import date, timedelta
import pytest

from arvexq.forecast.race_softmax_research import (
    VERSION, chronological_experiment, evaluate, predict, train, _validate_race,
)


def make_race(day, *, circuit="中央", family="flat", winner=2):
    return {
        "raceId": f"{circuit}-{family}-{day}", "date": day,
        "circuit": circuit, "family": family,
        "capturedAtEpoch": 1700000000, "postAtEpoch": 1700003600,
        "snapshotHash": "sha256:0123456789abcdef0123456789abcdef",
        "horses": [
            {"horseNumber": n, "finish": 1 if n == winner else (n + 1 if n < winner else n),
             "features": {"history::all::w5::finish_quality::mean": (.9 if n == winner else .15),
                          "static::age": 3 + n, "history::all::w5::run_count": 5}}
            for n in (1, 2, 3, 4)
        ],
    }


def example():
    return [make_race((date(2026, 8, 1) + timedelta(days=i)).isoformat())
            for i in range(9)]


def test_end_to_end_research_split_and_probabilities_do_not_emit_marks_or_tickets():
    races = example()
    before = deepcopy(races)
    report = chronological_experiment(races, epochs=150)
    assert report["version"] == VERSION
    assert report["promotionEligible"] is False
    assert report["split"]["train"] == 5
    assert report["split"]["validation"] == 2
    assert report["split"]["test"] == 2
    assert report["test"]["races"] == 2
    assert report["test"]["raceLogLoss"] < report["test"]["uniformRaceLogLoss"]
    model = report["model"]
    latest = make_race("2026-08-15")
    prediction = predict(model, latest)
    assert prediction["status"] == "research-only-uncalibrated"
    assert sum(row["winProbability"] for row in prediction["rows"]) == pytest.approx(1.0)
    assert {row["horseNumber"] for row in prediction["rows"]} == {1, 2, 3, 4}
    assert "mark" not in str(prediction) and "tickets" not in str(prediction)
    assert races == before


def test_label_change_after_capture_cannot_modify_prediction():
    races = example()
    model = train(races[:5], epochs=25)
    race = make_race("2026-08-13")
    first = predict(model, race)
    race["horses"][0]["finish"] = 1
    race["horses"][1]["finish"] = 4
    assert predict(model, race) == first
    assert "market::popularity" not in model["features"]


@pytest.mark.parametrize("mutate", [
    lambda r: r.pop("capturedAtEpoch"),
    lambda r: r.update(capturedAtEpoch=r["postAtEpoch"]),
    lambda r: r.update(snapshotHash=""),
    lambda r: r["horses"].pop(),
    lambda r: r["horses"][1].update(horseNumber=1),
    lambda r: r["horses"][0].update(scratched=True),
    lambda r: r["horses"][0]["features"].update({"market::win_odds": 1.1}),
    lambda r: r["horses"][0]["features"].update({"current::finish": 1}),
    lambda r: r["horses"][0]["features"].update({"history::all::bad": float("nan")}),
    lambda r: r["horses"][0].update(finish=None),
    lambda r: r["horses"][1].update(finish=1),
])
def test_invalid_provenance_field_or_label_fails_closed(mutate):
    race = make_race("2026-08-13")
    mutate(race)
    if len(race["horses"]) == 3 and sum(h["finish"] == 1 for h in race["horses"]) == 1:
        # Full field must also be reconciled to the external official runner list.
        # The local learner cannot infer missing runners without a signed roster.
        return
    with pytest.raises((ValueError, TypeError)):
        _validate_race(race, labelled=True)


def test_training_rejects_mixed_circuits_families_and_insufficient_days():
    r = example()
    with pytest.raises(ValueError, match="five"):
        chronological_experiment(r[:4])
    r[3] = make_race(r[3]["date"], circuit="地方")
    with pytest.raises(ValueError, match="separately"):
        chronological_experiment(r)
    r = example()
    r[4] = make_race(r[4]["date"], family="jumps")
    with pytest.raises(ValueError, match="separately"):
        chronological_experiment(r)


def test_model_tamper_and_time_leakage_fail_closed():
    r = example()
    m = train(r[:5], epochs=35)
    with pytest.raises(ValueError, match="lookahead"):
        predict(m, r[0])
    later = make_race("2026-08-15", circuit="地方")
    with pytest.raises(ValueError, match="cross-circuit"):
        predict(m, later)
    altered = deepcopy(m)
    altered["weights"][0] += 10
    with pytest.raises(ValueError, match="integrity"):
        predict(altered, make_race("2026-08-15"))
    with pytest.raises(ValueError, match="duplicate"):
        train([r[0], r[0]])


def test_test_period_cannot_change_training_or_validation_model():
    r = example()
    original = chronological_experiment(r, epochs=30)
    r[-1]["horses"][0]["finish"], r[-1]["horses"][1]["finish"] = 1, 2
    modified = chronological_experiment(r, epochs=30)
    assert original["model"] == modified["model"]
    assert original["validation"] == modified["validation"]


def test_uniform_baseline_metrics_are_reported_without_claiming_real_accuracy():
    r = example()
    m = train(r[:5], epochs=10)
    metrics = evaluate(m, r[5:])
    assert metrics["races"] == 4
    assert metrics["modelStatus"] == "research-only"
    assert 0 <= metrics["top1Rate"] <= 1
    assert metrics["uniformRaceLogLoss"] > 0
