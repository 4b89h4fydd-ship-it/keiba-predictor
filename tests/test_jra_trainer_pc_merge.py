"""JRA trainer recovery merge: PC-layout rows fill trainer by horse number.

The smartphone layout used by the fast card paths has no trainer column,
so the merge from a PC-layout page must fill trainer (and affiliation)
only where the card row is empty, keyed by horse number, and must leave
rows without a PC counterpart — and every other field — untouched.
"""
import unittest

from bs4 import BeautifulSoup

import app
from arvexq.ingest.entry_fields.netkeiba import parse_row

PC_PAGE = """
<table>
<tr class="HorseList">
  <td class="Waku1">1</td><td class="Umaban">1</td>
  <td class="Horse_Info"><dl><dt class="Horse"><a>ホースイチ</a></dt>
  <dd class="Age">牡4</dd><dd class="Jockey"><a><em>騎手甲</em></a>57.0</dd></dl></td>
  <td class="Trainer"><span class="Label1">美浦</span><a href="https://db.netkeiba.com/trainer/result/recent/01097/">鹿戸</a></td>
</tr>
<tr class="HorseList">
  <td class="Waku2">2</td><td class="Umaban">2</td>
  <td class="Horse_Info"><dl><dt class="Horse"><a>ホースニ</a></dt>
  <dd class="Age">牝5</dd><dd class="Jockey"><a><em>騎手乙</em></a>55.0</dd></dl></td>
  <td class="Trainer"><span class="Label1">栗東</span><a href="https://db.netkeiba.com/trainer/result/recent/01111/">友道</a></td>
</tr>
</table>
"""


class TrainerPcMergeTest(unittest.TestCase):
    def test_pc_rows_fill_trainer_by_horse_number_only(self):
        soup = BeautifulSoup(PC_PAGE, "html.parser")
        pc_rows = [h for h in (parse_row(tr) for tr in soup.select("tr.HorseList")) if h]
        self.assertEqual([r["trainer"] for r in pc_rows], ["美浦 鹿戸", "栗東 友道"])

        # Rows as the smartphone-layout fast path produces them: no trainer.
        card_rows = [
            {"horseNumber": 1, "name": "ホースイチ", "jockey": "騎手甲",
             "trainer": "", "affiliation": ""},
            {"horseNumber": 2, "name": "ホースニ", "jockey": "騎手乙",
             "trainer": "", "affiliation": ""},
            {"horseNumber": 3, "name": "ホースサン", "jockey": "騎手丙",
             "trainer": "", "affiliation": ""},
            {"horseNumber": 4, "name": "ホースシ", "jockey": "騎手丁",
             "trainer": "既存 太郎", "affiliation": "美浦"},
        ]
        merged = app._merge_trainer_rows(card_rows, pc_rows)
        by_no = {r["horseNumber"]: r for r in merged}

        self.assertEqual(by_no[1]["trainer"], "美浦 鹿戸")
        self.assertEqual(by_no[1]["affiliation"], "美浦")
        self.assertEqual(by_no[2]["trainer"], "栗東 友道")
        self.assertEqual(by_no[2]["affiliation"], "栗東")
        # No PC counterpart: stays empty, never borrowed from another horse.
        self.assertEqual(by_no[3]["trainer"], "")
        self.assertEqual(by_no[3]["affiliation"], "")
        # Already populated (e.g. official full name) is never overwritten.
        self.assertEqual(by_no[4]["trainer"], "既存 太郎")
        # Other fields are exactly as the card path produced them.
        self.assertEqual(by_no[1]["jockey"], "騎手甲")
        self.assertEqual(by_no[3]["name"], "ホースサン")


if __name__ == "__main__":
    unittest.main()
