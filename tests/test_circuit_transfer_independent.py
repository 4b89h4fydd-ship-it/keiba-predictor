from arvexq.ingest.circuit_transfer import race_circuit, transfer_observations
from arvexq.ingest.transfer_history import _history_rates, _run_circuit

def test_each_provider_code_is_independent_and_never_guesses_unknowns():
    assert race_circuit({"track":"東京"})=="JRA"
    assert race_circuit({"track":"大井"})=="NAR"
    assert race_circuit({"track":"未知場"}) is None
    assert race_circuit({"track":"東京","circuit":"NAR"})=="NAR"
    assert race_circuit({}) is None
    assert _run_circuit({"track":"園田"})=="NAR"

def test_transfer_evidence_is_observational_and_unrelated_to_bets():
    horse={"allPastRuns":[{"track":"大井","date":"2026-09-20","finish":3},
                            {"track":"東京","date":"2026-08-20","finish":1},
                            {"track":"未知場","date":"2026-07-20","finish":2}]}
    facts=transfer_observations(horse,{"track":"東京"})
    assert facts=={"targetCircuit":"JRA","knownCircuitStarts":2,
                   "unknownCircuitStarts":1,"hasCrossCircuitHistory":True,
                   "latestReportedCircuit":"NAR"}
    assert _history_rates(horse,{"date":"2026-10-18","circuit":"中央"})["transferEvidence"] is True


def test_transfer_observations_exclude_future_and_same_day_on_dated_target():
    horse = {"allPastRuns": [
        {"track":"東京", "date":"2026-10-24", "finish":1},
        {"track":"大井", "date":"2026-10-23", "finish":2},
        {"track":"東京", "date":"2026/10/22", "finish":3},
        {"track":"大井", "date":"2026-10-21", "finish":4},
        {"track":"東京", "date":"unknown", "finish":5},
    ]}
    out = transfer_observations(horse, {"track":"東京", "date":"2026-10-23"})
    assert out["knownCircuitStarts"] == 2
    assert out["unknownCircuitStarts"] == 0
    assert out["targetCircuit"] == "JRA"
    assert out["hasCrossCircuitHistory"] is True
    assert len(horse["allPastRuns"]) == 5


def test_history_rates_do_not_assume_unknown_target_is_nar():
    horse = {"allPastRuns": [{"track":"大井", "date":"2026-10-21", "finish":1}]}
    result = _history_rates(horse, {"date":"2026-10-23", "track":"未知場"})
    assert result["targetCircuit"] is None
    assert result["sameCircuitStarts"] == 0
    assert result["winRate"] is None
    assert result["transferEvidence"] is False


def test_history_rates_use_valid_chronological_dates_only_and_keep_jra_nar_separate():
    horse = {"allPastRuns": [
        {"track":"東京", "date":"2026-10-24", "finish":1},
        {"track":"東京", "date":"2026-10-23", "finish":1},
        {"track":"大井", "date":"2026-10-22", "finish":1},
        {"track":"東京", "date":"2026/10/20", "finish":"2.0"},
        {"track":"東京", "date":"invalid", "finish":1},
        {"track":"東京", "date":"2026-10-19", "finish":"unknown"},
    ]}
    central = _history_rates(horse, {"date":"2026-10-23", "circuit":"中央"})
    local = _history_rates(horse, {"date":"2026-10-23", "circuit":"地方"})
    assert central["starts"] == 1
    assert central["top2Rate"] == 1.0
    assert central["winRate"] == 0.0
    assert central["otherCircuitStarts"] == 1
    assert local["starts"] == 1
    assert local["winRate"] == 1.0
    assert local["otherCircuitStarts"] == 1
    assert horse["allPastRuns"][3]["finish"] == "2.0"
    assert _history_rates(horse, {"circuit":"中央"})["starts"] == 0

def test_transfer_class_proxy_rejects_malformed_field_size_without_changing_valid_quality():
    horse = {"allPastRuns": [
        {"track": "大井", "date": "2026-10-20", "finish": 1,
         "fieldSize": "not-a-number", "opponentLevel": 0.6},
        {"track": "大井", "date": "2026-10-19", "finish": 6,
         "fieldSize": 5, "opponentLevel": 0.6},
        {"track": "大井", "date": "2026-10-18", "finish": 2,
         "fieldSize": 8, "opponentLevel": 0.6},
    ]}
    race = {"track": "東京", "date": "2026-10-23", "opponentLevel": 0.7}
    outcome = _history_rates(horse, race)
    assert outcome["otherCircuitStarts"] == 3
    assert outcome["transferClassEvidenceStarts"] == 1
    assert outcome["transferClassSignal"] > 0
    assert horse["allPastRuns"][0]["fieldSize"] == "not-a-number"
