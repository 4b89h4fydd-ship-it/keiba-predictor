"""NAR official parser: non-finisher recording (follow-up 3, 2026-11-08).

The official RaceMarkTable accounts for every horse that started,
including one that stopped mid-race (競走中止): its row carries a
blank 着順 and the status text in the 着差 cell.  The parser used to
skip any row whose 着順 was not a bare integer, so the stored detail
silently dropped the horse (2026-11-07 Kochi 5R, 2番 ゲクウ) and the
named audit's finisher_completeness check failed with
finisher_count_short even though the stored finishers were exactly
the official finisher list.  The parser now records such rows in a
``nonFinishers`` list on the result dict; finishers, the podium gate
and every finisher count are unchanged.
"""
import copy
import io
import unittest
from unittest.mock import patch

from arvexq.results.audit import audit_detail

HEADERS = ["着順", "枠", "馬番", "馬名", "所属", "性齢", "負担 重量",
           "騎手 （所属）", "調教師", "馬体重 （増減）", "タイム", "着差",
           "上がり 3F", "コーナー 通過順", "人気", "単勝 オッズ"]

# Modelled on the real Kochi 2026-11-07 5R official table
# (keiba.go.jp RaceMarkTable, babaCode 31): 9 numeric finishers plus
# ゲクウ (馬番2, 着順 blank, 着差 「中止」, 馬体重 523(-2), 1番人気).
KOCHI_ROWS = [
    ["1", "7", "7", "クルマトラサン", "487 (7)", "1:26.7", "", "4", "10.3"],
    ["2", "8", "10", "タイキエクセロン", "514 (1)", "1:26.8", "1/2", "3", "4.7"],
    ["3", "1", "1", "エナジーアユ", "436 (-1)", "1:27.0", "3/4", "2", "2.6"],
    ["4", "3", "3", "ペイシャプレイ", "430 (0)", "1:27.0", "ハナ", "8", "43.7"],
    ["5", "4", "4", "リゼレインボー", "504 (2)", "1:27.0", "クビ", "7", "36.0"],
    ["6", "5", "5", "ローメット", "422 (-9)", "1:27.4", "2", "6", "23.8"],
    ["7", "7", "8", "セントキルダ", "482 (0)", "1:27.6", "1", "10", "237.4"],
    ["8", "8", "9", "シシフンジン", "472 (6)", "1:27.9", "1.1/2", "5", "14.3"],
    ["9", "6", "6", "トーケンタカハール", "467 (1)", "1:28.3", "2", "9", "142.9"],
    ["", "2", "2", "ゲクウ", "523 (-2)", "", "中止", "1", "2.5"],
]

KOCHI_HORSES = [(1, "エナジーアユ"), (2, "ゲクウ"), (3, "ペイシャプレイ"),
                (4, "リゼレインボー"), (5, "ローメット"),
                (6, "トーケンタカハール"), (7, "クルマトラサン"),
                (8, "セントキルダ"), (9, "シシフンジン"),
                (10, "タイキエクセロン")]


def _html(rows):
    lines = ["<html><body><h2>競走成績　確定</h2>",
             "<table><tr>" + "".join("<th>" + v + "</th>" for v in HEADERS) + "</tr>"]
    for fin, frame, no, name, bw, tm, margin, pop, odds in rows:
        cells = [fin, frame, no, name, "高知", "牡 4", "57.0", "騎手 （高知）",
                 "調教師", bw, tm, margin, "40.0", "", pop, odds]
        lines.append("<tr>" + "".join("<td>" + v + "</td>" for v in cells) + "</tr>")
    lines.append("</table></body></html>")
    return "".join(lines).encode("cp932")


def _detail(horses, race_no=5):
    return {"id": f"nar-2026-11-07-高知-{race_no:02d}", "date": "2026-11-07",
            "track": "高知", "raceNumber": race_no,
            "horses": [{"horseNumber": no, "name": name} for no, name in horses]}


def _parse(rows, horses, race_no=5):
    import app
    with patch.object(app.urllib.request, "urlopen",
                      return_value=io.BytesIO(_html(rows))):
        return app._nar_official_result_fast(_detail(horses, race_no))


