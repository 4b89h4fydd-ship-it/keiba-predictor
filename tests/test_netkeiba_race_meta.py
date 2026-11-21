# -*- coding: utf-8 -*-
"""_netkeiba_race_meta must read the current netkeiba page format.

Regression (2026-11-21): netkeiba stopped printing "天候：晴" /
"馬場：良" text on the shutuba page. Weather is now an icon span
(Icon_Weather*, aria-label/title) and the going is a one-letter
abbreviation span (Item03 = turf/jump, Item04 = dirt on JRA pages;
Item03 plus a WeatherData text span on NAR pages). The old text
regexes never matched, so the netkeiba secondary source for JRA
weather/going — and the central-detail fallback — returned nothing
and the builders' "不明" placeholder survived all day. Fixtures
below are trimmed copies of the real 2026-11-21 pages.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

import app

JRA_DIRT = """
<html><body><div class="RaceList_NameBox">
<h1 class="Race_Name">2歳未勝利</h1>
<div class="Race_Data">09:45 <span class="Dirt">ダ</span><span>1700m</span>
&nbsp;右&nbsp; 15頭 <span class="Icon_Weather02 Icon_W02" role="img"
aria-label="曇" title="曇"></span> <span class="Item04">不</span>
<span class="Item05">弱横風</span></div></div></body></html>
"""

JRA_TURF = """
<html><body><div class="RaceList_NameBox">
<h1 class="Race_Name">福島記念</h1>
<div class="Race_Data">15:20 <span class="Turf">芝</span><span>2000m</span>
&nbsp;右&nbsp;B 16頭 <span>予報</span><span class="Icon_Weather02 Icon_W04"
role="img" aria-label="雨" title="雨"></span> <span class="Item03">重</span>
<span class="Item05">弱横風</span></div></div></body></html>
"""

JRA_JUMP = """
<html><body><div class="RaceList_NameBox">
<h1 class="Race_Name">障害3歳以上未勝利</h1>
<div class="Race_Data">11:15 <span class="">障</span><span>2770m</span>
&nbsp;芝&nbsp; 13頭 <span>予報</span><span class="Icon_Weather02 Icon_W04"
role="img" aria-label="雨" title="雨"></span> <span class="Item03">重</span>
<span class="Item05">弱横風</span></div></div></body></html>
"""

NAR_PAGE = """
<html><body><div class="RaceList_NameBox">
<dl><dt class="Race_Name">C3ー13</dt>
<dd class="Race_Data"> 14:55&nbsp;<span class="">ダ</span><span>1600m</span>
(右) 8頭 <span class="WeatherData">&nbsp;晴
<span class="Icon_Weather Weather01"></span></span>
<span class="Item03">稍</span></dd></dl></div></body></html>
"""

NAR_UNANNOUNCED = """
<html><body><div class="RaceList_NameBox">
<dl><dt class="Race_Name">C2</dt>
<dd class="Race_Data"> 15:25&nbsp;<span class="">ダ</span><span>1400m</span>
(右) 11頭 <span class="WeatherData">&nbsp; </span>
<span class="Item03">−</span></dd></dl></div></body></html>
"""

LEGACY_TEXT = """
<html><body><h1>テストレース</h1>
<div>15:45発走 芝1800m 天候：晴 馬場：稍重</div></body></html>
"""


def _meta(html: str, **detail) -> dict:
    detail.setdefault("netkeibaRaceId", "202603030501")
    detail.setdefault("date", "2026-11-21")
    detail.setdefault("track", "福島")
    detail.setdefault("raceNumber", 1)
    with patch.object(app, "_netkeiba_get", return_value=html):
        return app._netkeiba_race_meta(detail)


class NetkeibaRaceMetaIconFormatTests(unittest.TestCase):
    def test_jra_dirt_icon_and_item04(self):
        meta = _meta(JRA_DIRT, surface="ダート")
        self.assertEqual(meta["weather"], "曇")
        self.assertEqual(meta["condition"], "不良")
        self.assertEqual(meta["conditionDirt"], "不良")

    def test_jra_turf_item03(self):
        meta = _meta(JRA_TURF, surface="芝")
        self.assertEqual(meta["weather"], "雨")
        self.assertEqual(meta["condition"], "重")
        self.assertEqual(meta["conditionTurf"], "重")

    def test_jra_jump_uses_turf_going(self):
        meta = _meta(JRA_JUMP, surface="障害")
        self.assertEqual(meta["weather"], "雨")
        self.assertEqual(meta["condition"], "重")

    def test_nar_weatherdata_and_item03(self):
        meta = _meta(NAR_PAGE, track="高知", surface="ダート")
        self.assertEqual(meta["weather"], "晴")
        self.assertEqual(meta["condition"], "稍重")

    def test_nar_unannounced_going_yields_nothing(self):
        meta = _meta(NAR_UNANNOUNCED, track="佐賀", surface="ダート")
        self.assertNotIn("weather", meta)
        self.assertNotIn("condition", meta)

    def test_legacy_text_format_still_parsed(self):
        meta = _meta(LEGACY_TEXT, surface="芝")
        self.assertEqual(meta["weather"], "晴")
        self.assertEqual(meta["condition"], "稍重")


if __name__ == "__main__":
    unittest.main()
