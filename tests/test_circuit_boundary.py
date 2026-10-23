from arvexq.ingest.circuit_boundary import (
    compatible_with,
    preoff_records,
    require_compatible,
)


def test_central_parser_rejects_explicit_local_records_without_relabeling():
    assert compatible_with({"circuit": "地方", "track": "大井"}, "中央") is False
    try:
        require_compatible({"circuit": "地方", "track": "大井"}, "中央")
    except ValueError:
        pass
    else:
        raise AssertionError("contradictory circuit must be rejected")


def test_unknown_track_is_not_silently_assigned_to_local():
    assert compatible_with({"track": "未知場"}, "中央") is True
    assert compatible_with({"track": "未知場"}, "地方") is True


def test_preoff_records_are_strictly_before_cutoff_circuit_scoped_and_copied():
    source = [
        {"track": "東京", "date": "2026-10-22", "finish": 2},
        {"track": "東京", "date": "2026-10-23", "finish": 1},
        {"track": "大井", "date": "2026-10-22", "finish": 3},
        {"track": "東京", "date": "invalid", "finish": 4},
    ]
    result = preoff_records(source, "2026-10-23", circuit="中央")
    assert result == [source[0]]
    assert result[0] is not source[0]
    source[0]["finish"] = 99
    assert result[0]["finish"] == 2


def test_preoff_records_does_not_impute_missing_dates_or_fields():
    source = [{"track": "東京", "finish": None}, {"track": "東京", "date": "2026-10-22"}]
    assert preoff_records(source, "2026-10-23", circuit="中央") == [source[1]]

