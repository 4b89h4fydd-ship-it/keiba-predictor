"""Existing manual Stage64 freeze accepts original saved arrays but not partial Prefetch."""
import unittest

from scripts.arvexq_stage64_capture_artifact import saved_race_rows


def race(owner, number):
    return {"id": f"{owner}-2026-10-22-試験場-{number:02d}",
            "date": "2026-10-22", "circuit": owner, "startTime": "14:00"}


class ManualArtifactSource(unittest.TestCase):
    def test_complete_prefetch_accepts_both_circuits_without_reordering(self):
        jra, nar = race("jra", 1), race("nar", 2)
        source = {"races": [jra, nar], "details": [nar, jra]}
        self.assertEqual(saved_race_rows(source), [nar, jra])
        self.assertEqual(source["races"], [jra, nar])

    def test_partial_extra_and_duplicate_prefetch_rejected(self):
        jra, nar, extra = race("jra", 1), race("nar", 2), race("jra", 3)
        for source in (
            {"races": [jra, nar], "details": [jra]},
            {"races": [jra], "details": [jra, extra]},
            {"races": [jra, jra], "details": [jra]},
            {"races": [jra], "details": [jra, jra]},
            {"races": [], "details": [jra]},
        ):
            with self.subTest(source=source), self.assertRaisesRegex(
                ValueError, "races/details identity mismatch"
            ):
                saved_race_rows(source)

    def test_invalid_index_and_detail_ids_rejected(self):
        row = race("nar", 1)
        for index in (None, [None], [{"id": ""}], [{"id": 7}]):
            with self.subTest(index=index), self.assertRaisesRegex(
                ValueError, "race index invalid"
            ):
                saved_race_rows({"races": index, "details": [row]})
        for detail in (None, {}, {"id": []}, {"id": 7}):
            with self.subTest(detail=detail), self.assertRaisesRegex(
                ValueError, "detail identity invalid"
            ):
                saved_race_rows({"races": [row], "details": [detail]})

    def test_legacy_detail_only_saved_input_preserved(self):
        row = race("jra", 1)
        self.assertEqual(saved_race_rows([row]), [row])
        self.assertEqual(saved_race_rows({"details": [row]}), [row])
        self.assertEqual(saved_race_rows({"races": [], "details": []}), [])
        for source in (None, {}, {"details": None}, {"details": {}}):
            with self.subTest(source=source), self.assertRaisesRegex(
                ValueError, "race array or details array"
            ):
                saved_race_rows(source)


if __name__ == "__main__":
    unittest.main()
