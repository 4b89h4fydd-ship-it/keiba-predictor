"""Live-only transport must not publish orphan mass matrices as frozen training data."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from arvexq.ingest.full_snapshot_codec import unpack_detail
from arvexq.prediction.mass_feature_snapshot import _stable_hash
from scripts import arvexq_sync_batches as batches


class LiveUnsealedMassTests(unittest.TestCase):
    def payload(self, *, live=True, frozen=False):
        rid = "nar-2026-10-24-佐賀-07"
        mass = {"raceId": rid, "date": "2026-10-24", "horseCount": 1,
                "rows": [{"horseNumber": 1, "features": {"speed": 5.1}}]}
        mass["featureHash"] = _stable_hash(mass)
        detail = {"id": rid, "date": "2026-10-24", "track": "佐賀",
                  "circuit": "地方", "horses": [{"horseNumber": 1, "name": "H1",
                  "winOdds": 3.5, "recentRaces": []}],
                  "massFeatureSnapshot": mass, "massFeatureHash": mass["featureHash"]}
        if frozen:
            detail["preRacePrediction"] = {"raceId": rid, "modelVersion": "original"}
        return {"summaries": [{"id": rid, "date": "2026-10-24", "track": "佐賀"}],
                "details": [detail],
                "meta": {"live_delta": live}}

    def run_batch(self, payload):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file, out = root / "source.json", root / "batches"
            original = copy.deepcopy(payload)
            file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(sys, "argv", ["arvexq_sync_batches",
                               "--input", str(file), "--out-dir", str(out)]):
                batches.main()
            self.assertEqual(json.loads(file.read_text(encoding="utf-8")), original)
            files = sorted(out.glob("batch-*.json"))
            self.assertTrue(files)
            batches_data = [json.loads(f.read_text(encoding="utf-8")) for f in files]
            return [unpack_detail(d) for b in batches_data
                    for d in b.get("details") or []]

    def test_orphan_is_not_published_as_preoff_while_other_live_fields_survive(self):
        record = self.payload()
        results = self.run_batch(record)
        self.assertEqual(len(results), 1)
        row = results[0]
        self.assertEqual(row["horses"][0]["name"], "H1")
        self.assertEqual(row["horses"][0]["winOdds"], 3.5)
        self.assertNotIn("massFeatureSnapshot", row)
        self.assertNotIn("massFeatureArchive", row)
        self.assertNotIn("massFeatureHash", row)
        self.assertIn("massFeatureSnapshot", record["details"][0])

    def test_ordinary_prefetch_still_refuses_unsealed_feature_matrix(self):
        record = self.payload(live=False)
        with self.assertRaisesRegex(ValueError, "without pre-off forecast"):
            self.run_batch(record)

    def test_frozen_live_feature_matrix_remains_lossless(self):
        record = self.payload(frozen=True)
        row = self.run_batch(record)[0]
        self.assertNotIn("massFeatureSnapshot", row)
        self.assertEqual(row["massFeatureArchive"]["originHashVerified"], True)
        self.assertEqual(row["massFeatureHash"],
                         record["details"][0]["massFeatureHash"])


if __name__ == "__main__":
    unittest.main()
