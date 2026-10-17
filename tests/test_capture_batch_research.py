import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from scripts.arvexq_capture_batch_research import capture


class BatchResearchCaptureTests(TestCase):
    def test_only_eligible_future_races_are_captured(self):
        future={'id':'nar-future','date':'2026-10-18','circuit':'地方',
                'startTime':'14:00','horses':[{'horseNumber':1},{'horseNumber':2}]}
        old={'id':'nar-old','date':'2026-10-16','circuit':'地方'}
        models={'地方':{'training':{'lastDate':'2026-10-17'}}}
        with tempfile.TemporaryDirectory() as tmp:
            with patch('scripts.arvexq_capture_batch_research.build_forecast',
                       return_value={'analysisType':'preoff-candidate',
                                     'recommendedBetPlan':{'researchLeader':{'status':'research-only-not-a-recommendation',
                                                                                'kind':'単勝','combos':[[1]]}}}), \
                 patch('scripts.arvexq_capture_batch_research.freeze_research_candidate',
                       return_value=Path(tmp)/'receipt.json') as freeze:
                out=capture({'details':[future,old]},models,tmp)
                self.assertEqual(len(out['saved']),1)
                self.assertEqual(out['skipped']['nar-old'],'training-not-earlier-than-race')
                self.assertFalse(out['independentlyVerifiedPreoff'])
                freeze.assert_called_once()

    def test_rejects_bundles_without_details(self):
        with self.assertRaises(ValueError):
            capture({'races':[]},{},'/tmp/not-written')
