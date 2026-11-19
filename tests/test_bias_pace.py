"""Same-day bias read + netkeiba pace-forecast overlay
(rewrite/analysis/bias_pace.py).

The bias definition is the one fixed by the 2026-11-16 validation:
same-day / same-track earlier races only, FB = front vs closer
top-3 rate difference by first-corner position ratio, IO = inner
vs outer top-3 rate difference by horse-number ratio, shrinkage
w = S / (S + 2), no source races -> exactly neutral. These tests
pin the direction of both biases on dummy same-day results, the
neutral behaviour when there is nothing to read, the 80%
first-corner coverage gate on source races, and the leak guards
(later races / other tracks / other dates / the target itself
never feed its own bias). The overlay tests pin that a front bias
lifts the forecast front-runners and drops the forecast closers,
and that a neutral bias moves nothing.
"""
import pytest

from rewrite.analysis.bias_pace import (
    bias_adjusted_pace,
    compute_same_day_bias,
    overlay_bias_on_pace,
    pace_positions_from_forecast,
)


def _fin(number, finish, corner1=None):
    corners = [corner1] if corner1 is not None else []
    return {"horseNumber": number, "finish": finish,
            "cornerPositions": corners}


def _race(no, finishers, date="2026-11-19", track="大井", start=None):
    race = {"date": date, "track": track, "raceNo": no,
            "finishers": finishers}
    if start is not None:
        race["startTime"] = start
    return race


def _front_race(no):
    """10 runners: the first-corner front group (1-3) sweeps the
    top 3, the back group (8-10) finishes out of the frame."""
    return _race(no, [
        _fin(1, 1, 1), _fin(2, 2, 2), _fin(3, 3, 3),
        _fin(4, 5, 4), _fin(5, 6, 5), _fin(6, 7, 6),
        _fin(7, 8, 7), _fin(8, 4, 8), _fin(9, 9, 9),
        _fin(10, 10, 10),
    ])


def _inside_race(no):
    """10 runners: inner numbers (1-3) sweep the top 3 from
    mid-pack first corners, while the first-corner front group
    (1-3) and back group (7-10) both place none in the top 3 —
    IO strongly positive, FB exactly zero."""
    return _race(no, [
        _fin(1, 1, 4), _fin(2, 2, 5), _fin(3, 3, 6),
        _fin(4, 4, 1), _fin(5, 5, 2), _fin(6, 6, 3),
        _fin(7, 7, 7), _fin(8, 8, 8), _fin(9, 9, 9),
        _fin(10, 10, 10),
    ])


# ------------------------------------------------------------------
# Bias direction
# ------------------------------------------------------------------

def test_front_bias_positive():
    target = _race(5, [])
    bias = compute_same_day_bias(target, [_front_race(1)])
    assert bias["available"] is True
    assert bias["sampleRaces"] == 1
    assert bias["sourceRaceNos"] == [1]
    # raw FB = 1.0 - 0.0, shrunk by w = 1/3
    assert bias["rawFrontBack"] == 1.0
    assert bias["strength"] == 1 / 3
    assert bias["frontBack"] == 1.0 / 3


def test_inside_bias_positive_front_neutral():
    target = _race(5, [])
    bias = compute_same_day_bias(target, [_inside_race(1)])
    assert bias["rawInsideOutside"] == 1.0
    assert bias["insideOutside"] == 1.0 / 3
    assert bias["rawFrontBack"] == 0.0
    assert bias["frontBack"] == 0.0


def test_shrinkage_grows_with_more_source_races():
    target = _race(6, [])
    bias = compute_same_day_bias(
        target, [_front_race(1), _front_race(2)])
    assert bias["sampleRaces"] == 2
    assert bias["strength"] == 0.5
    assert bias["frontBack"] == 0.5


