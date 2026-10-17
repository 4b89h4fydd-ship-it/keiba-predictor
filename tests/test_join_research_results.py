import tempfile
from datetime import datetime, timezone
from unittest import TestCase
from arvexq.backtest.freeze_research_candidate import freeze_research_candidate
from arvexq.backtest.join_research_results import join_receipts


class JoinResearchResultsTests(TestCase):
    def test_join_requires_independent_preoff_proof_before_metrics(self):
        race = {'id':'race-1','date':'2026-10-18','startTime':'14:00',
                'circuit':'地方','horses':[{'horseNumber':1},{'horseNumber':2}]}
        plan = {'researchLeader': {'status':'research-only-not-a-recommendation',
                'kind':'単勝','combos':[[1]]}}
        results = {'race-1': {'status':'確定','payouts':[
            {'type':'単勝','combination':'1','amount':250}]}}
        with tempfile.TemporaryDirectory() as folder:
            freeze_research_candidate(race,plan,folder,
                captured_at=datetime(2026,10,18,3,tzinfo=timezone.utc))
            report = join_receipts(folder,results)
            self.assertEqual(len(report['joined']),1)
            self.assertFalse(report['joined'][0]['preoffSourceVerified'])
            self.assertEqual(report['measured']['excluded']['not-proven-preoff-holdout'],1)
            self.assertIsNone(report['measured']['byCircuit']['地方']['単勝']['measuredHitRate'])
