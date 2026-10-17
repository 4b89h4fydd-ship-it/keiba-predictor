import unittest
from unittest.mock import patch
from scripts.arvexq_apply_learned_overlay import apply


class OverlayTests(unittest.TestCase):
    def test_new_forecast_preserves_original_and_does_not_publish_unverified_tickets(self):
        detail = {'id': 'race-1', 'date': '2026-10-18', 'circuit': '中央',
                  'preRacePrediction': {'frozen': True, 'horses': [1]},
                  'preRaceBet': {'decision': '旧買い目'}}
        models = {'中央': {'training': {'lastDate': '2026-10-17'}}}
        with patch('scripts.arvexq_apply_learned_overlay.build_forecast', return_value={
            'id': 'race-1', 'predictionModelVersion': 'new',
            'recommendedBetPlan': {'items': []},
            'preRacePrediction': {'frozen': False},
            'preRaceBet': {'decision': '上書き'}}):
            output, report = apply({'details': [detail]}, models)
        self.assertEqual(report['overlaid'], ['race-1'])
        row = output['details'][0]
        self.assertEqual(row['predictionModelVersion'], 'new')
        self.assertEqual(row['preRacePrediction'], detail['preRacePrediction'])
        self.assertEqual(row['preRaceBet'], detail['preRaceBet'])

    def test_rejects_unverified_ticket_promotion(self):
        detail = {'id': 'race-1', 'date': '2026-10-18', 'circuit': '地方'}
        models = {'地方': {'training': {'lastDate': '2026-10-17'}}}
        with patch('scripts.arvexq_apply_learned_overlay.build_forecast',
                   return_value={'recommendedBetPlan': {'items': [{'kind': '単勝'}]}}):
            result, report = apply({'details': [detail]}, models)
        self.assertEqual(result['details'], [detail])
        self.assertIn('ValueError', report['skipped']['race-1'])


if __name__ == '__main__':
    unittest.main()