def test_empty_group_difference_is_unmeasurable_not_zero():
    # A 2-runner source race has no front group at all: the raw
    # differences are None and the shrunk biases fall back to 0.
    tiny = _race(1, [_fin(1, 1, 1), _fin(2, 2, 2)])
    bias = compute_same_day_bias(_race(5, []), [tiny])
    assert bias["available"] is True
    assert bias["rawFrontBack"] is None
    assert bias["rawInsideOutside"] is None
    assert bias["frontBack"] == 0.0
    assert bias["insideOutside"] == 0.0


# ------------------------------------------------------------------
# Neutral when there is nothing to read
# ------------------------------------------------------------------

def test_no_earlier_races_is_neutral():
    bias = compute_same_day_bias(_race(1, []), [_front_race(2)])
    assert bias["available"] is False
    assert bias["status"] == "no-source-races"
    assert bias["frontBack"] == 0.0
    assert bias["insideOutside"] == 0.0
    assert bias["rawFrontBack"] is None
    assert bias["sampleRaces"] == 0
    assert bias["strength"] == 0.0


def test_no_corner_positions_anywhere_is_neutral():
    # The production reality until cornerPositions lands in the
    # result feed: finishers carry an empty list.
    bare = _race(1, [{"horseNumber": n, "finish": n,
                      "cornerPositions": []} for n in range(1, 11)])
    bias = compute_same_day_bias(_race(5, []), [bare])
    assert bias["available"] is False
    assert bias["frontBack"] == 0.0


def test_source_race_under_coverage_gate_is_skipped():
    # 7 of 10 finishers carry a first-corner position (70% < 80%).
    partial = _race(1, [
        _fin(1, 1, 1), _fin(2, 2, 2), _fin(3, 3, 3), _fin(4, 4, 4),
        _fin(5, 5, 5), _fin(6, 6, 6), _fin(7, 7, 7),
        _fin(8, 8), _fin(9, 9), _fin(10, 10),
    ])
    bias = compute_same_day_bias(_race(5, []), [partial])
    assert bias["available"] is False


def test_source_race_at_coverage_gate_is_used():
    # Exactly 80% coverage qualifies.
    gated = _race(1, [
        _fin(1, 1, 1), _fin(2, 2, 2), _fin(3, 3, 3), _fin(4, 4, 4),
        _fin(5, 5, 5), _fin(6, 6, 6), _fin(7, 7, 7), _fin(8, 8, 8),
        _fin(9, 9), _fin(10, 10),
    ])
    bias = compute_same_day_bias(_race(5, []), [gated])
    assert bias["available"] is True
    assert bias["sampleRaces"] == 1


# ------------------------------------------------------------------
# Leak guards
# ------------------------------------------------------------------

def test_later_race_never_feeds_the_bias():
    target = _race(3, [])
    bias = compute_same_day_bias(
        target, [_front_race(1), _front_race(9)])
    assert bias["sourceRaceNos"] == [1]
    assert bias["sampleRaces"] == 1


def test_target_race_itself_is_excluded():
    target = _front_race(3)
    bias = compute_same_day_bias(target, [target, _front_race(1)])
    assert bias["sourceRaceNos"] == [1]


def test_other_track_and_other_date_are_excluded():
    other_track = _front_race(1)
    other_track["track"] = "園田"
    other_date = _front_race(2)
    other_date["date"] = "2026-11-18"
    bias = compute_same_day_bias(
        _race(5, []), [other_track, other_date])
    assert bias["available"] is False


def test_start_time_ordering_beats_race_number():
    # Race 1 by number but starting after the target: not a source.
    late = _front_race(1)
    late["startTime"] = "16:00"
    target = _race(5, [], start="15:00")
    bias = compute_same_day_bias(target, [late])
    assert bias["available"] is False
    early = _front_race(9)
    early["startTime"] = "14:00"
    bias = compute_same_day_bias(target, [early])
    assert bias["available"] is True


# ------------------------------------------------------------------
# Pace-forecast positions (builder convention)
# ------------------------------------------------------------------

