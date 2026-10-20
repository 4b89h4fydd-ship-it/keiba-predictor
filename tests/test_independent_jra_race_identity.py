from arvexq.components.runtime import composed_app_source
from pathlib import Path
import re
from bs4 import BeautifulSoup
from arvexq.ingest.jra_identifiers import _jra_date_from_cname,_jra_race_no_from_cname
from arvexq.ingest.race_fields.track import extract as venue
from arvexq.ingest.race_fields.title import extract as title
from arvexq.ingest.race_fields.field_size import extract as entrants

CNAME="pw01dde1005"+"0001"+"0002"+"11"+"20261018/AF"

def test_jra_race_date_identity():
    assert _jra_date_from_cname(CNAME)=="2026-10-18"
    assert _jra_date_from_cname("unknown")==""

def test_jra_race_number_identity():
    assert _jra_race_no_from_cname(CNAME)==11
    assert _jra_race_no_from_cname("unknown")==0

def test_venue_parser():
    assert venue(CNAME,{"05":"東京"})=="東京"
    assert venue(CNAME,{"04":"京都"})==""
    assert venue("unknown",{"05":"東京"})==""

def test_race_title_parser():
    soup=BeautifulSoup("<h2>出馬表</h2><h3>11レース</h3><h2>秋の試験賞</h2>","html.parser")
    assert title(soup,11,re.compile("禁止"))=="秋の試験賞"
    assert title(BeautifulSoup("<h2>出馬表</h2>","html.parser"),11,re.compile("禁止"))=="11R"

def test_actual_field_count_excludes_unknown_numbers():
    assert entrants([{"horseNumber":1},{"horseNumber":2},{"horseNumber":None}])==2
    assert entrants([])==0

def test_live_parser_delegates_to_source_fact_modules():
    source=composed_app_source()
    assert "return jra_race_track(cname,JRA_TRACK_CODES)" in source
    part=source.split("def _jra_parse_race(",1)[1].split("\ndef ",1)[0]
    assert "title=jra_race_title(soup,race_no,JRA_BAD_TITLE_RE)" in part
    assert '"fieldSize":jra_race_field_size(horses)' in part
    assert "date=_jra_date_from_cname(cname)" in part
    assert "race_no=_jra_race_no_from_cname(cname)" in part


def test_jra_date_rejects_impossible_calendar_values():
    assert _jra_date_from_cname(CNAME.replace("20261018", "20260230")) == ""
    assert _jra_date_from_cname(CNAME.replace("20261018", "20261318")) == ""
    assert _jra_date_from_cname(CNAME.replace("20261018", "20240229")) == "2024-02-29"


def test_jra_race_number_rejects_out_of_range_source_ids():
    assert _jra_race_no_from_cname(CNAME.replace("1120261018", "0020261018")) == 0
    assert _jra_race_no_from_cname(CNAME.replace("1120261018", "1320261018")) == 0
    assert _jra_race_no_from_cname(CNAME.replace("1120261018", "1220261018")) == 12


def test_observed_field_count_ignores_corrupt_and_duplicate_source_rows():
    rows = [
        {"horseNumber": 1}, {"horseNumber": "01"}, {"horseNumber": 2.0},
        {"horseNumber": "取消"}, {"horseNumber": None}, {"horseNumber": True},
        {"horseNumber": 1.5}, {"horseNumber": 0}, {"horseNumber": 19},
        {"horseNumber": float("nan")}, {"horseNumber": float("inf")},
        {"horseNumber": "2.0"}, None,
    ]
    assert entrants(rows) == 2
    assert entrants(None) == 0


def test_jra_date_and_race_number_component_ownership_preserves_legacy_imports():
    from arvexq.components.catalog import describe
    from arvexq.components.item_008.jra_date import _jra_date_from_cname as owned_date
    from arvexq.components.item_011.race_number import _jra_race_no_from_cname as owned_number
    assert _jra_date_from_cname is owned_date
    assert _jra_race_no_from_cname is owned_number
    assert describe(8)['circuits'] == ['JRA']
    assert describe(11)['circuits'] == ['JRA']
    assert owned_date(CNAME) == '2026-10-18'
    assert owned_number(CNAME) == 11


def test_jra_venue_parser_compatibility_import_is_owning_component():
    import importlib
    original=importlib.import_module("arvexq.ingest.race_fields.track")
    owned=importlib.import_module("arvexq.components.item_009.track")
    assert original is owned
    assert original.extract(CNAME, {"05":"東京"})=="東京"
    assert original.extract(CNAME, {"04":"京都"})==""
    assert original.extract("invalid", {"05":"東京"})==""
