from unittest import TestCase
from arvexq.backtest.frozen_research_tickets import evaluate_frozen_candidates


def example():
    return {'raceId':'nar-fixture-1','circuit':'地方','capturedAt':'2026-10-18T10:00:00+09:00',
            'scheduledOffAt':'2026-10-18T11:00:00+09:00',
            'preoffSourceVerified':True,'heldOutFromTraining':True,
            'candidate':{'kind':'単勝','combos':[[1]],
                         'status':'research-only-not-a-recommendation'},
            'result':{'status':'確定','payouts':[
                {'type':'単勝','combination':'1','amount':250}]}}


class FrozenResearchTicketTests(TestCase):
    def test_verified_snapshot_only_measures_payout(self):
        row = evaluate_frozen_candidates([example()])
        kind = row['byCircuit']['地方']['単勝']
        self.assertEqual(kind['evaluatedRaces'], 1)
        self.assertEqual(kind['hitRaces'], 1)
        self.assertEqual(kind['measuredHitRate'], 1)
        self.assertEqual(kind['flatStakeReturnRate'], 2.5)
        self.assertFalse(row['target80Achieved'])

    def test_after_post_and_missing_provenance_never_count(self):
        changed = example()
        changed['capturedAt'] = '2026-10-18T12:00:00+09:00'
        missing = example()
        missing['preoffSourceVerified'] = False
        reused = example()
        reused['heldOutFromTraining'] = False
        output = evaluate_frozen_candidates([changed, missing, reused])
        self.assertEqual(output['excluded']['not-proven-preoff-holdout'], 3)
        self.assertIsNone(output['byCircuit']['地方']['単勝']['measuredHitRate'])

    def test_missing_official_payout_not_a_loss(self):
        row = example()
        row['result']['payouts'] = []
        out = evaluate_frozen_candidates([row])
        self.assertEqual(out['excluded']['missing-official-payout'], 1)
        self.assertIsNone(out['byCircuit']['地方']['単勝']['measuredHitRate'])

    def test_invalid_or_unfrozen_candidate_rejected(self):
        row = example()
        row['candidate']['combos'] = [[1]] * 11
        another = example()
        another['candidate']['status'] = 'approved'
        out = evaluate_frozen_candidates([row, another])
        self.assertEqual(out['excluded']['invalid-ticket'], 1)
        self.assertEqual(out['excluded']['missing-frozen-candidate'], 1)

    def test_duplicate_race_and_malformed_ticket_excluded(self):
        original = example()
        bad = example()
        bad['raceId'] = 'different'
        bad['candidate']['combos'] = [[1], [1]]
        result = evaluate_frozen_candidates([original, original, bad])
        self.assertEqual(result['byCircuit']['地方']['単勝']['evaluatedRaces'], 1)
        self.assertEqual(result['excluded']['duplicate-race'], 1)
        self.assertEqual(result['excluded']['invalid-ticket'], 1)

    def test_invalid_first_record_does_not_reserve_race(self):
        bad = example()
        bad['result']['payouts'] = []
        good = example()
        out = evaluate_frozen_candidates([bad, good])
        self.assertEqual(out['excluded']['missing-official-payout'], 1)
        self.assertEqual(out['byCircuit']['地方']['単勝']['evaluatedRaces'], 1)
        self.assertNotIn('duplicate-race', out['excluded'])
