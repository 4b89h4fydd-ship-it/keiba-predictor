"""Regression tests: the netkeiba fallback must not drop final popularity.

The production fetch uses the smartphone UA by default. That layout's
result table has no 人気 column and no 単勝オッズ column: the odds cell
carries both facts as one string ("2.7倍 1人気"). The parser used to
look only for the desktop columns, so every finisher stored through
the fallback carried popularity=None (all Kyoto/Tokyo results of
2026-11-07/08), silently blocking market-relative measurements.
"""
from arvexq.ingest.netkeiba_result import parse_current_result_html


def clean(value):
    return " ".join(str(value or "").split())


def parse_time(value):
    if value.startswith("1:13."):
        return 73.0
    return 0.0


def parse_payouts(soup):
    return [{"type": "単勝"}] if "払戻" in soup.get_text() else []


SMARTPHONE_HTML = """<table><tr><th>着順</th><th>枠番</th><th>馬番</th><th>馬名</th><th>タイム</th><th>オッズ</th></tr>
<tr><td>2 着</td><td>4</td><td>5</td><td>二番馬 牝3 480kg(+2) 武豊 55.0 栗東・石坂</td><td>1:13.4 1 (37.0)</td><td>5.1倍 3人気</td></tr>
<tr><td>1 着</td><td>2</td><td>2</td><td>一番馬 牡2 452kg(-2) 松山 55.0 栗東・松下</td><td>1:13.3 (36.7)</td><td>2.7倍 1人気</td></tr>
<tr><td>3 着</td><td>7</td><td>12</td><td>三番馬 牡2 430kg(+2) 浜中 56.0 栗東・藤野</td><td>1:13.5 1/2 (37.3)</td><td>16.1倍 7人気</td></tr></table><p>払戻</p>"""


def test_smartphone_layout_extracts_popularity_and_win_odds():
    result = parse_current_result_html(
        SMARTPHONE_HTML, clean=clean, parse_time_seconds=parse_time,
        parse_payouts=parse_payouts)
    assert result is not None
    by_no = {f["horseNumber"]: f for f in result["finishers"]}
    assert by_no[2]["popularity"] == 1
    assert by_no[2]["winOdds"] == 2.7
    assert by_no[5]["popularity"] == 3
    assert by_no[5]["winOdds"] == 5.1
    assert by_no[12]["popularity"] == 7
    assert by_no[12]["winOdds"] == 16.1
    assert all(f["popularity"] is not None for f in result["finishers"])


def test_desktop_columns_still_win_over_cell_scan():
    html = """<table><tr><th>着順</th><th>枠</th><th>馬番</th><th>馬名</th><th>タイム</th><th>人気</th><th>単勝オッズ</th><th>馬体重</th></tr>
    <tr><td>1</td><td>1</td><td>1</td><td>一番馬</td><td>1:13.3</td><td>2</td><td>3.4</td><td>486(-4)</td></tr>
    <tr><td>2</td><td>2</td><td>3</td><td>二番馬</td><td>1:13.5</td><td>1</td><td>2.1</td><td>470(+2)</td></tr>
    <tr><td>3</td><td>3</td><td>5</td><td>三番馬</td><td>1:13.8</td><td>3</td><td>4.0</td><td>500</td></tr></table><p>払戻</p>"""
    result = parse_current_result_html(
        html, clean=clean, parse_time_seconds=parse_time,
        parse_payouts=parse_payouts)
    by_no = {f["horseNumber"]: f for f in result["finishers"]}
    assert by_no[1]["popularity"] == 2
    assert by_no[1]["winOdds"] == 3.4
    assert by_no[3]["popularity"] == 1
    assert by_no[3]["winOdds"] == 2.1


def test_live_smartphone_page_shape_kyoto_20261108_1r():
    """The exact cell shapes observed on the real page that produced
    popularity=None rows in production (Kyoto 2026-11-08 1R)."""
    html = """<table><tr><th>着順</th><th>枠番</th><th>馬番</th><th>馬名</th><th>タイム</th><th>オッズ</th></tr>
    <tr><td>1 着</td><td>2</td><td>2</td><td>テリオスベラ 牝2 452kg(-2) 松山 55.0 栗東・松下</td><td>1:13.3 (36.7)</td><td>2.7倍 1人気</td></tr>
    <tr><td>2 着</td><td>4</td><td>5</td><td>スマートメモリー 牝2 432kg(-8) 武豊 55.0 栗東・石坂</td><td>1:13.4 1 (37.0)</td><td>5.1倍 3人気</td></tr>
    <tr><td>3 着</td><td>7</td><td>12</td><td>レグルスロウ 牡2 430kg(+2) 浜中 56.0 栗東・藤野</td><td>1:13.5 1/2 (37.3)</td><td>16.1倍 7人気</td></tr></table><p>払戻</p>"""
    result = parse_current_result_html(
        html, clean=clean, parse_time_seconds=parse_time,
        parse_payouts=parse_payouts)
    pops = {f["horseNumber"]: f["popularity"] for f in result["finishers"]}
    assert pops == {2: 1, 5: 3, 12: 7}
