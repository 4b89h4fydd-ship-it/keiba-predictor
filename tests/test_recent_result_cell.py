from arvexq.ingest.recent_result_cell import _parse_recent_cell

def test_empty_recent_race():
    assert _parse_recent_cell("") is None

def test_recent_race_cell():
    text="2026/10/01 園田 3 秋の特別 ダ1400 12頭 1:29.5 良 55.0 2-2-1"
    result=_parse_recent_cell(text)
    assert result is not None
    assert result["track"]=="園田"
    assert result["distance"]==1400
    assert result["surface"]=="ダート"
