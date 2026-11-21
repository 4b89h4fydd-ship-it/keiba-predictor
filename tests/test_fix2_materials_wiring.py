"""Fix2 regression tests (2026-11-21 audit, items B4 / B6 / B7 / B8).

The audit found four materials that were collected (or collectable)
but never reached the forecast, plus body weights that reached the
published data for only 10 of 589 horses:

  B6  the builder never wrote the integrated evaluation's
      comment_text / grade inputs from the newspaper entries it
      already carried — the press entry's 調教評価 letter is now
      extracted into "grade", a saved 短評 into comment_text, and
      a saved レーティング into "pressRating";
  B7  stable comments (厩舎コメント) had no builder input at all —
      the new --stable-comments input joins them by (race, horse
      number) into comment_text (primary) and stableComment;
  B4  oddsDrift needed two actual-odds snapshots and no
      collection ever wrote publishWin — successive --odds
      snapshots now merge (first actual win -> publishWin, last
      -> finalWin) with forecast provenance intact; the page
      collector's parsers for the 調子偏差値 table and the
      厩舎コメント table are pinned against the real pages'
      structure;
  B8  the JRA official card parser read body weight from the
      info cell only — the row's other cells are now scanned
      (body_weight.extract_from_texts), and the extractor cannot
      mistake the carried weight for a body weight.
"""
from __future__ import annotations

from unittest import TestCase

from arvexq.ingest.jra_fields.body_weight import (
    extract as body_weight, extract_from_texts)
from rewrite.analysis.nk_materials import (
    apply_nk_materials, parse_materials_payload)
from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from scripts.arvexq_nk_materials_build import build as build_materials
from scripts.arvexq_nk_page_collect import (
    parse_barometer, parse_stable_comments)

NK_ID = "202646111701"
RACE_ID = "nar-2026-11-17-金沢-01"
DATE = "2026-11-17"
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}
STRENGTHS = {1: 0.30, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.10}
TARGETS = {"targets": [{"netkeiba_race_id": NK_ID,
                        "arvexq_race_id": RACE_ID}]}
SPEED = {"races": {NK_ID: {"horses": {
    str(n): {"nk_best": 65, "nk_avg5": 60, "nk_dist": None,
             "nk_course": None, "nk_recent": [55, 54, 53]}
    for n in NAMES}}}}


def _build(**kwargs):
    return build_materials(DATE, SPEED, {}, TARGETS, **kwargs)


def _horses(payload):
    return payload["races"][RACE_ID]["horses"]


class PressGradeAndCommentTests(TestCase):
    def test_grade_extracted_from_chokyo_trailing_letter(self):
        newspaper = {"races": {NK_ID: {"horses": {
            "1": {"name": "アアア", "chokyo": "好気配B", "marks": {}},
            "2": {"name": "イイイ", "chokyo": "動き一息D", "marks": {}},
            "3": {"name": "ウウウ", "marks": {}},
        }}}}
        payload = _build(newspaper=newspaper)
        horses = _horses(payload)
        self.assertEqual(horses["1"]["grade"], "B")
        self.assertEqual(horses["2"]["grade"], "D")
        self.assertIsNone(horses["3"]["grade"])
        self.assertEqual(payload["fieldCoverage"]["grade"], 2)
        self.assertNotIn("grade", payload["zeroCoverage"])

    def test_explicit_grade_and_rating_and_tanpyo_carried(self):
        newspaper = {"races": {NK_ID: {"horses": {
            "1": {"name": "アアア", "grade": "A", "rating": 82,
                  "tanpyo": "好仕上がり", "marks": {}},
        }}}}
        payload = _build(newspaper=newspaper)
        horse = _horses(payload)["1"]
        self.assertEqual(horse["grade"], "A")
        self.assertEqual(horse["pressRating"], 82)
        self.assertEqual(horse["comment_text"], "好仕上がり")
        self.assertEqual(payload["fieldCoverage"]["pressRating"], 1)
        self.assertEqual(payload["fieldCoverage"]["commentText"], 1)

    def test_without_press_inputs_grade_is_null_and_named(self):
        payload = _build()
        horse = _horses(payload)["1"]
        self.assertIsNone(horse["grade"])
        self.assertIsNone(horse["comment_text"])
        self.assertIn("grade", payload["zeroCoverage"])
        self.assertIn("commentText", payload["zeroCoverage"])


