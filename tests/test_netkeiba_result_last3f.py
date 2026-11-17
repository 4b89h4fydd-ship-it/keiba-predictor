"""Contract tests: observed last-3F (上がり) and race lap times from
netkeiba result pages.

Fixtures mirror the two real layouts observed 2026-11-18:
- smartphone (nar.netkeiba.com): no 上がり column; the time cell
  carries the value as a trailing parenthesis, e.g. "1:54.4 (39.4)",
  and the lap table carries "<cumulative> <lap>" pairs per cell.
- desktop (race.netkeiba.com): a dedicated 後3F column, and a lap
  table of a cumulative row followed by a lap row.
"""
import re

from arvexq.ingest.netkeiba_result import parse_current_result_html


def clean(value):
    return " ".join(str(value or "").split())


def parse_time(value):
    m = re.search(r"(?:(\d+):)?(\d{1,2})\.(\d+)", value or "")
    if not m:
        return 0.0
    return (int(m.group(1) or 0) * 60 + int(m.group(2))
            + int(m.group(3)) / 10)


def parse_payouts(soup):
    return [{"type": "単勝"}] if "払戻" in soup.get_text() else []


KW = {"clean": clean, "parse_time_seconds": parse_time,
      "parse_payouts": parse_payouts}

SP_HTML = """<table><tr><th>着順</th><th>枠番</th><th>馬番</th><th>馬名</th><th>タイム</th><th>オッズ</th></tr>
<tr><td>1 着</td><td>7</td><td>13</td><td>アスコットミヤギ</td><td>1:54.4 (39.4)</td><td>3.0倍 2人気</td></tr>
<tr><td>2 着</td><td>5</td><td>8</td><td>アーススピリット</td><td>1:54.7 1.3/4 (39.3)</td><td>44.8倍 9人気</td></tr>
<tr><td>3 着</td><td>5</td><td>9</td><td>ボーヌロマネ</td><td>1:55.1 2 (39.3)</td><td>6.6倍 4人気</td></tr></table>
<h2>ラップタイム</h2><table>
<tr><th>200m</th><th>400m</th><th>600m</th></tr>
<tr><td>12.7 12.7</td><td>25.0 12.3</td><td>38.3 13.3</td></tr></table>
<p>払戻</p>"""

PC_HTML = """<table><tr><th>着順</th><th>枠</th><th>馬番</th><th>馬名</th><th>性齢</th><th>斤量</th><th>騎手</th><th>タイム</th><th>着差</th><th>人気</th><th>単勝オッズ</th><th>後3F</th><th>コーナー通過順</th><th>厩舎</th><th>馬体重(増減)</th></tr>
<tr><td>1</td><td>1</td><td>2</td><td>バンオンタイム</td><td>牝3</td><td>55.0</td><td>レーン</td><td>1:33.8</td><td></td><td>1</td><td>2.9</td><td>34.6</td><td>8-6-5</td><td>美浦 田中博</td><td>472 (+4)</td></tr>
<tr><td>2</td><td>3</td><td>6</td><td>ラグアイリータ</td><td>牝3</td><td>55.0</td><td>津村</td><td>1:33.8</td><td>クビ</td><td>8</td><td>31.5</td><td>35.2</td><td>2-1-1</td><td>美浦 岩戸</td><td>426 (+4)</td></tr>
<tr><td>3</td><td>4</td><td>8</td><td>ココナッツコースト</td><td>牝3</td><td>55.0</td><td>戸崎</td><td>1:33.9</td><td>1/2</td><td>2</td><td>3.4</td><td>34.8</td><td>5-5-4</td><td>美浦 小島</td><td>430 (-2)</td></tr></table>
<h2>ラップタイム</h2><table>
<tr><th>200m</th><th>400m</th><th>600m</th><th>800m</th></tr>
<tr><td>12.4</td><td>23.3</td><td>34.9</td><td>46.9</td></tr>
<tr><td>12.4</td><td>10.9</td><td>11.6</td><td>12.0</td></tr></table>
<p>払戻</p>"""


def test_smartphone_time_cell_parenthesis_is_the_last3f():
    result = parse_current_result_html(SP_HTML, **KW)
    assert result["status"] == "確定"
    finishers = result["finishers"]
    assert [f["last3fSeconds"] for f in finishers] == [39.4, 39.3, 39.3]
    # Both spellings are emitted: career/history use lowercase f,
    # the central-run builder reads capital F.
    assert [f["last3FSeconds"] for f in finishers] == [39.4, 39.3, 39.3]
    # The margin extraction that already lived in the time cell is
    # unchanged by the new parenthesis capture.
    assert finishers[1]["marginText"] == "1.3/4"
    assert finishers[2]["marginText"] == "2"


def test_smartphone_lap_table_pairs():
    result = parse_current_result_html(SP_HTML, **KW)
    assert result["raceLapTimes"] == [12.7, 12.3, 13.3]


def test_desktop_after3f_column_and_two_row_lap_table():
    result = parse_current_result_html(PC_HTML, **KW)
    finishers = result["finishers"]
    assert [f["last3fSeconds"] for f in finishers] == [34.6, 35.2, 34.8]
    # Laps are the second row; they must sum to the winner's time
    # (the cumulative row's final value), as on the real page.
    assert result["raceLapTimes"] == [12.4, 10.9, 11.6, 12.0]
    assert abs(sum(result["raceLapTimes"]) - 46.9) < 0.05


def test_missing_last3f_and_laps_stay_absent():
    html = """<table><tr><th>着順</th><th>枠</th><th>馬番</th><th>馬名</th><th>タイム</th></tr>
    <tr><td>1</td><td>1</td><td>1</td><td>一番馬</td><td>1:34.3</td></tr>
    <tr><td>2</td><td>2</td><td>3</td><td>二番馬</td><td>1:34.5</td></tr>
    <tr><td>3</td><td>3</td><td>5</td><td>三番馬</td><td>1:34.8</td></tr></table><p>払戻</p>"""
    result = parse_current_result_html(html, **KW)
    assert all("last3fSeconds" not in f for f in result["finishers"])
    assert "raceLapTimes" not in result
