"""netkeiba NAR b1 (単勝・複勝) desktop page parsing is independent
from networking and never reads a place range as win odds.

Fixture shape/values are the live page for Mizusawa 1R on
2026-11-17 (fetched after the off): two tables with identical
headers, win first (bare numbers), place second (ranges).
"""
from pathlib import Path

from arvexq.ingest.odds_fields.nar_netkeiba_b1 import _parse_nar_netkeiba_b1_html

_HEAD = """<tr><th>枠</th><th>馬番</th><th>印</th><th>選択</th><th>馬名</th><th>オッズ</th></tr>"""

HTML = f"""<html><body>
<table>{_HEAD}
<tr><td>1</td><td>1</td><td></td><td></td><td>ポルテボヌール</td><td>161.0</td></tr>
<tr><td>2</td><td>2</td><td></td><td></td><td>フィレルレーヴ</td><td>1.9</td></tr>
<tr><td>3</td><td>3</td><td></td><td></td><td>アッセクシー</td><td>43.0</td></tr>
<tr><td>4</td><td>4</td><td></td><td></td><td>スーパーハイウェイ</td><td>0.0</td></tr>
</table>
<table>{_HEAD}
<tr><td>1</td><td>1</td><td></td><td></td><td>ポルテボヌール</td><td>8.5 - 19.5</td></tr>
<tr><td>2</td><td>2</td><td></td><td></td><td>フィレルレーヴ</td><td>1.0 - 1.3</td></tr>
<tr><td>3</td><td>3</td><td></td><td></td><td>アッセクシー</td><td>4.1 - 9.0</td></tr>
<tr><td>4</td><td>4</td><td></td><td></td><td>スーパーハイウェイ</td><td>1.0 - 1.4</td></tr>
</table>
</body></html>"""


def test_b1_win_and_place_tables_are_separated_by_content():
    odds = _parse_nar_netkeiba_b1_html(HTML)
    assert odds[2]["winOdds"] == 1.9
    assert odds[2]["placeOddsLow"] == 1.0
    assert odds[2]["placeOddsHigh"] == 1.3
    assert odds[1]["winOdds"] == 161.0
    assert odds[1]["placeOddsLow"] == 8.5
    assert odds[1]["placeOddsHigh"] == 19.5
    assert odds[3]["winOdds"] == 43.0
    assert odds[3]["placeOddsLow"] == 4.1
    assert odds[3]["placeOddsHigh"] == 9.0


def test_b1_place_range_first_number_is_never_a_win_odd():
    odds = _parse_nar_netkeiba_b1_html(HTML)
    # Horse 4's win cell is the not-on-sale placeholder 0.0; its
    # place range must land as place odds only, not as win odds.
    assert "winOdds" not in odds[4]
    assert odds[4]["placeOddsLow"] == 1.0
    assert odds[4]["placeOddsHigh"] == 1.4


def test_b1_empty_and_unrelated_pages_yield_nothing():
    assert _parse_nar_netkeiba_b1_html("") == {}
    assert _parse_nar_netkeiba_b1_html("<table><tr><th>馬名</th></tr></table>") == {}


def test_production_fallback_uses_desktop_b1_parser():
    from app import _parse_nar_netkeiba_b1_html as production_parser
    assert production_parser is _parse_nar_netkeiba_b1_html
    source = Path("app.py").read_text()
    # The place ranges come from the desktop b1 page: the smartphone
    # layout is redirected to the SP shutuba card, which has no
    # place table, so the older scan's 複勝 search could never match.
    assert "nar.netkeiba.com/odds/?race_id={rid}&type=b1" in source
    assert "desktop=True" in source
