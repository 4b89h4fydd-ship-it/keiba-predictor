from arvexq.ingest.jra_identifiers import _jra_date_from_cname, _jra_race_no_from_cname

def test_jra_date_in_identifier():
    assert _jra_date_from_cname("test20261017/0A") == "2026-10-17"
    assert _jra_date_from_cname("invalid") == ""

def test_unrecognized_race_number():
    assert _jra_race_no_from_cname("invalid") == 0
