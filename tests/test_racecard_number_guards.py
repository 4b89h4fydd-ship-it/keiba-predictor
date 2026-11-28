"""Guards against the 2026-11-28 garbled-roster accident.

The netkeiba detail path once emitted the right horses under wrong
numbers with frame 0 everywhere. Count/name checks passed those lists,
the static racecard recovery locked them in, and the number-keyed merge
spread duplicates into the packs. These tests pin the three defenses:
heading matching in the JRA program parser, roster integrity in
_card_usable, and name-keyed fallback in _merge_horses.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

import app
from scripts import arvexq_prefetch as prefetch
from arvexq.ingest.entry_fields.horse_number import _nk_row_horse_no


def jra_card(numbers, frames=None, field_size=None):
    horses = []
    for i, no in enumerate(numbers):
        horse = {"horseNumber": no, "name": f"馬{no}", "jockey": "騎手",
                 "carriedWeight": 56}
        if frames is not None:
            horse["frameNumber"] = frames[i]
        horses.append(horse)
    return {"id": "jra-2026-11-28-東京-09", "circuit": "中央",
            "track": "東京", "date": "2026-11-28",
            "fieldSize": field_size if field_size is not None else len(numbers),
            "horses": horses}


class CardUsableNumberGuardTests(unittest.TestCase):
    def test_clean_jra_card_is_usable(self):
        frames = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7]
        self.assertTrue(prefetch._card_usable(jra_card(list(range(1, 14)), frames)))

    def test_garbled_numbers_are_not_usable(self):
        # The Kyoto 9R signature: right horses, numbers scattered to 18.
        numbers = [1, 2, 3, 4, 5, 7, 8, 9, 12, 13, 14, 16, 18]
        frames = [0] * len(numbers)
        card = jra_card(numbers, frames, field_size=13)
        self.assertFalse(prefetch._card_usable(card))

    def test_zero_frames_are_not_usable_for_jra(self):
        card = jra_card([1, 2, 3, 4], [0, 0, 0, 0])
        self.assertFalse(prefetch._card_usable(card))

    def test_missing_frame_is_not_usable_for_jra(self):
        card = jra_card([1, 2, 3, 4], [1, 2, 3, None])
        self.assertFalse(prefetch._card_usable(card))

    def test_duplicate_numbers_are_not_usable(self):
        card = jra_card([1, 2, 3, 3], [1, 2, 3, 3])
        self.assertFalse(prefetch._card_usable(card))

    def test_gap_in_numbers_is_not_usable(self):
        card = {"id": "nar-2026-11-28-大井-04", "track": "大井",
                "date": "2026-11-28", "fieldSize": 4,
                "horses": [{"horseNumber": n, "name": f"馬{n}",
                            "jockey": "騎手", "carriedWeight": 56}
                           for n in (1, 2, 4, 5)]}
        self.assertFalse(prefetch._card_usable(card))

    def test_local_card_without_frames_stays_usable(self):
        # Local rosters are number-gated but not frame-gated: some local
        # sources publish the roster without frame assignment payloads.
        card = {"id": "nar-2026-11-28-大井-04", "track": "大井",
                "date": "2026-11-28", "fieldSize": 4,
                "horses": [{"horseNumber": n, "name": f"馬{n}",
                            "jockey": "騎手", "carriedWeight": 56}
                           for n in (1, 2, 3, 4)]}
        self.assertTrue(prefetch._card_usable(card))


class MergeHorsesGarbleDefenseTests(unittest.TestCase):
    def base(self):
        return [{"horseNumber": 1, "frameNumber": 1, "name": "アルファ"},
                {"horseNumber": 2, "frameNumber": 2, "name": "ブラボー"},
                {"horseNumber": 3, "frameNumber": 3, "name": "チャーリー"}]

    def test_garbled_fresh_cannot_renumber_or_duplicate(self):
        fresh = [{"horseNumber": 8, "frameNumber": 6, "name": "アルファ",
                  "bodyWeight": 480},
                 {"horseNumber": 9, "frameNumber": 6, "name": "ブラボー"},
                 {"horseNumber": 18, "frameNumber": 8, "name": "チャーリー"},
                 {"horseNumber": 14, "frameNumber": 7, "name": "アルファ"}]
        merged = prefetch._merge_horses(self.base(), fresh)
        self.assertEqual([h["horseNumber"] for h in merged], [1, 2, 3])
        self.assertEqual([h["frameNumber"] for h in merged], [1, 2, 3])
        self.assertEqual([h["name"] for h in merged],
                         ["アルファ", "ブラボー", "チャーリー"])
        # Non-number fields from a name-matched garbled row still land.
        self.assertEqual(merged[0]["bodyWeight"], 480)

    def test_trusted_fresh_merges_by_number_as_before(self):
        fresh = [{"horseNumber": 2, "name": "ブラボー", "bodyWeight": 500},
                 {"horseNumber": 4, "name": "デルタ", "jockey": "騎手"}]
        merged = prefetch._merge_horses(self.base(), fresh)
        self.assertEqual([h["horseNumber"] for h in merged], [1, 2, 3, 4])
        self.assertEqual(merged[1]["bodyWeight"], 500)
        self.assertEqual(merged[3]["name"], "デルタ")


class JraHeadingMatchTests(unittest.TestCase):
    def test_split_heading_matches(self):
        self.assertTrue(app._jra_head_has("レース 番号 レース名 発走 時刻",
                                          "レース番号", "発走時刻"))

    def test_fullwidth_space_heading_matches(self):
        self.assertTrue(app._jra_head_has("レース　番号 発走　時刻",
                                          "レース番号", "発走時刻"))

    def test_missing_word_does_not_match(self):
        self.assertFalse(app._jra_head_has("レース 番号", "レース番号", "発走時刻"))

    def test_program_summaries_parse_split_headings(self):
        html = """<html><body><h2>5回東京3日</h2>
        <table><thead><tr><th>レース<span>番号</span></th><th>競走名</th>
        <th>発走<span>時刻</span></th></tr></thead>
        <tr><td>1レース</td><td>2歳新馬 1,600（芝）</td><td>10時05分</td></tr>
        </table></body></html>"""
        with patch.object(app, "_jra_request", return_value=html):
            out = app._jra_program_summaries("2027-01-05")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["track"], "東京")
        self.assertEqual(out[0]["raceNumber"], 1)
        self.assertEqual(out[0]["startTime"], "10:05")


class NetkeibaHorseNumberPriorityTests(unittest.TestCase):
    def row(self, html):
        return BeautifulSoup(html, "html.parser").find("tr")

    def test_umaban_cell_wins_over_odds_span(self):
        tr = self.row('<tr><td class="Umaban">7</td>'
                      '<td><span id="odds-1_03">3.1</span></td></tr>')
        self.assertEqual(_nk_row_horse_no(tr), 7)

    def test_odds_span_is_fallback_without_cell(self):
        tr = self.row('<tr><td><span id="odds-1_03">3.1</span></td></tr>')
        self.assertEqual(_nk_row_horse_no(tr), 3)

    def test_no_source_returns_zero(self):
        tr = self.row('<tr><td>text</td></tr>')
        self.assertEqual(_nk_row_horse_no(tr), 0)


if __name__ == "__main__":
    unittest.main()