class StableCommentTests(TestCase):
    def test_stable_comment_becomes_comment_text(self):
        comments = {"races": {NK_ID: {
            "published": True,
            "horses": {"1": {"comment": "前走以上に好調です"},
                       "2": {"comment": "使えば良くなる"}}}}}
        payload = _build(stable_comments=comments)
        horses = _horses(payload)
        self.assertEqual(horses["1"]["comment_text"], "前走以上に好調です")
        self.assertEqual(horses["1"]["stableComment"], "前走以上に好調です")
        self.assertIsNone(horses["3"]["comment_text"])
        self.assertEqual(payload["fieldCoverage"]["stableComment"], 2)
        self.assertEqual(payload["fieldCoverage"]["commentText"], 2)

    def test_unpublished_race_is_a_state_not_a_failure(self):
        comments = {"races": {NK_ID: {"published": False, "horses": {}}}}
        payload = _build(stable_comments=comments)
        self.assertIsNone(_horses(payload)["1"]["comment_text"])
        self.assertEqual(payload["fieldCoverage"]["commentText"], 0)

    def test_stable_comment_wins_over_newspaper_tanpyo(self):
        newspaper = {"races": {NK_ID: {"horses": {
            "1": {"name": "アアア", "tanpyo": "短評テキスト",
                  "marks": {}}}}}}
        comments = {"races": {NK_ID: {
            "published": True,
            "horses": {"1": {"comment": "厩舎コメントテキスト"}}}}}
        payload = _build(newspaper=newspaper, stable_comments=comments)
        self.assertEqual(_horses(payload)["1"]["comment_text"],
                         "厩舎コメントテキスト")

    def test_comment_and_grade_terms_fire_in_adapter(self):
        newspaper = {"races": {NK_ID: {"horses": {
            "1": {"name": "アアア", "chokyo": "好気配A", "marks": {}},
            "2": {"name": "イイイ", "chokyo": "一息C", "marks": {}},
            "3": {"name": "ウウウ", "chokyo": "平凡C", "marks": {}},
            "4": {"name": "エエエ", "chokyo": "平凡C", "marks": {}},
            "5": {"name": "オオオ", "chokyo": "平凡C", "marks": {}},
        }}}}
        comments = {"races": {NK_ID: {
            "published": True,
            "horses": {"1": {"comment": "前走以上の好調で万全"},
                       "2": {"comment": "成長待ちで力不足"},
                       "3": {"comment": "順調に仕上がり"},
                       "4": {"comment": "普通の出来"},
                       "5": {"comment": "普通の出来"}}}}}
        payload = _build(newspaper=newspaper, stable_comments=comments)
        materials = parse_materials_payload(payload)
        runners = [RunnerForecast(
            number=n, name=NAMES[n], ability_score=0.5, strength=s,
            pace_adjustment=1.0, pace_reasons=(), p_win=s, p_top2=None,
            p_top3=None, mark="", status="scored")
            for n, s in STRENGTHS.items()]
        forecast = RaceForecast(RACE_ID, 3.0, "calibrated",
                                tuple(runners), "ok")
        adjusted, info = apply_nk_materials(forecast, materials[RACE_ID])
        self.assertTrue(info["applied"])
        by_number = {r.number: r for r in adjusted.runners}
        # Horse 1 (top comment score + top grade) must gain on the
        # field; horse 2 (negative comment) must lose.
        self.assertGreater(by_number[1].p_win, STRENGTHS[1])
        self.assertLess(by_number[2].p_win, STRENGTHS[2])


