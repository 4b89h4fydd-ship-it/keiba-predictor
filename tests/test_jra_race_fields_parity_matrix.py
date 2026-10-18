"""Regression matrix for the five independent JRA official race-card facts.

Keep observed values distinct from unknown ones; no odds/prediction fallbacks.
"""
import pytest

from arvexq.ingest.race_fields.start_time import extract as start_time
from arvexq.ingest.race_fields.course import extract as course
from arvexq.ingest.race_fields.distance import extract as distance
from arvexq.ingest.race_fields.surface import extract as surface
from arvexq.ingest.race_fields.prize import extract_first_prize as first_prize


@pytest.mark.parametrize(
    "text, expected",
    [
        ("発走時刻：09時05分", "09:05"),
        ("発走時刻：15時40分", "15:40"),
        ("発走時刻：23時59分", "23:59"),
        ("発走時刻：24時00分", ""),
        ("発走時刻：12時60分", ""),
        ("発走時刻：未定", ""),
        ("", ""),
    ],
)
def test_official_post_time_boundaries(text, expected):
    assert start_time(text) == expected


@pytest.mark.parametrize(
    "text, expected_course, expected_distance, expected_surface",
    [
        ("コース：1,200メートル（芝・右）", "芝・右", 1200, "芝"),
        ("コース：1,800メートル（ダート・左）", "ダート・左", 1800, "ダート"),
        ("コース：3,000メートル（障害）", "障害", 3000, "障害"),
        ("コース未発表", "", 0, ""),
        ("", "", 0, ""),
    ],
)
def test_course_distance_surface_are_sourced_from_same_official_descriptor(
    text, expected_course, expected_distance, expected_surface
):
    assert course(text) == (expected_course, expected_distance)
    assert distance(text) == expected_distance
    assert surface(text) == expected_surface


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1着 1,200", 12000000),
        ("1着 5,000", 50000000),
        ("賞金未定", 0),
        ("", 0),
    ],
)
def test_first_place_purse_observed_only(text, expected):
    assert first_prize(text) == expected
