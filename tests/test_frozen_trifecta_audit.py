import unittest
from scripts.arvexq_frozen_trifecta_audit import evaluate, summarize

def sample():
    return {"id":"A","date":"2026-10-15","circuit":"JRA","scheduledStartTime":"15:00","raceStatus":"確定","result":{"finishers":[{"finish":i,"horseNumber":n} for i,n in enumerate((2,5,1),1)]},"preRaceBet":{"raceId":"A","fixedAt":"2026-10-15T05:00:00Z","items":[{"kind":"3連単","combos":[[2,5,1],[2,1,5]]}]}}

class FrozenTrifectaAuditTests(unittest.TestCase):
    def test_hit(self):
        self.assertTrue(evaluate(sample())[1]["hit"])
    def test_order_miss(self):
        d=sample();d["preRaceBet"]["items"][0]["combos"]=[[2,1,5]]
        self.assertFalse(evaluate(d)[1]["hit"])
    def test_late_lock(self):
        d=sample();d["preRaceBet"]["fixedAt"]="2026-10-15T06:00:00Z"
        self.assertEqual(evaluate(d)[0],"not_proven_preoff")
    def test_over_ten(self):
        d=sample();d["preRaceBet"]["items"][0]["combos"]=[[i,20,21] for i in range(1,12)]
        self.assertEqual(evaluate(d)[0],"over_ten_tickets")
    def test_no_ticket(self):
        d=sample();d["preRaceBet"]["items"]=[]
        self.assertEqual(evaluate(d)[0],"no_trifecta_ticket")
    def test_aggregate(self):
        a=sample();b=sample();b["id"]="B";b["preRaceBet"]["raceId"]="B";b["preRaceBet"]["items"][0]["combos"]=[[2,1,5]]
        self.assertEqual(summarize([a,b])["byCircuit"]["JRA"]["observedHitRate"],0.5)
