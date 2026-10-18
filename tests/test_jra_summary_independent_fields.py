from pathlib import Path
from arvexq.ingest.race_fields.start_time import extract as start
from arvexq.ingest.race_fields.distance import extract as distance
from arvexq.ingest.race_fields.surface import extract as surface
from arvexq.ingest.race_fields.title import extract as title
from bs4 import BeautifulSoup
import re

def test_summary_uses_same_independent_extractors_as_detail():
    source=Path("app.py").read_text()
    summary=source.split("def _jra_parse_race_summary(",1)[1].split("\ndef ",1)[0]
    detail=source.split("def _jra_parse_race(",1)[1].split("\ndef ",1)[0]
    for expression in ("jra_start_time(full)","jra_distance(full)","jra_surface(full)","jra_race_title(soup,race_no,JRA_BAD_TITLE_RE)"):
        assert expression in summary
        assert expression in detail

def test_date_and_course_values_are_not_synthetic():
    observation="発走時刻：15時35分 コース：1,800メートル（ダート・右）"
    assert start(observation)=="15:35"
    assert distance(observation)==1800
    assert surface(observation)=="ダート"
    assert distance("コース情報未掲載")==0
    soup=BeautifulSoup("<h2>3歳未勝利</h2>","html.parser")
    assert title(soup,4,re.compile("出走表"))=="3歳未勝利"