class OddsSnapshotMergeTests(TestCase):
    def _actual(self, wins):
        return {"races": {NK_ID: {"kind": "actual", "horses": [
            {"no": n, "win_odds": w, "place_min": 1.5,
             "place_max": 2.5} for n, w in wins.items()]}}}

    def test_two_actual_snapshots_light_odds_drift(self):
        evening = self._actual({1: 5.0, 2: 3.0})
        morning = self._actual({1: 4.0, 2: 3.5})
        payload = _build(odds=[evening, morning])
        horses = _horses(payload)
        self.assertEqual(horses["1"]["odds"]["publishWin"], 5.0)
        self.assertEqual(horses["1"]["odds"]["finalWin"], 4.0)
        self.assertEqual(horses["2"]["odds"]["publishWin"], 3.0)
        self.assertEqual(horses["2"]["odds"]["finalWin"], 3.5)
        self.assertEqual(payload["fieldCoverage"]["oddsDrift"], 2)
        self.assertNotIn("oddsDrift", payload["zeroCoverage"])

    def test_single_snapshot_keeps_legacy_behaviour(self):
        payload = _build(odds=[self._actual({1: 5.0})])
        odds = _horses(payload)["1"]["odds"]
        self.assertIsNone(odds["publishWin"])
        self.assertEqual(odds["finalWin"], 5.0)
        self.assertEqual(payload["fieldCoverage"]["oddsDrift"], 0)

    def test_forecast_snapshot_is_never_promoted(self):
        forecast = {"races": {NK_ID: {"kind": "forecast", "horses": [
            {"no": 1, "win_odds": 9.9}]}}}
        payload = _build(odds=[forecast, self._actual({1: 5.0})])
        odds = _horses(payload)["1"]["odds"]
        self.assertEqual(odds["forecastWin"], 9.9)
        self.assertIsNone(odds["publishWin"])
        self.assertEqual(odds["finalWin"], 5.0)

    def test_explicit_dict_shape_publish_win_wins(self):
        sealed = {"races": {NK_ID: {"horses": {
            "1": {"publishWin": 6.0, "finalWin": 4.5,
                  "placeLow": 1.5, "placeHigh": 2.5}}}}}
        payload = _build(odds=[sealed, self._actual({1: 4.0})])
        odds = _horses(payload)["1"]["odds"]
        self.assertEqual(odds["publishWin"], 6.0)
        self.assertEqual(odds["finalWin"], 4.0)


BAROMETER_HTML = """
<table>
<tr><th>着順</th><th>馬番</th><th>馬名</th><th>今回 偏差値</th>
<th>上昇度</th><th>オッズ 人気</th></tr>
<tr><td></td><td>14</td><td>スターリーデー</td><td>59 (5位)</td>
<td>(7位)</td><td>4.9 2人気</td></tr>
<tr><td></td><td>3</td><td>サンプル</td><td>47</td>
<td></td><td>9.9 5人気</td></tr>
<tr><td></td><td>7</td><td>ノーデータ</td><td>-</td>
<td></td><td></td></tr>
</table>
"""

COMMENT_HTML = """
<table class="Stable_Comment">
<tr><td class="Waku1">1</td><td class="Horse_Info">カラマティアノス
奥村武師</td></tr>
<tr><td>Ｑ　前走は〈木村〉 状態がいいので挑んでみます。</td></tr>
<tr><td class="Waku1">2</td><td class="Horse_Info">ヴィスマール
奥村豊師</td></tr>
<tr><td>Ｑ　仕上がりは〈塩手〉 いい精神状態で臨めます。</td></tr>
</table>
"""


class PageCollectorParserTests(TestCase):
    def test_barometer_values_by_horse_number(self):
        values = parse_barometer(BAROMETER_HTML)
        self.assertEqual(values, {"14": 59.0, "3": 47.0})

    def test_barometer_without_table_is_empty(self):
        self.assertEqual(parse_barometer("<html></html>"), {})

    def test_stable_comments_parsed_verbatim(self):
        comments = parse_stable_comments(COMMENT_HTML)
        self.assertEqual(sorted(comments), ["1", "2"])
        self.assertIn("状態がいい", comments["1"])

    def test_page_without_comment_table_is_none(self):
        self.assertIsNone(parse_stable_comments("<html></html>"))


class BodyWeightCellScanTests(TestCase):
    def test_weight_in_a_dedicated_cell_is_found(self):
        texts = ["サンプル 牡2", "牡2 55.0kg 騎手", "504kg (0)", "前走情報"]
        self.assertEqual(extract_from_texts(texts), (504, 0))

    def test_full_form_wins_over_bare_number_elsewhere(self):
        texts = ["前走 480kg", "今回 490kg (+4)"]
        self.assertEqual(extract_from_texts(texts), (490, 4))

    def test_carried_weight_is_never_a_body_weight(self):
        self.assertEqual(body_weight("サンプル 55.0kg"), 0)
        self.assertEqual(
            extract_from_texts(["牡2 55.0kg", "芝 1600m"]), (0, None))

    def test_no_weight_anywhere(self):
        self.assertEqual(extract_from_texts(["", "前走 1:35.2"]), (0, None))
        self.assertEqual(extract_from_texts([]), (0, None))
