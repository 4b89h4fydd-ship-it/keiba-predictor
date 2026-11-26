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


def _netkeiba_geometry(**overrides):
    record = {
        "sourceKind": "netkeiba_course_analysis", "sourcePublishedBeforeOff": True,
        "sourceUrl": "https://nar.sp.netkeiba.com/racecourse/course_analytics.html"
                     "?id=50&dist=1400&track=2",
        "track": "園田", "surface": "ダート", "distance": 1400,
        "firstCornerDistanceMeters": 377,
        "publishedAt": "2026-10-23T11:00:00+09:00",
    }
    record.update(overrides)
    return record


def test_netkeiba_course_analysis_geometry_is_accepted():
    source = race()
    source["courseGeometry"] = _netkeiba_geometry()
    result = public_pace_factors(source)
    assert result["firstCornerMetersOfficial"] == 377
    assert result["firstCornerShortPublicRule"] is False
    source["courseGeometry"] = _netkeiba_geometry(firstCornerDistanceMeters=250)
    result = public_pace_factors(source)
    assert result["firstCornerMetersOfficial"] == 250
    assert result["firstCornerShortPublicRule"] is True


def test_netkeiba_geometry_rejects_wrong_host_and_kind_host_mismatch():
    source = race()
    # A host outside the netkeiba set cannot attest the netkeiba kind.
    source["courseGeometry"] = _netkeiba_geometry(
        sourceUrl="https://unsafe.example/geometry")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    # An official host cannot attest the netkeiba kind.
    source["courseGeometry"] = _netkeiba_geometry(
        sourceUrl="https://www.keiba.go.jp/track/sonoda")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    # A netkeiba host cannot attest the official kind (official stays strict).
    source["courseGeometry"] = _netkeiba_geometry(
        sourceKind="official_course_geometry")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None


def test_netkeiba_geometry_rejects_mismatch_and_post_off():
    source = race()
    source["courseGeometry"] = _netkeiba_geometry(distance=1234)
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    source["courseGeometry"] = _netkeiba_geometry(track="姫路")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    source["courseGeometry"] = _netkeiba_geometry(surface="芝")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    source["courseGeometry"] = _netkeiba_geometry(
        publishedAt="2026-10-24T12:01:00+09:00")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    source["courseGeometry"] = _netkeiba_geometry(sourcePublishedBeforeOff=False)
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None


def jra_race():
    source = race()
    source.update({
        "id": "jra-2026-10-24-東京-11", "circuit": "中央",
        "track": "東京", "surface": "芝", "distance": 2400,
    })
    return source


def _jravan_geometry(**overrides):
    record = {
        "sourceKind": "jravan_course_guide", "sourcePublishedBeforeOff": True,
        "sourceUrl": "https://sugo.jra-van.jp/sugotoku/crs/crs05t2400.html",
        "track": "東京", "surface": "芝", "distance": 2400,
        "firstCornerDistanceMeters": 350,
        "publishedAt": "2026-10-23T11:00:00+09:00",
    }
    record.update(overrides)
    return record


def test_jravan_course_guide_geometry_is_accepted():
    source = jra_race()
    source["courseGeometry"] = _jravan_geometry()
    result = public_pace_factors(source)
    assert result["firstCornerMetersOfficial"] == 350
    assert result["firstCornerShortPublicRule"] is False
    source["courseGeometry"] = _jravan_geometry(firstCornerDistanceMeters=250)
    result = public_pace_factors(source)
    assert result["firstCornerMetersOfficial"] == 250
    assert result["firstCornerShortPublicRule"] is True


def test_jravan_geometry_rejects_wrong_host_and_kind_host_mismatch():
    source = jra_race()
    # A host outside the JRA-VAN set cannot attest the JRA-VAN kind.
    source["courseGeometry"] = _jravan_geometry(
        sourceUrl="https://unsafe.example/geometry")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    # An official host cannot attest the JRA-VAN kind.
    source["courseGeometry"] = _jravan_geometry(
        sourceUrl="https://www.jra.go.jp/keiba/race/102.html")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    # A netkeiba host cannot attest the JRA-VAN kind.
    source["courseGeometry"] = _jravan_geometry(
        sourceUrl="https://nar.sp.netkeiba.com/racecourse/course_analytics.html")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    # The JRA-VAN host cannot attest the official kind (official stays strict).
    source["courseGeometry"] = _jravan_geometry(
        sourceKind="official_course_geometry")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    # The JRA-VAN host cannot attest the netkeiba kind either.
    source["courseGeometry"] = _jravan_geometry(
        sourceKind="netkeiba_course_analysis")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None


def test_jravan_geometry_rejects_mismatch_and_post_off():
    source = jra_race()
    source["courseGeometry"] = _jravan_geometry(distance=1234)
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    source["courseGeometry"] = _jravan_geometry(track="中山")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    source["courseGeometry"] = _jravan_geometry(surface="ダート")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    source["courseGeometry"] = _jravan_geometry(
        publishedAt="2026-10-24T12:01:00+09:00")
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None
    source["courseGeometry"] = _jravan_geometry(sourcePublishedBeforeOff=False)
    assert public_pace_factors(source)["firstCornerMetersOfficial"] is None


def test_retired_banei_and_jumps_are_not_cast_as_flat():
    import pytest
    for track, surface in (("帯広ば", "ダート"), ("園田", "障害"), ("帯広", "ばんえい")):
        source = race()
        source["track"], source["surface"] = track, surface
        with pytest.raises(ValueError, match="retired Banei"):
            public_pace_factors(source)
