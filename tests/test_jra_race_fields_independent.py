"""JRA official factual race-card fields, no reliance on betting UI."""
from pathlib import Path
from arvexq.ingest.race_fields.start_time import extract as post
from arvexq.ingest.race_fields.course import extract as course
from arvexq.ingest.race_fields.distance import extract as distance
from arvexq.ingest.race_fields.surface import extract as surface
from arvexq.ingest.race_fields.prize import extract_first_prize as prize
TEXT="東京11R 発走時刻：15時40分 コース：2,000メートル（芝・左回り） 1着 5,000"

def test_post_time():
    assert post(TEXT)=="15:40"
    assert post("発走時刻：25時40分")==""
    assert post("発走時刻：不明")==""

def test_course():
    assert course(TEXT)==("芝・左回り",2000)
    assert course("未発表")==("",0)

def test_trip():
    assert distance(TEXT)==2000
    assert distance("未取得")==0

def test_surface():
    assert surface(TEXT)=="芝"
    assert surface("コース：1,800メートル（ダート・右回り）")=="ダート"
    assert surface("コース：3,000メートル（障害）")=="障害"
    assert surface("未取得")==""

def test_first_prize():
    assert prize(TEXT)==50000000
    assert prize("賞金未発表")==0

def test_jra_official_parser_uses_all_independent_extractors():
    src=Path("app.py").read_text()
    segment=src.split("def _jra_parse_race(",1)[1].split("\ndef ",1)[0]
    for phrase in ("jra_start_time(full)","jra_course(full)","jra_distance(full)",
                   "jra_surface(full)","jra_first_prize(full)"):
        assert phrase in segment
