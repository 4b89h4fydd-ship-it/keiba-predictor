"""Official NAR odds parsing is independent from networking, JRA and forecasts."""
from pathlib import Path

from arvexq.ingest.odds_fields.nar_official import _parse_nar_live_odds_html


def test_nar_header_observations_are_preserved_but_popularity_tracks_final_odds():
    html = """<table><tr><th>馬番</th><th>単勝</th><th>人気</th><th>馬体重</th></tr>
    <tr><td>1</td><td>3.3</td><td>1</td><td>480 (+4)</td></tr>
    <tr><td>2</td><td>2.1</td><td>2</td><td>未発表</td></tr></table>"""
    odds = _parse_nar_live_odds_html(html)
    assert odds[1]["winOdds"] == 3.3
    assert odds[1]["bodyWeight"] == 480
    assert odds[1]["bodyWeightChange"] == 4
    assert odds[1]["popularity"] == 2
    assert odds[2]["winOdds"] == 2.1
    assert odds[2]["popularity"] == 1
    assert odds[2]["bodyWeight"] is None


def test_nar_flat_row_keeps_place_odds_distinct_from_win_odds():
    html = """<table><tr><td>1</td><td>2</td><td>観測馬</td>
    <td>4.2</td><td>1.2</td><td>2.4</td><td>牡3</td><td>488 (+0)</td></tr></table>"""
    odds = _parse_nar_live_odds_html(html)
    assert odds[2]["winOdds"] == 4.2
    assert odds[2]["placeOddsLow"] == 1.2
    assert odds[2]["placeOddsHigh"] == 2.4
    assert odds[2]["bodyWeight"] == 488
    assert odds[2]["bodyWeightChange"] == 0


def test_nar_live_layout_split_place_cells_are_observed():
    # Verbatim shape of the live OddsTanFuku page (2026-11-04 Sonoda 4R,
    # fetched 10:55 JST while on sale): the place header spans two
    # columns and each body row carries the range as "3.5-" | "7.8".
    html = """<table><tr><th>枠</th><th>馬番</th><th>馬名</th><th>単勝 オッズ</th>
    <th colspan="2">複勝オッズ (3着払い)</th><th>性齢</th><th>馬体重 (増減)</th>
    <th>負担 重量</th><th>騎手 (所属)</th><th>所属</th></tr>
    <tr><td>1</td><td>1</td><td>ワローテル</td><td>23.4</td><td>3.5-</td><td>7.8</td>
    <td>牡3</td><td></td><td>54.0</td><td>▲塩津璃 （兵庫）</td><td>兵庫</td></tr>
    <tr><td>2</td><td>2</td><td>ニネンエフグミ</td><td>4.0</td><td>1.1-</td><td>2.1</td>
    <td>牝4</td><td></td><td>55.0</td><td>廣瀬航 （兵庫）</td><td>兵庫</td></tr></table>"""
    odds = _parse_nar_live_odds_html(html)
    assert odds[1]["winOdds"] == 23.4
    assert odds[1]["placeOddsLow"] == 3.5
    assert odds[1]["placeOddsHigh"] == 7.8
    assert odds[2]["winOdds"] == 4.0
    assert odds[2]["placeOddsLow"] == 1.1
    assert odds[2]["placeOddsHigh"] == 2.1


def test_existing_application_entrypoint_uses_independent_nar_parser():
    from app import _parse_nar_live_odds_html as production_parser
    assert production_parser is _parse_nar_live_odds_html
    assert _parse_nar_live_odds_html("") == {}
    source = Path("app.py").read_text()
    assert "from arvexq.ingest.odds_fields.nar_official import _parse_nar_live_odds_html" in source

def test_nar_popularity_isolated_and_preserves_equal_odds_ties():
    from arvexq.ingest.odds_fields.nar_popularity import apply_observed_win_popularity
    facts = {
        4: {"winOdds": 6.0, "popularity": 1},
        3: {"winOdds": 3.0, "popularity": 4},
        2: {"winOdds": 3.0, "popularity": 5},
        1: {"winOdds": None, "popularity": None},
    }
    result = apply_observed_win_popularity(facts)
    assert result is facts
    assert result[2]["popularity"] == 1
    assert result[3]["popularity"] == 1
    assert result[4]["popularity"] == 3
    assert result[1]["popularity"] is None
    assert "return apply_observed_win_popularity(out)" in Path(
        "arvexq/ingest/odds_fields/nar_official.py"
    ).read_text()
