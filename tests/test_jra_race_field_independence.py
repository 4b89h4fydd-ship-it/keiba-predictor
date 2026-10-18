from arvexq.ingest.race_fields.start_time import extract as start
from arvexq.ingest.race_fields.course import extract as course
from arvexq.ingest.race_fields.distance import extract as distance
from arvexq.ingest.race_fields.surface import extract as surface
from arvexq.ingest.race_fields.prize import extract_first_prize as prize

def test_independent_official_jra_fields():
    s="発走時刻：15時40分 コース 1,600メートル（芝・右） 1着 2,000"
    assert start(s)=="15:40"
    assert course(s)==("芝・右",1600)
    assert distance(s)==1600
    assert surface(s)=="芝"
    assert prize(s)==20000000
    assert start("不明")==""
    assert distance("不明")==0
    assert surface("不明")==""
