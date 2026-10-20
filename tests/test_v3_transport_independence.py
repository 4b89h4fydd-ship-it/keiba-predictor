"""Phase 3: read-only storage/cache/API/screen contracts."""
from __future__ import annotations

from copy import deepcopy
import pytest

from arvexq.v3.transport.cache import factual_cache_key, freshness
from arvexq.v3.transport.storage import read_saved
from arvexq.v3.transport.api import factual_response
from arvexq.v3.transport.display import factual_screen
from arvexq.v3.transport.boundary import read_boundary
from arvexq.v3.prediction.status import UNITS


def saved(circuit="JRA"):
    source = circuit.lower()
    race = {
        "id": f"{source}-2026-10-19-東京-04", "date": "2026-10-19",
        "track": "東京", "circuit": circuit, "startTime": "11:00",
        "horses": [
            {"horseNumber": 2, "name": "別馬", "winOdds": 4.2,
             "recentRaces": [{"date": "2026-10-01", "finish": 3,
                               "preRaceBet": {"bet": "leak"}},
                             {"date": "2026-10-20", "finish": 1}],
             "mark": "◎", "preRaceBet": {"bets": ["leak"]}},
            {"horseNumber": 1, "name": "本馬", "placeOdds": "2.0",
             "allPastRuns": [{"date": "2026-09-01", "finish": 2}],
             "predictionScore": 99},
        ],
        "result": {"finishers": [{"horseNumber": 1, "finish": 1, "mark": "◎"}],
                   "payouts": [{"kind": "単勝", "payout": 500, "bet": "leak"}]},
        "preRacePrediction": {"bets": "leak"}, "preRaceBet": "leak",
    }
    return race


@pytest.mark.parametrize("circuit", ["JRA", "NAR"])
def test_api_and_screen_are_read_only_and_keep_prediction_empty(circuit):
    original = saved(circuit)
    unchanged = deepcopy(original)
    getter_calls = []
    def getter(rid):
        getter_calls.append(rid)
        return original, 1690000000
    detail = read_saved(getter, original["id"], circuit=circuit)
    prereq = factual_response(detail)
    assert prereq["results"] is None
    assert prereq["coverage"]["domains"]["results"] == "withheld-until-postrace"
    assert prereq["coverage"]["counts"]["resultFinishers"] is None
    assert prereq["prediction"] is None and prereq["marks"] is None and prereq["tickets"] is None
    assert "preRaceBet" not in str(prereq) and "'mark':" not in str(prereq)
    view = factual_screen(prereq)
    assert [r["horseNumber"] for r in view["rows"]] == [1, 2]
    assert [r["date"] for r in view["rows"][1]["recentRaces"]] == ["2026-10-01"]
    assert view["results"] is None
    assert view["rows"][0]["careerCompleteness"] == "unverified"
    view["rows"][0]["horse"]["name"] = "変更"
    assert original == unchanged
    assert getter_calls == [original["id"]]
    post = factual_screen(factual_response(detail, include_results=True))
    assert post["results"]["resultState"] == "observed-unverified"
    assert post["results"]["finishers"] == [{"horseNumber": 1, "finish": 1}]
    assert post["results"]["payouts"] == [{"kind": "単勝", "payout": 500}]


def test_cache_policy_requires_explicit_ttl_and_times():
    key = factual_cache_key("jra-2026-10-19-東京-04", "JRA")
    assert key.startswith("race-detail:v3-factual-observed:")
    assert key != factual_cache_key("nar-2026-10-19-東京-04", "NAR")
    assert freshness(None, now_epoch=120, ttl_seconds=60) == "unknown"
    assert freshness(100, now_epoch=159, ttl_seconds=60) == "fresh"
    assert freshness(100, now_epoch=160, ttl_seconds=60) == "stale"
    assert freshness(200, now_epoch=199, ttl_seconds=60) == "clock-conflict"
    with pytest.raises(ValueError):
        freshness(100, now_epoch=150, ttl_seconds=-1)
    with pytest.raises(ValueError):
        factual_cache_key("nar-2026-10-19-東京-04", "JRA")


def test_wrong_identity_fails_without_second_store_fetch():
    item = saved("JRA")
    calls = []
    def getter(rid):
        calls.append(rid)
        return item
    with pytest.raises(ValueError):
        read_saved(getter, item["id"], circuit="NAR")
    assert calls == []
    wrong = saved("NAR")
    with pytest.raises(ValueError):
        read_saved(lambda rid: wrong, item["id"], circuit="JRA")
    with pytest.raises(ValueError):
        factual_response({**item, "id": "nar-2026-10-19-東京-04"})


def test_screen_rejects_mismatched_horse_identity_not_name_join():
    source = saved()
    out = factual_response(source)
    out["history"][0]["horseNumber"] = 3
    with pytest.raises(ValueError, match="identity"):
        factual_screen(out)
    out = factual_response(source)
    out["entries"][1]["horseNumber"] = 2
    with pytest.raises(ValueError, match="identity"):
        factual_screen(out)


def test_boundary_refuses_unknown_circuit():
    assert read_boundary(saved("JRA"))["identityStatus"] == "routed"
    status = read_boundary({"id": "nar-2026-10-19-東京-04", "circuit": "JRA"})
    assert status["identityStatus"] == "unavailable"
    assert read_boundary({"id": "x", "circuit": None})["cacheKey"] is None


def test_prediction_modules_remain_exactly_twelve_empty():
    from importlib import import_module
    for circuit in ("jra", "nar"):
        for module in UNITS:
            assert import_module(f"arvexq.v3.prediction.{circuit}.{module}").run(
                evidence=saved(circuit.upper())) is None
