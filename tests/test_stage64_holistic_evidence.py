"""Observed opposition/finish-margin/individual-start/course geometry contracts."""
from copy import deepcopy

from arvexq.research.stage64.holistic import evidence, direct_rematch_candidate
from arvexq.research.stage64.pipeline import predict


def _run(date, finish, *, no=1, reaction=None, source="individual_sensor"):
    row = {"date": date, "track": "園田", "raceNumber": 3,
           "distance": 1400, "fieldSize": 10, "finish": finish,
           "cornerPositions": [no, max(1, no-1)],
           "marginSeconds": (finish-1)*0.2, "opponentLevel": 0.7}
    if reaction is not None:
        row["earlyTiming"] = {"sourceKind": source, "sourceRef": "official:run:"+date,
                              "gateReactionSeconds": reaction,
                              "first200mSeconds": 12.2}
    return row


def _race():
    return {"id": "nar-2026-10-21-園田-03", "date": "2026-10-21",
            "circuit": "nar", "analysisMode": "平地", "track": "園田",
            "surface": "ダート", "distance": 1400, "fieldSize": 4, "startTime": "12:30",
            "horses": [
                {"horseNumber": 1, "frameNumber": 1,
                 "recentRaces": [_run("2026-10-04", 2, no=2, reaction=.15),
                                 _run("2026-09-15", 2, no=2)]},
                {"horseNumber": 2, "frameNumber": 2,
                 "recentRaces": [_run("2026-10-04", 1, no=1, reaction=.10),
                                 _run("2026-09-15", 1, no=1)]},
                {"horseNumber": 3, "frameNumber": 3,
                 "recentRaces": [_run("2026-10-04", 4, no=4, reaction=.09,
                                       source="official_race_lap"),
                                 _run("2026-09-15", 4, no=4)]},
                {"horseNumber": 4, "frameNumber": 4,
                 "recentRaces": [_run("2026-10-04", 6, no=6),
                                 _run("2026-09-15", 6, no=6)]},
            ]}


def test_all_observed_factors_are_in_same_six_stage_chain():
    r = _race()
    original = deepcopy(r)
    p = predict(r, expected_circuit="nar")
    assert r == original
    assert len(p["stages"]) == 6
    report = p["paceEvidence"]["holisticWinnerEvidence"]
    a, b, c = (report["byHorse"][n] for n in (1,2,3))
    assert a["opponentLevelSamples"] == 2
    assert a["historicalMarginSamples"] == 2
    assert a["individualGateReactionSamples"] == 1
    assert b["individualFirst200mSamples"] == 1
    assert c["individualGateReactionSamples"] == 0
    assert report["headToHead"][2][1]["wins"] == 2
    assert report["headToHead"][1][2]["losses"] == 2
    assert report["firstCorner"] is None and report["courseGeometryUnknown"]
    assert p["winnerEvidenceComparison"]["winnerRankUnchanged"] is True


def test_unsupported_margin_string_and_aggregate_lap_are_missing_not_bad():
    r = _race()
    r["horses"][0]["recentRaces"][0].pop("marginSeconds")
    r["horses"][0]["recentRaces"][0]["beatenLength"] = 3.5
    r["horses"][0]["recentRaces"][0]["earlyTiming"] = {
        "sourceKind": "official_race_lap", "sourceRef": "official:run",
        "gateReactionSeconds": .1}
    p = predict(r, expected_circuit="nar")
    fact = p["paceEvidence"]["holisticWinnerEvidence"]["byHorse"][1]
    assert fact["historicalMarginSamples"] == 1
    assert fact["individualGateReactionSamples"] == 0


def test_future_result_and_non_comparable_history_never_enter_opposition():
    r = _race()
    for horse in r["horses"]:
        horse["recentRaces"].insert(0, _run("2026-10-22", 1, no=1,
                                           reaction=.01))
    p = predict(r, expected_circuit="nar")
    facts = p["paceEvidence"]["holisticWinnerEvidence"]
    assert facts["byHorse"][1]["historicalStarts"] == 2
    assert facts["byHorse"][1]["individualGateReactionSamples"] == 1
    assert facts["headToHead"][2][1]["wins"] == 2


