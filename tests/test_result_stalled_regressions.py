"""Guard result repair and NAR parser failures that left the UI indefinitely pending."""
import io
import unittest
from unittest.mock import patch

from arvexq.results.state import merge_detail, merge_result


class StoredResultMergeTests(unittest.TestCase):
    def test_sparse_update_keeps_final_result_and_payouts(self):
        previous = {
            "status": "確定",
            "finishers": [{"horseNumber": 1, "finish": 1},
                          {"horseNumber": 2, "finish": 2},
                          {"horseNumber": 3, "finish": 3}],
            "payouts": [{"type": "単勝", "amount": 120},
                        {"type": "馬連", "amount": 750}],
        }
        partial = {"status": "速報", "finishers": [{"horseNumber": 1, "finish": 1}],
                   "payouts": [{"type": "単勝", "amount": 120}]}
        after = merge_result(previous, partial)
        self.assertEqual(after["status"], "確定")
        self.assertEqual(after["finishers"], previous["finishers"])
        self.assertEqual(after["payouts"], previous["payouts"])
        detail = merge_detail({"id": "test-1", "result": previous, "horses": [{"horseNumber": 1}]},
                              {"id": "test-1", "result": partial, "horses": []})
        self.assertEqual(detail["result"], previous)
        self.assertEqual(len(detail["horses"]), 1)

    def test_new_complete_payout_supersedes_partial(self):
        initial = {"status": "速報", "finishers": [{"horseNumber": 1, "finish": 1}],
                   "payouts": [{"type": "単勝", "amount": 120}]}
        updated = {"status": "確定",
                   "finishers": [{"horseNumber": 1, "finish": 1},
                                 {"horseNumber": 2, "finish": 2},
                                 {"horseNumber": 3, "finish": 3}],
                   "payouts": [{"type": "単勝", "amount": 120},
                               {"type": "馬連", "amount": 750}]}
        result = merge_result(initial, updated)
        self.assertEqual(result["status"], "確定")
        self.assertEqual(len(result["finishers"]), 3)
        self.assertEqual(len(result["payouts"]), 2)


class OfficialNarResultParserTests(unittest.TestCase):
    @staticmethod
    def _html(split_col=False):
        heads = ["着順", "枠", "馬番", "馬名", "馬体重", "タイム"]
        if split_col:
            heads.append("上がり")
        lines = ["<html><body><h2>競走成績　確定</h2>",
                 "<table><tr>" + "".join("<th>" + v + "</th>" for v in heads) + "</tr>"]
        for i in range(1, 4):
            cells = [str(i), str(i), str(i), "競走馬" + str(i),
                     "480(+0)", "1:33.2"]
            if split_col:
                cells.append("37.4")
            lines.append("<tr>" + "".join("<td>" + v + "</td>" for v in cells) + "</tr>")
        lines.append("</table></body></html>")
        return "".join(lines).encode("cp932")

    def test_official_result_without_last3f_column(self):
        import app
        detail = {"id": "nar-2026-10-10-大井-01", "date": "2026-10-10",
                  "track": "大井", "raceNumber": 1,
                  "horses": [{"horseNumber": i, "name": "競走馬" + str(i)} for i in range(1, 4)]}
        with patch.object(app.urllib.request, "urlopen", return_value=io.BytesIO(self._html(False))):
            actual = app._nar_official_result_fast(detail)
        self.assertIsNotNone(actual, "NAR result without 上がり is still usable")
        self.assertEqual(actual["status"], "確定")
        self.assertEqual([x["finish"] for x in actual["finishers"]], [1, 2, 3])
        self.assertEqual([x["last3FSeconds"] for x in actual["finishers"]], [None, None, None])

    def test_official_result_with_last3f_column(self):
        import app
        detail = {"id": "nar-2026-10-10-大井-02", "date": "2026-10-10",
                  "track": "大井", "raceNumber": 2,
                  "horses": [{"horseNumber": i, "name": "競走馬" + str(i)} for i in range(1, 4)]}
        with patch.object(app.urllib.request, "urlopen", return_value=io.BytesIO(self._html(True))):
            actual = app._nar_official_result_fast(detail)
        self.assertIsNotNone(actual)
        self.assertEqual([x["last3FSeconds"] for x in actual["finishers"]], [37.4, 37.4, 37.4])


if __name__ == "__main__":
    unittest.main()
