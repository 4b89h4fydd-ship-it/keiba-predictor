"""NAR official parser: cornerPositions from the cornerPassTable section.

The official RaceMarkTable's per-horse コーナー通過順 cells are empty
in the raw HTML (the site fills them with JavaScript), so the parser
used to store cornerPositions=[] for every finisher even though the
same page carries the full passing order in its 全馬コーナー通過順
section (class cornerPassTable).  Production therefore never received
corner positions on the official path — the netkeiba fallback fixed
in PR #589 only runs when the official fetch fails — and the same-day
track-bias computation had no data.  The parser now fills any
finisher the column left blank from that section; a value the column
itself produced always wins, and a horse missing from one corner's
order gets None at that slot (the NAR公式CSV convention).
"""
import io
import unittest
from unittest.mock import patch

HEADERS = ["着順", "枠", "馬番", "馬名", "所属", "性齢", "負担 重量",
           "騎手 （所属）", "調教師", "馬体重 （増減）", "タイム", "着差",
           "上がり 3F", "コーナー 通過順", "人気", "単勝 オッズ"]

# Modelled on the real Oi 2026-11-19 5R official page (RaceMarkTable,
# babaCode 20): 10 finishers, the per-horse corner column empty, and
# the cornerPassTable rows below (horse numbers in passing order).
OOI_ORDERS = [
    ("１角", "(3,7),9,(1,4,10),8-2-6-5"),
    ("２角", "(3,7),9,(1,4,10)-8-2-6-5"),
    ("３角", "(3,7)-9-4,(10,8)-1-5,2=6"),
    ("４角", "(3,7)-9-4-8-10-1-(2,5)=6"),
]
OOI_FINISH = [9, 7, 3, 4, 1, 8, 10, 5, 2, 6]  # horse numbers by finish


def _html(finish_order, orders=None, corner_cells=None):
    lines = ["<html><body><h2>競走成績　確定</h2>",
             "<table><tr>" + "".join("<th>" + v + "</th>" for v in HEADERS) + "</tr>"]
    for i, no in enumerate(finish_order):
        corner = ""
        if corner_cells and no in corner_cells:
            corner = corner_cells[no]
        cells = [str(i + 1), "1", str(no), f"テスト{no}", "大井", "牡 4", "56.0",
                 "騎手 （大井）", "調教師", "500 (0)", "1:40.0", "", "40.0",
                 corner, "1", "2.0"]
        lines.append("<tr>" + "".join("<td>" + v + "</td>" for v in cells) + "</tr>")
    lines.append("</table>")
    if orders is not None:
        lines.append('<section class="cornerPassTable"><table>')
        for label, order in orders:
            lines.append("<tr><td>" + label + "</td><td>" + order + "</td></tr>")
        lines.append("</table></section>")
    lines.append("</body></html>")
    return "".join(lines).encode("cp932")


def _detail(nos, track="大井", race_no=5):
    return {"id": f"nar-2026-11-19-{track}-{race_no:02d}", "date": "2026-11-19",
            "track": track, "raceNumber": race_no,
            "horses": [{"horseNumber": no, "name": f"テスト{no}"} for no in nos]}


def _parse(html, detail):
    import app
    with patch.object(app.urllib.request, "urlopen",
                      return_value=io.BytesIO(html)):
        return app._nar_official_result_fast(detail)


def _by_no(result):
    return {int(f["horseNumber"]): f for f in result["finishers"]}


class NarOfficialCornersTests(unittest.TestCase):
    def test_ooi_corner_table_fills_blank_column(self):
        result = _parse(_html(OOI_FINISH, OOI_ORDERS), _detail(OOI_FINISH))
        self.assertIsNotNone(result)
        by_no = _by_no(result)
        self.assertEqual(by_no[9]["cornerPositions"], [3, 3, 3, 3])
        self.assertEqual(by_no[3]["cornerPositions"], [1, 1, 1, 1])
        self.assertEqual(by_no[7]["cornerPositions"], [1, 1, 1, 1])
        self.assertEqual(by_no[5]["cornerPositions"], [10, 10, 8, 8])
        self.assertEqual(by_no[2]["cornerPositions"], [8, 8, 9, 8])
        self.assertTrue(all(f["cornerPositions"] for f in result["finishers"]))

    def test_column_value_wins_over_table(self):
        result = _parse(_html(OOI_FINISH, OOI_ORDERS,
                              corner_cells={9: "2-2-2-2"}),
                        _detail(OOI_FINISH))
        by_no = _by_no(result)
        self.assertEqual(by_no[9]["cornerPositions"], [2, 2, 2, 2])
        self.assertEqual(by_no[3]["cornerPositions"], [1, 1, 1, 1])

    def test_sonoda_corner_word_labels(self):
        orders = [("１コーナー", "6,2,8,3"),
                  ("２コーナー", "6,2,3,8"),
                  ("３コーナー", "6,3,2,8"),
                  ("４コーナー", "6,3,8,2")]
        result = _parse(_html([6, 3, 8, 2], orders),
                        _detail([6, 3, 8, 2], track="園田", race_no=1))
        by_no = _by_no(result)
        self.assertEqual(by_no[6]["cornerPositions"], [1, 1, 1, 1])
        self.assertEqual(by_no[2]["cornerPositions"], [2, 2, 3, 4])

    def test_kasamatsu_straight_row_is_not_a_corner(self):
        orders = [("最初の直線", "7,2,4,3"),
                  ("第２コーナー", "2,7,4,3"),
                  ("第３コーナー", "2,4,7,3"),
                  ("第４コーナー", "2,4,3,7")]
        result = _parse(_html([7, 2, 4, 3], orders),
                        _detail([7, 2, 4, 3], track="笠松", race_no=1))
        by_no = _by_no(result)
        self.assertEqual(by_no[7]["cornerPositions"], [2, 3, 4])
        self.assertEqual(by_no[2]["cornerPositions"], [1, 1, 1])

    def test_missing_corner_row_slot_is_none(self):
        orders = [("１角", "3,9,4"), ("２角", "3,9"), ("３角", "3,9,4")]
        result = _parse(_html([3, 9, 4], orders), _detail([3, 9, 4]))
        by_no = _by_no(result)
        self.assertEqual(by_no[4]["cornerPositions"], [3, None, 3])
        self.assertEqual(by_no[3]["cornerPositions"], [1, 1, 1])

    def test_no_corner_section_keeps_empty(self):
        result = _parse(_html(OOI_FINISH, None), _detail(OOI_FINISH))
        self.assertIsNotNone(result)
        self.assertTrue(all(f["cornerPositions"] == []
                            for f in result["finishers"]))


if __name__ == "__main__":
    unittest.main()
