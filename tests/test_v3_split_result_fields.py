"""JRA/NAR results: independent factual extraction, privacy, no fabricated bets."""
from copy import deepcopy
from importlib import import_module

import pytest

from arvexq.v3.data.result_split import MODULES, read_breakdown
from arvexq.v3.transport.api import factual_response
from arvexq.v3.transport.display import factual_screen


def race(circuit):
    venue = "京都" if circuit == "jra" else "高知"
    return {
        "id": f"{circuit}-2026-10-18-{venue}-01", "date": "2026-10-18",
        "circuit": "中央" if circuit == "jra" else "地方",
        "track": venue, "horses": [
            {"horseNumber": 1, "name": "実測馬", "mark": "◎",
             "preRaceBet": {"tickets": [1]}}],
        "result": {
            "finishers": [
                {"horseNumber": 1, "finish": 1, "time": "1:23.4",
                 "margin": 0, "cornerPositions": [1, 1], "mark": "◎",
                 "predictionScore": 0.99},
                {"horseNumber": 2, "finish": 2, "margin": None, "mark": "○"}],
            "payouts": [
                {"kind": "単勝", "combination": "1", "payout": 500, "bets": [1]},
                {"kind": "3連単", "combination": "1-2-3", "payout": 13000},
                {"kind": "不明券種", "payout": 123},
            ],
            "mark": "◎", "predictions": {"win": 1},
        }, "preRacePrediction": {"win": 1}, "preRaceBet": {"numbers": [1]}
    }


@pytest.mark.parametrize("circuit", ["jra", "nar"])
def test_twenty_four_independently_importable_result_readers(circuit):
    observed = race(circuit)
    before = deepcopy(observed)
    assert len(MODULES) == 12
    for field in MODULES:
        func = import_module(f"arvexq.v3.data.{circuit}.result_fields.{field}").read
        assert isinstance(func(observed), list)
    assert observed == before
    o = read_breakdown(observed, circuit)
    assert o["finisherFields"]["finish"]["rows"] == [
        {"horseNumber": 1, "finish": 1}, {"horseNumber": 2, "finish": 2}]
    assert o["finisherFields"]["margin"]["rows"] == [{"horseNumber": 1, "margin": 0}]
    assert o["finisherFields"]["clock"]["rows"] == [{"horseNumber": 1, "time": "1:23.4"}]
    assert o["payoutKinds"]["win"]["rows"] == [{"kind": "単勝", "combination": "1", "payout": 500}]
    assert o["payoutKinds"]["trifecta"]["rows"][0]["payout"] == 13000
    assert o["payoutKinds"]["trio"]["status"] == "field-not-observed"
    assert o["unmappedPayoutRows"] == 1
    assert o["officialFinalityVerified"] is False and o["predictionsCalculated"] is False
    assert "preRaceBet" not in str(o) and "predictionScore" not in str(o) and "'mark'" not in str(o)
    assert observed == before


@pytest.mark.parametrize("circuit,other", [("jra", "nar"), ("nar", "jra")])
def test_cross_circuit_result_reader_refuses_wrong_input(circuit, other):
    with pytest.raises(ValueError, match="circuit"):
        read_breakdown(race(circuit), other)
    for field in MODULES:
        with pytest.raises(ValueError, match="circuit"):
            import_module(f"arvexq.v3.data.{other}.result_fields.{field}").read(race(circuit))


@pytest.mark.parametrize("circuit", ["jra", "nar"])
def test_pre_race_api_and_screen_hide_results_and_field_breakdown(circuit):
    source = race(circuit)
    pre = factual_response(source)
    assert pre["results"] is None and pre["resultFields"] is None
    s = factual_screen(pre)
    assert s["results"] is None and s["resultFields"] is None
    assert "13000" not in str(s)
    post = factual_response(source, include_results=True)
    assert post["resultFields"]["payoutKinds"]["trifecta"]["rows"][0]["payout"] == 13000
    post_view = factual_screen(post)
    assert post_view["resultFields"]["payoutKinds"]["win"]["rows"][0]["payout"] == 500
    post_view["resultFields"]["payoutKinds"]["win"]["rows"][0]["payout"] = 1
    assert source["result"]["payouts"][0]["payout"] == 500


def test_no_result_or_odds_does_not_mean_zero_payoff_or_ticket():
    original = race("jra")
    original.pop("result")
    out = read_breakdown(original, "jra")
    assert out["resultState"] == "not-observed"
    assert all(v["status"] == "not-observed" and not v["rows"]
               for v in list(out["finisherFields"].values()) + list(out["payoutKinds"].values()))
    assert out["unmappedPayoutRows"] == 0
