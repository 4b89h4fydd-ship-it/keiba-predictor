"""result_state: accounted non-finishers are not missing finishers.

Regression for the day summaries stuck at 速報: Kanazawa 8R
(2026-11-23) and Urawa 2R (2026-11-24) hold complete official
result blocks (status 確定, podium, full payouts) with one horse
recorded in ``nonFinishers`` as 中止 (stopped mid-race).  The
runner-coverage guard compared only ``len(finishers)`` against the
card's active runners, so such a race could never be judged final:
the repair lane re-fetched it on every run and its payload summary
stayed 速報 forever.  Three more races of the same shape were live
on 2026-11-25 (Sonoda 10R, Urawa 8R, Urawa 12R).

The accounting mirrors finisher_completeness in
arvexq.results.audit: a starter accounted for as a non-finisher
(a finish<=0 row in finishers / nonFinishers carrying a 中止・
失格・落馬・転倒 marker, or a card status carrying the marker)
counts as accounted.  A horse silently dropped with NO accounting
(the 2026-11-07 Kochi 5R pattern the guard was written for) must
still fail.
"""
from __future__ import annotations

import unittest

from arvexq.results.state import result_state


def make_detail(runners=10, placed=9, non_finishers=(),
                finishers_extra=(), card_status=None):
    """A final NAR-style block: `placed` placed finishers out of
    `runners` card horses, plus optional non-finisher accounting."""
    horses = []
    for no in range(1, runners + 1):
        horse = {"horseNumber": no, "name": f"馬{no}",
                 "scratched": False, "status": ""}
        if card_status and no in card_status:
            horse["status"] = card_status[no]
        horses.append(horse)
    finishers = [{"horseNumber": no, "finish": no}
                 for no in range(1, placed + 1)]
    finishers.extend(finishers_extra)
    result = {
        "status": "確定",
        "finishers": finishers,
        "payouts": [{"type": "単勝", "combination": "1",
                     "amount": 250, "popularity": 1}],
    }
    if non_finishers:
        result["nonFinishers"] = list(non_finishers)
    return {"id": "nar-2026-11-23-金沢-08", "date": "2026-11-23",
            "track": "金沢", "raceNumber": 8, "fieldSize": runners,
            "horses": horses, "result": result}


def stopped(no):
    return {"horseNumber": no, "finish": 0, "finishLabel": "中止",
            "status": "中止", "marginText": "中止"}


class NonFinisherAccountingTest(unittest.TestCase):
    def test_nonfinisher_entry_accounts_for_the_missing_runner(self):
        # Kanazawa 8R shape: 10 runners, 9 finishers, horse 4 中止.
        detail = make_detail(non_finishers=[stopped(10)])
        self.assertEqual(result_state(detail), (True, True, "確定"))

    def test_disqualified_nonfinisher_counts(self):
        detail = make_detail(non_finishers=[
            {"horseNumber": 10, "finish": 0, "finishLabel": "失格",
             "status": "失格", "marginText": "失格"}])
        self.assertEqual(result_state(detail), (True, True, "確定"))

    def test_silently_dropped_horse_still_fails(self):
        # Kochi 5R pattern: no accounting anywhere for horse 10.
        detail = make_detail()
        self.assertEqual(result_state(detail), (False, True, "確定"))

    def test_unlabelled_nonfinisher_row_does_not_account(self):
        detail = make_detail(non_finishers=[
            {"horseNumber": 10, "finish": 0, "finishLabel": "",
             "status": "", "marginText": ""}])
        self.assertEqual(result_state(detail), (False, True, "確定"))

    def test_stopped_row_inside_finishers_counts(self):
        detail = make_detail(placed=9, finishers_extra=[stopped(10)])
        self.assertEqual(result_state(detail), (True, True, "確定"))

    def test_card_status_marker_accounts(self):
        detail = make_detail(card_status={10: "競走中止"})
        self.assertEqual(result_state(detail), (True, True, "確定"))

    def test_two_missing_one_accounted_still_fails(self):
        detail = make_detail(runners=11, placed=9,
                             non_finishers=[stopped(10)])
        self.assertEqual(result_state(detail), (False, True, "確定"))

    def test_complete_finisher_list_unchanged(self):
        detail = make_detail(runners=10, placed=10)
        self.assertEqual(result_state(detail), (True, True, "確定"))


if __name__ == "__main__":
    unittest.main()
