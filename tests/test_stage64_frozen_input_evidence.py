"""Regression checks for existing Stage64 pre-off evidence transport.

Synthetic fixtures test data integrity, NOT a claim of higher hit rate.
"""
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from arvexq.research.stage64.pipeline import predict
from arvexq.research.stage64.protocol import clean_input, make_plan, snapshot, verify_local


def _race(owner="nar"):
    track = "園田" if owner == "nar" else "京都"
    circuit_surface = "ダート" if owner == "nar" else "芝"
    return {
        "id": f"{owner}-2026-10-28-{track}-03",
        "date": "2026-10-28", "circuit": owner,
        "track": track, "surface": circuit_surface, "analysisMode": "平地",
        "distance": 1400, "startTime": "12:30", "scheduledStartTime": "12:30",
        "raceNumber": 3, "fieldSize": 3,
        "horses": [
            {
                "horseNumber": n,
                "recentRaces": [{
                    "date": "2026-10-20", "track": track, "surface": circuit_surface,
                    "raceNumber": 3, "distance": 1400, "fieldSize": 8,
                    "finish": n, "cornerPositions": [n, n],
                    "marginSeconds": n * .2, "opponentLevel": .7,
                    "earlyTiming": {"sourceKind": "individual_sensor",
                                    "sourceRef": "official:sample", "first200mSeconds": 12.0,
                                    "targetFinish": 1},
                    "targetOdds": 1.01,
                }],
                "result": {"finish": 1},
                "winOdds": 1.01,
            }
            for n in (1, 2, 3)
        ],
        "courseGeometry": {
            "sourceKind": "official_course_geometry",
            "sourceUrl": "https://www.keiba.go.jp/guide/course/",
            "sourcePublishedBeforeOff": True, "publishedAt": "2026-10-21T12:00:00+09:00",
            "track": track, "distance": 1400, "surface": circuit_surface,
            "firstCornerDistanceMeters": 320,
        },
    }


def test_nar_seal_retains_comparable_history_without_target_outcome():
    race = _race("nar")
    horse = race["horses"][0]
    horse["recentRaces"].append({
        "date": "2026-10-28", "finish": 1, "fieldSize": 8,
        "track": "園田", "distance": 1400, "cornerPositions": [1]})
    horse["recentRaces"].append({
        "date": "2026-10-29", "finish": 1, "fieldSize": 8,
        "track": "園田", "distance": 1400, "cornerPositions": [1]})
    horse["allPastRuns"] = [
        deepcopy(horse["recentRaces"][0]),
        {"date": "2026-10-10", "track": "園田", "surface": "ダート",
         "raceNumber": 3, "distance": 1400, "fieldSize": 8, "finish": 2,
         "cornerPositions": [2], "marginSeconds": .3, "opponentLevel": .7},
        {"date": "2026-10-29", "track": "園田", "surface": "ダート",
         "raceNumber": 3, "distance": 1400, "fieldSize": 8, "finish": 1,
         "cornerPositions": [1]},
    ]
    original = deepcopy(race)
    frozen = clean_input(race)
    assert original == race
    assert frozen["distance"] == 1400
    assert frozen["courseGeometry"]["sourceKind"] == "official_course_geometry"
    assert len(frozen["horses"][0]["recentRaces"]) == 1
    assert len(frozen["horses"][0]["allPastRuns"]) == 2
    assert all(run["date"] < race["date"] for h in frozen["horses"]
               for key in ("recentRaces", "allPastRuns") for run in h.get(key, []))
    assert "result" not in frozen["horses"][0]
    assert "winOdds" not in frozen["horses"][0]
    assert "targetOdds" not in frozen["horses"][0]["recentRaces"][0]
    assert "targetFinish" not in frozen["horses"][0]["recentRaces"][0]["earlyTiming"]
    assert frozen["horses"][0]["recentRaces"][0]["marginSeconds"] == .2
    assert frozen["horses"][0]["recentRaces"][0]["distance"] == 1400
    assert clean_input(frozen) == frozen

    predicted = predict(frozen, expected_circuit="nar")
    assert predicted["abilityHistoryCoverage"]["fullCareerRunners"] == 1
    facts = predicted["paceEvidence"]["holisticWinnerEvidence"]["byHorse"][1]
    assert facts["historicalMarginSamples"] == 2
    assert facts["sameTrackDistanceStarts"] == 2
    assert predicted["paceEvidence"]["holisticWinnerEvidence"]["firstCorner"]["meters"] == 320
    assert len(predicted["stages"]) == 6
    assert predicted["productionEligible"] is False


def test_jra_seal_cannot_import_nar_full_career():
    race = _race("jra")
    race["horses"][0]["allPastRuns"] = [{
        "date": "2026-09-01", "finish": 1, "fieldSize": 8,
        "cornerPositions": [1], "track": "京都", "distance": 1400,
    }]
    frozen = clean_input(race)
    assert "allPastRuns" not in frozen["horses"][0]
    assert frozen["horses"][0]["recentRaces"][0]["distance"] == 1400
    predicted = predict(frozen, expected_circuit="jra")
    assert predicted["abilityHistoryCoverage"]["fullCareerRunners"] == 0
    assert predicted["predictionMethod"]["abilityHistory"] == "jra-visible-history"


def test_stage64_snapshot_integrity_uses_sealed_facts_only():
    race = _race("nar")
    race["horses"][0]["allPastRuns"] = deepcopy(race["horses"][0]["recentRaces"]) + [{
        "date": "2026-10-12", "track": "園田", "surface": "ダート",
        "raceNumber": 3, "distance": 1400, "fieldSize": 8, "finish": 2,
        "cornerPositions": [2], "marginSeconds": .3,
    }]
    plan = make_plan("nar", ["development-race"])
    with patch("arvexq.research.stage64.protocol.datetime") as clock:
        clock.now.return_value = datetime(2026, 10, 24, 4, tzinfo=timezone.utc)
        clock.fromisoformat.side_effect = datetime.fromisoformat
        receipt = snapshot(race, plan)
    assert verify_local(receipt, plan)["localIntegrityVerified"] is True
    assert receipt["snapshot"]["input"]["horses"][0]["allPastRuns"]
    assert receipt["snapshot"]["predictions"]["baseline"]["productionEligible"] is False
    changed = deepcopy(receipt)
    changed["snapshot"]["input"]["horses"][0]["allPastRuns"][0]["finish"] = 8
    with pytest.raises(ValueError, match="checksum"):
        verify_local(changed, plan)


def test_target_result_is_never_accepted_into_preoff_freeze():
    race = _race("nar")
    race["result"] = {"status": "確定", "finishers": [{"horseNumber": 1, "finish": 1}]}
    with pytest.raises(ValueError, match="target outcome"):
        clean_input(race)
