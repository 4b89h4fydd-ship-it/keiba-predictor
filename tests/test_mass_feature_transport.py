"""Lossless multi-megabyte feature evidence transport, immutability and training."""
from __future__ import annotations
import copy
import json
import unittest
from datetime import datetime
from arvexq.prediction.prerace_archive import JST, seal_detail
from arvexq.prediction.mass_prerace_bridge import apply_mass_prerace_fields

from arvexq.prediction.mass_feature_snapshot import _stable_hash, SNAPSHOT_VERSION
from arvexq.prediction.mass_feature_transport import (
    archive_snapshot, restore_snapshot, pack_mass_detail, recover_mass_detail)
from arvexq.prediction.mass_prerace_bridge import prepare_mass_prerace_fields
from arvexq.prediction.mass_training_store import frozen_training_rows_from_detail
from arvexq.ingest.career_transport import pack_detail


def historical_detail(large: bool = True):
    features = {
        f"historic_observed_stat_{i:05d}_distance_track_going": round((i % 21) / 11, 6)
        for i in range(3100 if large else 12)
    }
    rows = [{"horseNumber":n, "name":f"H{n}", "features":features,
             "featureCount":len(features)} for n in range(1, 17 if large else 4)]
    core = {
        "snapshotVersion": SNAPSHOT_VERSION, "schemaVersion":"schema",
        "selectionVersion":"selected", "raceId":"race-10",
        "date":"2026-10-10", "circuit":"地方", "track":"高知",
        "raceNumber":1, "distance":1400, "horseCount":len(rows),
        "rows":rows,
    }
    original = copy.deepcopy(core)
    core["featureHash"] = _stable_hash(core)
    assert core["featureHash"] == _stable_hash(original)
    return {
        "id":"race-10", "date":"2026-10-10", "raceNumber":1,
        "preRacePrediction":{"modelVersion":"original", "massFeatureHash":core["featureHash"]},
        "massFeatureSnapshot":core,
        "massFeatureHash":core["featureHash"],
        "massFeatureSchemaVersion":"schema",
        "massFeatureSnapshotVersion":SNAPSHOT_VERSION,
        "horses":[{"horseNumber":i,"name":f"H{i}","recentRaces":[]} for i in range(1,len(rows)+1)],
    }


def json_size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


class MassFeatureTransportTest(unittest.TestCase):
    def test_multi_megabyte_feature_snapshot_is_losslessly_compressed(self):
        original = historical_detail()
        original_copy = copy.deepcopy(original)
        self.assertGreater(json_size(original),2_000_000)
        packed = pack_detail(original)
        self.assertEqual(original,original_copy)
        self.assertNotIn("massFeatureSnapshot",packed)
        self.assertIn("massFeatureArchive",packed)
        self.assertLess(json_size(packed),900_000)
        recovered = recover_mass_detail(packed)
        self.assertEqual(recovered["massFeatureSnapshot"],original["massFeatureSnapshot"])
        self.assertEqual(recovered["massFeatureHash"],original["massFeatureHash"])
        self.assertEqual(pack_detail(packed),packed)
        self.assertEqual(prepare_mass_prerace_fields(packed)["massFeatureHash"],original["massFeatureHash"])

    def test_final_training_can_only_read_frozen_preoff_archived_features(self):
        original=historical_detail(False)
        packed=pack_detail(original)
        packed["result"]={"status":"確定","finishers":[
            {"horseNumber":1,"finish":2},{"horseNumber":2,"finish":1},{"horseNumber":3,"finish":3}]}
        rows=frozen_training_rows_from_detail(packed)
        self.assertEqual(len(rows),0)
        # Legacy hash-valid data without authenticated capture time is not training evidence.

    def test_corruption_wrong_race_and_hash_fail_closed(self):
        packed=pack_mass_detail(historical_detail(False))
        original=packed["massFeatureArchive"]
        for field,value in [("sha256","a"*64),("raceDate","2026-10-11"),("featureHash","a"*64),
                            ("payload","not valid base64")]:
            bad=copy.deepcopy(original)
            bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                restore_snapshot(bad,race_id="race-10",race_date="2026-10-10")
        with self.assertRaises(ValueError):
            restore_snapshot(original,race_id="another-race",race_date="2026-10-10")

    def test_preoff_archive_guard_never_invents_features(self):
        data=historical_detail(False)
        data["massFeatureSnapshot"]["rows"].clear()
        with self.assertRaises(ValueError):
            pack_mass_detail(data)


    def test_missing_mass_features_cannot_be_rebuilt_after_post(self):
        date = "2026-10-14"
        detail = {"id": "R", "date": date, "startTime": "12:00",
                  "circuit": "地方", "track": "大井", "raceNumber": 1,
                  "distance": 1400, "surface": "ダート",
                  "horses": [{"horseNumber": 1, "name": "A", "recentRaces": []},
                             {"horseNumber": 2, "name": "B", "recentRaces": []}]}
        start = datetime(2026, 10, 14, 11, 0, tzinfo=JST)
        captured = datetime(2026, 10, 14, 10, 50, tzinfo=JST)
        lock = {"raceId": "R", "raceDate": date,
                "capturedAtEpoch": int(captured.timestamp()),
                "horses": [{"horseNumber": 1, "mark": "◎"},
                           {"horseNumber": 2, "mark": "○"}]}
        sealed = seal_detail(detail, lock, now=start)
        before = prepare_mass_prerace_fields(sealed, now=start)
        self.assertIn("massFeatureSnapshot", before)
        self.assertEqual(before["massFeatureCapturedAtEpoch"], int(start.timestamp()))
        later = datetime(2026, 10, 14, 12, 5, tzinfo=JST)
        self.assertEqual(prepare_mass_prerace_fields(sealed, now=later), {})
        finalized = dict(sealed, result={"status": "確定"})
        self.assertEqual(prepare_mass_prerace_fields(finalized, now=start), {})
        persisted = apply_mass_prerace_fields(copy.deepcopy(sealed), before)
        self.assertEqual(persisted["preRacePrediction"]["massFeatureCapturedAtEpoch"],
                         int(start.timestamp()))
        self.assertIn("massFeatureHash", prepare_mass_prerace_fields(persisted, now=later))
        persisted["result"] = {"status": "確定", "finishers": [
            {"horseNumber": 1, "finish": 1}, {"horseNumber": 2, "finish": 2}]}
        trusted = frozen_training_rows_from_detail(persisted)
        self.assertEqual(len(trusted), 2)
        self.assertEqual(sum(row["labelWin"] for row in trusted), 1)
        forged = copy.deepcopy(persisted)
        forged["massFeatureCapturedAtEpoch"] = int(later.timestamp())
        self.assertEqual(frozen_training_rows_from_detail(forged), [])



if __name__=="__main__":
    unittest.main()
