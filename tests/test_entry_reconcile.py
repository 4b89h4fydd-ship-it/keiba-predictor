"""Unit tests for the canonical entry reconciliation route.

The principle under test (2026-11-28): the official card and the
netkeiba card are two readings of the SAME real racecard, so a
disagreement is a bug in one reading.  Given a shifted/permuted
input, the route must produce output that matches the true card —
never a mix of the two readings, and never a stop.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arvexq.ingest.entry_reconcile import (
    dedupe_roster_by_name,
    frame_for_number,
    graft_field_by_name,
    identity_map,
    merge_rows_by_name,
    numbering_report,
    reconcile_detail_numbers,
    reconcile_finisher_flags,
    reconcile_rosters,
)


def roster(names_numbers_frames):
    return [{"name": n, "horseNumber": no, "frameNumber": fr}
            for n, no, fr in names_numbers_frames]


# The true Kyoto 9R card of 2026-11-28 (13 runners), from the
# netkeiba entry table verified against the official card that day.
KYOTO9_TRUE = [
    ("ロイスター", 1, 1), ("テイエムパイロット", 2, 2),
    ("ストロングエース", 3, 3), ("タイキインドラ", 4, 4),
    ("マハートマーベル", 5, 4), ("ジーニアスバローズ", 6, 5),
    ("リメンバーヒム", 7, 5), ("スカイドゥエラー", 8, 6),
    ("フォーワンセルフ", 9, 6), ("クリノラピダス", 10, 7),
    ("アートレスマインド", 11, 7), ("レッドイステル", 12, 8),
    ("ナイトスラッガー", 13, 8),
]


class FrameMapTest(unittest.TestCase):
    def test_known_fields(self):
        self.assertEqual([frame_for_number(n, 13) for n in range(1, 14)],
                         [1, 2, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8])
        self.assertEqual([frame_for_number(n, 16) for n in range(1, 17)],
                         [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8])
        self.assertEqual([frame_for_number(n, 18) for n in range(1, 19)],
                         [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 7, 8, 8, 8])
        self.assertEqual([frame_for_number(n, 8) for n in range(1, 9)],
                         [1, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(frame_for_number(0, 13), 0)
        self.assertEqual(frame_for_number(14, 13), 0)


class ReconcileTest(unittest.TestCase):
    def test_permuted_secondary_is_corrected_to_truth(self):
        official = roster(KYOTO9_TRUE)
        # netkeiba reading with the numbers rotated by one (the frame
        # column still describes the true gates, as it is read from a
        # different page feature): internally inconsistent.
        shifted = roster([(n, (no % 13) + 1, fr) for n, no, fr in KYOTO9_TRUE])
        rows, report = reconcile_rosters(official, shifted,
                                         primary_label="official",
                                         secondary_label="netkeiba")
        self.assertEqual(identity_map(rows),
                         {n: no for n, no, _ in KYOTO9_TRUE})
        self.assertEqual(report["identitySource"], "official")
        self.assertTrue(report["corrections"])
        self.assertTrue(all(c["correctedSide"] == "netkeiba"
                            for c in report["corrections"]))

    def test_permuted_primary_is_corrected_to_truth(self):
        shifted = roster([(n, (no % 13) + 1, fr) for n, no, fr in KYOTO9_TRUE])
        netkeiba = roster(KYOTO9_TRUE)
        rows, report = reconcile_rosters(shifted, netkeiba,
                                         primary_label="official",
                                         secondary_label="netkeiba")
        self.assertEqual(identity_map(rows),
                         {n: no for n, no, _fr in KYOTO9_TRUE})
        self.assertEqual(report["identitySource"], "netkeiba")

    def test_single_source_horse_is_kept_and_flagged(self):
        official = roster(KYOTO9_TRUE)
        partial = roster(KYOTO9_TRUE[:-1])  # one reading missed a horse
        rows, report = reconcile_rosters(official, partial)
        self.assertEqual(len(rows), 13)
        self.assertEqual(report["singleSource"], ["ナイトスラッガー"])

    def test_agreeing_readings_have_no_corrections(self):
        rows, report = reconcile_rosters(roster(KYOTO9_TRUE),
                                         roster(KYOTO9_TRUE))
        self.assertEqual(report["corrections"], [])
        self.assertEqual(identity_map(rows),
                         {n: no for n, no, _ in KYOTO9_TRUE})


class MergeByNameTest(unittest.TestCase):
    def test_permuted_fresh_can_never_renumber(self):
        # The garble shape: right horses, wrong numbers.  The merge
        # must leave every identity exactly as the base had it, and
        # must surface every disagreement instead of absorbing it.
        # Materials still follow the name (they were read from the
        # same source row as the name), but no number ever crosses.
        base = roster(KYOTO9_TRUE)
        fresh = roster([(n, (no % 13) + 1, fr) for n, no, fr in KYOTO9_TRUE])
        for h in fresh:
            h["winOdds"] = 9.9
        disagreements = []
        out = merge_rows_by_name(base, fresh,
                                 disagreements=disagreements)
        self.assertEqual(identity_map(out),
                         {n: no for n, no, _ in KYOTO9_TRUE})
        self.assertEqual(len(disagreements), 13)
        by_name = {h["name"]: h for h in out}
        self.assertTrue(all(by_name[n]["winOdds"] == 9.9
                            for n, _, _ in KYOTO9_TRUE))
        self.assertTrue(all(by_name[n]["frameNumber"] == fr
                            for n, _, fr in KYOTO9_TRUE))

    def test_agreeing_fresh_materials_merge_identity_untouched(self):
        base = roster(KYOTO9_TRUE)
        fresh = roster(KYOTO9_TRUE)
        fresh[0]["winOdds"] = 3.1
        fresh[0]["horseNumber"] = 1
        out = merge_rows_by_name(base, fresh)
        self.assertEqual(out[0]["winOdds"], 3.1)
        self.assertEqual(out[0]["horseNumber"], 1)

    def test_unknown_fresh_horse_appended_with_own_identity(self):
        base = roster(KYOTO9_TRUE[:3])
        fresh = roster(KYOTO9_TRUE[3:4])
        out = merge_rows_by_name(base, fresh)
        self.assertEqual(identity_map(out)[KYOTO9_TRUE[3][0]], 4)


class GraftByNameTest(unittest.TestCase):
    def test_graft_skips_number_disagreement(self):
        target = roster(KYOTO9_TRUE)
        donor = roster([(n, (no % 13) + 1, fr) for n, no, fr in KYOTO9_TRUE])
        for h in donor:
            h["researchEvidence"] = {"score": 1}
        moved = graft_field_by_name(target, donor, "researchEvidence")
        self.assertEqual(moved, 0)
        self.assertFalse(any("researchEvidence" in h for h in target))

    def test_graft_applies_on_agreement(self):
        target = roster(KYOTO9_TRUE)
        donor = roster(KYOTO9_TRUE)
        donor[2]["researchEvidence"] = {"score": 7}
        moved = graft_field_by_name(target, donor, "researchEvidence")
        self.assertEqual(moved, 1)
        self.assertEqual(target[2]["researchEvidence"], {"score": 7})


class DedupeTest(unittest.TestCase):
    def test_phantom_duplicate_collapses_to_witnessed_number(self):
        rows = roster(KYOTO9_TRUE)
        # The 2026-11-28 Kyoto 9R phantom shape: the same horse again
        # at the end of the card under a second number.
        rows.append({"name": "ロイスター", "horseNumber": 18,
                     "frameNumber": 8, "winOdds": 2.5})
        report = []
        out = dedupe_roster_by_name(rows, report=report)
        self.assertEqual(len(out), 13)
        self.assertEqual(identity_map(out)["ロイスター"], 1)
        self.assertEqual(report[0]["keptNumber"], 1)
        self.assertEqual(report[0]["droppedNumbers"], [18])
        # Materials from the phantom row are not lost, only its
        # identity is.
        self.assertEqual(out[0]["winOdds"], 2.5)


class NumberingReportTest(unittest.TestCase):
    def test_permutation_is_clean_but_frames_betray_it(self):
        shifted = roster([(n, (no % 13) + 1, fr) for n, no, fr in KYOTO9_TRUE])
        rep = numbering_report(shifted)
        self.assertTrue(rep["clean"])
        self.assertLess(rep["frameMatches"], rep["frameKnown"])


def tokyo9_detail():
    """The 2026-11-28 Tokyo 9R shape: two horses the official result
    records as 6th in a dead heat carry the morning collection's
    wrong 除外 marking in the roster blocks."""
    return {
        "horses": [
            {"name": "ローズマイスター", "horseNumber": 4,
             "scratched": True, "status": "除外"},
            {"name": "リラゲイル", "horseNumber": 12,
             "scratched": True, "status": "除外"},
            {"name": "ウィロークリーク", "horseNumber": 11,
             "scratched": False, "status": ""},
        ],
        "raceCardView": [
            {"name": "ローズマイスター", "horseNumber": 4,
             "scratched": True},
            {"name": "リラゲイル", "horseNumber": 12,
             "scratched": True},
            {"name": "ウィロークリーク", "horseNumber": 11,
             "scratched": False},
        ],
        "result": {
            "status": "確定",
            "finishers": [
                {"name": "ウィロークリーク", "horseNumber": 11,
                 "finish": 1},
                {"name": "ローズマイスター", "horseNumber": 4,
                 "finish": 6},
                {"name": "リラゲイル", "horseNumber": 12,
                 "finish": 6},
            ],
        },
    }


class FinisherFlagTest(unittest.TestCase):
    def test_finisher_markings_cleared_in_every_roster_block(self):
        detail = tokyo9_detail()
        entries = reconcile_finisher_flags(detail)
        self.assertEqual(len(entries), 4)
        for row in detail["horses"][:2] + detail["raceCardView"][:2]:
            self.assertFalse(row["scratched"])
        self.assertEqual(detail["horses"][0]["status"], "")
        self.assertEqual(detail["horses"][1]["status"], "")

    def test_genuine_scratch_keeps_its_marking(self):
        # A finish=0 row labelled 取消 is the result's own scratch
        # accounting: that horse did NOT run and its marking stands.
        detail = tokyo9_detail()
        detail["horses"].append(
            {"name": "ネーロノワール", "horseNumber": 9,
             "scratched": True, "status": "出走取消"})
        detail["result"]["finishers"].append(
            {"name": "ネーロノワール 牝2 川田 55.0 栗東・斉藤崇",
             "horseNumber": 9, "finish": 0, "finishLabel": "取消"})
        entries = reconcile_finisher_flags(detail)
        row = detail["horses"][-1]
        self.assertTrue(row["scratched"])
        self.assertEqual(row["status"], "出走取消")
        self.assertFalse(any(e["name"] == "ネーロノワール"
                             for e in entries))

    def test_no_result_no_change(self):
        detail = tokyo9_detail()
        del detail["result"]
        self.assertEqual(reconcile_finisher_flags(detail), [])
        self.assertTrue(detail["horses"][0]["scratched"])

    def test_clearing_is_by_name_not_number(self):
        # The Kyoto 11R garble shape: the roster row sits under a
        # shifted number.  The marking must still be cleared — the
        # name is the identity, the number is the corrupted reading.
        detail = tokyo9_detail()
        detail["horses"][0]["horseNumber"] = 9
        entries = reconcile_finisher_flags(detail)
        self.assertFalse(detail["horses"][0]["scratched"])
        self.assertTrue(any(e["name"] == "ローズマイスター"
                            and e["number"] == 9 for e in entries))

    def test_clean_detail_untouched(self):
        detail = tokyo9_detail()
        for row in detail["horses"]:
            row["scratched"] = False
            row["status"] = ""
        for row in detail["raceCardView"]:
            row["scratched"] = False
        self.assertEqual(reconcile_finisher_flags(detail), [])


def permuted_detail():
    """The Kyoto 11R garble shape in miniature: no duplicate names,
    but the roster's numbering is a permuted reading (frames lost),
    while the official result accounts for every horse by name,
    number and frame.  One horse is a genuine scratch whose marking
    the stored roster lost.  Each roster row carries a per-horse
    payload (winProbability / mark) that must stay with its NAME."""
    return {
        "horses": [
            {"name": "サノノキセキ", "horseNumber": 1, "frameNumber": 0,
             "winProbability": 0.30, "mark": "◎", "scratched": False,
             "status": ""},
            {"name": "ネーロノワール", "horseNumber": 2, "frameNumber": 0,
             "winProbability": 0.0, "mark": "", "scratched": False,
             "status": ""},
            {"name": "ドラゴンバルド", "horseNumber": 9, "frameNumber": 0,
             "winProbability": 0.10, "mark": "▲", "scratched": True,
             "status": "出走取消"},
            {"name": "アーケントレイル", "horseNumber": 10,
             "frameNumber": 0, "winProbability": 0.20, "mark": "○",
             "scratched": False, "status": ""},
        ],
        "raceCardView": [
            {"name": "サノノキセキ", "number": 1, "frame": None,
             "scratched": False},
            {"name": "ネーロノワール", "number": 2, "frame": None,
             "scratched": False},
            {"name": "ドラゴンバルド", "number": 9, "frame": None,
             "scratched": True},
            {"name": "アーケントレイル", "number": 10, "frame": None,
             "scratched": False},
        ],
        "horseFeatures": [
            {"horseNumber": 1, "samples": 11},
            {"horseNumber": 2, "samples": 22},
            {"horseNumber": 9, "samples": 99},
            {"horseNumber": 10, "samples": 44},
        ],
        "result": {
            "status": "確定",
            "finishers": [
                {"name": "アーケントレイル", "horseNumber": 1,
                 "frameNumber": 1, "finish": 2},
                {"name": "ネーロノワール 牝2 川田 55.0 栗東・斉藤崇",
                 "horseNumber": 9, "frameNumber": 7, "finish": 0,
                 "finishLabel": "取消"},
                {"name": "ドラゴンバルド", "horseNumber": 10,
                 "frameNumber": 8, "finish": 7},
                {"name": "サノノキセキ", "horseNumber": 11,
                 "frameNumber": 8, "finish": 5},
            ],
        },
    }


class DetailNumbersTest(unittest.TestCase):
    def test_permuted_roster_renumbered_by_name_everywhere(self):
        detail = permuted_detail()
        entries = reconcile_detail_numbers(detail)
        self.assertTrue(entries)
        by_name = {r["name"]: r for r in detail["horses"]}
        self.assertEqual(by_name["サノノキセキ"]["horseNumber"], 11)
        self.assertEqual(by_name["サノノキセキ"]["frameNumber"], 8)
        self.assertEqual(by_name["ネーロノワール"]["horseNumber"], 9)
        self.assertEqual(by_name["ネーロノワール"]["frameNumber"], 7)
        self.assertEqual(by_name["ドラゴンバルド"]["horseNumber"], 10)
        self.assertEqual(by_name["アーケントレイル"]["horseNumber"], 1)
        # Blocks are re-sorted by the official number.
        self.assertEqual([r["horseNumber"] for r in detail["horses"]],
                         [1, 9, 10, 11])
        view = {r["name"]: r for r in detail["raceCardView"]}
        self.assertEqual(view["サノノキセキ"]["number"], 11)
        # A None frame means the view carries no frames: left alone.
        self.assertIsNone(view["サノノキセキ"]["frame"])

    def test_materials_stay_with_the_name(self):
        # The mark and the probability were computed for the horse
        # (the name on the row); renumbering must not move them to
        # whichever horse previously held the new number.
        detail = permuted_detail()
        reconcile_detail_numbers(detail)
        by_name = {r["name"]: r for r in detail["horses"]}
        self.assertEqual(by_name["サノノキセキ"]["mark"], "◎")
        self.assertEqual(by_name["サノノキセキ"]["winProbability"],
                         0.30)
        self.assertEqual(by_name["アーケントレイル"]["mark"], "○")
        self.assertEqual(by_name["アーケントレイル"]["horseNumber"],
                         1)

    def test_number_only_blocks_follow_the_permutation(self):
        detail = permuted_detail()
        reconcile_detail_numbers(detail)
        feats = {r["horseNumber"]: r["samples"]
                 for r in detail["horseFeatures"]}
        # The feature row stored under the garbled number belongs
        # to the horse the roster had under that number: garbled 1
        # was サノノキセキ, whose official number is 11.
        self.assertEqual(feats, {11: 11, 9: 22, 10: 99, 1: 44})

    def test_genuine_scratch_marking_restored(self):
        detail = permuted_detail()
        entries = reconcile_detail_numbers(detail)
        by_name = {r["name"]: r for r in detail["horses"]}
        self.assertTrue(by_name["ネーロノワール"]["scratched"])
        self.assertEqual(by_name["ネーロノワール"]["status"],
                         "出走取消")
        view = {r["name"]: r for r in detail["raceCardView"]}
        self.assertTrue(view["ネーロノワール"]["scratched"])
        self.assertTrue(any(e.get("restored")
                            and e["name"] == "ネーロノワール"
                            for e in entries))

    def test_existing_scratch_spelling_not_rewritten(self):
        # Kochi 10R shape (2026-11-28): the result's non-finisher
        # label is 除外 while the roster already carries the more
        # specific 競走除外.  Restoration fills only what is
        # missing; it never rewrites an existing scratch marking.
        detail = permuted_detail()
        detail["result"]["finishers"] = [
            r for r in detail["result"]["finishers"]
            if "ネーロ" not in str(r.get("name"))]
        detail["result"]["nonFinishers"] = [
            {"name": "ネーロノワール", "horseNumber": 9,
             "frameNumber": 7, "finish": 0, "finishLabel": "除外"}]
        row = {r["name"]: r for r in detail["horses"]}["ネーロノワール"]
        row["scratched"] = True
        row["status"] = "競走除外"
        entries = reconcile_detail_numbers(detail)
        self.assertEqual(row["status"], "競走除外")
        # The horses row needed nothing; the raceCardView row's
        # missing flag is still restored, as it should be.
        self.assertFalse(any(e.get("restored")
                             and e["name"] == "ネーロノワール"
                             and e["block"] == "horses"
                             for e in entries))

    def test_no_result_no_change(self):
        detail = permuted_detail()
        del detail["result"]
        before = [dict(r) for r in detail["horses"]]
        self.assertEqual(reconcile_detail_numbers(detail), [])
        self.assertEqual(detail["horses"], before)

    def test_partial_result_no_change(self):
        # A flash result that does not account for the whole roster
        # must not renumber anything.
        detail = permuted_detail()
        detail["result"]["finishers"] = \
            detail["result"]["finishers"][:2]
        self.assertEqual(reconcile_detail_numbers(detail), [])
        self.assertEqual(detail["horses"][0]["horseNumber"], 1)

    def test_duplicate_names_left_to_the_dedupe_pass(self):
        detail = permuted_detail()
        detail["horses"].append(dict(detail["horses"][0]))
        self.assertEqual(reconcile_detail_numbers(detail), [])

    def test_clean_detail_untouched(self):
        detail = permuted_detail()
        reconcile_detail_numbers(detail)
        self.assertEqual(reconcile_detail_numbers(detail), [])


if __name__ == "__main__":
    unittest.main()
