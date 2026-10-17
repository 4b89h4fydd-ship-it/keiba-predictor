from arvexq.pipeline.race_clock import _race_minutes_server

def test_race_clock():
    assert _race_minutes_server({"startTime":"15:30"}) == 930
    assert _race_minutes_server({"scheduledStartTime":"09:45"}) == 585
    assert _race_minutes_server({}) == 9999