def test_full_career_reused_without_discarding_recent_runs_or_future_leak():
    r = _race()
    complete = deepcopy(r["horses"][0]["recentRaces"])
    older = _run("2026-08-01", 3, no=3)
    future = _run("2026-11-01", 1, no=1, reaction=.01)
    complete.extend([older, future])
    r["horses"][0]["allPastRuns"] = complete
    p = predict(r, expected_circuit="nar")
    fact = p["paceEvidence"]["holisticWinnerEvidence"]["byHorse"][1]
    assert fact["historicalStarts"] == 3
    assert fact["historicalMarginSamples"] == 3
    assert fact["individualGateReactionSamples"] == 1
    # A partial old career cannot erase a known recent start.
    r["horses"][0]["allPastRuns"] = [older]
    p2 = predict(r, expected_circuit="nar")
    assert p2["paceEvidence"]["holisticWinnerEvidence"]["byHorse"][1]["historicalStarts"] == 2


def test_preoff_first_corner_needs_identified_official_course_geometry():
    r = _race()
    geo = {"sourceKind": "official_course_geometry",
           "sourceUrl": "https://www.keiba.go.jp/guide/course/",
           "sourcePublishedBeforeOff": True, "publishedAt": "2026-09-01T12:00:00+09:00", "track": "園田",
           "distance": 1400, "surface": "ダート",
           "firstCornerDistanceMeters": 320}
    # This is a synthetic test fixture, not a measured first-corner distance.
    r["courseGeometry"] = geo
    p = predict(r, expected_circuit="nar")
    value = p["paceEvidence"]["holisticWinnerEvidence"]["firstCorner"]
    assert value is not None and value["meters"] == 320
    for change in ({"sourceUrl": "https://example.com/course"},
                   {"distance": 1230}, {"sourcePublishedBeforeOff": False},
                   {"publishedAt": "2026-10-21T13:00:00+09:00"},
                   {"publishedAt": "2026-10-21T12:30:00+09:00"},
                   {"sourceKind": "unverified"}, {"firstCornerDistanceMeters": None}):
        candidate = deepcopy(r)
        candidate["courseGeometry"].update(change)
        got = predict(candidate, expected_circuit="nar")
        assert got["paceEvidence"]["holisticWinnerEvidence"]["firstCorner"] is None


def test_head_to_head_challenger_is_audited_not_automatically_promoted():
    facts = {
        "headToHead": {2: {1: {"wins": 2, "losses": 0, "ties": 0,
                                "raceIds": ["2026-09-15", "2026-10-04"]}}},
        "firstCorner": None,
        "byHorse": {
            1: {"sameTrackDistanceMarginSeconds": .5,
                "sameTrackDistanceMarginSamples": 2,
                "opponentLevelMedian": .7, "opponentLevelSamples": 2,
                "sameTrackDistanceTop3": 1, "sameTrackDistanceStarts": 2},
            2: {"sameTrackDistanceMarginSeconds": .2,
                "sameTrackDistanceMarginSamples": 2,
                "opponentLevelMedian": .8, "opponentLevelSamples": 2,
                "sameTrackDistanceTop3": 2, "sameTrackDistanceStarts": 2},
        },
    }
    proposed = direct_rematch_candidate([1,2,3,4], facts)
    assert proposed["horseNumber"] == 2 and proposed["researchOnly"] is True
    assert "same-track-distance-margin" in proposed["confirmedChecks"]
    assert "verified-first-corner-geometry" in proposed["unavailableChecks"]
    facts["byHorse"][2]["opponentLevelMedian"] = .1
    assert direct_rematch_candidate([1,2,3,4], facts) is None
    facts["byHorse"][2]["opponentLevelMedian"] = .8
    facts["headToHead"][2][1]["losses"] = 1
    assert direct_rematch_candidate([1,2,3,4], facts) is None


def test_cross_circuit_rejected_even_with_context_evidence():
    r = _race()
    try:
        predict(r, expected_circuit="jra")
    except ValueError as exc:
        assert "cross-circuit" in str(exc)
    else:
        raise AssertionError("JRA/NAR separated")
