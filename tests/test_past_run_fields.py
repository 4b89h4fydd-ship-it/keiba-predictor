"""Past-run fields that already-fetched source pages publish.

Covers the pure-mapping additions of 2026-11-01: the netkeiba career
listing's 天気/オッズ columns, the NAR RaceMarkTable adapter's winOdds and
weather, the JRA prior-result adapter's race weather, the career merge
replacing the "不明" weather placeholder (and nothing else), and the
transport whitelist letting last3fSeconds/winOdds reach the payload.

Extended 2026-11-03 with the frame/post-position mapping of the same
kind: the listing's 枠番/馬番 columns and both prior-result adapters'
finisher rows already carried frameNumber/horseNumber; only the copies
into the career run were missing (the transport whitelist had both keys
all along).
"""
from __future__ import annotations

import copy
import unittest
from unittest.mock import Mock

from arvexq.databanks.legacy_bridge import (
    _jra_official_prior_result_adapter,
    _nar_official_past_result_adapter,
)
from arvexq.databanks.netkeiba_career import parse_verified_runs
from arvexq.ingest.career_transport import pack_horse
from arvexq.ingest.full_career import merge_career

HEADERS = ["日付", "開催", "天気", "R", "レース名", "映像", "頭数", "枠番",
           "馬番", "オッズ", "人気", "着順", "騎手", "斤量", "距離", "水分量",
           "馬場", "馬場指数", "タイム", "着差", "通過", "ペース", "上り",
           "馬体重", "厩舎コメント", "備考", "勝ち馬(2着馬)", "賞金"]


def _row(cells):
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def _listing_html():
    head = "<tr>" + "".join(f"<th>{h}</th>" for h in HEADERS) + "</tr>"
    nagoya = ["2026/09/17", "名古屋", "晴", "12", "金シャチ最終戦(C)", "",
              "12", "6", "8", "5.5", "2", "2", "加藤誓二", "57", "ダ1500",
              "", "稍", "", "1:38.0", "0.1", "8-6-5", "", "40.6",
              "451(-6)", "", "", "サクリファイス", "20.0"]
    ohi = ["2026/09/04", "大井", "雨", "12", "月見特別競走(C1四)", "",
           "15", "4", "7", "141.9", "15", "14", "古岡勇樹", "56", "ダ1200",
           "", "重", "-16", "1:14.8", "2.0", "14-12", "35.4-37.4", "37.6",
           "475(+3)", "", "", "グルナルーフス", ""]
    blank_odds = ["2026/08/16", "大井", "曇", "8", "へびつかい座特別競走(C1三)", "",
                  "13", "6", "9", "---", "13", "10", "遠藤健太", "56", "ダ1200",
                  "", "重", "-16", "1:14.6", "1.8", "7-8", "35.7-37.1", "",
                  "472(0)", "", "", "ユメゴテン", ""]
    return ("<html><body><table>" + head + _row(nagoya) + _row(ohi)
            + _row(blank_odds) + "</table></body></html>")


class NetkeibaListingFieldsTest(unittest.TestCase):
    def test_weather_and_win_odds_copied_from_listing_row(self):
        runs = parse_verified_runs(
            _listing_html(), "2026-10-01",
            ["2026-09-17", "2026-09-04", "2026-08-16"], 10)
        self.assertEqual(len(runs), 3)
        by_date = {r["date"]: r for r in runs}
        nagoya = by_date["2026-09-17"]
        self.assertEqual(nagoya["weather"], "晴")
        self.assertEqual(nagoya["winOdds"], 5.5)
        self.assertEqual(nagoya["last3fSeconds"], 40.6)
        self.assertEqual(nagoya["timeSeconds"], 98.0)
        ohi = by_date["2026-09-04"]
        self.assertEqual(ohi["weather"], "雨")
        self.assertEqual(ohi["winOdds"], 141.9)
        self.assertEqual(ohi["last3fSeconds"], 37.6)
        blank = by_date["2026-08-16"]
        self.assertEqual(blank["weather"], "曇")
        self.assertNotIn("winOdds", blank)
        self.assertNotIn("last3fSeconds", blank)


