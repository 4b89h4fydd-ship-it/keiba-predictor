import base64
from datetime import datetime
import gzip
import hashlib
import json
import unittest

from scripts.arvexq_preoff_snapshot_inventory import inspect_envelope


def envelope(captured):
    raw = json.dumps({"date": "2026-10-13", "startTime": "12:00",
                      "circuit": "地方", "preRacePrediction": {"fixedAt": "2026-10-13T10:00:00+09:00"},
                      "horses": []}).encode()
    return {"capturedAt": captured,
            "gzipBase64": base64.b64encode(gzip.compress(raw)).decode(),
            "sha256": hashlib.sha256(raw).hexdigest()}


class SnapshotInventoryTests(unittest.TestCase):
    def test_only_preoff_snapshot_timestamp_makes_candidate(self):
        early = inspect_envelope(envelope("2026-10-13T11:00:00+09:00"))
        late = inspect_envelope(envelope("2026-10-13T12:01:00+09:00"))
        no_timestamp = inspect_envelope(envelope(""))
        self.assertTrue(early["candidate"])
        self.assertFalse(late["candidate"])
        self.assertFalse(no_timestamp["candidate"])
        self.assertTrue(late["lockedForecast"])

    def test_mass_feature_hash_link_is_not_capture_timestamp_proof(self):
        race = {"date": "2026-10-13", "startTime": "12:00", "circuit": "中央",
                "id": "race-1",
                "preRacePrediction": {"massFeatureHash": "abc"},
                "massFeatureHash": "abc",
                "massFeatureArchive": {"featureHash": "abc", "originHashVerified": True}}
        raw = json.dumps(race).encode()
        data = {"gzipBase64": base64.b64encode(gzip.compress(raw)).decode(),
                "sha256": hashlib.sha256(raw).hexdigest()}
        report = inspect_envelope(data)
        self.assertTrue(report["massLinked"])
        self.assertTrue(report["originDeclaredVerified"])
        self.assertFalse(report["candidate"])

    def test_hash_failure_is_not_silently_accepted(self):
        data = envelope("2026-10-13T11:00:00+09:00")
        data["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            inspect_envelope(data)


if __name__ == "__main__":
    unittest.main()
