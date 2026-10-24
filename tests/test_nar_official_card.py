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

def test_banei_three_digit_carried_load_from_existing_official_column():
    html = """<table><tr><th>馬番</th><th>馬名</th><th>負担重量</th><th>馬体重</th><th>増減</th></tr>
    <tr><td>1</td><td>ばんえい馬</td><td>620</td><td>1050kg</td><td>+5</td></tr></table>"""
    detail = {"track": "帯広ば", "analysisMode": "ばんえい",
              "horses": [{"horseNumber": 1, "name": "ばんえい馬"}]}
    rows = parse_card_html(detail, html, clean)
    assert len(rows) == 1
    assert rows[0]["carriedWeight"] == 620.0
    assert rows[0]["bodyWeight"] == 1050
    assert rows[0]["bodyWeightChange"] == 5


def test_flat_race_cannot_consume_banei_carried_load():
    html = """<table><tr><th>馬番</th><th>馬名</th><th>負担重量</th><th>馬体重</th></tr>
    <tr><td>1</td><td>確認馬</td><td>620</td><td>480kg</td></tr></table>"""
    detail = {"track": "園田", "analysisMode": "平地",
              "horses": [{"horseNumber": 1, "name": "確認馬"}]}
    rows = parse_card_html(detail, html, clean)
    assert len(rows) == 1
    assert rows[0]["carriedWeight"] is None


def test_banei_rejects_invalid_flat_weight_not_body_mass():
    html = """<table><tr><th>馬番</th><th>馬名</th><th>負担重量</th><th>馬体重</th></tr>
    <tr><td>1</td><td>確認馬</td><td>59</td><td>1050kg</td></tr></table>"""
    detail = {"track": "帯広ば", "horses": [{"horseNumber": 1, "name": "確認馬"}]}
    rows = parse_card_html(detail, html, clean)
    assert len(rows) == 1
    assert rows[0]["bodyWeight"] == 1050
    assert rows[0]["carriedWeight"] is None


def test_actual_official_banei_multirow_layout_no_previous_run_mixup():
    html = """<table><tbody>
      <tr class="tBorder"><td class="horseNum">1</td>
          <td><a class="horseName">ニジイロアオゾラ</a></td>
          <td class="odds_weight">6.6 (2人気)</td></tr>
      <tr><td>父名</td><td>競走歴</td></tr>
      <tr><td>母名</td><td>過去走 1093 騎手620</td></tr>
      <tr><td><span class="male">牝6</span></td><td>鹿毛</td>
          <td>04.10生</td><td>620　9-6-2-45</td></tr>
      <tr><td class="odds_weight">1084<br>(-9)</td><td>1093 620</td></tr>
      <tr class="tBorder"><td class="horseNum">2</td>
          <td><a class="horseName">別の馬</a></td></tr>
      <tr><td>欠損</td></tr><tr><td>欠損</td></tr>
      <tr><td><span class="male">牡5</span></td><td>栗毛</td>
          <td>01.01生</td><td>600 1-2-3-4</td></tr>
      <tr><td class="odds_weight">998<br>(+5)</td></tr>
      </tbody></table>"""
    detail = {"track": "帯広ば", "analysisMode": "ばんえい",
              "horses": [{"horseNumber": 1, "name": "ニジイロアオゾラ"},
                         {"horseNumber": 2, "name": "別の馬"}]}
    rows = parse_card_html(detail, html, clean)
    assert rows == [
        {"horseNumber": 1, "bodyWeight": 1084,
         "bodyWeightChange": -9, "carriedWeight": 620.0,
         "source": "NAR公式出馬表"},
        {"horseNumber": 2, "bodyWeight": 998,
         "bodyWeightChange": 5, "carriedWeight": 600.0,
         "source": "NAR公式出馬表"},
    ]


def test_official_banei_identity_mismatch_does_not_assign_wrong_horse():
    html = """<table><tr class="tBorder"><td class="horseNum">1</td>
      <td><a class="horseName">別馬</a></td></tr>
      <tr><td><span class="male">牡5</span></td><td>栗毛</td>
      <td>01.01生</td><td>620 1-2-3-4</td></tr>
      <tr><td class="odds_weight">1050 (-2)</td></tr></table>"""
    detail = {"track": "帯広ば",
              "horses": [{"horseNumber": 1, "name": "本来の馬"}]}
    assert parse_card_html(detail, html, clean) == []
