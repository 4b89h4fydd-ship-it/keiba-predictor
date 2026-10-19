"""Independent JRA historical field contracts and the real production composition."""
from arvexq.components.runtime import composed_app_source
from pathlib import Path
from bs4 import BeautifulSoup
from arvexq.ingest.past_fields.date import extract_date
from arvexq.ingest.past_fields.track import extract_track
from arvexq.ingest.past_fields.distance import extract_distance,extract_surface
from arvexq.ingest.past_fields.going import extract_going
from arvexq.ingest.past_fields.finish import extract_finish
from arvexq.ingest.past_fields.clock import extract_time_seconds
from arvexq.ingest.past_fields.margin import extract_margin_seconds
from arvexq.ingest.past_fields.corners import extract_corners
from arvexq.ingest.past_fields.carried_weight import extract_carried_weight
from arvexq.ingest.past_fields.field_size import extract_field_size
from arvexq.ingest.past_fields.jockey import extract_jockey
from arvexq.ingest.past_fields.last3f import extract_last3f_seconds
from arvexq.ingest.past_fields.grade import extract_class
from arvexq.ingest.past_fields.jra import parse_jra_history_cell

TEXT="2026年10月1日 大井 1勝クラス 4着 14頭 1800ダ 良 57kg 1:51.2 3F 36.2 対戦馬(0.3) 騎手：山田"

def test_date_field():
    assert extract_date(TEXT)=="2026-10-01"
    assert extract_date("日付取得待ち") is None

def test_track_field():
    assert extract_track(TEXT,["東京","大井"])=="大井"
    assert extract_track("開催場不明",["東京"])==""

def test_distance_field():
    assert extract_distance(TEXT)==1800
    assert extract_distance("距離未取得")==0

def test_surface_field():
    assert extract_surface(TEXT)=="ダ"
    assert extract_surface("距離未取得")==""

def test_going_field():
    assert extract_going(TEXT)=="良"
    assert extract_going("馬場未取得")=="不明"

def test_finish_field():
    assert extract_finish(TEXT)==4
    assert extract_finish("除外") == 0

def test_clock_field():
    assert extract_time_seconds(TEXT)==111.2
    assert extract_time_seconds("時計なし")==0.0

def test_margin_field():
    assert extract_margin_seconds(TEXT,4)==0.3
    assert extract_margin_seconds(TEXT,1)==0.0
    assert extract_margin_seconds("着順 4(5) 頭数 14",4) is None

def test_corners_field():
    cell=BeautifulSoup("<td><li>3</li><li>7</li><li>不明</li></td>","html.parser")
    assert extract_corners(cell)==[3,7]

def test_carried_weight_field():
    assert extract_carried_weight(TEXT)==57.0
    assert extract_carried_weight("測定前")==0.0

def test_field_size_field():
    assert extract_field_size(TEXT)==14
    assert extract_field_size("頭数取得待ち")==0

def test_grade_field():
    assert extract_class(TEXT)=="1勝クラス"
    assert extract_class("開催予定") is None

def test_last3f_field():
    assert extract_last3f_seconds(TEXT)==36.2
    assert extract_last3f_seconds("上がり未掲載") is None

def test_jockey_field():
    assert extract_jockey(TEXT)=="山田"
    assert extract_jockey("関係者未掲載") is None

def test_actual_jra_cell_calls_independent_parsers():
    cell=BeautifulSoup("<td>"+TEXT+"<ul><li>3</li><li>7</li></ul></td>","html.parser")
    row=parse_jra_history_cell(cell,"2026-10-07",["東京","大井"],"jra-result-test")
    assert row["date"]=="2026-10-01"
    assert row["finish"]==4 and row["fieldSize"]==14
    assert row["cornerPositions"]==[3,7]
    assert row["jockey"]=="山田" and row["last3FSeconds"]==36.2
    assert row["raceId"]=="jra-result-test"
    assert parse_jra_history_cell(cell,"2026-10-01",["東京","大井"]) is None
    assert "parse_jra_history_cell(cell,cutoff,tracks,race_id=rid)" in composed_app_source()
