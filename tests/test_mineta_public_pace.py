"""Public Mineta-method feature extraction regression, not proprietary predictions."""
from copy import deepcopy
from arvexq.prediction.mineta_public_pace import public_pace_factors


def race():
    return {
        "id": "nar-2026-10-24-園田-09", "date": "2026-10-24", "circuit": "地方",
        "track": "園田", "surface": "ダート", "distance": 1400, "startTime": "12:00",
        "horses": [
            {"horseNumber": 1, "recentRaces": [
                {"date": "2026-10-20", "finish": 2, "fieldSize": 10,
                 "cornerPositions": [2, 3], "distance": 1400}]},
            {"horseNumber": 2, "recentRaces": [
                {"date": "2026-10-20", "finish": 3, "fieldSize": 10,
                 "cornerPositions": [5, 4], "distance": 1200}]},
            {"horseNumber": 3, "recentRaces": [
                {"date": "2026-10-20", "finish": 4, "fieldSize": 10,
                 "cornerPositions": [6, 5], "distance": 1600}]},
            {"horseNumber": 4, "recentRaces": [
                {"date": "2026-10-20", "finish": 4, "fieldSize": 10,
                 "distance": 1400}]},
            {"horseNumber": 5, "recentRaces": [
                {"date": "2026-10-25", "finish": 1, "fieldSize": 10,
                 "cornerPositions": [1], "distance": 1400}]},
        ],
    }


def test_public_position_and_distance_cues_are_observations_only():
    source = race()
    original = deepcopy(source)
    result = public_pace_factors(source)
    assert result["forwardIntentCandidates"] == [1, 2]
    assert result["adjacentForwardCandidates"] == [[1, 2]]
    assert result["forwardCandidateShare"] == 2/5
    assert result["horses"][0]["lastFirstCornerTop3"] is True
    assert result["horses"][1]["lastRunDistanceChange"] == "extension"
    assert result["horses"][2]["lastRunDistanceChange"] == "shortening"
    assert result["horses"][3]["lastFirstCornerTop3"] is None
    assert result["horses"][4]["lastFirstCornerTop3"] is None
    assert result["predictedPaceProbabilities"] is None
    assert result["winProbability"] is None
    assert source == original


def test_unverified_geometry_is_unknown_not_fabricated():
    source = race()
    source["courseGeometry"] = {
        "sourceKind": "official_course_geometry", "sourcePublishedBeforeOff": True,
        "sourceUrl": "https://www.keiba.go.jp/track/sonoda",
        "track": "園田", "surface": "ダート", "distance": 1400,
        "firstCornerDistanceMeters": 250,
        "publishedAt": "2026-10-23T11:00:00+09:00",
    }
    assert public_pace_factors(source)["firstCornerShortPublicRule"] is True
    source["courseGeometry"]["publishedAt"] = "2026-10-24T12:01:00+09:00"
    result = public_pace_factors(source)
    assert result["firstCornerMetersOfficial"] is None
    assert result["firstCornerShortPublicRule"] is None
    source["courseGeometry"]["publishedAt"] = "2026-10-23T11:00:00+09:00"
    source["courseGeometry"]["sourceUrl"] = "https://unsafe.example/geometry"
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None


def test_retired_banei_and_jumps_are_not_cast_as_flat():
    import pytest
    for track, surface in (("帯広ば", "ダート"), ("園田", "障害"), ("帯広", "ばんえい")):
        source = race()
        source["track"], source["surface"] = track, surface
        with pytest.raises(ValueError, match="retired Banei"):
            public_pace_factors(source)


def test_four_phase_evidence_does_not_invent_race_positions():
    source = race()
    source["horses"][0]["recentRaces"][0]["cornerPositions"] = [2, 3, 4, 5]
    result = public_pace_factors(source)
    assert result["phaseOrder"] == ["start", "thirdCorner", "fourthCorner", "straight"]
    observed = result["horses"][0]["phaseEvidence"]
    assert observed["start"]["observedPosition"] is None
    assert observed["thirdCorner"]["observedPosition"] == 4
    assert observed["fourthCorner"]["observedPosition"] == 5
    assert observed["straight"]["observedFinish"] == 2
    # Two-corner race history cannot be mislabelled as 3C/4C evidence.
    missing = result["horses"][1]["phaseEvidence"]
    assert missing["thirdCorner"]["status"] == "unavailable"
    assert missing["fourthCorner"]["observedPosition"] is None
    assert result["predictedPaceProbabilities"] is None


def test_four_phase_baseline_uses_only_past_field_relative_positions():
    source = race()
    source["horses"][0]["recentRaces"][0]["cornerPositions"] = [2, 3, 4, 5]
    source["horses"][0]["recentRaces"].append({
        "date": "2026-10-18", "finish": 4, "fieldSize": 5,
        "cornerPositions": [1, 2, 2, 3], "distance": 1400
    })
    prediction = public_pace_factors(source)
    phases = prediction["horses"][0]["phaseProjection"]
    assert phases["start"]["projectedRank"] is None
    assert phases["thirdCorner"]["observedStarts"] == 2
    assert phases["thirdCorner"]["status"] == "historical-baseline-unvalidated"
    assert phases["thirdCorner"]["projectedRank"] == 2.17
    assert phases["fourthCorner"]["projectedRank"] == 2.89
    assert phases["straight"]["projectedRank"] == 2.72
    assert prediction["horses"][1]["phaseProjection"]["thirdCorner"]["projectedRank"] is None
    assert prediction["phaseProjectionKind"] == "historical-relative-rank-baseline-not-calibrated"


def test_four_phase_baseline_has_no_data_for_debutant():
    source = race()
    source["horses"][0]["recentRaces"] = []
    phases = public_pace_factors(source)["horses"][0]["phaseProjection"]
    assert all(phase["projectedRank"] is None for phase in phases.values())
