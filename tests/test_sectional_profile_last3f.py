"""Observed last-3F in researchEvidence.sectionals inputs.

Regression: the past-run records actually stored by the career /
official-CSV builders carry the lowercase spellings last3fSeconds /
last3f / last3fRank, while sectional_profile only probed the
capital-F spellings, so every measured late-3F read as null (audit
2026-11-17: NAR runs existed but no 3F value anywhere; the same
mismatch starved jra_sectional_evidence percentiles)."""
from arvexq.prediction.jra_sectional_evidence import (
    horse_sectional_evidence)
from arvexq.prediction.sectional_profile import profile


def _horse(runs):
    return {"horseNumber": 1, "name": "テスト", "allPastRuns": runs}


RACE = {"date": "2026-11-17"}


def test_lowercase_last3f_seconds_becomes_measured_late():
    horse = _horse([
        {"date": "2026-10-28", "track": "大井", "raceNumber": 10,
         "finish": 2, "fieldSize": 14, "last3fSeconds": 38.6},
        {"date": "2026-10-07", "track": "大井", "raceNumber": 11,
         "finish": 5, "fieldSize": 13, "last3f": 39.9},
    ])
    result = profile(horse, RACE)
    assert result["measuredLate"] == 2
    assert [r["late3FSeconds"] for r in result["runs"]] == [38.6, 39.9]


def test_capital_f_spelling_still_works():
    horse = _horse([
        {"date": "2026-10-28", "track": "東京", "raceNumber": 10,
         "finish": 2, "fieldSize": 14, "last3FSeconds": 34.1},
    ])
    result = profile(horse, RACE)
    assert result["runs"][0]["late3FSeconds"] == 34.1


def test_percentile_reconstructed_from_stored_rank():
    horse = _horse([
        {"date": "2026-10-28", "track": "東京", "raceNumber": 10,
         "finish": 1, "fieldSize": 11, "last3fSeconds": 34.1,
         "last3fRank": 1},
        {"date": "2026-10-07", "track": "東京", "raceNumber": 10,
         "finish": 6, "fieldSize": 11, "last3fSeconds": 35.9,
         "last3fRank": 11},
    ])
    result = profile(horse, RACE)
    pct = [r["last3FWithinRacePercentile"] for r in result["runs"]]
    assert pct == [1.0, 0.0]


def test_jra_evidence_reads_lowercase_rank():
    horse = _horse([
        {"date": "2026-10-28", "track": "東京", "raceNumber": 10,
         "finish": 1, "fieldSize": 11, "last3fSeconds": 34.1,
         "last3fRank": 2},
    ])
    evidence = horse_sectional_evidence(horse, RACE)
    assert evidence["sample"] == 1
    assert evidence["median"] == 0.9


def test_runs_without_observation_stay_null():
    horse = _horse([
        {"date": "2026-10-28", "track": "大井", "raceNumber": 10,
         "finish": 2, "fieldSize": 14},
    ])
    result = profile(horse, RACE)
    assert result["measuredLate"] == 0
    assert result["runs"][0]["late3FSeconds"] is None
    assert result["runs"][0]["last3FWithinRacePercentile"] is None
