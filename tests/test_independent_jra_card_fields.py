from arvexq.ingest.race_fields import start_time,course,distance,surface,prize
def test_independent_jra_card_fields():
    text="発走時刻：15時40分 コース：2,000メートル（芝・右） 1着 1200"
    assert start_time.extract(text)=="15:40"
    assert course.extract(text)==("芝・右",2000)
    assert distance.extract(text)==2000
    assert surface.extract(text)=="芝"
    assert prize.extract_first_prize(text)==12000000
    assert start_time.extract("発走時刻：25時99分")==""
    assert distance.extract("未発表")==0
    assert surface.extract("未発表")==""
