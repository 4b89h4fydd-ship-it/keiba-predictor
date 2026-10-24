import unittest
from unittest.mock import patch
from scripts.arvexq_apply_learned_overlay import apply


class OverlayTests(unittest.TestCase):
    def test_no_postoff_replacement_of_persisted_prediction(self):
        race = {
            'id': 'jra-2026-10-24-新潟-09', 'date': '2026-10-24',
            'circuit': '中央', 'startTime': '14:15',
            'predictionStatus': 'ready',
            'predictionModelVersion': 'previous-observed-research',
            'preRacePrediction': {'frozen': True, 'sealRevision': 'immutable'},
            'predictionMarks': [{'horseNumber': 1, 'mark': '◎'}],
            'horses': [{'horseNumber': 1, 'name': 'preserved'}],
        }
        model = {'中央': {'training': {'lastDate': '2026-10-23'}}}
        with patch('scripts.arvexq_apply_learned_overlay.may_create_prerace_prediction',
                   return_value=False), \
                patch('scripts.arvexq_apply_learned_overlay.build_forecast',
                      side_effect=AssertionError('post-off forecast generated')) as build:
            payload, report = apply({'details': [race]}, model)
            build.assert_not_called()
        self.assertEqual(payload['details'][0], race)
        self.assertEqual(report['overlaid'], [])
        self.assertEqual(report['skipped'][race['id']], 'post-off-original-preserved')

    def test_future_race_continues_approved_overlay_policy(self):
        race = {'id': 'jra-2026-10-25-東京-09', 'date': '2026-10-25',
                'circuit': '中央', 'startTime': '14:15'}
        model = {'中央': {'training': {'lastDate': '2026-10-24'}}}
        with patch('scripts.arvexq_apply_learned_overlay.may_create_prerace_prediction',
                   return_value=True), \
                patch('scripts.arvexq_apply_learned_overlay.build_forecast',
                      return_value={'id':race['id'], 'recommendedBetPlan': {'items': []},
                                    'predictionModelVersion': 'research-learned'}) as build:
            payload, report = apply({'details': [race]}, model)
            build.assert_called_once()
        self.assertEqual(report['overlaid'], [race['id']])
        self.assertEqual(payload['details'][0]['predictionModelVersion'],
                         'research-learned')

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
        self.assertEqual(result['details'][0]['id'], detail['id'])
        self.assertEqual(result['details'][0]['predictionStatus'], 'new-model-unavailable')
        self.assertEqual(result['details'][0]['recommendedBetPlan']['items'], [])
        self.assertIn('ValueError', report['skipped']['race-1'])

    def test_missing_new_model_removes_legacy_display_but_keeps_frozen_original(self):
        detail = {
            'id': 'race-2', 'date': '2026-10-17', 'circuit': '中央',
            'aiEvaluation': {'old': True}, 'predictionModelVersion': 'old',
            'recommendedBetPlan': {'items': [{'kind': '馬単'}]},
            'preRacePrediction': {'frozen': True},
            'preRaceBet': {'frozen': True},
            'horses': [{'horseNumber': 1, 'name': 'A',
                        'allPastRuns': [{'date': '2026-10-01'}],
                        'integratedEvaluation': {'mark': '◎'}}],
        }
        output, report = apply({'details': [detail]}, {})
        row = output['details'][0]
        self.assertNotIn('aiEvaluation', row)
        self.assertNotIn('predictionModelVersion', row)
        self.assertNotIn('integratedEvaluation', row['horses'][0])
        self.assertEqual(row['recommendedBetPlan']['items'], [])
        self.assertEqual(row['preRacePrediction'], detail['preRacePrediction'])
        self.assertEqual(row['preRaceBet'], detail['preRaceBet'])
        self.assertEqual(row['horses'][0]['allPastRuns'], detail['horses'][0]['allPastRuns'])
        self.assertEqual(report['overlaid'], [])


if __name__ == '__main__':
    unittest.main()
