"""Protect existing frozen snapshots whose declared origin hashes are invalid."""
from __future__ import annotations
import copy
import unittest
from arvexq.prediction.mass_feature_snapshot import _stable_hash
from arvexq.prediction.mass_feature_transport import (
    pack_mass_detail, restore_snapshot, recover_mass_detail)
from arvexq.prediction.mass_training_store import frozen_training_rows_from_detail
from arvexq.ingest.career_transport import pack_detail
from arvexq.prediction.mass_prerace_bridge import prepare_mass_prerace_fields
from scripts.arvexq_protect_sync import protect_detail


def old_detail():
    core={"raceId":"R1","date":"2026-10-10","horseCount":2,
          "rows":[{"horseNumber":1,"features":{"speed":3.4}},
                  {"horseNumber":2,"features":{"speed":2.1}}]}
    core["featureHash"]=_stable_hash(core)
    d={"id":"R1","date":"2026-10-10","preRacePrediction":{"modelVersion":"old"},
       "massFeatureSnapshot":core,"massFeatureHash":core["featureHash"],
       "horses":[{"horseNumber":1,"name":"H1"},{"horseNumber":2,"name":"H2"}]}
    return d


class FrozenLegacyHashTest(unittest.TestCase):
    def test_old_modified_source_remains_archived_not_fabricated(self):
        old=old_detail()
        old["massFeatureSnapshot"]["rows"][0]["features"]["speed"]=9.99
        baseline=copy.deepcopy(old)
        with self.assertRaisesRegex(ValueError,"origin hash mismatch"):
            pack_mass_detail(old)
        packed=pack_mass_detail(old,preserve_unverified_legacy=True)
        self.assertFalse(packed["massFeatureArchive"]["originHashVerified"])
        self.assertEqual(packed["massFeatureArchive"]["originStatus"],
                         "legacy-unverified-not-for-training")
        self.assertEqual(old,baseline)
        with self.assertRaisesRegex(ValueError,"not eligible for training"):
            recover_mass_detail(packed)
        recovered=restore_snapshot(packed["massFeatureArchive"],
                                  race_id="R1",race_date="2026-10-10",
                                  allow_unverified_legacy=True)
        self.assertEqual(recovered,old["massFeatureSnapshot"])
        self.assertEqual(prepare_mass_prerace_fields(packed)["massFeatureHash"],
                         old["massFeatureHash"])
        packed["result"]={"status":"確定","finishers":[{"horseNumber":1,"finish":1}]}
        self.assertEqual(frozen_training_rows_from_detail(packed),[])

    def test_live_legacy_source_is_archived_but_new_morning_is_strict(self):
        old=old_detail()
        old["massFeatureSnapshot"]["rows"][0]["features"]["speed"]=9.99
        from copy import deepcopy
        with self.assertRaisesRegex(ValueError, "origin hash mismatch"):
            pack_detail(deepcopy(old))
        retained=pack_detail(deepcopy(old), preserve_unverified_legacy=True)
        self.assertEqual(retained["massFeatureArchive"]["originHashVerified"],False)
        self.assertNotIn("massFeatureSnapshot",retained)
        self.assertEqual(retained["massFeatureHash"],old["massFeatureHash"])

    def test_protected_upsert_preserves_original_unverified_hash(self):
        old=old_detail()
        old["massFeatureSnapshot"]["rows"][0]["features"]["speed"]=9.99
        incoming=copy.deepcopy(old)
        incoming.pop("massFeatureSnapshot",None)
        incoming["massFeatureHash"]="made-up-new-hash"
        incoming["result"]={"status":"確定","finishers":[{"horseNumber":1,"finish":1}]}
        combined=protect_detail(old,incoming)
        self.assertEqual(combined["massFeatureHash"],old["massFeatureHash"])
        self.assertEqual(combined["massFeatureArchive"]["originHashVerified"],False)
        self.assertNotIn("massFeatureSnapshot",combined)
        self.assertEqual(combined["result"]["status"],"確定")


if __name__=="__main__":
    unittest.main()
