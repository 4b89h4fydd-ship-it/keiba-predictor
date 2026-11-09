"""Contracts for observed fields in NAR official race-card HTML."""
from arvexq.ingest.nar_official_card import parse_card_html


def clean(value):
    return " ".join(str(value or "").split())


def test_header_driven_card_reads_carried_weight_and_split_body_weight_change():
    html = """<table><tr><th>馬番</th><th>馬名</th><th>負担重量</th><th>馬体重</th><th>増減</th></tr>
    <tr><td>1</td><td>テスト馬</td><td>54.0</td><td>482kg</td><td>+4</td></tr></table>"""
    detail = {"horses": [{"horseNumber": 1, "name": "テスト馬"}]}
    assert parse_card_html(detail, html, clean) == [{
        "horseNumber": 1, "bodyWeight": 482, "bodyWeightChange": 4,
        "carriedWeight": 54.0, "source": "NAR公式出馬表",
    }]


def test_inline_weight_and_change_are_observed_without_inference():
    html = "<table><tr><td>2</td><td>別の馬</td><td>480kg（-2）</td></tr></table>"
    detail = {"horses": [{"horseNumber": 2, "name": "別の馬"}]}
    assert parse_card_html(detail, html, clean) == [{
        "horseNumber": 2, "bodyWeight": 480, "bodyWeightChange": -2,
        "carriedWeight": None, "source": "NAR公式出馬表",
    }]


def test_standalone_weight_and_next_cell_change_are_supported():
    html = "<table><tr><td>3</td><td>確認馬</td><td>498</td><td>0</td></tr></table>"
    detail = {"horses": [{"horseNumber": 3, "name": "確認馬"}]}
    rows = parse_card_html(detail, html, clean)
    assert rows[0]["horseNumber"] == 3
    assert rows[0]["bodyWeight"] == 498
    assert rows[0]["bodyWeightChange"] == 0


def test_combined_header_and_unbracketed_pair_cell_are_read():
    # DebaTableSmall shape from the 2026-11-07 diagnosis: the header row
    # is one combined cell (column detection cannot resolve) and weight
    # and change share one cell as "482 3" without parentheses. Before
    # the fix this parsed to no rows at all.
    html = """<table>
    <tr><th>枠番 馬番 馬名 性齢 負担重量 騎手 馬体重 増減 調教師</th></tr>
    <tr><td>1</td><td>1</td><td>テスト馬</td><td>牡4</td><td>56.0</td><td>騎手名</td><td>482 3</td><td>調教師名</td></tr>
    <tr><td>2</td><td>2</td><td>二番馬</td><td>牝5</td><td>54.0</td><td>騎手名</td><td>455 -2</td><td>調教師名</td></tr>
    </table>"""
    detail = {"horses": [{"horseNumber": 1, "name": "テスト馬"},
                         {"horseNumber": 2, "name": "二番馬"}]}
    rows = parse_card_html(detail, html, clean)
    assert [(r["horseNumber"], r["bodyWeight"], r["bodyWeightChange"]) for r in rows] == [
        (1, 482, 3), (2, 455, -2)]


def test_unbracketed_pair_in_weight_column_keeps_the_change():
    html = """<table><tr><th>馬番</th><th>馬名</th><th>馬体重</th><th>増減</th></tr>
    <tr><td>1</td><td>テスト馬</td><td>482 3</td><td></td></tr></table>"""
    detail = {"horses": [{"horseNumber": 1, "name": "テスト馬"}]}
    rows = parse_card_html(detail, html, clean)
    assert rows[0]["bodyWeight"] == 482
    assert rows[0]["bodyWeightChange"] == 3


def test_later_card_copy_without_change_does_not_erase_earlier_change():
    html = """<table><tr><th>馬番</th><th>馬名</th><th>馬体重</th></tr>
    <tr><td>1</td><td>テスト馬</td><td>480kg（-2）</td></tr></table>
    <table><tr><th>馬番</th><th>馬名</th><th>馬体重</th></tr>
    <tr><td>1</td><td>テスト馬</td><td>480</td></tr></table>"""
    detail = {"horses": [{"horseNumber": 1, "name": "テスト馬"}]}
    rows = parse_card_html(detail, html, clean)
    assert rows == [{
        "horseNumber": 1, "bodyWeight": 480, "bodyWeightChange": -2,
        "carriedWeight": None, "source": "NAR公式出馬表",
    }]


def test_change_combined_with_result_string_reads_leading_token_only():
    # The change cell continues into a career result string; only the
    # leading token is the change, and a bare result string in the
    # change column is not a change at all.
    html = """<table><tr><th>馬番</th><th>馬名</th><th>馬体重</th><th>増減</th></tr>
    <tr><td>1</td><td>テスト馬</td><td>482</td><td>+3 1-1-4-15</td></tr>
    <tr><td>2</td><td>二番馬</td><td>455</td><td>1-1-4-15</td></tr></table>"""
    detail = {"horses": [{"horseNumber": 1, "name": "テスト馬"},
                         {"horseNumber": 2, "name": "二番馬"}]}
    rows = parse_card_html(detail, html, clean)
    assert [(r["horseNumber"], r["bodyWeightChange"]) for r in rows] == [
        (1, 3), (2, None)]


def test_change_before_result_string_in_next_cell_is_read():
    # No separate change column: the cell after the standalone weight
    # combines the change with the career result string.
    html = """<table><tr><th>馬番</th><th>馬名</th><th>馬体重</th><th>通算成績</th></tr>
    <tr><td>1</td><td>テスト馬</td><td>482</td><td>+3 1-1-4-15</td></tr>
    <tr><td>2</td><td>二番馬</td><td>455</td><td>1-1-4-15</td></tr></table>"""
    detail = {"horses": [{"horseNumber": 1, "name": "テスト馬"},
                         {"horseNumber": 2, "name": "二番馬"}]}
    rows = parse_card_html(detail, html, clean)
    assert [(r["horseNumber"], r["bodyWeight"], r["bodyWeightChange"]) for r in rows] == [
        (1, 482, 3), (2, 455, None)]


def test_missing_or_out_of_range_weight_is_not_fabricated():
    html = "<table><tr><td>4</td><td>未発表馬</td><td>999kg</td></tr></table>"
    detail = {"horses": [{"horseNumber": 4, "name": "未発表馬"}]}
    assert parse_card_html(detail, html, clean) == []
    assert parse_card_html(detail, "", clean) == []
