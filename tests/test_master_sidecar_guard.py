"""Guard the signed research sidecar through ordinary D1 sync traffic."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import unittest

from rewrite.output.api_shape import MODEL_VERSION
from scripts.arvexq_protect_sync import protect_detail


def signed_sidecar(captured="2026-11-09T09:00:00+09:00"):
    value = {
        "version": "master-18-factor-shadow-v1",
        "status": "shadow-candidate",
        "capturedAt": captured, "validated": False,
        "runners": [{"horseNumber": 1, "pWin": 0.5}],
    }
    value["contentSha256"] = sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()
    return value


def saved():
    return {
        "id": "nar-2026-11-09-園田-01",
        "date": "2026-11-09", "horses": [],
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preparedMeta": {"rewritePublish": {
            "modelVersion": MODEL_VERSION,
            "publishedAt": "2026-11-09T09:00:00+09:00",
            "receiptSha256": "a" * 64,
        }},
        "prediction": {"capturedAt": "2026-11-09T09:00:00+09:00"},
        "predictionMarks": [], "unifiedForecast": {"marks": []},
        "recommendedBets": [], "forecastText": "",
        "masterAnalysis": signed_sidecar(),
    }


class MasterSidecarGuardTests(unittest.TestCase):
    def test_live_sync_omitting_sidecar_preserves_original(self):
        old = saved()
        incoming = {"id": old["id"], "date": old["date"],
                    "horses": [], "oddsUpdatedAt": 123}
        protected = protect_detail(old, incoming)
        self.assertEqual(protected["masterAnalysis"], old["masterAnalysis"])
        self.assertEqual(protected["unifiedForecast"], old["unifiedForecast"])
        self.assertEqual(protected["oddsUpdatedAt"], 123)

    def test_non_publish_sync_cannot_modify_signed_research(self):
        old = saved()
        incoming = {"id": old["id"], "date": old["date"],
                    "horses": [], "masterAnalysis": signed_sidecar("2099-01-01T00:00:00+09:00")}
        protected = protect_detail(old, incoming)
        self.assertEqual(protected["masterAnalysis"], old["masterAnalysis"])

    def test_non_publish_sync_cannot_inject_research(self):
        old = saved()
        old.pop("masterAnalysis")
        incoming = {"id": old["id"], "date": old["date"],
                    "horses": [], "masterAnalysis": signed_sidecar()}
        protected = protect_detail(old, incoming)
        self.assertNotIn("masterAnalysis", protected)

    def test_new_authorized_publication_requires_correct_hash_and_time(self):
        old = saved()
        old.pop("masterAnalysis")
        old.pop("preparedMeta")
        write = saved()
        good = protect_detail(old, deepcopy(write))
        self.assertEqual(good["masterAnalysis"], write["masterAnalysis"])

        forged = deepcopy(write)
        forged["masterAnalysis"]["runners"][0]["pWin"] = 0.9
        with self.assertRaisesRegex(ValueError, "signature"):
            protect_detail(old, forged)

        mismatched = deepcopy(write)
        mismatched["masterAnalysis"] = signed_sidecar("2026-11-09T08:00:00+09:00")
        with self.assertRaisesRegex(ValueError, "capture mismatch"):
            protect_detail(old, mismatched)

    def test_surgical_authorized_publish_does_not_erase_research(self):
        old = saved()
        incoming = deepcopy(old)
        incoming.pop("masterAnalysis")
        incoming["preparedMeta"]["rewritePublish"]["publishedAt"] = "2026-11-09T09:30:00+09:00"
        incoming["prediction"]["capturedAt"] = "2026-11-09T09:30:00+09:00"
        protected = protect_detail(old, incoming)
        self.assertEqual(protected["masterAnalysis"], old["masterAnalysis"])


if __name__ == "__main__":
    unittest.main()
