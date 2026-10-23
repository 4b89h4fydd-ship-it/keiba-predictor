from arvexq.ingest.jra_identifiers import _jra_date_from_cname, _jra_race_no_from_cname

def test_jra_date_in_identifier():
    assert _jra_date_from_cname("test20261017/0A") == "2026-10-17"
    assert _jra_date_from_cname("invalid") == ""

def test_unrecognized_race_number():
    assert _jra_race_no_from_cname("invalid") == 0

from arvexq.ingest.race_fields.date import extract as independent_jra_day
from arvexq.ingest.race_fields.race_number import extract as independent_jra_number


def test_jra_date_and_race_number_have_independent_parsers():
    cname = "pw01dde1005" + "0001" + "0002" + "11" + "20261018/AF"
    assert independent_jra_day is _jra_date_from_cname
    assert independent_jra_number is _jra_race_no_from_cname
    assert independent_jra_day(cname) == "2026-10-18"
    assert independent_jra_number(cname) == 11
    assert independent_jra_day("20260229/AF") == ""
    assert independent_jra_number("20260229/AF") == 0
    assert independent_jra_day("test20240229/AF") == "2024-02-29"
    assert independent_jra_number("bad") == 0
