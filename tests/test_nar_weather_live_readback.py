from scripts.arvexq_nar_weather_readback import verify


def test_nar_weather_all_observed():
    result = verify({"date": "2026-10-17", "races": [{"id": "nar-one"}],
                     "details": [{"id": "nar-one", "weather": "晴"}],
                     "readErrors": []})
    assert result["ok"] and result["valid"] == 1


def test_nar_weather_missing_not_inferred():
    result = verify({"date": "2026-10-17", "races": [{"id": "nar-one"}],
                     "details": [{"id": "nar-one", "condition": "良", "weather": "不明"}],
                     "readErrors": []})
    assert not result["ok"] and len(result["missingOrInvalid"]) == 1


def test_missing_nar_details_is_failure():
    result = verify({"date": "2026-10-17", "races": [{"id": "nar-one"}],
                     "details": [], "readErrors": [{"raceId": "nar-one"}]})
    assert not result["ok"] and result["read"] == 0


def test_no_nar_racing_day_not_false_success():
    result = verify({"date": "2026-10-17", "races": [{"id": "jra-one"}],
                     "details": [{"id": "jra-one", "weather": "晴"}], "readErrors": []})
    assert not result["ok"]
