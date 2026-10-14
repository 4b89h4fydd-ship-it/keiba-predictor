import re
import unittest

class OfficialJraPastMarginRegex(unittest.TestCase):
    def test_observed_past_run_examples(self):
        pattern=r"3F\s*\d{2}(?:\.\d)?\s+[^()]+?\s*\(([+-]?\d+(?:\.\d+)?)\)"
        for cell, expected in [
            ("11 11 11 11 3F 39.5 アイウィル(2.8)",2.8),
            ("4 4 3F 36.2 キャッチアシーフ(0.0)",0.0),
            ("11-11-11-11 3F 39.5 アイウィル (2.8)",2.8),
        ]:
            match=re.search(pattern,cell)
            self.assertIsNotNone(match,cell)
            self.assertEqual(float(match.group(1)),expected)

if __name__ == "__main__":
    unittest.main()
