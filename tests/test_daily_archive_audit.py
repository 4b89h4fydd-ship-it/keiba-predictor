import unittest
from copy import deepcopy
from datetime import datetime, timedelta
from arvexq.prediction.prerace_archive import JST, seal_detail
from scripts.arvexq_daily_archive_audit import inspect


class DailyArchiveTests(unittest.TestCase):
    def setUp(self):
        now=datetime(2026,10,8,19,30,tzinfo=JST)
        post=now+timedelta(minutes=30)
        self.race={"id":"nar-2026-10-08-大井-11","date":post.strftime("%Y-%m-%d"),
                   "startTime":"20:00","horses":[{"horseNumber":i,"name":"Horse","integratedEvaluation":{"mark":m}}
                    for i,m in ((1,"◎"),(2,"○"),(3,"▲"))]}
        lock={"raceId":self.race["id"],"raceDate":self.race["date"],
              "capturedAtEpoch":int(now.timestamp()),"horses":[
              {"horseNumber":i,"mark":m} for i,m in ((1,"◎"),(2,"○"),(3,"▲"))]}
        self.sealed=seal_detail(self.race,lock,now)
        self.sealed["preRaceBet"]={"fixedAt":now.isoformat(),"decision":"採用","items":[]}

    def test_sealed_eligible_ticket(self):
        r=inspect(self.race,self.sealed)
        self.assertEqual((r["status"],r["ticket"]),("sealed","recorded"))

    def test_unsealed_missing_not_fabricated(self):
        self.assertEqual(inspect(self.race,self.race)["status"],"missing-preoff-seal")

    def test_missing_ticket_reported_separately(self):
        d=deepcopy(self.sealed)
        d.pop("preRaceBet")
        r=inspect(self.race,d)
        self.assertEqual((r["status"],r["ticket"]),("sealed","missing"))

    def test_misleading_ticket_failure_not_called_bet_skip(self):
        d=deepcopy(self.sealed)
        d["preRaceBet"]={"fixedAt":"2026-10-08T19:40:00+09:00",
                         "decision":"未取得","captureStatus":"failed","items":[]}
        self.assertEqual(inspect(self.race,d)["ticket"],"capture-failed")

    def test_cancelled_race_can_be_excluded_without_postbackfill(self):
        r=dict(self.race,raceStatus="取止")
        self.assertEqual(inspect(r,None)["status"],"race-cancelled")


if __name__=="__main__":
    unittest.main()
