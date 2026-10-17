from arvexq.pipeline.race_priority import _race_minutes, _commercial_target_rows

def test_time_priority():
    assert _race_minutes({"startTime": "09:45"}) == 585
    assert _race_minutes({"startTime": "missing"}) == 9999

def test_race_queue_is_sorted_and_deduplicated():
    rows = [
        {"id":"a","track":"園田","raceNumber":1,"startTime":"10:00"},
        {"id":"b","track":"園田","raceNumber":2,"startTime":"10:20"},
        {"id":"a","track":"園田","raceNumber":1,"startTime":"10:00"},
    ]
    result = _commercial_target_rows(rows, 610)
    assert [r["id"] for r in result] == ["b","a"]
