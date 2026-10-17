import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import TestCase
from arvexq.backtest.freeze_research_candidate import freeze_research_candidate
from arvexq.backtest.verify_research_receipt import verify_receipt


class ResearchReceiptVerificationTests(TestCase):
    def test_source_and_receipt_digest_and_tamper_detection(self):
        race = {'id':'test-2026-10-18','date':'2026-10-18','startTime':'14:00',
                'circuit':'地方','horses':[{'horseNumber':1},{'horseNumber':2}]}
        plan = {'modelVersion':'research','researchLeader':{
            'status':'research-only-not-a-recommendation',
            'kind':'単勝','combos':[[1]]}}
        with tempfile.TemporaryDirectory() as directory:
            path = freeze_research_candidate(race,plan,directory,
                captured_at=datetime(2026,10,18,3,tzinfo=timezone.utc))
            check = verify_receipt(path,original_race=race)
            self.assertTrue(check['checksumVerified'])
            self.assertFalse(check['independentlyVerifiedPreoff'])
            with self.assertRaisesRegex(ValueError,'source race checksum'):
                verify_receipt(path,original_race=dict(race,track='different'))
            saved = json.loads(path.read_text(encoding='utf-8'))
            saved['snapshot']['candidate']['combos'] = [[2]]
            path.write_text(json.dumps(saved,ensure_ascii=False),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'receipt checksum'):
                verify_receipt(path,original_race=race)
