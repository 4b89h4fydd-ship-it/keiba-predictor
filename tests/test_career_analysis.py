from arvexq.career_analysis import analyze_career


def _run(i, **kw):
    base = {
        "date": f"2026-01-{i:02d}",
        "distance": 1600,
        "course_type": "turf",
        "track_condition": "good",
        "finish_position": (i % 6) + 1,
        "field_size": 12,
        "running_style": "front",
    }
    base.update(kw)
    return base


def test_analyzes_all_runs_beyond_recent_window():
    runs = [_run(i) for i in range(1, 9)]
    result = analyze_career(runs)
    assert result["total_runs"] == 8
    assert result["analyzed_runs"] == 8
    assert len(result["recent_runs"]) == 5


def test_missing_fields_are_flagged_not_invented():
    runs = [_run(1), _run(2, track_condition=None)]
    result = analyze_career(runs)
    assert "track_condition" in result["missing_fields"]
    assert result["data_limitation"] == "partial"


def test_empty_input_is_safe():
    result = analyze_career([])
    assert result["total_runs"] == 0
    assert result["data_limitation"] == "no_runs"
