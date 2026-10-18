from scripts.arvexq_nar_scratches_readback import verify


def test_empty_and_observed_scratch_maps_are_valid():
    result = verify({"date": "2026-10-17",
                     "races": [{"id": "nar-a"}, {"id": "nar-b"}],
                     "details": [{"id": "nar-a", "scratchMap": {}},
                                 {"id": "nar-b", "scratchMap": {7: "除外"}}],
                     "readErrors": []})
    assert result["ok"] and result["valid"] == 2


def test_invalid_scratch_status_fails_closed():
    result = verify({"date": "2026-10-17", "races": [{"id": "nar-a"}],
                     "details": [{"id": "nar-a", "scratchMap": {19: "取消"}}],
                     "readErrors": []})
    assert not result["ok"] and len(result["invalid"]) == 1