class MergeWeatherPlaceholderTest(unittest.TestCase):
    def test_placeholder_weather_replaced_but_real_values_never_overwritten(self):
        existing = [{"date": "2026-09-01", "track": "東京", "weather": "不明",
                     "timeSeconds": 95.0}]
        incoming = [{"date": "2026-09-01", "track": "東京", "weather": "晴",
                     "timeSeconds": 99.9}]
        merged = merge_career(existing, incoming, "2026-10-01")
        self.assertEqual(merged[0]["weather"], "晴")
        # Fill-only still holds for every other field.
        self.assertEqual(merged[0]["timeSeconds"], 95.0)
        merged2 = merge_career(
            [{"date": "2026-09-01", "weather": "雨"}],
            [{"date": "2026-09-01", "weather": "晴"}], "2026-10-01")
        self.assertEqual(merged2[0]["weather"], "雨")


class TransportWhitelistTest(unittest.TestCase):
    def test_last3f_seconds_and_win_odds_survive_packing(self):
        runs = [{"date": "2026-09-01", "track": "大井", "raceNumber": 3,
                 "distance": 1200, "surface": "ダート", "condition": "良",
                 "fieldSize": 12, "finish": 2, "timeSeconds": 72.1,
                 "last3fSeconds": 38.4, "winOdds": 7.3, "weather": "晴"}]
        horse = {"horseNumber": 1, "name": "test", "recentRaces": runs,
                 "allPastRuns": copy.deepcopy(runs)}
        packed = pack_horse(horse, "2026-10-10")
        visible = packed["recentRaces"][0]
        self.assertEqual(visible["last3fSeconds"], 38.4)
        self.assertEqual(visible["winOdds"], 7.3)
        self.assertEqual(visible["weather"], "晴")
        self.assertEqual(packed["allPastRuns"][0]["last3fSeconds"], 38.4)


class NarAdapterFieldsTest(unittest.TestCase):
    def test_win_odds_and_weather_copied_from_result_row(self):
        def official(previous):
            return {"weather": "曇", "finishers": [
                {"finish": 1, "name": "勝ち馬", "timeSeconds": 60.0},
                {"finish": 2, "name": "地元の馬", "timeSeconds": 60.8,
                 "last3FSeconds": 38.0, "winOdds": 12.4},
            ]}
        fetch = _nar_official_past_result_adapter(
            {"_nar_official_result_fast": official})
        horse = {"name": "地元の馬", "recentRaces": [
            {"date": "2026-10-09", "track": "園田", "raceNumber": 1,
             "distance": 1400, "finish": 2}]}
        out = fetch(horse, {"date": "2026-10-15"}, 5)
        observed = out["recentRaces"][0]
        self.assertEqual(observed["winOdds"], 12.4)
        self.assertEqual(observed["weather"], "曇")
        self.assertEqual(observed["last3fSeconds"], 38.0)


class JraAdapterWeatherTest(unittest.TestCase):
    def test_result_weather_copied_onto_observed_run(self):
        import base64
        rid = "jraresult-" + base64.urlsafe_b64encode(
            b"linked-official-race").decode().rstrip("=")
        profile = Mock(return_value=[{
            "date": "2026-10-01", "track": "東京", "raceId": rid,
            "fieldSize": 10, "finish": 2, "cornerPositions": [],
            "weather": "不明"}])
        results = Mock(return_value={
            "date": "2026-10-01", "track": "東京", "weather": "晴",
            "result": {"finishers": [
                {"name": "勝馬", "finish": 1, "timeSeconds": 95.1},
                {"name": "対象馬", "finish": 2, "timeSeconds": 95.5,
                 "last3FSeconds": 34.7, "cornerPositions": [4, 3]}]}})
        fetch = _jra_official_prior_result_adapter(
            {"_jra_profile_runs": profile, "_jra_parse_result": results})
        out = fetch({"name": "対象馬", "_jraHorseCname": "official-horse"},
                    {"date": "2026-10-13"}, 200)
        self.assertEqual(out["recentRaces"][0]["weather"], "晴")


class NetkeibaListingFrameTest(unittest.TestCase):
    def test_frame_and_post_copied_from_listing_row(self):
        runs = parse_verified_runs(
            _listing_html(), "2026-10-01",
            ["2026-09-17", "2026-09-04", "2026-08-16"], 10)
        by_date = {r["date"]: r for r in runs}
        nagoya = by_date["2026-09-17"]
        self.assertEqual(nagoya["frameNumber"], 6)
        self.assertEqual(nagoya["horseNumber"], 8)
        ohi = by_date["2026-09-04"]
        self.assertEqual(ohi["frameNumber"], 4)
        self.assertEqual(ohi["horseNumber"], 7)
        blank = by_date["2026-08-16"]
        self.assertEqual(blank["frameNumber"], 6)
        self.assertEqual(blank["horseNumber"], 9)


