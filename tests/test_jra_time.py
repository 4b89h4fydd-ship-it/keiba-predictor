from arvexq.ingest.jra_time import _jra_iso_date, _jra_parse_time_seconds

def test_jra_calendar_and_clock():
    assert _jra_iso_date(2026,10,17) == "2026-10-17"
    assert _jra_parse_time_seconds("1:34.5") == 94.5
    assert _jra_parse_time_seconds("unknown") == 0.0
