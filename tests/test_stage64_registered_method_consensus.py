"""Regression tests: registered cross-method evidence inside the same six stages."""
from copy import deepcopy
from unittest.mock import patch

from arvexq.forecast.engine import _attach_registered_method_consensus


def _candidate(method, *, owner="nar", winner=1, axis=1, picks=None, complete=True):
    if picks is None:
        picks = [(1, 2, 3), (1, 3, 2), (2, 1, 3)]
    stages = {
        "ability": {"value": {1: 0.8, 2: 0.7, 3: 0.4}},
        "runningStyle": {"value": {1: [1, 0, 0, 0], 2: [0, 1, 0, 0],
                                    3: [0, 0, 1, 0]}},
        "pace": {"value": [{1: 0, 2: 0, 3: 0}]},
        "probability": {"value": {"win": {1: 0.5, 2: 0.3, 3: 0.2},
                                   "top3": {1: 1, 2: 1, 3: 1}}},
        "marks": {"value": {"winRole": {"horseNumber": winner, "grade": None},
                             "axisRole": {"horseNumber": axis, "grade": None},
                             "productMarks": None}},
        "tickets": {"value": {"hypotheticalTrifectaTop10": picks,
                               "recommendedBets": None}},
    }
    if not complete:
        stages["runningStyle"]["value"] = None
    return {"raceId": owner + "-2026-10-22-門別-12" if owner == "nar" else
            "jra-2026-10-22-東京-12",
            "date": "2026-10-22", "circuit": owner,
            "abilityMethod": method, "modelVersion": owner + "-flat-shadow-v1",
            "stages": stages, "productionEligible": False}


def test_majority_candidates_do_not_replace_registered_baseline():
    base = _candidate("baseline")
    previous = deepcopy(base)
    recent = _candidate("recent5", winner=2, axis=1,
                        picks=[(1, 2, 3), (3, 2, 1)])
    shrunk = _candidate("recent5_shrunk", winner=2, axis=3,
                        picks=[(2, 1, 3), (3, 1, 2)])
    with patch("arvexq.forecast.engine.predict", side_effect=[recent, shrunk]) as mocked:
        _attach_registered_method_consensus({"id": base["raceId"]}, "nar", base)
    assert mocked.call_count == 2
    assert all(c.kwargs["expected_circuit"] == "nar" for c in mocked.call_args_list)
    assert [c.kwargs["ability_method"] for c in mocked.call_args_list] == [
        "recent5", "recent5_shrunk"]
    assert base["stages"]["marks"]["value"]["winRole"] == previous["stages"]["marks"]["value"]["winRole"]
    assert base["stages"]["marks"]["value"]["axisRole"] == previous["stages"]["marks"]["value"]["axisRole"]
    assert base["stages"]["tickets"]["value"]["hypotheticalTrifectaTop10"] == previous["stages"]["tickets"]["value"]["hypotheticalTrifectaTop10"]
    assert base["stages"]["tickets"]["value"]["recommendedBets"] is None
    consensus = base["stages"]["marks"]["value"]["registeredMethodConsensus"]
    assert consensus["majorityWinCandidate"] == 2
    assert consensus["majorityAxisCandidate"] == 1
    assert consensus["baselineWinRoleUnchanged"] is True
    shared = base["stages"]["tickets"]["value"]["registeredMethodConsensus"]
    assert shared["sharedTop10Candidates"] == [(1, 2, 3), (2, 1, 3)]
    assert shared["recommendedBetsPromoted"] is False
    assert base["stages"]["probability"]["registeredMethodWinRangeUncalibrated"][1] == {
        "min": 0.5, "max": 0.5}
    assert base["stages"]["ability"]["registeredMethodComparison"]["arms"] == [
        "baseline", "recent5", "recent5_shrunk"]
    assert len(base["stages"]) == 6


def test_split_vote_has_no_majority_and_no_fabricated_grade():
    base = _candidate("baseline", winner=1)
    recent = _candidate("recent5", winner=2)
    shrunk = _candidate("recent5_shrunk", winner=3)
    with patch("arvexq.forecast.engine.predict", side_effect=[recent, shrunk]):
        _attach_registered_method_consensus({"id": base["raceId"]}, "nar", base)
    m = base["stages"]["marks"]["value"]
    assert m["registeredMethodConsensus"]["majorityWinCandidate"] is None
    assert m["winRole"]["horseNumber"] == 1
    assert m["winRole"]["grade"] is None


def test_incomplete_or_cross_circuit_comparison_fails_closed():
    base = _candidate("baseline")
    previous = deepcopy(base)
    recent = _candidate("recent5", complete=False)
    shrunk = _candidate("recent5_shrunk")
    with patch("arvexq.forecast.engine.predict", side_effect=[recent, shrunk]):
        _attach_registered_method_consensus({"id": base["raceId"]}, "nar", base)
    assert base == previous

    other_circuit = _candidate("recent5", owner="jra")
    with patch("arvexq.forecast.engine.predict", side_effect=[other_circuit, shrunk]):
        _attach_registered_method_consensus({"id": base["raceId"]}, "nar", base)
    assert base == previous


def test_jra_stays_on_jra_registered_arms_only():
    base = _candidate("baseline", owner="jra")
    recent = _candidate("recent5", owner="jra")
    shrunk = _candidate("recent5_shrunk", owner="jra")
    with patch("arvexq.forecast.engine.predict", side_effect=[recent, shrunk]) as mocked:
        _attach_registered_method_consensus({"id": base["raceId"]}, "jra", base)
    assert all(c.kwargs["expected_circuit"] == "jra" for c in mocked.call_args_list)
    assert base["stages"]["marks"]["value"]["registeredMethodConsensus"]["majorityWinCandidate"] == 1
