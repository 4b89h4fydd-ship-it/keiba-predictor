"""Synthetic CI-only fixtures: API stays disabled until real approved artifacts exist."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

import pytest

from arvexq.forecast.frozen_research_input import _hash_snapshot
from arvexq.forecast.approved_model_runtime import forecast_from_approved_joint

DAY = "2099-01-10"
JST = timezone(timedelta(hours=9))


def sample(circuit="地方", track="園田"):
    race_id = ("nar-" if circuit == "地方" else "jra-")+DAY+"-"+track+"-03"
    snapshot = {
        "raceId": race_id, "date": DAY, "circuit": circuit,
        "surface": "ダート", "track": track, "horseCount": 5,
        "rows": [
            {"horseNumber": i, "name": f"Runner-{i}",
             "features": {"history::all::w5::finish_quality::mean": i / 7}}
            for i in range(1, 6)
        ],
    }
    snapshot["featureHash"] = _hash_snapshot(snapshot)
    captured = int(datetime(2099, 1, 10, 9, tzinfo=JST).timestamp())
    post = int(datetime(2099, 1, 10, 15, tzinfo=JST).timestamp())
    receipt = {"raceId": race_id, "featureHash": snapshot["featureHash"],
               "source": "preoff-acquisition-log", "attestedPreOff": True,
               "activeHorseNumbers": [1, 2, 3, 4, 5],
               "capturedAtEpoch": captured, "postAtEpoch": post}
    orders = [
        {"horses": [1, 2, 3], "probability": .45},
        {"horses": [2, 3, 1], "probability": .25},
        {"horses": [3, 1, 4], "probability": .15},
        {"horses": [4, 5, 2], "probability": .10},
        {"horses": [5, 4, 3], "probability": .05},
    ]
    pace = {
        "stages": [
            {"key": key, "pack": [{"no": n, "lane": 0} for n in order]}
            for key, order in [
                ("start", [2, 1, 3, 4, 5]),
                ("turn3", [2, 1, 3, 5, 4]),
                ("turn4", [1, 2, 3, 5, 4]),
                ("straight", [1, 2, 3, 4, 5]),
            ]
        ]
    }
    manifest = {"publishApproved": True,
                "modelId": "CI-ONLY-artificial-mass-v1",
                "family": "nar-flat" if circuit == "地方" else "jra-flat",
                "holdoutArtifactSha256": "a" * 64,
                "calibrationArtifactSha256": "b" * 64}
    quotes = [{"kind": "trifecta", "horses": [1, 2, 3], "odds": 5.0,
               "quotedAtEpoch": captured + 30}]
    return snapshot, receipt, orders, pace, manifest, quotes


def run(parts):
    a, b, c, d, e, f = parts
    return forecast_from_approved_joint(a, b, c, d, e, preoff_trifecta_quotes=f)


@pytest.mark.parametrize("circuit,track", [("地方", "園田"), ("中央", "東京")])
def test_verified_fixture_produces_all_six_lanes(circuit, track):
    parts = sample(circuit, track)
    before = deepcopy(parts)
    output = run(parts)
    assert output["modelFamily"] == ("nar-flat" if circuit == "地方" else "jra-flat")
    assert output["horseNumbers"] == [1, 2, 3, 4, 5]
    assert len(output["probabilities"]) == 5
    assert abs(sum(p["win"] for p in output["probabilities"]) - 1) < 1e-6
    assert abs(sum(p["top2"] for p in output["probabilities"]) - 2) < 1e-6
    assert abs(sum(p["top3"] for p in output["probabilities"]) - 3) < 1e-6
    assert output["probabilities"][0]["mark"] == "◎"
    assert len(output["pace"]["stages"]) == 4
    assert output["tickets"][0]["kind"] == "3連単"
    assert output["tickets"][0]["combos"] == [[1, 2, 3]]
    assert output["tickets"][0]["expectedReturn"] > 1
    assert parts == before, "production adapter must never modify frozen evidence"


def test_preoff_quotes_missing_yield_skip_not_fake_bets():
    parts = list(sample())
    parts[-1] = []
    record = run(parts)
    assert record["tickets"] == []
    assert record["ticketStatus"] == "skip-no-positive-preoff-ev"


def test_jra_nar_manifest_is_not_interchangeable():
    parts = list(sample("中央", "東京"))
    parts[4]["family"] = "nar-flat"
    with pytest.raises(ValueError, match="JRA/NAR"):
        run(parts)


def test_training_unapproved_fails_not_fallback():
    parts = list(sample())
    parts[4]["publishApproved"] = False
    with pytest.raises(ValueError, match="not approved"):
        run(parts)


def test_result_or_tampered_snapshot_cannot_enter():
    parts = list(sample())
    parts[0]["rows"][0]["features"]["history::all::w5::finish_quality::mean"] = 999
    with pytest.raises(ValueError, match="hash mismatch"):
        run(parts)


@pytest.mark.parametrize("fault", ["duplicate_order", "bad_total", "bad_field", "nan"])
def test_bad_joint_mass_is_rejected(fault):
    parts = list(sample())
    if fault == "duplicate_order":
        parts[2].append(deepcopy(parts[2][0]))
    elif fault == "bad_total":
        parts[2][0]["probability"] = 0.1
    elif fault == "bad_field":
        parts[2][0]["horses"][0] = 90
    else:
        parts[2][0]["probability"] = float("nan")
    with pytest.raises(ValueError):
        run(parts)


def test_truncated_pace_field_never_publishes():
    parts = list(sample())
    parts[3]["stages"][2]["pack"].pop()
    with pytest.raises(ValueError, match="all official runners"):
        run(parts)


def test_odds_must_exist_before_post_and_after_capture():
    parts = list(sample())
    parts[5][0]["quotedAtEpoch"] = parts[1]["postAtEpoch"]
    with pytest.raises(ValueError, match="pre-off odds"):
        run(parts)


def test_no_postoff_retro_forecast_and_no_horse_swap():
    parts = list(sample())
    parts[1]["capturedAtEpoch"] = parts[1]["postAtEpoch"]
    with pytest.raises(ValueError):
        run(parts)
    parts = list(sample())
    parts[1]["activeHorseNumbers"] = [1, 2, 3, 4, 6]
    with pytest.raises(ValueError):
        run(parts)
