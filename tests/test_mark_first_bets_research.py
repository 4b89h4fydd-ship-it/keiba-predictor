import unittest
from arvexq.prediction.mark_first_bets_research import assign_marks,tickets_from_marks,check_hits

class MarkFirstBetTests(unittest.TestCase):
    def test_marks_and_markets(self):
        marks=assign_marks([8,5,11,2,3,7])
        self.assertEqual(marks["◎"],8)
        self.assertEqual(marks["注"],7)
        ts=tickets_from_marks(marks)
        self.assertEqual(set(ts),{"単勝","複勝","馬連","ワイド","馬単","3連複","3連単"})
        self.assertTrue(all(len(v)<=10 for v in ts.values()))
    def test_settlement_independent_of_popularity(self):
        ts=tickets_from_marks(assign_marks([8,5,11,2,3,7]))
        checks=check_hits(ts,(8,5,11))
        self.assertTrue(any(f(tuple(t)) for t in ts["単勝"] for f in [checks["単勝"]]))
        self.assertTrue(any(f(tuple(t)) for t in ts["3連複"] for f in [checks["3連複"]]))
        self.assertFalse(any(f(tuple(t)) for t in ts["3連単"] for f in [checks["3連単"]]))
