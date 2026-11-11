import math
import tempfile
import unittest
from pathlib import Path
from test_ranking_challenger import sample
from arvexq.research.ranking_challenger import train_one,prepare_races,metrics
from arvexq.research.ranking_probability import podium_probabilities,win_probabilities,calibrate_and_evaluate,date_bootstrap,ticket_metrics

class BenchmarkContracts(unittest.TestCase):
    def test_real_estimators_on_synthetic_group_contract(self):
        rows=[]
        for day in ('2026-10-21','2026-10-22','2026-10-24','2026-10-25'):
            for suffix in ('a','b'):
                extra=sample(day)
                for r in extra:r['raceId']+=suffix
                rows.extend(extra)
        for learner,target in [('pointwise','graded'),('xgboost','graded'),('lambdarank','win'),('lambdarank','podium')]:
            with self.subTest(learner=learner,target=target), tempfile.TemporaryDirectory() as d:
                r=train_one(rows,'jra','ability',Path(d),min_train_races=2,
                            development_only=True,learner=learner,target=target)
                self.assertEqual(r['testRaces'],0)
                self.assertGreater(r['modelBytes'],0)
                self.assertEqual(r['validationRaces'],2)
    def test_rank_and_opponent_metrics(self):
        r=prepare_races(sample('2026-10-01'),'jra','ability')
        m=metrics(r,[6,5,4,3,2,1]);self.assertEqual(m['mrr'],1)
        self.assertEqual(m['podiumCountAt3'],3);self.assertEqual(m['winnerHitAt2'],1)
    def test_probability_and_dates(self):
        p=win_probabilities([0,1,2],1);self.assertAlmostEqual(sum(p),1)
        pp=podium_probabilities([0,1,2,3,4],1)
        self.assertAlmostEqual(sum(pp),3)
        self.assertTrue(all(0<=v<=1 for v in pp))
        self.assertAlmostEqual(sum(podium_probabilities([0,0,0],1)),3)
        with self.assertRaises(ValueError):calibrate_and_evaluate([],[])
        self.assertIsNone(date_bootstrap([{'date':'x','new':1,'baseline':0}])['ci95'])
        b=date_bootstrap([{'date':'a','new':1,'baseline':0},{'date':'b','new':1,'baseline':0}])
        self.assertEqual(b['ci95'],[1,1])
    def test_native_class_is_categorical_not_an_invented_opponent_score(self):
        from arvexq.prediction.mass_feature_factory import build_horse_features
        h={"allPastRuns":[{"date":"2026-10-01","track":"金沢","class":"Ｃ２"}]}
        f=build_horse_features(h,{"date":"2026-10-02"})
        self.assertEqual(f["category::past_class::金沢::C2"],1)
        self.assertNotIn("history::all::w5::opponent_level::mean",f)

    def test_calibrator_fits_only_earlier_dates(self):
        def cards(days):
            return [{"raceId":d,"date":d,"rows":[{"score":float(5-i),"finish":i} for i in range(1,5)]} for d in days]
        cal=cards(['2026-11-01','2026-11-02']);test=cards(['2026-11-03','2026-11-04'])
        r=calibrate_and_evaluate(cal,test,train_through='2026-10-31')
        self.assertEqual(r['after']['races'],2)
        with self.assertRaises(ValueError):calibrate_and_evaluate(cal,test,train_through='2026-11-01')

    def test_missing_field_size_is_not_invented(self):
        from arvexq.prediction.mass_feature_factory import _finish_quality,_position_quality
        self.assertIsNone(_finish_quality({"finish":1}))
        self.assertIsNone(_position_quality({"corner4":2}))
        self.assertEqual(_finish_quality({"finish":1,"fieldSize":10}),1)

    def test_actual_returns_required(self):
        with self.assertRaises(ValueError):ticket_metrics([{'stake':100,'odds':5}])
        r=ticket_metrics([{'stake':100,'return':500,'settled':True},{'stake':100,'return':0,'settled':True}])
        self.assertEqual(r['roi'],2.5);self.assertEqual(r['roiWithoutLargestPayout'],0)
