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


def test_missing_or_out_of_range_weight_is_not_fabricated():
    html = "<table><tr><td>4</td><td>未発表馬</td><td>999kg</td></tr></table>"
    detail = {"horses": [{"horseNumber": 4, "name": "未発表馬"}]}
    assert parse_card_html(detail, html, clean) == []
    assert parse_card_html(detail, "", clean) == []
