"""A single bad race must not abort the daily research-capture batch."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.arvexq_capture_batch_research import capture


class CaptureIsolationTests(unittest.TestCase):
    def test_prediction_exception_skips_one_race_and_continues(self):
        bundle = {'details': [
            {'id': 'bad', 'date': '2026-10-20', 'circuit': '地方'},
            {'id': 'good', 'date': '2026-10-20', 'circuit': '地方'},
        ]}
        models = {'地方': {'training': {'lastDate': '2026-10-19'}}}
        calls = []
        def fake_forecast(race, _model):
            calls.append(race['id'])
            if race['id'] == 'bad':
                raise RuntimeError('scenario evaluation failed')
            return {'analysisType': 'preoff-candidate', 'recommendedBetPlan': {'researchLeader': {}}}
        with tempfile.TemporaryDirectory() as folder:
            with patch('scripts.arvexq_capture_batch_research.build_forecast', side_effect=fake_forecast), \
                 patch('scripts.arvexq_capture_batch_research.freeze_research_candidate', return_value=Path(folder) / 'good.json'):
                result = capture(bundle, models, Path(folder))
        self.assertEqual(calls, ['bad', 'good'])
        self.assertEqual([x['raceId'] for x in result['saved']], ['good'])
        self.assertIn('RuntimeError', result['skipped']['bad'])
        self.assertFalse(result['independentlyVerifiedPreoff'])

    def test_invalid_models_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'models must'):
            capture({'details': []}, [], Path('.'))


if __name__ == '__main__':
    unittest.main()
