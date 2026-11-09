"""Race-day scratch accounting between the result and the card.

2026-11-01 Tokyo 6R/7R: a horse withdrawn on race day （取消） is
listed on the official result table with no placing. The stored
details carried that row as a finish=0 finisher while the card —
published before the withdrawal — marked no scratch, so the roster
count (15) never matched the placed finishers (14): result_state
read the races complete forever while the named audit failed their
finisher accounting on every run. These tests pin the repair: the
state judgement treats an unaccounted result-side scratch as
incomplete, and merge_detail stamps the card from the result.
"""
import copy
import unittest

from arvexq.results.state import merge_detail, result_state


def _detail(scratch_label="取消", card_scratched=False, label_key="finishLabel"):
    horses = [{"horseNumber": n, "name": f"H{n}", "scratched": False}
              for n in range(1, 16)]
    if card_scratched:
        horses[12]["scratched"] = True
    finishers = [{"finish": i + 1, "horseNumber": n, "finishLabel": f"{i + 1}着"}
                 for i, n in enumerate([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15])]
    finishers.append({"finish": 0, "horseNumber": 13, label_key: scratch_label})
    return {
        "id": "jra-2026-11-01-東京-06",
        "horses": horses,
        "result": {
            "status": "確定",
            "finishers": finishers,
            "payouts": [{"type": "単勝", "combination": "1", "amount": 200}],
        },
    }


class ScratchAccountingTests(unittest.TestCase):
    def test_unaccounted_scratch_row_is_not_final(self):
        final, _, _ = result_state(_detail())
        self.assertFalse(final)

    def test_merge_stamps_card_and_restores_final(self):
        stored = _detail()
        fresh = {"id": stored["id"], "result": copy.deepcopy(stored["result"])}
        merged = merge_detail(stored, fresh)
        horse13 = next(h for h in merged["horses"] if h["horseNumber"] == 13)
        self.assertTrue(horse13["scratched"])
        self.assertEqual(horse13["status"], "出走取消")
        # No horse removed, no other card field touched.
        self.assertEqual(len(merged["horses"]), 15)
        final, payout_ok, _ = result_state(merged)
        self.assertTrue(final)
        self.assertTrue(payout_ok)

    def test_card_already_scratched_reads_final_without_merge(self):
        final, _, _ = result_state(_detail(card_scratched=True))
        self.assertTrue(final)

    def test_excluded_label_stamps_competition_exclusion(self):
        stored = _detail(scratch_label="競走除外")
        merged = merge_detail(stored, {"id": stored["id"],
                                       "result": copy.deepcopy(stored["result"])})
        horse13 = next(h for h in merged["horses"] if h["horseNumber"] == 13)
        self.assertTrue(horse13["scratched"])
        self.assertEqual(horse13["status"], "競走除外")

    def test_did_not_finish_row_never_stamps_a_scratch(self):
        # 中止 (stopped mid-race) is a starter, not a scratch: the row
        # must neither block finality nor mark the card.
        stored = _detail(scratch_label="中止")
        final, _, _ = result_state(stored)
        self.assertTrue(final)
        merged = merge_detail(stored, {"id": stored["id"],
                                       "result": copy.deepcopy(stored["result"])})
        horse13 = next(h for h in merged["horses"] if h["horseNumber"] == 13)
        self.assertFalse(horse13["scratched"])

    def test_cardless_skeleton_detail_is_not_judged(self):
        # Skeleton-seeded details (2026-10-31 repair) carry a result
        # but no card: there is no roster to disagree with, and the
        # lane must not chase them forever.
        stored = _detail()
        del stored["horses"]
        final, _, _ = result_state(stored)
        self.assertTrue(final)

    def test_nonfinisher_entry_also_accounts(self):
        stored = _detail()
        row = stored["result"]["finishers"].pop()
        stored["result"]["nonFinishers"] = [row]
        final, _, _ = result_state(stored)
        self.assertFalse(final)  # still unaccounted on the card
        merged = merge_detail(stored, {"id": stored["id"],
                                       "result": copy.deepcopy(stored["result"])})
        final, _, _ = result_state(merged)
        self.assertTrue(final)


if __name__ == "__main__":
    unittest.main()
