"""Exact observable value and circuit behavior for separately owned result projections."""
import pytest
from arvexq.v3.data.result_facts import finish_field, payout_field, FINISH_FIELDS, PAYOUT_KINDS
from arvexq.v3.data.result_split import read_breakdown


def detail(circuit):
    return {"id": circuit + "-20261020-sample", "circuit": circuit,
            "result": {"finishers": [
                {"horseNumber": 2, "finish": 1, "rank": 1, "margin": 0,
                 "time": "1:23.4", "cornerPositions": [1, 1], "mark": "◎"},
                {"horseNumber": 3, "finish": None, "margin": None}],
                "payouts": [{"kind": "複勝", "payout": 200, "combination": "2", "bets": [1]},
                            {"kind": "3連単", "payout": 10000, "combination": "2-3-4"}]}}


@pytest.mark.parametrize("circuit", ["jra", "nar"])
def test_result_projection_preserves_observed_fields_only(circuit):
    race = detail(circuit)
    assert finish_field(race, circuit, "finish") == [{"horseNumber": 2, "finish": 1, "rank": 1}]
    assert finish_field(race, circuit, "margin") == [{"horseNumber": 2, "margin": 0}]
    assert finish_field(race, circuit, "clock") == [{"horseNumber": 2, "time": "1:23.4"}]
    assert payout_field(race, circuit, "place") == [{"kind": "複勝", "combination": "2", "payout": 200}]
    assert payout_field(race, circuit, "trifecta") == [{"kind": "3連単", "combination": "2-3-4", "payout": 10000}]
    assert list(read_breakdown(race, circuit)["payoutKinds"]) == list(PAYOUT_KINDS)
    assert list(read_breakdown(race, circuit)["finisherFields"]) == list(FINISH_FIELDS)
    assert all(not payout_field(race, circuit, kind) for kind in ("trio", "exacta", "win"))


@pytest.mark.parametrize("left,right", [("jra", "nar"), ("nar", "jra")])
def test_cross_circuit_result_projection_is_rejected(left, right):
    with pytest.raises(ValueError, match="circuit"): finish_field(detail(left), right, "finish")
    with pytest.raises(ValueError, match="circuit"): payout_field(detail(left), right, "place")


def test_unknown_field_stays_an_error():
    with pytest.raises(ValueError, match="unrecognized finish field"): finish_field(detail("jra"), "jra", "bad")
    with pytest.raises(ValueError, match="unrecognized payout kind"): payout_field(detail("jra"), "jra", "bad")