def test_pace_positions_rank_and_pct():
    entry = {
        "pace": "H",
        "n_runners": 4,
        "positions": {
            "start": [[9], [6, 2], [4]],
            "corner4": [[2], [9], [6], [4]],
        },
    }
    positions = pace_positions_from_forecast(entry)
    assert positions[9]["start"] == {"rank": 1, "pct": 0.25}
    assert positions[6]["start"] == {"rank": 2, "pct": 0.5}
    assert positions[2]["start"] == {"rank": 3, "pct": 0.75}
    assert positions[4]["start"] == {"rank": 4, "pct": 1.0}
    assert positions[2]["corner4"] == {"rank": 1, "pct": 0.25}
    assert "corner3" not in positions[9]


# ------------------------------------------------------------------
# Overlay
# ------------------------------------------------------------------

def _positions(front_pct, back_pct):
    def cell(pct):
        return {"rank": 1, "pct": pct}
    return {
        1: {"start": cell(front_pct), "corner3": cell(front_pct),
            "corner4": cell(front_pct)},
        10: {"start": cell(back_pct), "corner3": cell(back_pct),
             "corner4": cell(back_pct)},
    }


def test_overlay_front_bias_lifts_front_runner():
    bias = compute_same_day_bias(_race(5, []), [_front_race(1)])
    overlay = overlay_bias_on_pace(bias, _positions(0.1, 0.9),
                                   field_size=10)
    front = overlay["horses"][1]
    back = overlay["horses"][10]
    # frontness +0.8 / -0.8 against FB = 1/3; frame +1 / -1
    # against IO = 1/3 (the dummy race is inner-biased too).
    assert front["frontness"] == pytest.approx(0.8)
    assert front["frontBackComponent"] == pytest.approx((1 / 3) * 0.8)
    assert front["insideOutsideComponent"] == pytest.approx(1 / 3)
    assert front["adjustment"] > 0
    assert back["adjustment"] < 0
    assert overlay["summary"]["frontBackTendency"] == "front"
    assert overlay["summary"]["insideOutsideTendency"] == "inside"
    assert "front-favourable" in overlay["summary"]["tags"]
    assert overlay["summary"]["mostAdvantaged"][0] == 1
    assert overlay["summary"]["mostDisadvantaged"][0] == 10


def test_overlay_neutral_bias_moves_nothing():
    bias = compute_same_day_bias(_race(1, []), [])
    overlay = overlay_bias_on_pace(bias, _positions(0.1, 0.9),
                                   field_size=10)
    assert overlay["available"] is False
    assert overlay["horses"][1]["adjustment"] == 0.0
    assert overlay["horses"][10]["adjustment"] == 0.0
    assert overlay["summary"]["tags"] == ["no-bias"]
    assert overlay["summary"]["frontBackTendency"] == "neutral"


def test_overlay_horse_without_position_gets_no_adjustment():
    bias = compute_same_day_bias(_race(5, []), [_front_race(1)])
    overlay = overlay_bias_on_pace(
        bias, {3: {"start": {"rank": 2, "pct": 0.2}}, 7: {}},
        field_size=10)
    assert overlay["horses"][3]["adjustment"] is not None
    assert overlay["horses"][7]["adjustment"] is None
    assert overlay["horses"][7]["frontness"] is None


def test_bias_adjusted_pace_end_to_end():
    entry = {
        "pace": "H",
        "n_runners": 10,
        "positions": {
            "start": [[1], [5], [10]],
            "corner3": [[1], [5], [10]],
            "corner4": [[1], [5], [10]],
        },
    }
    result = bias_adjusted_pace(
        _race(5, []), [_front_race(1)], entry)
    assert result["bias"]["available"] is True
    horses = result["overlay"]["horses"]
    assert horses[1]["adjustment"] > horses[5]["adjustment"]
    assert horses[5]["adjustment"] > horses[10]["adjustment"]
