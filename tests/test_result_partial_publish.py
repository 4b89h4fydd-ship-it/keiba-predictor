"""Partial official result progress must be delivered without waiting for payouts."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import arvexq_result_repair as repair_mod


class ResultProgressPublishTests(unittest.TestCase):
    def execute(self, base, observed):
        rid = base["id"]
        rows = [{
            "id": rid, "date": "2020-01-01", "circuit": "地方",
            "track": "大井", "raceNumber": 1, "startTime": "12:00"
        }]
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            bundle=folder/"bundle.json"
            payload=folder/"payload.json"
            report=folder/"report.json"
            bundle.write_text(json.dumps({"date":"2020-01-01","races":rows,"details":[base]},ensure_ascii=False))
            with patch.object(repair_mod,"_seed_base"), \
                 patch.object(repair_mod.app,"_refresh_result_fast",side_effect=[observed,observed]), \
                 patch.object(repair_mod.time,"sleep",return_value=None):
                self.assertEqual(repair_mod.repair(str(bundle),str(payload),str(report),workers=1),0)
            return json.loads(payload.read_text()),json.loads(report.read_text())

    def test_podium_without_payout_is_still_published(self):
        rid="nar-2020-01-01-大井-01"
        original={"id":rid,"horses":[{"horseNumber":1,"name":"保存馬"}],
                  "preRacePrediction":{"frozen":True},
                  "result":{"status":"未確定","finishers":[]}}
        partial={"id":rid,"horses":[],"result":{"status":"速報",
                 "finishers":[{"horseNumber":1,"finish":1},{"horseNumber":2,"finish":2},{"horseNumber":3,"finish":3}]}}
        payload,report=self.execute(original,partial)
        self.assertEqual(report["repaired"],[])
        self.assertEqual(report["published"],[rid])
        self.assertEqual(payload["meta"]["result_published_count"],1)
        self.assertEqual(len(payload["details"]),1)
        detail=payload["details"][0]
        self.assertEqual(len(detail["result"]["finishers"]),3)
        self.assertEqual(detail["horses"],original["horses"])
        self.assertEqual(detail["preRacePrediction"],original["preRacePrediction"])

    def test_completed_result_and_payout_are_saved(self):
        rid="nar-2020-01-01-大井-01"
        base={"id":rid,"result":{"status":"速報",
              "finishers":[{"horseNumber":1,"finish":1}]}}
        complete={"id":rid,"result":{"status":"確定",
                  "finishers":[{"horseNumber":1,"finish":1},{"horseNumber":2,"finish":2},{"horseNumber":3,"finish":3}],
                  "payouts":[{"type":"馬連","combination":"1-2","amount":360}]}}
        payload,report=self.execute(base,complete)
        self.assertEqual(report["repaired"],[rid])
        self.assertEqual(report["published"],[rid])
        self.assertEqual(payload["meta"]["result_repaired_count"],1)


if __name__=="__main__":
    unittest.main()
