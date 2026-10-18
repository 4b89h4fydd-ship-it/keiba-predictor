from scripts.arvexq_jra_weather_readback import verify


def test_observed_jra_weather_is_valid():
    result = verify({"date": "2026-10-17", "races": [{"id": "jra-a"}],
                     "details": [{"id": "jra-a", "weather": "晴"}],
                     "readErrors": []})
    assert result["ok"] and result["valid"] == 1


def test_missing_weather_is_not_inferred():
    result = verify({"date": "2026-10-17", "races": [{"id": "jra-a"}],
                     "details": [{"id": "jra-a", "condition": "良"}],
                     "readErrors": []})
    assert not result["ok"] and len(result["missingOrInvalid"]) == 1
