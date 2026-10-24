"""Contract tests for empirical fusion. Synthetic fixtures are NOT real accuracy claims."""
from copy import deepcopy
from datetime import date, timedelta

import pytest

from arvexq.prediction.empirical_fusion import VERSION, fit_weights, blend

METHODS = ("mineta", "expert:position", "expert:course", "ai:learned", "ai:mass")


def opinion(top=1, *, return_yen=100, method="mineta", day="2026-10-24"):
    win = {i: (0.6 if i == top else 0.1) for i in range(1, 6)}
    return {"win": win, "top3": {i: 0.6 for i in range(1, 6)},
            "evidenceId": f"frozen-test:{method}:{day}", "modelVersion": method+"/v1",
            "raceId": f"nar-{day}-園田-01", "capturedAt": day+"T10:00:00+09:00",
            "stakeYen": 100, "returnYen": return_yen}


def samples(count=30, circuit="地方"):
    rows = []
    for i in range(count):
        day = (date(2026, 9, 1) + timedelta(days=i)).isoformat()
        rows.append({
            "raceId": f"nar-{day}-園田-01",
            "raceDate": day, "circuit": circuit,
            "capturedAt": day+"T10:00:00+09:00",
            "scheduledOffAt": day+"T12:00:00+09:00",
            "roster": [1, 2, 3, 4, 5], "finishers": [1, 2, 3],
            "arms": {name: opinion(return_yen=200 if name == "mineta" else 100,
                                   method=name, day=day)
                     for name in METHODS}
        })
    return rows


def race(circuit="地方"):
    return {"id": "nar-2026-10-24-園田-01", "date": "2026-10-24",
            "circuit": circuit, "startTime": "12:00",
            "horses": [{"horseNumber": i} for i in range(1, 6)]}


def test_empirical_weights_are_measured_from_exact_matched_past_cohort():
    fitted = fit_weights(samples(), target_date="2026-10-24")
    assert fitted["version"] == VERSION
    assert fitted["nRaces"] == 30
    assert fitted["weights"]["mineta"] == pytest.approx(2/6)
    for method in METHODS[1:]:
        assert fitted["weights"][method] == pytest.approx(1/6)
    assert fitted["metrics"]["mineta"]["roi"] == 2
    assert sum(fitted["weights"].values()) == pytest.approx(1)


def test_future_labels_unsealed_prediction_and_missing_experts_are_rejected():
    rows = samples()
    rows[0]["capturedAt"] = rows[0]["scheduledOffAt"]
    with pytest.raises(ValueError, match="post-off"):
        fit_weights(rows, target_date="2026-10-24")
    rows = samples()
    rows[0]["raceDate"] = "2026-10-24"
    with pytest.raises(ValueError, match="predate"):
        fit_weights(rows, target_date="2026-10-24")
    rows = samples()
    rows[0]["arms"].pop("expert:position")
    with pytest.raises(ValueError, match="at least two"):
        fit_weights(rows, target_date="2026-10-24")
    with pytest.raises(ValueError, match="insufficient"):
        fit_weights(samples(1), target_date="2026-10-24")


def test_no_subjective_override_and_mixed_circuit_transfer():
    fitted = fit_weights(samples(), target_date="2026-10-24")
    opinions = {name: opinion(top=2 if name == "mineta" else 1, method=name) for name in METHODS}
    target = race()
    initial = blend(target, opinions, fitted)
    assert initial["humanOverrideAllowed"] is False
    assert initial["predictionMarks"][0]["mark"] == "◎"
    assert initial["predictionMarks"][0]["horseNumber"] == 1
    changed = deepcopy(opinions)
    for key in METHODS[1:]:
        changed[key] = opinion(top=2, method=key)
    adjusted = blend(target, changed, fitted)
    assert adjusted["predictionMarks"][0]["horseNumber"] == 2
    assert adjusted["recommendedBets"] == []
    assert adjusted["betStatus"] == "joint-distribution-or-verified-odds-unavailable"
    with pytest.raises(ValueError, match="separate JRA and NAR"):
        blend(race("中央"), opinions, fitted)


def test_bets_must_have_independent_joint_distributions_and_verified_odds():
    fitted = fit_weights(samples(), target_date="2026-10-24")
    opinions = {name: opinion(method=name) for name in METHODS}
    for opinion_row in opinions.values():
        opinion_row["trifecta"] = [
            {"combo": [1, 2, 3], "probability": 0.6},
            {"combo": [1, 3, 2], "probability": 0.3},
            {"combo": [2, 1, 3], "probability": 0.1},
        ]
    without_quotes = blend(race(), opinions, fitted)
    assert without_quotes["recommendedBets"] == []
    with_quotes = blend(race(), opinions, fitted,
                        quoted_odds={"capturedAt": "2026-10-24T10:00:00+09:00",
                                     "prices": {("馬連", (1, 2)): 2.0,
                                                ("3連複", (1, 2, 3)): 3.0,
                                                ("3連単", (1, 2, 3)): 4.0}})
    assert 1 <= len(with_quotes["recommendedBets"]) <= 5
    assert all(t["expectedReturn"] >= 1 for t in with_quotes["recommendedBets"])
    assert with_quotes["recommendedBets"][0]["kind"] == "3連複"
    broken = deepcopy(opinions)
    broken["ai:mass"]["trifecta"] = []
    assert not blend(race(), broken, fitted,
                     quoted_odds={"capturedAt": "2026-10-24T10:00:00+09:00",
                                  "prices": {("馬連", (1, 2)): 10}})["recommendedBets"]


def test_invalid_probability_or_missing_record_cannot_be_published():
    fitted = fit_weights(samples(), target_date="2026-10-24")
    opinions = {name: opinion(method=name) for name in METHODS}
    opinions["ai:mass"]["win"][1] = 0.61
    with pytest.raises(ValueError, match="mass"):
        blend(race(), opinions, fitted)
    opinions = {name: opinion(method=name) for name in METHODS}
    opinions["expert:position"].pop("evidenceId")
    with pytest.raises(ValueError, match="identity/evidence"):
        blend(race(), opinions, fitted)


def test_duplicate_ai_and_postoff_quotes_cannot_masquerade_as_independent():
    fitted = fit_weights(samples(), target_date="2026-10-24")
    opinions = {name: opinion(method=name) for name in METHODS}
    opinions["ai:mass"]["modelVersion"] = opinions["ai:learned"]["modelVersion"]
    with pytest.raises(ValueError, match="duplicate model"):
        blend(race(), opinions, fitted)
    opinions = {name: opinion(method=name) for name in METHODS}
    opinions["mineta"]["capturedAt"] = "2026-10-24T12:01:00+09:00"
    with pytest.raises(ValueError, match="post-off method"):
        blend(race(), opinions, fitted)
    opinions = {name: opinion(method=name) for name in METHODS}
    with pytest.raises(ValueError, match="post-off odds"):
        blend(race(), opinions, fitted,
              quoted_odds={"capturedAt": "2026-10-24T12:01:00+09:00",
                           "prices": {("馬連", (1, 2)): 10}})
