import itertools
import math
import unittest
from arvexq.research.rank_distribution import ranking_distribution, mix_scenarios


class DistributionTests(unittest.TestCase):
    def test_all_positions_match_independent_full_order_enumeration(self):
        w = {1: 2.0, 3: 1.0, 6: 4.0, 9: .5}
        d = ranking_distribution(w)
        brute = [[0.0]*4 for _ in w]
        for order in itertools.permutations(d.runners):
            p = 1.0
            for rank, no in enumerate(order):
                p *= w[no]/sum(w[j] for j in order[rank:])
            for rank, no in enumerate(order):
                brute[d.runners.index(no)][rank] += p
        for got, expected in zip(d.marginals, brute):
            for p, q in zip(got, expected):
                self.assertAlmostEqual(p, q, places=12)
        for rank in range(4):
            self.assertAlmostEqual(sum(row[rank] for row in d.marginals), 1)
        for row in d.marginals:
            self.assertAlmostEqual(sum(row), 1)
        self.assertAlmostEqual(sum(d.podium.values()), 1)
        self.assertFalse(d.calibrated)

    def test_ticket_unions_respect_dependence_and_overlap(self):
        d = ranking_distribution({1: 1., 2: 1., 3: 1., 4: 1.})
        self.assertAlmostEqual(d.ticket_probability("単勝", [[1]]), .25)
        self.assertAlmostEqual(d.ticket_probability("馬単", [[1, 2]]), 1/12)
        self.assertAlmostEqual(d.ticket_probability("馬連", [[1, 2], [2, 1]]), 1/6)
        self.assertAlmostEqual(d.ticket_probability("3連複", [[1, 2, 3]]), .25)
        self.assertAlmostEqual(d.ticket_probability("3連単", [[1, 2, 3]]), 1/24)
        self.assertAlmostEqual(d.ticket_probability("ワイド", [[1, 2], [1, 3]]), .75)

    def test_small_fields_and_missing_runner_fail_closed(self):
        d = ranking_distribution({2: 3.})
        self.assertEqual(d.marginals, ((1.,),))
        self.assertEqual(d.ticket_probability("単勝", [[2]]), 1)
        for kind, combo in (("ワイド", [2, 3]), ("単勝", [3])):
            with self.assertRaises(ValueError):
                d.ticket_probability(kind, [combo])
        for w in ({}, {1: math.nan}, {1: 0.}, {1: -1.}):
            with self.assertRaises(ValueError):
                ranking_distribution(w)

    def test_mixture_preserves_probability_law(self):
        a = ranking_distribution({1: 1., 2: 3., 3: 2.})
        b = ranking_distribution({1: 4., 2: 1., 3: 2.})
        d = mix_scenarios([(.2, a), (.8, b)])
        self.assertAlmostEqual(d.marginals[0][0], .2*a.marginals[0][0]+.8*b.marginals[0][0])
        self.assertAlmostEqual(sum(d.podium.values()), 1)
        with self.assertRaises(ValueError):
            mix_scenarios([(.2, a), (.7, b)])
        with self.assertRaises(ValueError):
            mix_scenarios([(.2, a), (.8, ranking_distribution({1: 1., 2: 1.}))])


if __name__ == "__main__":
    unittest.main()
