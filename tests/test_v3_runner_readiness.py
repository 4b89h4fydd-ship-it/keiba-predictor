"""JRA/NAR runner factual evidence and unverified missingness contracts."""
from copy import deepcopy
from importlib import import_module
import pytest
from arvexq.v3.transport.api import factual_response
from arvexq.v3.transport.display import factual_screen

def saved(circuit):
    city = "京都" if circuit == "jra" else "高知"
    return {
        "id": f"{circuit}-2026-10-19-{city}-03",
        "date": "2026-10-19", "circuit": circuit.upper(),
        "track": city, "fieldSize": 2,
        "horses": [
            {"horseNumber": 2, "name": "走歴あり", "winOdds": 2.4,
             "placeOdds": "1.2-1.4", "popularity": 2,
             "allPastRuns": [
                 {"date": f"2026-10-{day:02d}", "finish": 3}
                 for day in range(1, 9)
             ] + [{"date": "2026-10-18", "finish": 4}],
             "recentRaces": [{"date": "2026-10-08", "track": city, "finish": 3},
                             {"date": "2026-10-19", "finish": 1}],
             "mark": "◎", "preRaceBet": {"ticket": "secret"}},
            {"horseNumber": 1, "name": "履歴不明", "winOdds": 0,
             "placeOdds": None, "popularity": 0,
             "recentRaces": [{"date": "2026-10-19", "finish": 1}],
             "preRacePrediction": {"winner": 1}},
        ],
        "result": {"finishers": [{"horseNumber": 2, "finish": 1}]},
    }

@pytest.mark.parametrize("circuit", ("jra", "nar"))
def test_runner_status_and_full_count_not_truncated_to_five(circuit):
    detail = saved(circuit)
    original = deepcopy(detail)
    reader = import_module(f"arvexq.v3.data.{circuit}.runner_readiness")
    evidence = reader.read(detail)
    assert [row["horseNumber"] for row in evidence] == [2, 1]
    assert [row["observedPriorRunCount"] for row in evidence] == [9, 0]
    assert evidence[0]["history"] == "partial-unverified"
    assert evidence[0]["odds"] == "observed-unverified"
    assert evidence[1]["history"] == "missing"
    assert evidence[1]["odds"] == "incomplete"
    assert [evidence[1][k] for k in ("win", "place", "popularity")] == ["invalid", "missing", "invalid"]
    assert all(not x["canClaimFullyRetrieved"] and not x["allCareerRunsVerified"] and
               not x["marketFreshnessVerified"] for x in evidence)
    screen = factual_screen(factual_response(detail))
    assert [x["horseNumber"] for x in screen["rows"]] == [1, 2]
    assert len(screen["rows"][1]["recentRaces"]) == 5
    assert screen["rows"][1]["observedPriorRunCount"] == 9
    assert screen["rows"][1]["readiness"] == evidence[0]
    assert screen["rows"][0]["readiness"] == evidence[1]
    assert screen["displayReadiness"]["history"] == "partial-unverified"
    assert screen["displayReadiness"]["odds"] == "incomplete"
    assert screen["results"] is None and screen["marks"] is None and screen["tickets"] is None
    assert "preRaceBet" not in str(screen) and "preRacePrediction" not in str(screen)
    assert detail == original

@pytest.mark.parametrize("circuit,other", (("jra", "nar"), ("nar", "jra")))
def test_other_circuit_refused(circuit, other):
    with pytest.raises(ValueError, match="circuit"):
        import_module(f"arvexq.v3.data.{other}.runner_readiness").read(saved(circuit))

def test_screen_refuses_misaligned_readiness():
    dto = factual_response(saved("jra"))
    dto["runnerReadiness"][1]["horseNumber"] = 999
    with pytest.raises(ValueError, match="readiness"):
        factual_screen(dto)
    dto = factual_response(saved("jra"))
    dto["runnerReadiness"][0]["observedPriorRunCount"] = 123
    with pytest.raises(ValueError, match="readiness"):
        factual_screen(dto)

@pytest.mark.parametrize("circuit", ("jra", "nar"))
def test_readiness_rejects_cross_horse_market_and_fabricated_completeness(circuit):
    data = factual_response(saved(circuit))
    data["oddsFields"]["win"][0]["horseNumber"] = 1
    with pytest.raises(ValueError, match="readiness"):
        factual_screen(data)
    data = factual_response(saved(circuit))
    data["runnerReadiness"][1]["win"] = "observed"
    with pytest.raises(ValueError, match="readiness"):
        factual_screen(data)
    data = factual_response(saved(circuit))
    data["runnerReadiness"][0]["canClaimFullyRetrieved"] = True
    with pytest.raises(ValueError, match="readiness"):
        factual_screen(data)


@pytest.mark.parametrize("circuit", ("jra", "nar"))
def test_screen_rejects_tampered_prior_field_evidence(circuit):
    original = factual_response(saved(circuit))
    wrong = deepcopy(original)
    wrong["runnerReadiness"][0]["pastFieldStates"][0]["fields"]["finish"] = "missing"
    with pytest.raises(ValueError, match="past field state"):
        factual_screen(wrong)
    wrong = deepcopy(original)
    wrong["runnerReadiness"][0]["pastFieldStates"][0]["date"] = "2026-01-01"
    with pytest.raises(ValueError, match="past field identity"):
        factual_screen(wrong)
    wrong = deepcopy(original)
    wrong["runnerReadiness"][0]["pastFieldStates"].pop()
    with pytest.raises(ValueError, match="past field alignment"):
        factual_screen(wrong)
    wrong = deepcopy(original)
    wrong["history"][0]["observedPriorRunCount"] += 1
    wrong["runnerReadiness"][0]["observedPriorRunCount"] += 1
    with pytest.raises(ValueError, match="historical run count"):
        factual_screen(wrong)
    wrong = deepcopy(original)
    wrong["runnerReadiness"][0]["quoteTimeState"] = "verified-fresh"
    with pytest.raises(ValueError, match="quote time"):
        factual_screen(wrong)
