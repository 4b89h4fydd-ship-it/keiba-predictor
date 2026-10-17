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
