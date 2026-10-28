"""Unit tests for the race-title class mapping."""
import unittest

from rewrite.analysis.ability import class_level


class ClassLevelTest(unittest.TestCase):
    def test_jra_ladder(self):
        self.assertEqual(class_level("2歳新馬"), 0.0)
        self.assertEqual(class_level("メイクデビュー東京"), 0.0)
        self.assertEqual(class_level("3歳未勝利"), 1.0)
        self.assertEqual(class_level("3歳以上1勝クラス"), 2.0)
        self.assertEqual(class_level("4歳以上2勝クラス"), 3.0)
        self.assertEqual(class_level("3歳以上3勝クラス"), 4.0)
        self.assertEqual(class_level("壬生特別"), 5.0)
        self.assertEqual(class_level("長岡京ステークス"), 5.0)
        self.assertEqual(class_level("障害3歳以上オープン"), 5.0)

    def test_nar_letters_fullwidth(self):
        self.assertEqual(class_level("Ｃ１"), 3.0)
        self.assertEqual(class_level("３歳以上 Ｃ４－３"), 2.25)
        self.assertEqual(class_level("C2一"), 2.75)
        self.assertEqual(class_level("Ｂ－２"), 3.75)
        self.assertAlmostEqual(class_level("３歳以上C4ー3"), 2.25)

    def test_nar_stakes_and_juvenile_groups(self):
        self.assertEqual(class_level("園田重賞"), 5.5)
        self.assertEqual(class_level("準重賞競走"), 5.25)
        self.assertAlmostEqual(class_level("２歳 ３組"), 1.3)

    def test_unknown_titles_stay_missing(self):
        self.assertIsNone(class_level("なでしこ賞"))
        self.assertIsNone(class_level("ファイナルレース"))
        self.assertIsNone(class_level(""))
        self.assertIsNone(class_level(None))


if __name__ == "__main__":
    unittest.main()
