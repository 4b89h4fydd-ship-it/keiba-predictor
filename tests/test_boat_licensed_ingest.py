"""Single licensed BOAT ingestion: no invented data and no rewritten pre-off bets."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from scripts.arvexq_boat_ingest import ingest, merge_public
from scripts.arvexq_boat_publish import validate_day

DAY="2026-10-12"

def licensed():
    return {
        "version":"arvexq-boat-day-v1","date":DAY,"verified":True,
        "rights":{"commercialUseAuthorized":True,
                  "provenanceId":"test-contract-not-a-production-license",
                  "permissionEvidence":"fixture-only-not-redistributable"},
        "verifiedAt":DAY+"T09:00:00+09:00",
        "races":[{
            "id":"boat-"+DAY+"-桐生-01","venue":"桐生","raceNo":1,
            "closeAt":DAY+"T11:30:00+09:00","closeTime":"11:30",
            "entries":[{"boatNo":i,"name":"fixture選手"+str(i)} for i in range(1,7)],
        }],
    }

class BoatLicensedIngestTests(unittest.TestCase):
    def test_ingest_idempotent_and_keeps_actual_records(self):
        with tempfile.TemporaryDirectory() as td:
            a=licensed()
            first,changed=ingest(a,DAY,Path(td))
            self.assertTrue(changed)
            self.assertEqual(json.loads(first.read_text())["races"][0]["entries"][5]["boatNo"],6)
            self.assertFalse(ingest(a,DAY,Path(td))[1])
            self.assertNotIn("permissionEvidence",first.read_text())

    def test_wrong_day_or_unlicensed_rejected_without_replacing_file(self):
        with tempfile.TemporaryDirectory() as td:
            a=licensed()
            original,_=ingest(a,DAY,Path(td))
            prior=original.read_bytes()
            b=copy.deepcopy(a);b["rights"]["commercialUseAuthorized"]=False
            with self.assertRaises(ValueError):ingest(b,DAY,Path(td))
            with self.assertRaises(ValueError):ingest(a,"2026-10-13",Path(td))
            self.assertEqual(original.read_bytes(),prior)

    def test_append_races_and_keep_locked_bets(self):
        old=validate_day(licensed())
        old["races"][0]["forecast"]={"status":"verified","snapshotAt":DAY+"T11:00:00+09:00","tickets":["1-2-3"]}
        fresh=licensed()
        fresh["verifiedAt"]=DAY+"T11:20:00+09:00"
        fresh["races"].append({
            "id":"boat-"+DAY+"-桐生-02","venue":"桐生","raceNo":2,
            "closeAt":DAY+"T12:00:00+09:00","closeTime":"12:00",
        })
        next_day=merge_public(old,validate_day(fresh))
        self.assertEqual(len(next_day["races"]),2)
        self.assertEqual(next_day["races"][0]["forecast"],old["races"][0]["forecast"])
        altered=validate_day(fresh)
        altered["races"][0]["forecast"]={"status":"verified","snapshotAt":DAY+"T11:20:00+09:00","tickets":["1-3-2"]}
        with self.assertRaises(ValueError):merge_public(old,altered)

    def test_verified_result_cannot_be_erased_by_late_snapshot(self):
        old=validate_day(licensed())
        old["races"][0]["result"]={"status":"confirmed","trifecta":"1-2-3","confirmedAt":DAY+"T11:39:00+09:00","trifectaPayoutYen":990}
        later=validate_day(licensed())
        new=merge_public(old,later)
        self.assertEqual(new["races"][0]["result"],old["races"][0]["result"])
        later["races"][0]["result"]={"status":"confirmed","trifecta":"1-2-4","confirmedAt":DAY+"T11:39:00+09:00"}
        with self.assertRaises(ValueError):merge_public(old,later)

if __name__=="__main__":unittest.main()
