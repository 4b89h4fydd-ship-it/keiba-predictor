import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import TestCase
from arvexq.backtest.freeze_research_candidate import freeze_research_candidate


class FreezeResearchCandidateTests(TestCase):
    def setUp(self):
        self.detail = {'id':'nar-2026-10-18-test-01','date':'2026-10-18',
                       'startTime':'14:00','circuit':'地方',
                       'horses':[{'horseNumber':1},{'horseNumber':2}]}
        self.plan = {'modelVersion':'research-v1','researchLeader': {
            'status':'research-only-not-a-recommendation',
            'kind':'単勝','combos':[[1]],'points':1}}

    def test_preoff_receipt_created_once_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            before = datetime(2026, 10, 18, 3, 0, tzinfo=timezone.utc)
            path = freeze_research_candidate(self.detail,self.plan,folder,captured_at=before)
            original = path.read_bytes()
            self.assertIn(b'snapshotSha256',original)
            with self.assertRaises(FileExistsError):
                freeze_research_candidate(self.detail,self.plan,folder,captured_at=before)
            self.assertEqual(path.read_bytes(),original)

    def test_late_and_missing_candidate_cannot_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            late = datetime(2026, 10, 18, 6, 0, tzinfo=timezone.utc)
            with self.assertRaises(ValueError):
                freeze_research_candidate(self.detail,self.plan,folder,captured_at=late)
            with self.assertRaises(ValueError):
                freeze_research_candidate(self.detail,{'researchLeader':None},folder,
                    captured_at=datetime(2026,10,18,3,0,tzinfo=timezone.utc))
            self.assertEqual(list(Path(folder).iterdir()),[])

    def test_result_bearing_card_cannot_be_frozen_even_before_post(self):
        before = datetime(2026, 10, 18, 3, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as folder:
            for field, value in [('result', {'status':'確定'}),
                                 ('analysisType', 'retrospective')]:
                detail = dict(self.detail, **{field:value})
                with self.subTest(field=field), self.assertRaises(ValueError):
                    freeze_research_candidate(detail,self.plan,folder,captured_at=before)
            self.assertFalse(list(Path(folder).iterdir()))
