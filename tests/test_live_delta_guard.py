"""Regression cases for avoiding needless D1 detail rewrites on odds ticks."""
from __future__ import annotations
import copy
import unittest
from arvexq.infra.live_delta_guard import requires_full_write, durable_fingerprint

def base():
    return {
        "id": "jra-2026-10-10-京都-01",
        "date": "2026-10-10", "weather": "晴", "condition": "良",
        "morningMarkSnapshot": {"version": "arvexq-morning-marks-v1", "raceId": "jra-2026-10-10-京都-01", "horses": [{"horseNumber": 1, "mark": "◎"}]},
        "preRaceBet": {"fixedAt": "2026-10-10T08:00:00+09:00", "items": []},
        "preparedMeta": {"diagnosisReady": True, "liveUpdatedAtEpoch": 100},
        "horses": [{"horseNumber":1,"name":"test horse","winOdds":2.4,"popularity":1,
                   "bodyWeight":456,"scratched":False,"careerArchive":{"payload":"foo"}}],
    }

class LiveDeltaGuardTest(unittest.TestCase):
    def test_unchanged_and_market_only_do_not_rewrite_detail(self):
        x=base()
        self.assertFalse(requires_full_write(x,copy.deepcopy(x)))
        later=copy.deepcopy(x)
        later["horses"][0].update(winOdds=4.8,popularity=2,oddsForecast=False,oddsSource="official")
        later["preparedMeta"]["liveUpdatedAtEpoch"]=120
        later["oddsUpdatedAt"]="12:00"
        later["oddsSource"]="official"
        self.assertFalse(requires_full_write(x,later))

    def test_important_updates_cannot_be_skipped(self):
        changes=[
            lambda x: x.update(weather="雨"),
            lambda x: x.update(condition="重"),
            lambda x: x.update(result={"status":"確定","finishers":[{"horseNumber":1,"finish":1}]}),
            lambda x: x.update(preRacePrediction={"mark":"○"}),
            lambda x: x["preRaceBet"].update(items=[{"selection":"1-2"}]),
            lambda x: x["horses"][0].update(scratched=True),
            lambda x: x["horses"][0].update(bodyWeight=468),
            lambda x: x["horses"][0].update(jockey="川田"),
            lambda x: x["horses"][0].update(careerArchive={"payload":"expanded"}),
            lambda x: x["morningMarkSnapshot"]["horses"][0].update(mark="○"),
            lambda x: x.update(officialMarkRevisions=[{"publishedAt":"2026-10-10T10:00:00+09:00"}]),
        ]
        prior=base()
        for modify in changes:
            incoming=copy.deepcopy(prior)
            modify(incoming)
            self.assertTrue(requires_full_write(prior,incoming))

    def test_absent_base_must_publish_complete_card(self):
        self.assertTrue(requires_full_write(None,base()))
        self.assertFalse(requires_full_write(base(),{"not":"valid"}))
        self.assertEqual(durable_fingerprint(base()),durable_fingerprint(copy.deepcopy(base())))


if __name__=="__main__":
    unittest.main()
