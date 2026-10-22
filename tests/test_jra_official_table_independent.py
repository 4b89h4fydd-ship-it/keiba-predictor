"""Official JRA card table selector contracts."""
from stage4_source_support import implementation_source
from pathlib import Path
from bs4 import BeautifulSoup
from arvexq.ingest.jra_official_table import select_runners_table

def test_select_only_observed_runner_table():
    html="<table><thead><tr><th>結果</th></tr></thead></table><table><thead><tr><th>馬番</th><th>前走</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>"
    soup=BeautifulSoup(html,"html.parser")
    assert select_runners_table(soup) is soup.find_all("table")[1]

def test_missing_runner_table_is_none():
    soup=BeautifulSoup("<table><tr><th>賞金</th></tr></table>","html.parser")
    assert select_runners_table(soup) is None

def test_detail_parser_uses_selector():
    source=implementation_source()
    detail=source.split("def _jra_parse_race(",1)[1].split("def _jra_parse_race_summary(",1)[0]
    assert "target_table=select_jra_runners_table(soup)" in detail
