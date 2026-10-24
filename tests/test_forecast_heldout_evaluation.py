from itertools import permutations
from arvexq.forecast.heldout_evaluation import evaluate_archived_races


def record(race_id, with_forecast=True):
    triples = list(permutations((1, 2, 3), 3))
    return {"raceId": race_id,
        "orderedTop3": [{"horseNumbers": list(t), "probability": 1 / 6} for t in triples] if with_forecast else None,
        "finishOrder": [1, 2, 3], "predictionCutoff": "2026-10-17T18:00:00+09:00",
        "offTime": "2026-10-18T12:00:00+09:00"}


def test_coverage_not_inflated_by_missing_pre_race_forecast():
    out = evaluate_archived_races([record("A"), record("B", False)])
    assert out["totalRaces"] == 2
    assert out["evaluatedRaces"] == 1
    assert out["coverage"] == .5
    assert out["exclusions"] == {"missing_pre_race_forecast": 1}
    assert out["metrics"]["raceCount"] == 1
    assert out["productionApproved"] is False


def test_no_empty_or_duplicate_sample_is_approved():
    assert evaluate_archived_races([])["metrics"] is None
    assert evaluate_archived_races([record("A"), record("A")]) is None
    assert evaluate_archived_races([{"raceId": ""}]) is None


def test_post_off_snapshot_excluded():
    r = record("A")
    r["predictionCutoff"] = "2026-10-18T13:00:00+09:00"
    out = evaluate_archived_races([r])
    assert out["evaluatedRaces"] == 0
    assert out["exclusions"] == {"invalid_snapshot_or_result": 1}
