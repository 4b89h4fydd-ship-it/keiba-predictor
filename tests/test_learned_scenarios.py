from copy import deepcopy
from unittest import TestCase

from arvexq.prediction.learned_scenarios import FEATURES, VERSION, evidence, fit_model, predict_model
from arvexq.prediction.new_forecast import build_forecast
from test_unified_jra_nar_observed_authority import race


def training_race(circuit, date='2026-10-01'):
    d = race(circuit)
    d['date'], d['id'] = date, circuit+'-'+date
    for h in d['horses']:
        no = h['horseNumber']
        h['name'] = 'テスト馬'
        for r in h['recentRaces']:
            r['finish'] = no
            r['cornerPositions'] = [no, no]
    d['result'] = {'status': '確定', 'finishers': [{'horseNumber': n, 'finish': n} for n in range(1,7)]}
    return d


def target(circuit):
    d = training_race(circuit, '2026-10-12')
    d.pop('result')
    return d


class LearnedScenariosTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = {c: fit_model([training_race(c)], circuit=c) for c in ('中央','地方')}

    def test_both_circuits_full_joint_distribution_and_single_axis(self):
        for circuit in self.models:
            with self.subTest(circuit=circuit):
                d = target(circuit)
                original = deepcopy(d)
                result = build_forecast(d, self.models[circuit])
                self.assertEqual(d, original)
                self.assertEqual(result['predictionStatus'], 'candidate-analysis')
                self.assertFalse(result['productionEligible'])
                self.assertEqual(result['recommendedBetPlan']['decision'], '見送り')
                self.assertEqual(result['honmeiDecision']['horseNumber'], 1)
                self.assertEqual(result['honmeiDecision']['axisHorseNumber'], 1)
                self.assertEqual(sum(h['integratedEvaluation']['mark']=='◎' for h in result['horses']), 1)
                self.assertNotRegex(result['forecastText'], r'[0-9０-９A-Za-z%％]')
                for s in result['scenarioAnalysis']['scenarios']:
                    self.assertAlmostEqual(sum(e['probability'] for e in s['orders']), 1)
                    self.assertAlmostEqual(sum(v['win'] for v in s['probabilities'].values()), 1)
                    self.assertAlmostEqual(sum(v['top3'] for v in s['probabilities'].values()), 3)
                self.assertEqual(len(result['recommendedBetPlan']['comparisons']), 8)

    def test_date_leakage_and_wrong_circuit_rejected(self):
        model = self.models['中央']
        for d in (training_race('中央'), target('地方')):
            with self.assertRaises(ValueError):
                predict_model(d, model)
        d = target('中央'); d['date'] = '2026-09-30'
        with self.assertRaises(ValueError):
            predict_model(d, model)

    def test_target_results_odds_old_marks_and_today_runs_cannot_change_prediction(self):
        a = target('中央')
        b = deepcopy(a)
        b['result'] = {'status': '確定', 'finishers': [{'horseNumber':6,'finish':1}]}
        for h in b['horses']:
            h.update({'winOdds':999, 'popularity':1, 'integratedEvaluation':{'score':99999,'mark':'◎'}})
            h['recentRaces'].append({'date':b['date'],'fieldSize':12,'finish':1})
        self.assertEqual(predict_model(a,self.models['中央']), predict_model(b,self.models['中央']))

    def test_originals_preserved_and_postanalysis_labeled(self):
        d = target('地方')
        d['result'] = {'status':'確定'}
        d['preRacePrediction'], d['preRaceBet'] = {'original':'予想'}, {'original':'買い目'}
        result = build_forecast(d,self.models['地方'])
        self.assertEqual(result['analysisType'], 'retrospective')
        self.assertEqual(result['preRacePrediction'], d['preRacePrediction'])
        self.assertEqual(result['preRaceBet'], d['preRaceBet'])

    def test_full_career_beyond_recent_five_and_missing_not_zero(self):
        d = target('地方'); h = d['horses'][0]
        h['allPastRuns'] = deepcopy(h['recentRaces']) + [{'date':'2025-01-01','fieldSize':10,'finish':10}]
        report = evidence(h,d)
        self.assertEqual(report['observedStarts'],6)
        self.assertFalse(report['careerComplete'])
        self.assertIsNone(report['featureValues']['same_going_finish'])
        self.assertIn('sire',report['missingFields'])

    def test_missing_runner_history_disables_whole_field_prediction(self):
        d = target('地方'); d['horses'][0]['recentRaces'] = []
        result = build_forecast(d,self.models['地方'])
        self.assertEqual(result['predictionStatus'],'insufficient-history')
        self.assertFalse(any(h['integratedEvaluation']['mark'] for h in result['horses']))
        self.assertEqual(result['recommendedBetPlan']['decision'],'見送り')

    def test_no_model_never_falls_back_to_fixed_weight_candidate(self):
        result = build_forecast(target('地方'))
        self.assertEqual(result['predictionStatus'],'missing-trained-model')
        self.assertEqual(result['honmeiDecision']['horseNumber'],0)
        self.assertFalse(any(h['integratedEvaluation']['mark'] for h in result['horses']))

    def test_training_determinism_and_empty_bad_artifacts(self):
        model = fit_model([training_race('地方')], circuit='地方')
        self.assertEqual(model,self.models['地方'])
        self.assertEqual(model['calibrationStatus'],'unvalidated')
        self.assertEqual(len(model['weights']),len(FEATURES)*2)
        with self.assertRaises(ValueError):
            fit_model([],circuit='地方')
        bad = deepcopy(model); bad['weights'][0] = float('nan')
        with self.assertRaises(ValueError):
            predict_model(target('地方'),bad)
