from unittest import TestCase
from arvexq.backtest.ticket_metrics import parse_official_payouts, ticket_payout


class AllKindMetricsTests(TestCase):
    def test_place_and_frame_with_multiple_winners_and_shared_frame(self):
        result = {'payouts': [
            {'type':'複勝','combination':'1','amount':'180円'},
            {'type':'複勝','combination':'2','amount':240},
            {'type':'枠連','combination':'1-1','amount':540},
            {'type':'枠連','combination':'2-8','amount':'1,230'},
        ]}
        prices, invalid = parse_official_payouts(result)
        self.assertEqual(invalid,set())
        self.assertEqual(ticket_payout('複勝',[[1],[2],[3]],prices,invalid),420)
        self.assertEqual(ticket_payout('枠連',[[8,2]],prices,invalid),1230)
        self.assertEqual(ticket_payout('枠連',[[1,1]],prices,invalid),540)

    def test_missing_or_corrupt_payout_is_unknown_not_zero(self):
        prices, invalid = parse_official_payouts({'payouts':[
            {'type':'複勝','combination':'1','amount':180},
            {'type':'複勝','combination':'2','amount':'不明'}]})
        self.assertIsNone(ticket_payout('複勝',[[1]],prices,invalid))
        self.assertIsNone(ticket_payout('枠連',[[1,2]],prices,invalid))
