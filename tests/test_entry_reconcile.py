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


if __name__ == "__main__":
    unittest.main()
