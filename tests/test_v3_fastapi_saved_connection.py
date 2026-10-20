"""Existing FastAPI race route, saved-only v3 facts, no result or model leakage."""
from copy import deepcopy
import importlib
import pytest

from arvexq.v3.transport.fastapi_readonly import saved_fact_screen


def saved(circuit="jra"):
    venue="京都" if circuit=="jra" else "高知"
    return {
        "id":f"{circuit}-2026-10-18-{venue}-01",
        "date":"2026-10-18","track":venue,"fieldSize":2,
        "circuit":"JRA" if circuit=="jra" else "NAR",
        "horses":[
            {"horseNumber":2,"name":"テスト二","winOdds":3.2,
             "allPastRuns":[{"date":"2026-10-01","finish":2,"mark":"◎"}],
             "mark":"◎","preRaceBet":{"ticket":"leak"}},
            {"horseNumber":1,"name":"テスト一","placeOdds":"1.2-1.3",
             "recentRaces":[{"date":"2026-10-05","finish":1},
                            {"date":"2026-10-19","finish":1}]},
        ],
        "result":{"finishers":[{"horseNumber":2,"finish":1}],
                  "payouts":[{"kind":"単勝","payout":300}]},
        "preRacePrediction":{"winner":2},
    }


@pytest.mark.parametrize("circuit",["jra","nar"])
def test_saved_read_only_facts_and_empty_prediction(circuit):
    detail=saved(circuit)
    unchanged=deepcopy(detail)
    calls=[]
    view=saved_fact_screen(detail["id"],lambda rid: calls.append(rid) or detail)
    assert calls==[detail["id"]]
    assert view["schema"]=="arvexq-v3-factual-screen-1"
    assert [r["horseNumber"] for r in view["rows"]]==[1,2]
    assert [r["date"] for r in view["rows"][1]["recentRaces"]]==["2026-10-01"]
    assert view["results"] is None and view["resultFields"] is None
    assert view["marks"] is None and view["tickets"] is None
    assert view["predictionStatus"]=="not-implemented"
    assert "preRaceBet" not in str(view) and "preRacePrediction" not in str(view)
    assert view["oddsFields"]["schema"]=="arvexq-v3-observed-odds-fields-1"
    assert view["quoteFields"]["schema"]=="arvexq-v3-observed-quote-fields-1"
    assert detail==unchanged


def test_missing_and_unknown_race_never_fetch_second_source():
    calls=[]
    assert saved_fact_screen("jra-2026-10-18-京都-01",
        lambda rid:calls.append(rid) or None) is None
    assert calls==["jra-2026-10-18-京都-01"]
    with pytest.raises(ValueError):
        saved_fact_screen("unknown-race-id",lambda _:pytest.fail("no getter call"))


def test_circuit_conflict_fails_closed():
    data=saved("jra")
    data["circuit"]="NAR"
    with pytest.raises(ValueError,match="circuit"):
        saved_fact_screen(data["id"],lambda _:data)


@pytest.mark.parametrize("circuit",["jra","nar"])
def test_existing_route_optin_does_not_refresh_or_mutate(monkeypatch,circuit):
    app=importlib.import_module("app")
    source=saved(circuit)
    unchanged=deepcopy(source)
    calls=[]
    monkeypatch.setattr(app,"_prepared_get_fresh",lambda rid:calls.append(rid) or source)
    monkeypatch.setattr(app,"_racedb_get_fast",lambda rid:pytest.fail("unexpected fallback"))
    monkeypatch.setattr(app,"_schedule_fast_card_refresh",lambda *a,**k:pytest.fail("no refresh"))
    monkeypatch.setattr(app,"_fast_local_race_detail",lambda *a,**k:pytest.fail("no fetch"))
    monkeypatch.setattr(app,"_store_fast_snapshot",lambda *a,**k:pytest.fail("no write"))
    result=app.race_detail(source["id"],refresh=1,history=1,prepared=1,view="v3-facts")
    assert result["schema"]=="arvexq-v3-factual-screen-1"
    assert result["results"] is None and result["marks"] is None
    assert calls==[source["id"]]
    assert source==unchanged


def test_existing_route_v3_missing_is_404_not_async_rebuild(monkeypatch):
    app=importlib.import_module("app")
    monkeypatch.setattr(app,"_prepared_get_fresh",lambda _:None)
    monkeypatch.setattr(app,"_racedb_get_fast",lambda _:None)
    monkeypatch.setattr(app,"_schedule_fast_card_refresh",lambda *a,**k:pytest.fail("no scheduling"))
    response=app.race_detail("jra-2026-10-18-京都-01",view="v3-facts")
    assert response.status_code==404


@pytest.mark.parametrize("circuit", ["jra", "nar"])
def test_saved_screen_readiness_conservative_and_aligned(circuit):
    source = saved(circuit)
    result = saved_fact_screen(source["id"], lambda _: source)
    state = result["displayReadiness"]
    assert state["schema"] == "arvexq-v3-display-readiness-1"
    assert state["complete"] is False
    assert state["canClaimFullyRetrieved"] is False
    assert state["predictionsEnabled"] is False
    assert state["roster"] == "unverified"
    assert state["history"] == "partial-unverified"
    assert state["odds"] == "incomplete"
    assert result["marks"] is None and result["tickets"] is None


@pytest.mark.parametrize("circuit", ["jra", "nar"])
def test_saved_screen_roster_mismatch_and_absent_history(circuit):
    source = saved(circuit)
    source["fieldSize"] = 3
    for horse in source["horses"]:
        horse["allPastRuns"] = []
        horse["recentRaces"] = []
    state = saved_fact_screen(source["id"], lambda _: source)["displayReadiness"]
    assert state["roster"] == "count-mismatch"
    assert state["history"] == "missing"
    assert state["complete"] is False