class NarNonFinisherParserTests(unittest.TestCase):
    def test_kochi_non_finisher_is_recorded_not_dropped(self):
        actual = _parse(KOCHI_ROWS, KOCHI_HORSES)
        self.assertIsNotNone(actual)
        self.assertEqual(actual["status"], "確定")
        self.assertEqual(
            [(f["finish"], f["horseNumber"]) for f in actual["finishers"]],
            [(1, 7), (2, 10), (3, 1), (4, 3), (5, 4),
             (6, 5), (7, 8), (8, 9), (9, 6)])
        self.assertEqual(actual["nonFinishers"], [{
            "horseNumber": 2, "name": "ゲクウ", "finish": 0,
            "finishLabel": "中止", "status": "中止", "marginText": "中止",
            "bodyWeight": 523, "bodyWeightChange": -2,
        }])
        self.assertNotIn(2, [f["horseNumber"] for f in actual["finishers"]])

    def test_clean_all_finisher_race_has_no_non_finishers_key(self):
        rows = [r for r in KOCHI_ROWS if r[0]][:4]
        horses = [(int(r[2]), r[3]) for r in rows]
        actual = _parse(rows, horses, race_no=6)
        self.assertIsNotNone(actual)
        self.assertNotIn("nonFinishers", actual)
        self.assertEqual(
            [(f["finish"], f["horseNumber"]) for f in actual["finishers"]],
            [(1, 7), (2, 10), (3, 1), (4, 3)])

    def test_blank_finish_without_status_marker_is_still_skipped(self):
        rows = [r for r in KOCHI_ROWS if r[0]][:3] + [
            ["", "2", "2", "ゲクウ", "523 (-2)", "", "", "1", "2.5"]]
        horses = [(7, "クルマトラサン"), (10, "タイキエクセロン"),
                  (1, "エナジーアユ"), (2, "ゲクウ")]
        actual = _parse(rows, horses, race_no=7)
        self.assertIsNotNone(actual)
        self.assertNotIn("nonFinishers", actual)
        self.assertEqual(len(actual["finishers"]), 3)


PAYOUTS = [
    {"type": "単勝", "combination": "7", "amount": 1030},
    {"type": "複勝", "combination": "7", "amount": 130},
    {"type": "複勝", "combination": "10", "amount": 140},
    {"type": "複勝", "combination": "1", "amount": 120},
    {"type": "枠連", "combination": "7-8", "amount": 930},
    {"type": "馬連", "combination": "7-10", "amount": 1480},
    {"type": "馬単", "combination": "7-10", "amount": 3280},
    {"type": "ワイド", "combination": "7-10", "amount": 320},
    {"type": "ワイド", "combination": "1-7", "amount": 190},
    {"type": "ワイド", "combination": "1-10", "amount": 300},
    {"type": "3連複", "combination": "1-7-10", "amount": 1010},
    {"type": "3連単", "combination": "7-10-1", "amount": 12080},
]


class NarNonFinisherAuditIntegrationTests(unittest.TestCase):
    """The parser-shaped result passes finisher_completeness; the same
    detail without the nonFinishers accounting still fails by name."""

    def _detail_with_result(self, result):
        detail = _detail(KOCHI_HORSES)
        for horse in detail["horses"]:
            horse["scratched"] = False
        detail["result"] = result
        return detail

    def test_audit_both_directions(self):
        parsed = _parse(KOCHI_ROWS, KOCHI_HORSES)
        result = {"status": "確定", "finishers": parsed["finishers"],
                  "nonFinishers": parsed["nonFinishers"], "payouts": PAYOUTS}
        detail = self._detail_with_result(copy.deepcopy(result))
        failures = audit_detail(detail, expected_race_id=detail["id"])
        self.assertNotIn(
            ("finisher_completeness", "finisher_count_short"),
            {(f["check"], f["failure_class"]) for f in failures})

        stripped = copy.deepcopy(result)
        del stripped["nonFinishers"]
        detail = self._detail_with_result(stripped)
        failures = audit_detail(detail, expected_race_id=detail["id"])
        short = [f for f in failures
                 if f["failure_class"] == "finisher_count_short"]
        self.assertEqual(len(short), 1)
        self.assertEqual(short[0]["expected"], 10)
        self.assertEqual(short[0]["actual"], 9)
        self.assertEqual(short[0]["missing_horse_numbers"], [2])


if __name__ == "__main__":
    unittest.main()
