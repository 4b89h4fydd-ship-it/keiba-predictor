"""Independent NAR official observations: no cross-field inference or source mutation."""
from arvexq.ingest.nar_fields.body_weight import extract as body_weight, parse_weight_cell
from arvexq.ingest.nar_fields.body_weight_change import from_separate_column, from_next_cell
from arvexq.ingest.nar_fields.carried_weight import extract as carried_weight
from arvexq.ingest.nar_official_card import parse_card_html


def clean(value):
    return " ".join(str(value or "").split())


def test_carried_weight_is_independent_of_body_weight_and_unknowns_remain_null():
    assert carried_weight(["馬A", "56.5", "482 (+4)"], 1) == 56.5
    assert carried_weight(["馬A", "56.5", "482 (+4)"], 0) is None
    assert carried_weight(["馬A", "90.5", "482 (+4)"], 1) is None
    assert carried_weight(["馬A", "56.5"], -1) is None
    assert body_weight(["1", "馬A", "56.5"], "1 馬A 56.5", -1, -1) == (None, None)


def test_body_weight_and_change_are_independently_observed():
    assert parse_weight_cell("482kg（+4）") == (482, 4)
    assert parse_weight_cell("999kg（+4）") == (None, None)
    assert from_separate_column(["482", "-6"], 1) == -6
    assert from_separate_column(["482", "未発表"], 1) is None
    assert from_next_cell(["482", "0"], 0) == 0
    assert from_next_cell(["482"], 0) is None
    assert body_weight(["1", "馬A", "56.5", "482", "+4"], "1 馬A 56.5 482 +4", 3, 4) == (482, 4)
    assert body_weight(["1", "馬A", "482kg（-2）"], "1 馬A 482kg（-2）", 2, -1) == (482, -2)


def test_composition_keeps_weight_change_without_leaking_into_carried_weight():
    race = {"horses": [{"horseNumber": 1, "name": "確認馬"}]}
    html = """<table><tr><th>馬番</th><th>馬名</th><th>負担重量</th><th>馬体重</th><th>増減</th></tr>
    <tr><td>1</td><td>確認馬</td><td>55.0</td><td>482</td><td>-4</td></tr></table>"""
    expected = [{"horseNumber": 1, "bodyWeight": 482, "bodyWeightChange": -4,
                 "carriedWeight": 55.0, "source": "NAR公式出馬表"}]
    assert parse_card_html(race, html, clean) == expected
    assert race == {"horses": [{"horseNumber": 1, "name": "確認馬"}]}
