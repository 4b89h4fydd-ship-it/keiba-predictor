import unittest
from math import fsum
from rewrite.safety.probability import distribution, marginals, marks, ticket_probability, expected_return


class ProbabilityTests(unittest.TestCase):
    def test_symmetric_field_and_probability_conservation(self):
        d = distribution({i: 1.0 for i in range(1, 7)})
        self.assertAlmostEqual(fsum(d.values()), 1)
        for win, top2, top3 in marginals(d).values():
            self.assertAlmostEqual(win, 1/6)
            self.assertAlmostEqual(top2, 2/6)
            self.assertAlmostEqual(top3, 3/6)
        for kind, selection, expected in (
            ('win', (1,), 1/6), ('place', (1,), 1/2), ('wide', (1,2), 1/5),
            ('quinella', (1,2), 1/15), ('exacta', (1,2), 1/30),
            ('trio', (1,2,3), 1/20), ('trifecta', (1,2,3), 1/120)):
            self.assertAlmostEqual(ticket_probability(d, kind, selection), expected)
        self.assertAlmostEqual(ticket_probability(d, 'place', (1,), 2), 1/3)

    def test_monotonic_marginals_and_unique_marks(self):
        d = distribution({1: 10, 2: 4, 3: 2, 4: 1, 5: 0.5, 6: 0.2})
        for win, top2, top3 in marginals(d).values():
            self.assertTrue(0 <= win <= top2 <= top3 <= 1 + 1e-12)
        self.assertEqual(marks(d)[1], '◎')
        self.assertEqual(sorted(v for v in marks(d).values() if v), sorted('◎○▲△☆'))

    def test_invalid_strength_and_ticket(self):
        for strengths in ({1: 0, 2: 1}, {1: float('nan'), 2: 1}, {1:1}, {0:1, 1:2}):
            with self.assertRaises(ValueError):
                distribution(strengths)
        d = distribution({1:1, 2:1, 3:1})
        for kind, selection in [('win',(4,)), ('exacta',(1,1)), ('unknown',(1,))]:
            with self.assertRaises(ValueError):
                ticket_probability(d, kind, selection)

    def test_ev_cannot_claim_unvalidated_success(self):
        with self.assertRaises(ValueError):
            expected_return(.5, 3, validated=False)
        self.assertEqual(expected_return(.5, 3, validated=True), 1.5)


if __name__ == '__main__':
    unittest.main()
