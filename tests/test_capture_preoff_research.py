import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from scripts.arvexq_capture_preoff_research import main


class CaptureResearchEntrypointTests(TestCase):
    def test_trained_before_target_and_research_only(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            race = folder/'race.json'; model = folder/'model.json'
            race.write_text(json.dumps({'id':'fixture','date':'2026-10-18','horses':[]}))
            model.write_text(json.dumps({'training':{'lastDate':'2026-10-17'}}))
            with patch('scripts.arvexq_capture_preoff_research.build_forecast',
                       return_value={'analysisType':'preoff-candidate',
                                     'recommendedBetPlan':{'researchLeader':{'status':'research-only-not-a-recommendation'}}}) as build, \
                 patch('scripts.arvexq_capture_preoff_research.freeze_research_candidate',
                       return_value=folder/'receipt.json') as freeze:
                main(['--race-json',str(race),'--model-json',str(model),
                      '--receipt-dir',str(folder/'receipts')])
                build.assert_called_once()
                freeze.assert_called_once()

    def test_training_on_target_day_rejected_without_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            race=folder/'race.json';model=folder/'model.json'
            race.write_text(json.dumps({'id':'fixture','date':'2026-10-18'}))
            model.write_text(json.dumps({'training':{'lastDate':'2026-10-18'}}))
            with patch('scripts.arvexq_capture_preoff_research.build_forecast') as build, \
                 self.assertRaises(SystemExit):
                main(['--race-json',str(race),'--model-json',str(model),
                      '--receipt-dir',str(folder/'receipts')])
            build.assert_not_called()
