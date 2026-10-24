"""Regression checks for the replacement ARVEXQ prediction path."""
import unittest
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo

from arvexq.forecast.new_method import (
    FEATURES, VERSION, extract, history, predict, validate_model
)
from arvexq.forecast.publication import public_race


def sample():
    return {
        "id":"nar-2099-01-01-園田-01", "date":"2099-01-01", "circuit":"地方",
        "track":"園田", "surface":"ダート", "distance":1400, "scheduledStartTime":"23:00",
        "horses":[
            {"horseNumber":i,"id":100+i,"frameNumber":i,"name":"テスト馬"+str(i),
             "recentRaces":[{"date":"2098-02-01","track":"園田","surface":"ダート",
                             "distance":1400,"fieldSize":3,"finish":i,
                             "cornerPositions":[i, i],"marginSeconds":i-1}]}
            for i in range(1,4)]
    }


def model():
    return {
        "version":VERSION,"circuit":"地方",
        "trainedThrough":"2098-03-01","calibratedThrough":"2098-06-01",
        "outOfSampleValidated":True,"missingVideoValidated":True,
        "scenarioWeightsValidated":True,"scenarioWeights":{"baseline":1.0,"fast":0.0,"slow":0.0},
        "weights":{k:(2.0 if k=="form" else 0.0) for k in FEATURES},
        "featureMeans":{k:0.0 for k in FEATURES},"temperature":1.0,"paceEffect":0.0
    }


class NewMethodTests(unittest.TestCase):
    def test_no_old_pipeline_or_scorer(self):
        from pathlib import Path
        import arvexq.forecast.new_method as module
        s=Path(module.__file__).read_text()
        self.assertNotIn("research.stage64",s)
        self.assertNotIn("research.stage63",s)
        self.assertNotIn("retired",s.split("VERSION =",1)[1])

    def test_future_historical_rows_are_excluded(self):
        race=sample()
        race["horses"][0]["recentRaces"].append({"date":"2099-01-02","finish":1})
        self.assertEqual(len(history(race["horses"][0],race["date"])),1)

    def test_different_circuits_never_share_models(self):
        with self.assertRaises(ValueError):
            validate_model({**model(),"circuit":"中央"},sample())

    def test_uncalibrated_model_cannot_predict(self):
        with self.assertRaises(ValueError):
            predict(sample(),{**model(),"outOfSampleValidated":False})

    def test_verified_video_only_by_permanent_identity(self):
        race=sample()
        v={"101":{"identityVerified":True,"geometryCalibrated":True,
                  "coordinateUnit":"meter","sourceDates":["2098-01-10"],
                  "meanSpeedMps":15.0,"initialSpeedMps":12.0,
                  "idealPathExcessMeters":5.0,"slowdownCount":1}}
        features=extract(race,videos=v)
        self.assertEqual(features[1]["video_speed"],15.0)
        self.assertIsNone(features[2]["video_speed"])
        self.assertEqual(features[2]["video_missing"],1.0)
        v["101"]["sourceDates"]=["2099-02-01"]
        with self.assertRaises(ValueError):
            extract(race,videos=v)

    def test_probabilities_and_marks_same_joint(self):
        f=predict(sample(),model(),quoted_odds=[{"kind":"3連単","horses":[1,2,3],"odds":10.0}])
        win=f["probabilities"]["win"]
        self.assertAlmostEqual(sum(win.values()),1.0,places=9)
        self.assertAlmostEqual(sum(f["probabilities"]["top3"].values()),3.0,places=9)
        self.assertEqual(f["marks"][0]["horseNumber"],1)
        self.assertEqual(f["tickets"][0]["kind"],"3連単")

    def test_private_video_never_published(self):
        race=sample()
        race["_internalVideoFeatures"]={"101":{"secretFootage":"never public"}}
        with patch("arvexq.forecast.publication.build_prediction",return_value=predict(sample(),model())):
            public=public_race(race)
        self.assertEqual(public["predictionStatus"],"ready")
        self.assertNotIn("_internalVideoFeatures",str(public))
        self.assertNotIn("secretFootage",str(public))
        self.assertNotIn("videoAnalyzedInternally",str(public))

    def test_blank_result_placeholder_is_accepted_without_leaking_finishers(self):
        from arvexq.forecast.engine import build_prediction
        race=sample()
        race["result"]={"status":"未確定","finishers":[]}
        with patch("arvexq.forecast.engine.load_model", return_value=model()):
            with patch("arvexq.forecast.engine.predict") as scorer:
                scorer.return_value={"predictionStatus":"ready"}
                out=build_prediction(race,now=datetime(2098,12,1,tzinfo=ZoneInfo("Asia/Tokyo")))
                self.assertEqual(out["predictionStatus"],"ready")
                scorer.assert_called_once()
                self.assertNotIn("result",scorer.call_args.args[0])
        race["result"]={"status":"確定","finishers":[{"horseNumber":1,"finish":1}]}
        with patch("arvexq.forecast.engine.load_model") as load_model:
            self.assertIsNone(build_prediction(race,now=datetime(2098,12,1,tzinfo=ZoneInfo("Asia/Tokyo"))))
            load_model.assert_not_called()

    def test_missing_model_does_not_restore_retired_products(self):
        race=sample()
        race["predictionStatus"]="ready"
        race["predictionModelVersion"]="old"
        race["prediction"]={"modelVersion":"old"}
        with patch("arvexq.forecast.publication.build_prediction",return_value=None):
            public=public_race(race)
        self.assertEqual(public["predictionStatus"],"disabled")
        self.assertNotIn("prediction",public)


if __name__=="__main__":
    unittest.main()
