"""Contract tests for factual netkeiba result HTML parsing."""
from bs4 import BeautifulSoup
from arvexq.ingest.netkeiba_result import parse_current_result_html


def clean(value):
    return " ".join(str(value or "").split())


def parse_time(value):
    if value == "1:34.5":
        return 94.5
    return 0.0


def parse_payouts(soup):
    return [{"type": "単勝"}] if "払戻" in soup.get_text() else []


def test_result_rows_preserve_observed_runner_facts_and_sort_by_finish():
    html = """<table><tr><th>着順</th><th>枠</th><th>馬番</th><th>馬名</th><th>タイム</th><th>コーナー通過順</th><th>人気</th><th>単勝オッズ</th><th>馬体重</th></tr>
    <tr><td>2</td><td>2</td><td>3</td><td>二番馬</td><td>1:34.5</td><td>3-3-2</td><td>4</td><td>8.2</td><td>470(+2)</td></tr>
    <tr><td>1</td><td>1</td><td>1</td><td>一番馬</td><td>1:34.3</td><td>1-1-1</td><td>1</td><td>2.1</td><td>486(-4)</td></tr>
    <tr><td>3</td><td>3</td><td>5</td><td>三番馬</td><td>1:34.8</td><td>5-5-4</td><td>2</td><td>4.0</td><td>500</td></tr></table><p>払戻</p>"""
    result = parse_current_result_html(html, clean=clean, parse_time_seconds=parse_time, parse_payouts=parse_payouts)
    assert result["status"] == "確定"
    assert result["source"] == "netkeiba結果"
    assert [row["horseNumber"] for row in result["finishers"]] == [1, 3, 5]
    assert result["finishers"][0]["timeSeconds"] == 0.0
    assert result["finishers"][0]["bodyWeightChange"] == -4
    assert result["finishers"][1]["cornerPositions"] == [3, 3, 2]


def test_missing_or_unrecognized_result_table_is_not_fabricated():
    kwargs = {"clean": clean, "parse_time_seconds": parse_time, "parse_payouts": parse_payouts}
    assert parse_current_result_html("", **kwargs) is None
    assert parse_current_result_html("<table><tr><th>馬番</th><th>馬名</th></tr></table>", **kwargs) is None
    html = "<table><tr><th>着順</th><th>馬番</th><th>馬名</th></tr><tr><td>1</td><td>1</td><td>一番馬</td></tr></table>"
    assert parse_current_result_html(html, **kwargs) is None
