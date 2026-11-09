"""Regression tests: the netkeiba fallback must not drop margin text.

The official JRA parse stores marginText for every finisher (the
winner's is ""). The fallback parser never looked for the margin at
all: the desktop layout's 着差 column was ignored, and the smartphone
layout (the default fetch UA) has no 着差 column — the margin rides
inside the time cell as "<time> <margin> (<last 3F>)". Every finisher
stored through the fallback therefore carried no marginText (the same
Kyoto/Tokyo results hit by the popularity drop).
"""
from arvexq.ingest.netkeiba_result import parse_current_result_html


def clean(value):
    return " ".join(str(value or "").split())


def parse_time(value):
    return 73.3 if value.startswith("1:13.3") else 0.0


def parse_payouts(soup):
    return [{"type": "単勝"}] if "払戻" in soup.get_text() else []


def test_smartphone_layout_extracts_margin_from_time_cell():
    """Exact cell shapes observed on the real page for Kyoto
    2026-11-08 1R: the middle token of the time cell equals the
    desktop layout's 着差 column for all 14 finishers."""
    html = """<table><tr><th>着順</th><th>枠番</th><th>馬番</th><th>馬名</th><th>タイム</th><th>オッズ</th></tr>
    <tr><td>1 着</td><td>2</td><td>2</td><td>テリオスベラ 牝2 452kg(-2) 松山 55.0 栗東・松下</td><td>1:13.3 (36.7)</td><td>2.7倍 1人気</td></tr>
    <tr><td>2 着</td><td>4</td><td>5</td><td>スマートメモリー 牝2 432kg(-8) 武豊 55.0 栗東・石坂</td><td>1:13.4 1 (37.0)</td><td>5.1倍 3人気</td></tr>
    <tr><td>3 着</td><td>7</td><td>12</td><td>レグルスロウ 牡2 430kg(+2) 浜中 56.0 栗東・藤野</td><td>1:13.5 1/2 (37.3)</td><td>16.1倍 7人気</td></tr>
    <tr><td>8 着</td><td>1</td><td>1</td><td>シュライアハフト 牡2 484kg(-8) 酒井 56.0 栗東・小栗</td><td>1:14.2 アタマ (37.5)</td><td>11.9倍 6人気</td></tr>
    <tr><td>10 着</td><td>7</td><td>11</td><td>ワイドウィンザー 牡2 462kg(+6) 斎藤 56.0 栗東・西園翔</td><td>1:14.6 2.1/2 (38.5)</td><td>36.9倍 8人気</td></tr>
    <tr><td>14 着</td><td>8</td><td>14</td><td>キタノゲートウェイ 牡2 460kg(-2) 井上 56.0 栗東・吉田</td><td>1:18.2 大 (38.9)</td><td>568.8倍 14人気</td></tr></table><p>払戻</p>"""
    result = parse_current_result_html(
        html, clean=clean, parse_time_seconds=parse_time,
        parse_payouts=parse_payouts)
    assert result is not None
    by_no = {f["horseNumber"]: f for f in result["finishers"]}
    assert by_no[2]["marginText"] == ""
    assert by_no[5]["marginText"] == "1"
    assert by_no[12]["marginText"] == "1/2"
    assert by_no[1]["marginText"] == "アタマ"
    assert by_no[11]["marginText"] == "2.1/2"
    assert by_no[14]["marginText"] == "大"
    assert all("marginText" in f for f in result["finishers"])


def test_desktop_margin_column_is_used():
    html = """<table><tr><th>着順</th><th>枠</th><th>馬番</th><th>馬名</th><th>性齢</th><th>斤量</th><th>騎手</th><th>タイム</th><th>着差</th><th>人気</th><th>単勝オッズ</th><th>後3F</th><th>コーナー通過順</th><th>厩舎</th><th>馬体重</th></tr>
    <tr><td>1</td><td>2</td><td>2</td><td>テリオスベラ</td><td>牝2</td><td>55.0</td><td>松山</td><td>1:13.3</td><td></td><td>1</td><td>2.7</td><td>36.7</td><td>7-5</td><td>栗東 松下</td><td>452 (-2)</td></tr>
    <tr><td>2</td><td>4</td><td>5</td><td>スマートメモリー</td><td>牝2</td><td>55.0</td><td>武豊</td><td>1:13.4</td><td>クビ</td><td>3</td><td>5.1</td><td>37.0</td><td>4-3</td><td>栗東 石坂</td><td>432 (-8)</td></tr>
    <tr><td>3</td><td>7</td><td>12</td><td>レグルスロウ</td><td>牡2</td><td>56.0</td><td>浜中</td><td>1:13.5</td><td>1/2</td><td>7</td><td>16.1</td><td>37.3</td><td>3-3</td><td>栗東 藤野</td><td>430 (+2)</td></tr></table><p>払戻</p>"""
    result = parse_current_result_html(
        html, clean=clean, parse_time_seconds=parse_time,
        parse_payouts=parse_payouts)
    by_no = {f["horseNumber"]: f for f in result["finishers"]}
    assert by_no[2]["marginText"] == ""
    assert by_no[5]["marginText"] == "クビ"
    assert by_no[12]["marginText"] == "1/2"


def test_no_margin_anywhere_stores_empty_string_not_missing_key():
    html = """<table><tr><th>着順</th><th>枠</th><th>馬番</th><th>馬名</th><th>タイム</th><th>人気</th><th>単勝オッズ</th><th>馬体重</th></tr>
    <tr><td>1</td><td>1</td><td>1</td><td>一番馬</td><td>1:13.3</td><td>2</td><td>3.4</td><td>486(-4)</td></tr>
    <tr><td>2</td><td>2</td><td>3</td><td>二番馬</td><td>1:13.5</td><td>1</td><td>2.1</td><td>470(+2)</td></tr>
    <tr><td>3</td><td>3</td><td>5</td><td>三番馬</td><td>1:13.8</td><td>3</td><td>4.0</td><td>500</td></tr></table><p>払戻</p>"""
    result = parse_current_result_html(
        html, clean=clean, parse_time_seconds=parse_time,
        parse_payouts=parse_payouts)
    assert all(f["marginText"] == "" for f in result["finishers"])
