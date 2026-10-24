"""The new three-analysis product must never invent 3連系 odds or trim all outsiders."""
from copy import deepcopy
from unittest import TestCase
from arvexq.forecast.tickets import generate_tickets


class TripleTicketContractTests(TestCase):
    def setUp(self):
        self.marks=[{'horseNumber':n,'mark':m} for n,m in
                    zip((1,2,3,4,5),('◎','○','▲','△','☆'))]
        self.prediction={
            'predictionStatus':'ready','modelVersion':'arvexq-three-analysis-vnext-1',
            'tickets':[
                {'kind':'3連複','combos':[[1,2,6]],'points':1,'hitProbability':.15,'expectedReturn':1.2},
                {'kind':'3連単','combos':[[1,2,6]],'points':1,'hitProbability':.04,'expectedReturn':1.1},
            ]}
        self.race={'id':'nar-2099-01-01-高知-12','track':'高知'}

    def test_unmarked_third_remains_eligible_when_joint_and_real_quote_support_it(self):
        original=deepcopy(self.prediction)
        bets=generate_tickets(self.prediction,self.marks,race=self.race)
        self.assertEqual({b['kind'] for b in bets},{'3連複','3連単'})
        self.assertTrue(any(6 in combo for b in bets for combo in b['combos']))
        self.assertEqual(original,self.prediction)

    def test_after_finish_no_recomputation_or_reordering(self):
        before=generate_tickets(self.prediction,self.marks)
        self.assertEqual(before,generate_tickets(self.prediction,self.marks,
            race={**self.race,'result':{'finishers':[{'horseNumber':5,'finish':1}]}}))

    def test_no_odds_no_invented_ticket_for_any_track(self):
        no_quote={**self.prediction,'tickets':[]}
        for track in ('高知','大井','東京'):
            self.assertEqual(generate_tickets(no_quote,self.marks,race={'track':track}),[])

    def test_disabled_or_missing_forecast_does_not_infer_probabilities(self):
        self.assertEqual(generate_tickets({'predictionStatus':'disabled'},self.marks),[])
        self.assertEqual(generate_tickets({},self.marks),[])
