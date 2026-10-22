"""#13 Observed JRA grade/class: source-only field contracts."""
from stage4_source_support import implementation_source
from pathlib import Path
from arvexq.ingest.race_fields.grade_class import extract

def test_official_grade_and_class():
    assert extract("第21回秋華賞 GⅠ 3歳オープン")==("G1","オープン")
    assert extract("レース JpnⅡ 3勝クラス")==("Jpn2","3勝クラス")
    assert extract("3歳未勝利")==("","未勝利")
    assert extract("2歳新馬")==("","新馬")
    assert extract("未掲載")==("","")

def test_real_parser_paths_call_extract():
    source=implementation_source()
    for func,following in (("_jra_program_summaries","_jra_program_lookup"),("_jra_parse_race(","_jra_parse_race_summary("),("_jra_parse_race_summary(","fetch_jra_official(")):
        segment=source.split("def "+func,1)[1].split("def "+following,1)[0]
        assert "jra_grade_class(" in segment
        assert '"raceGrade":race_grade,"raceClass":race_class' in segment
