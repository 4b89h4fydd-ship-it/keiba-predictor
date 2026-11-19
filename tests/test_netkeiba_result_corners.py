"""Contract tests: corner positions (通過順) from netkeiba result pages.

Fixtures mirror the real layouts observed 2026-11-19:
- smartphone (nar.sp.netkeiba.com): the result table has no corner
  column; a race-level コーナー通過順位 table (class Corner_Num)
  carries one passing-order string per corner, e.g.
  "(2,6),8,(3,7),9,1,(4,10)-5".
- desktop (race.netkeiba.com): a per-horse コーナー通過順 column.
  The column wins; the corner table must reproduce it exactly,
  including the "*" refinement (a starred horse inside a group is
  slightly ahead of its groupmates — verified against real JRA
  result pages, 48/48 horses).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_netkeiba_result_last3f import KW  # noqa: E402

from arvexq.ingest.netkeiba_result import (  # noqa: E402
    _corner_order_ranks,
    parse_current_result_html,
)

# Smartphone layout, modelled on 園田1R 2026-11-19 (10 runners):
# corner orders are the page's real strings, shortened field.
SP_HTML = """<table><tr><th>着順</th><th>枠番</th><th>馬番</th><th>馬名</th><th>タイム</th><th>オッズ</th></tr>
<tr><td>1 着</td><td>4</td><td>6</td><td>ママトモ</td><td>1:31.4 (39.4)</td><td>3.0倍 2人気</td></tr>
<tr><td>2 着</td><td>1</td><td>1</td><td>テイケイアンジェ</td><td>1:31.7 1.3/4 (39.3)</td><td>44.8倍 9人気</td></tr>
<tr><td>3 着</td><td>7</td><td>10</td><td>ジーティーパール</td><td>1:32.1 2 (39.3)</td><td>6.6倍 4人気</td></tr>
<tr><td>4 着</td><td>2</td><td>3</td><td>メイショウセツゲツ</td><td>1:32.4 1.1/2 (40.0)</td><td>5.0倍 3人気</td></tr>
<tr><td>5 着</td><td>5</td><td>7</td><td>ミトロージア</td><td>1:32.9 3 (40.1)</td><td>9.9倍 5人気</td></tr>
<tr><td>6 着</td><td>3</td><td>5</td><td>ニックオブタイム</td><td>1:33.0 1/2 (40.2)</td><td>12.0倍 6人気</td></tr>
<tr><td>7 着</td><td>6</td><td>9</td><td>エザルターレ</td><td>1:33.2 1 (39.9)</td><td>15.0倍 7人気</td></tr>
<tr><td>8 着</td><td>5</td><td>8</td><td>キョウワグロリア</td><td>1:33.5 2 (40.5)</td><td>20.0倍 8人気</td></tr>
<tr><td>9 着</td><td>1</td><td>2</td><td>ヘルタースケルター</td><td>1:33.8 2 (40.3)</td><td>25.0倍 10人気</td></tr>
<tr><td>10 着</td><td>2</td><td>4</td><td>ミラクルサーダ</td><td>1:34.0 1 (40.8)</td><td>30.0倍 11人気</td></tr></table>
<h2>コーナー通過順位</h2>
<table class="RaceCommon_Table Corner_Num mt15">
<tr><th>1 コーナー</th><td>(2,6),8,(3,7),9,1,(4,10)-5</td></tr>
<tr><th>2 コーナー</th><td>(2,6)-8,(3,7),(1,9),(4,10)-5</td></tr>
<tr><th>3 コーナー</th><td>6-(2,1),3,(8,9)-(4,7,10)-5</td></tr>
<tr><th>4 コーナー</th><td>6-1,(2,3),9,(7,8,10),(4,5)</td></tr></table>
<p>払戻</p>"""

# Desktop layout: per-horse column present AND a corner table whose
# conversion must agree with it (the "*" group (1,*2) included).
PC_HTML = """<table><tr><th>着順</th><th>枠</th><th>馬番</th><th>馬名</th><th>性齢</th><th>斤量</th><th>騎手</th><th>タイム</th><th>着差</th><th>人気</th><th>単勝オッズ</th><th>後3F</th><th>コーナー通過順</th><th>厩舎</th><th>馬体重(増減)</th></tr>
<tr><td>1</td><td>1</td><td>2</td><td>二番馬</td><td>牡3</td><td>57.0</td><td>騎手甲</td><td>1:20.4</td><td></td><td>1</td><td>2.9</td><td>34.6</td><td>1-1</td><td>美浦 甲</td><td>472 (+4)</td></tr>
<tr><td>2</td><td>1</td><td>1</td><td>一番馬</td><td>牡3</td><td>57.0</td><td>騎手乙</td><td>1:20.7</td><td>2</td><td>4</td><td>7.8</td><td>35.2</td><td>2-2</td><td>美浦 乙</td><td>426 (+4)</td></tr>
<tr><td>3</td><td>2</td><td>3</td><td>三番馬</td><td>牝3</td><td>55.0</td><td>騎手丙</td><td>1:20.9</td><td>1/2</td><td>2</td><td>3.4</td><td>34.8</td><td>3-2</td><td>美浦 丙</td><td>430 (-2)</td></tr></table>
<table class="RaceCommon_Table Corner_Num">
<tr><th>1 コーナー</th><td></td></tr>
<tr><th>3 コーナー</th><td>(1,*2),3</td></tr>
<tr><th>4 コーナー</th><td>*2,(1,3)</td></tr></table>
<p>払戻</p>"""


def test_smartphone_corner_table_fills_positions():
    result = parse_current_result_html(SP_HTML, **KW)
    by_no = {f["horseNumber"]: f["cornerPositions"]
             for f in result["finishers"]}
    # Winner led at every corner; parenthesised horses share a rank.
    assert by_no[6] == [1, 1, 1, 1]
    assert by_no[2] == [1, 1, 2, 3]
    assert by_no[5] == [10, 10, 10, 9]
    assert by_no[1] == [7, 6, 2, 2]
    assert all(len(v) == 4 for v in by_no.values())


def test_desktop_column_wins_and_table_agrees():
    result = parse_current_result_html(PC_HTML, **KW)
    by_no = {f["horseNumber"]: f["cornerPositions"]
             for f in result["finishers"]}
    assert by_no[2] == [1, 1]
    assert by_no[1] == [2, 2]
    assert by_no[3] == [3, 2]


def test_star_marks_the_group_leader():
    assert _corner_order_ranks("(1,*2),3") == {2: 1, 1: 2, 3: 3}
    assert _corner_order_ranks("(2,6),8") == {2: 1, 6: 1, 8: 3}
    assert _corner_order_ranks("5=3,10") == {5: 1, 3: 2, 10: 3}


def test_no_corner_source_keeps_empty_list():
    html = """<table><tr><th>着順</th><th>枠番</th><th>馬番</th><th>馬名</th><th>タイム</th></tr>
    <tr><td>1</td><td>1</td><td>1</td><td>一番馬</td><td>1:34.3</td></tr>
    <tr><td>2</td><td>2</td><td>3</td><td>二番馬</td><td>1:34.5</td></tr>
    <tr><td>3</td><td>3</td><td>5</td><td>三番馬</td><td>1:34.8</td></tr></table><p>払戻</p>"""
    result = parse_current_result_html(html, **KW)
    assert all(f["cornerPositions"] == [] for f in result["finishers"])


def test_horse_missing_from_one_corner_gets_none_slot():
    html = SP_HTML.replace("-(4,7,10)-5", "-(4,7,10)")
    result = parse_current_result_html(html, **KW)
    by_no = {f["horseNumber"]: f["cornerPositions"]
             for f in result["finishers"]}
    # Horse 5 drops out of the 3rd corner order only: its slot is
    # None (never estimated), the other corners stay aligned.
    assert by_no[5] == [10, 10, None, 9]
