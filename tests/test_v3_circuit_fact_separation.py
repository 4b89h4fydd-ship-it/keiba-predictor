"""Exercise ten independent observed-only domains across JRA and NAR."""
from copy import deepcopy
from importlib import import_module

import pytest

from arvexq.v3.data.circuit_review import DOMAINS, inspect_circuit
from arvexq.v3.data.observed_fields import ensure_circuit


def saved(circuit):
    prefix = circuit.lower()
    track = "東京" if circuit == "JRA" else "高知"
    return {
        "id": f"{prefix}-2026-10-18-{track}-03", "circuit": circuit,
        "date": "2026-10-18", "track": track, "startTime": "10:00",
        "surface": "ダート", "distance": 1400, "fieldSize": 2,
        "horses": [
            {"horseNumber": 1, "name": "テスト一", "jockey": "A", "carriedWeight": 56,
             "winOdds": 3.5, "popularity": 2, "mark": "◎",
             "allPastRuns": [
                 {"date": "2026-10-01", "track": track, "finish": 2,
                  "mark": "▲", "futurePrediction": {"winning": 0.99}},
                 {"date": "2026-10-18", "finish": 1},
                 {"date": "2026-10-19", "finish": 1}],
             "preRaceBet": {"items": [1]}},
            {"horseNumber": 2, "name": "テスト二", "winOdds": None,
             "recentRaces": [{"date": "2026-10-02", "finish": 3},
                             {"date": "2026-10-02", "finish": 3}]},
        ],
        "result": {"finishers": [{"horseNumber": 2, "finish": 1, "mark": "◎"}],
                   "payouts": [{"kind": "単勝", "payout": 440, "bets": [1]}]},
        "preRacePrediction": {"favorite": 1},
        "preRaceBet": {"tickets": [[1, 2]]},
    }


@pytest.mark.parametrize("circuit", ["JRA", "NAR"])
def test_independent_modules_only_read_existing_snapshot(circuit):
    detail = saved(circuit)
    before = deepcopy(detail)
    readers = {domain: import_module(f"arvexq.v3.data.{circuit.lower()}.{domain}").read
               for domain in DOMAINS}
    assert set(readers) == set(DOMAINS)
    assert readers["race"](detail)["id"] == detail["id"]
    rows = readers["entries"](detail)
    assert len(rows) == 2 and rows[0]["name"] == "テスト一"
    history = readers["history"](detail)
    assert [r["date"] for r in history[0]["pastRuns"]] == ["2026-10-01"]
    assert len(history[1]["pastRuns"]) == 1
    assert history[0]["careerCompleteness"] == "unverified"
    assert "mark" not in history[0]["pastRuns"][0]
    odds = readers["odds"](detail)
    assert odds[0]["winOdds"] == 3.5
    assert odds[1]["winOdds"] is None
    results = readers["results"](detail)
    assert results["resultState"] == "observed-unverified"
    assert results["payouts"] == [{"kind": "単勝", "payout": 440}]
    assert all("mark" not in r for r in results["finishers"])
    assert detail == before
    assert "preRacePrediction" not in str(results)
    assert "preRaceBet" not in str(rows)
    entries_a = readers["entries"](detail)
    entries_a[0]["name"] = "changed"
    assert detail["horses"][0]["name"] == "テスト一"


@pytest.mark.parametrize("circuit,wrong", [("JRA", "nar"), ("NAR", "jra")])
def test_cross_circuit_modules_refuse_wrong_input(circuit, wrong):
    obj = saved(circuit)
    for domain in DOMAINS:
        with pytest.raises(ValueError, match="circuit"):
            import_module(f"arvexq.v3.data.{wrong}.{domain}").read(obj)


def test_identity_conflict_and_unknown_circuit_cannot_route():
    obj = saved("JRA")
    obj["id"] = "nar-2026-10-18-東京-03"
    summary = inspect_circuit(obj)
    assert "circuit-routing-refused" in summary["warnings"]
    assert summary["domains"]["race"] == "unavailable"
    obj["circuit"] = "unknown"
    summary = inspect_circuit(obj)
    assert summary["circuit"] is None and summary["domains"]["entries"] == "unavailable"


def test_full_coverage_report_does_not_claim_verified_histories_or_predictions():
    r = inspect_circuit(saved("NAR"))
    assert r["circuit"] == "nar"
    assert r["domains"]["history"] == "observed"
    assert r["domains"]["results"] == "observed-unverified"
    assert r["counts"]["observedPriorRuns"] == 2
    assert r["counts"]["runnersWithPriorRuns"] == 2
    assert r["counts"]["resultFinishers"] == 1
    assert r["historyCompleteness"] == "unverified"
    assert r["predictionStatus"] == "not-implemented"
    assert not any(x in str(r) for x in ("preRaceBet", "probability", "winRate", "predictionMarks"))


def test_no_results_and_no_odds_is_missing_not_zero():
    obj = saved("JRA")
    obj.pop("result")
    for horse in obj["horses"]:
        horse.pop("winOdds", None)
        horse.pop("popularity", None)
    s = inspect_circuit(obj)
    assert s["domains"]["results"] == "not-observed"
    assert s["domains"]["odds"] == "missing"
    assert s["counts"]["resultPayoutRows"] == 0


def test_no_predictions_installed_by_source_separation():
    for circuit in ("jra", "nar"):
        for name in ("ability", "running_style", "pace", "probability", "marks", "tickets"):
            mod = import_module(f"arvexq.v3.prediction.{circuit}.{name}")
            assert mod.run(evidence=saved(circuit.upper())) is None
