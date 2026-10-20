"""Independent meeting calendar context from JRA official headings."""
from arvexq.components.runtime import composed_app_source
import re
from pathlib import Path
from bs4 import BeautifulSoup
from arvexq.ingest.race_fields.meeting_schedule import extract

MEETING = re.compile(r"(\d+)回(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)(\d+)日")

def test_meeting_calendar_context():
    soup=BeautifulSoup("<h2>4回東京3日</h2><table><tr><th>レース番号</th></tr></table>","html.parser")
    assert extract(soup.table,MEETING)==(4,"東京",3)

def test_missing_calendar_context_is_unknown():
    soup=BeautifulSoup("<h2>番組表</h2><table></table>","html.parser")
    assert extract(soup.table,MEETING)==(0,"",0)

def test_official_calendar_uses_extractor():
    source=composed_app_source()
    segment=source.split("def _jra_program_summaries(",1)[1].split("\ndef ",1)[0]
    assert "jra_meeting_schedule(table,JRA_MEETING_DAY_RE,_jra_text)" in segment


def test_jra_schedule_parser_compatibility_import_is_owning_component():
    import importlib
    original=importlib.import_module("arvexq.ingest.race_fields.meeting_schedule")
    owned=importlib.import_module("arvexq.components.item_010.meeting_schedule")
    assert original is owned
    soup=BeautifulSoup("<h2>4回東京3日</h2><table></table>", "html.parser")
    assert original.extract(soup.table, MEETING)==(4,"東京",3)
    missing=BeautifulSoup("<h2>番組表</h2><table></table>", "html.parser")
    assert original.extract(missing.table, MEETING)==(0,"",0)
