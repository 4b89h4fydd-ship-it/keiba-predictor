from scripts.arvexq_nar_going_readback import verify


def test_standard_going_and_banei_moisture_are_valid_observations():
    result = verify({"date": "2026-10-17",
                     "races": [{"id": "nar-a"}, {"id": "nar-b"}],
                     "details": [{"id": "nar-a", "track": "門別", "condition": "良"},
                                 {"id": "nar-b", "track": "帯広ば", "condition": "不明",
                                  "goingMoisture": "1.0"}],
                     "readErrors": []})
    assert result["ok"] and result["valid"] == 2


def test_banei_moisture_is_not_inferred_from_unknown_condition():
    result = verify({"date": "2026-10-17", "races": [{"id": "nar-b"}],
                     "details": [{"id": "nar-b", "track": "帯広ば", "condition": "不明"}],
                     "readErrors": []})
    assert not result["ok"] and len(result["missingOrInvalid"]) == 1


def test_missing_nar_detail_is_failure():
    result = verify({"date": "2026-10-17", "races": [{"id": "nar-a"}],
                     "details": [], "readErrors": [{"raceId": "nar-a"}]})
    assert not result["ok"] and result["read"] == 0