class MergeFrameTest(unittest.TestCase):
    def test_frame_fills_from_incoming_but_is_never_overwritten(self):
        merged = merge_career(
            [{"date": "2026-09-01", "track": "東京", "timeSeconds": 95.0}],
            [{"date": "2026-09-01", "track": "東京", "frameNumber": 3,
              "horseNumber": 5}], "2026-10-01")
        self.assertEqual(merged[0]["frameNumber"], 3)
        self.assertEqual(merged[0]["horseNumber"], 5)
        merged2 = merge_career(
            [{"date": "2026-09-01", "frameNumber": 2}],
            [{"date": "2026-09-01", "frameNumber": 7}], "2026-10-01")
        self.assertEqual(merged2[0]["frameNumber"], 2)


class TransportFrameTest(unittest.TestCase):
    def test_frame_and_post_survive_packing(self):
        runs = [{"date": "2026-09-01", "track": "大井", "raceNumber": 3,
                 "distance": 1200, "surface": "ダート", "condition": "良",
                 "fieldSize": 12, "finish": 2, "timeSeconds": 72.1,
                 "frameNumber": 5, "horseNumber": 9}]
        horse = {"horseNumber": 1, "name": "test", "recentRaces": runs,
                 "allPastRuns": copy.deepcopy(runs)}
        packed = pack_horse(horse, "2026-10-10")
        visible = packed["recentRaces"][0]
        self.assertEqual(visible["frameNumber"], 5)
        self.assertEqual(visible["horseNumber"], 9)
        self.assertEqual(packed["allPastRuns"][0]["frameNumber"], 5)


class NarAdapterFrameTest(unittest.TestCase):
    def test_frame_and_post_copied_from_result_row(self):
        def official(previous):
            return {"weather": "曇", "finishers": [
                {"finish": 1, "name": "勝ち馬", "timeSeconds": 60.0},
                {"finish": 2, "name": "地元の馬", "timeSeconds": 60.8,
                 "last3FSeconds": 38.0, "winOdds": 12.4,
                 "frameNumber": 5, "horseNumber": 9},
            ]}
        fetch = _nar_official_past_result_adapter(
            {"_nar_official_result_fast": official})
        horse = {"name": "地元の馬", "recentRaces": [
            {"date": "2026-10-09", "track": "園田", "raceNumber": 1,
             "distance": 1400, "finish": 2}]}
        out = fetch(horse, {"date": "2026-10-15"}, 5)
        observed = out["recentRaces"][0]
        self.assertEqual(observed["frameNumber"], 5)
        self.assertEqual(observed["horseNumber"], 9)


class JraAdapterFrameTest(unittest.TestCase):
    def _fetch(self, target_row):
        import base64
        rid = "jraresult-" + base64.urlsafe_b64encode(
            b"linked-official-race").decode().rstrip("=")
        profile = Mock(return_value=[{
            "date": "2026-10-01", "track": "東京", "raceId": rid,
            "fieldSize": 10, "finish": 2, "cornerPositions": [],
            "weather": "不明"}])
        results = Mock(return_value={
            "date": "2026-10-01", "track": "東京", "weather": "晴",
            "result": {"finishers": [
                {"name": "勝馬", "finish": 1, "timeSeconds": 95.1},
                target_row]}})
        return _jra_official_prior_result_adapter(
            {"_jra_profile_runs": profile, "_jra_parse_result": results})

    def test_frame_and_post_copied_from_result_row(self):
        fetch = self._fetch(
            {"name": "対象馬", "finish": 2, "timeSeconds": 95.5,
             "frameNumber": 3, "horseNumber": 5})
        out = fetch({"name": "対象馬", "_jraHorseCname": "official-horse"},
                    {"date": "2026-10-13"}, 200)
        observed = out["recentRaces"][0]
        self.assertEqual(observed["frameNumber"], 3)
        self.assertEqual(observed["horseNumber"], 5)

    def test_unpublished_frame_zero_is_not_copied(self):
        fetch = self._fetch(
            {"name": "対象馬", "finish": 2, "timeSeconds": 95.5,
             "frameNumber": 0, "horseNumber": 5})
        out = fetch({"name": "対象馬", "_jraHorseCname": "official-horse"},
                    {"date": "2026-10-13"}, 200)
        observed = out["recentRaces"][0]
        self.assertNotIn("frameNumber", observed)
        self.assertEqual(observed["horseNumber"], 5)


if __name__ == "__main__":
    unittest.main()
