from itertools import permutations
from arvexq.forecast.validation_metrics import evaluate_race, summarize_results


def sample():
    trips = list(permutations([1, 2, 3], 3))
    return [{"horseNumbers": list(t), "probability": 1 / len(trips)} for t in trips]


def score(rows=None, cutoff="2026-10-17T15:00:00+09:00"):
    return evaluate_race(sample() if rows is None else rows, [1, 2, 3],
        prediction_cutoff=cutoff, off_time="2026-10-18T15:00:00+09:00")


def test_race_scores_valid_forecast_without_approving_release():
    result = score()
    assert result["winTop1Hit"] == 1
    assert result["orderedTop3Hit"] == 1
    assert result["top3SetHit"] == 1
    assert result["top3Recall"] == 1
    assert "approvedForProduction" not in result
    assert summarize_results([result])["raceCount"] == 1


def test_no_future_prediction_or_naive_datetime():
    assert score(cutoff="2026-10-18T16:00:00+09:00") is None
    assert score(cutoff="2026-10-17T15:00:00") is None


def test_incomplete_mass_duplicated_or_invalid_forecast():
    rows = sample()
    assert score(rows[:-1]) is None
    rows = sample()
    rows[0] = rows[1].copy()
    assert score(rows) is None
    rows = sample()
    rows[0]["probability"] = 0.9
    assert score(rows) is None
    assert summarize_results([]) is None
