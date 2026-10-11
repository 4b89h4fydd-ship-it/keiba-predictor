"""Validate commercial-rights audit and progress-only data publication."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from scripts.arvexq_boat_publish import validate_day,publish

DAY="2026-10-12"
def snapshot():
    return {
        "version":"arvexq-boat-day-v1","date":DAY,"verified":True,
        "rights":{"commercialUseAuthorized":True,"provenanceId":"authorized-test-fixture",
                  "permissionEvidence":"local-fixture-only"},
        "verifiedAt":DAY+"T08:00:00+09:00",
        "races":[{
            "id":"boat-"+DAY+"-桐生-01","venue":"桐生","raceNo":1,
            "closeAt":DAY+"T12:00:00+09:00","closeTime":"12:00",
            "entries":[{"boatNo":n,"name":"選手"+str(n)} for n in range(1,7)],
            "odds3t":{"verified":True,"source":"BOATRACE公式",
                      "updatedAt":DAY+"T11:40:00+09:00","values":{"1-2-3":4.5}},
            "result":{"status":"confirmed","trifecta":"1-2-3",
                      "trifectaPayoutYen":450,"confirmedAt":DAY+"T12:09:00+09:00"}
        }]
    }

class BoatFeedPublisherTest(unittest.TestCase):
    def test_verified_snapshot(self):
        src=snapshot()
        out=validate_day(src)
        self.assertNotIn("rights",out)
        self.assertEqual(out["races"][0]["result"]["trifecta"],"1-2-3")
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            source=folder/"feed.json"
            source.write_text(json.dumps(src,ensure_ascii=False))
            target=publish(source,folder/"public")
            loaded=json.loads(target.read_text())
            self.assertEqual(loaded["verified"],True)
            self.assertEqual(loaded["races"][0]["entries"][0]["name"],"選手1")
            self.assertNotIn("permissionEvidence",target.read_text())

    def test_reject_unlicensed_or_unverified(self):
        for change in (
            {"verified":False}, {"rights":{}},
            {"rights":{"commercialUseAuthorized":False,"provenanceId":"some",
                       "permissionEvidence":"some"}},
            {"races":[]}
        ):
            data=snapshot();data.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                validate_day(data)

    def test_no_after_cutoff_or_fake_teams(self):
        data=snapshot()
        race=data["races"][0]
        race["forecast"]={"status":"verified","snapshotAt":DAY+"T12:02:00+09:00",
                          "tickets":[{"combination":"1-2-3"}]}
        with self.assertRaises(ValueError):validate_day(data)
        race["forecast"]["snapshotAt"]=DAY+"T11:30:00+09:00"
        race["forecast"]["model"]={"experimental":True}
        with self.assertRaises(ValueError):validate_day(data)
        del race["forecast"]["model"]
        with self.assertRaises(ValueError):
            race["forecast"]["tickets"]=[{"combination":"1-2-3"}]*7
            validate_day(data)

    def test_allow_results_without_payouts(self):
        data=snapshot()
        data["races"][0]["result"]={"status":"pending"}
        self.assertEqual(validate_day(data)["races"][0]["result"]["status"],"pending")
        del data["races"][0]["result"]
        self.assertEqual(validate_day(data)["races"][0].get("result"),None)


if __name__=="__main__":unittest.main()
