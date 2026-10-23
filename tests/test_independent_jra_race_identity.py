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
    assert _jra_date_from_cname("test20260229/0A")==""
    assert _jra_date_from_cname("test20261315/0A")==""
    assert _jra_date_from_cname("test20240229/0A")=="2024-02-29"

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
    source=Path("app.py").read_text()
    assert "return jra_race_track(cname,JRA_TRACK_CODES)" in source
    part=source.split("def _jra_parse_race(",1)[1].split("\ndef ",1)[0]
    assert "title=jra_race_title(soup,race_no,JRA_BAD_TITLE_RE)" in part
    assert '"fieldSize":jra_race_field_size(horses)' in part
    assert "date=_jra_date_from_cname(cname)" in part
    assert "race_no=_jra_race_no_from_cname(cname)" in part
