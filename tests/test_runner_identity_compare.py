"""Unit contract for independent runner identity comparison (item 39)."""
from arvexq.ingest.runner_identity_compare import compare_same_day_runner


def test_observed_name_collision_across_two_races():
    index = {}
    assert compare_same_day_runner(index, race_id="jra-2026-10-11-京都-02",
                                   horse_name="エールヴォル", horse_number=12) is None
    assert compare_same_day_runner(index, race_id="jra-2026-10-11-京都-02",
                                   horse_name="エールヴォル", horse_number=12) is None
    assert compare_same_day_runner(index, race_id="jra-2026-10-11-京都-05",
                                   horse_name="エールヴォル", horse_number=12) == {
        "raceId": "jra-2026-10-11-京都-05", "otherRaceId": "jra-2026-10-11-京都-02",
        "horseName": "エールヴォル", "horseNumber": 12,
        "error": "same runner name in multiple races on day"}
    assert index == {"エールヴォル": "jra-2026-10-11-京都-02"}


def test_missing_name_never_creates_fabricated_runner():
    index = {}
    assert compare_same_day_runner(index, race_id="race", horse_name=None, horse_number=1) is None
    assert compare_same_day_runner(index, race_id="race", horse_name="  ", horse_number=2) is None
    assert index == {}


def test_identity_comparison_does_not_modify_runner_record():
    index = {}
    horse = {"horseNumber": 1, "name": "実馬", "frameNumber": 9, "sex": ""}
    before = dict(horse)
    assert compare_same_day_runner(index, race_id="race-1",
                                   horse_name=horse["name"], horse_number=horse["horseNumber"]) is None
    assert horse == before
