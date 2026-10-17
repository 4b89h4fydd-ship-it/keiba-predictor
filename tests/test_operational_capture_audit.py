import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import TestCase
from arvexq.backtest.freeze_research_candidate import freeze_research_candidate
from arvexq.backtest.audit_research_capture import audit_capture


class OperationalCaptureAuditTests(TestCase):
    def test_receipt_identity_and_checksum_required(self):
        race={'id':'audit-2026-10-18','date':'2026-10-18','startTime':'14:00',
              'circuit':'地方','horses':[{'horseNumber':1},{'horseNumber':2}]}
        plan={'researchLeader':{'status':'research-only-not-a-recommendation',
             'kind':'単勝','combos':[[1]]}}
        with tempfile.TemporaryDirectory() as folder:
            path=freeze_research_candidate(race,plan,folder,
                 captured_at=datetime(2026,10,18,3,tzinfo=timezone.utc))
            report={'saved':[{'raceId':race['id'],'receipt':str(path)}]}
            result=audit_capture(folder,report)
            self.assertTrue(result['verified'])
            self.assertFalse(result['independentlyVerifiedPreoff'])
            self.assertFalse(audit_capture(folder,{'saved':[{'raceId':'wrong'}]})['verified'])
            saved=json.loads(path.read_text())
            saved['snapshot']['candidate']['combos']=[[2]]
            path.write_text(json.dumps(saved))
            result=audit_capture(folder,report)
            self.assertFalse(result['verified'])
            self.assertEqual(result['reason'],'invalid-receipt')

    def test_zero_receipts_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            result=audit_capture(folder,{'saved':[]})
            self.assertFalse(result['verified'])
