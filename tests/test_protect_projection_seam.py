"""Regression: the projection seam (2026-11-05).

Two chained failures hid nine races' forecasts in the app and then
destroyed the stored forecast blocks themselves:

- Flip: a display-compacted write — a stored publication that had
  passed through the Python delivery projection (public_race), whose
  top-level status reads "unified-reference-ready" — carried a
  complete current-version marker, so protect_detail accepted it as
  a genuine publish write and stored the projection's vocabulary in
  D1. The worker projection honours only status exactly "ready",
  so the races vanished from the app.
- Tombstone restore: once flipped, every API read of the race was
  the worker's projection tombstone (status "disabled", model
  version "arvexq-prediction-removed", forecast blocks stripped).
  protect_detail restored the forecast blocks FROM that read, so
  the next sync write deleted prediction/predictionMarks/
  recommendedBets from storage and stamped the tombstone values.

These tests pin the fix in scripts/arvexq_protect_sync.py:
- a genuine publish write must carry predictionStatus "ready";
  a projection-shaped write goes through the restore branch and
  the stored status/blocks survive;
- a tombstoned stored read is restored from the sealed pre-off
  archive (or, at the fetch layer, through the worker's display
  view) and fails closed when no verified restore exists.
"""
from __future__ import annotations

import io
import json
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from arvexq.prediction.unified_product import MODEL_VERSION
from scripts import arvexq_protect_sync as protect_sync
from scripts.arvexq_protect_sync import fetch_current, protect_detail

RID = "nar-2026-11-05-園田-04"
DATE = "2026-11-05"
MARKER = {"modelVersion": MODEL_VERSION,
          "publishedAt": "2026-11-04T16:15:00+09:00",
          "receiptSha256": "a" * 64, "abilityLane": "v9b-cal-market",
          "temperature": 0.6692, "blendApplied": True}
LABELS = ["◎", "○", "▲", "△", "☆"]


def _horses() -> list:
    return [{"horseNumber": n, "name": f"H{n}"} for n in range(1, 11)]


def _marks() -> list:
    return [{"horseNumber": n + 1, "mark": LABELS[n],
             "winProbability": 0.3 - 0.04 * n} for n in range(5)]


def _prediction() -> dict:
    return {"raceId": RID, "date": DATE, "modelVersion": MODEL_VERSION,
            "predictionStatus": "ready", "productionEligible": True,
            "predictionMarks": _marks()}


def _publication() -> dict:
    """A complete stored publication as the publish lane wrote it."""
    return {
        "id": RID, "date": DATE, "horses": _horses(),
        "preparedMeta": {"rewritePublish": deepcopy(MARKER)},
        "unifiedForecast": {"receiptSha256": "a" * 64,
                            "modelVersion": MODEL_VERSION},
        "prediction": _prediction(),
        "predictionMarks": _marks(),
        "recommendedBets": [{"kind": "三連単", "combos": [[1, 2, 3]]}],
        "forecastText": "text",
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preRaceBet": {"decision": "推奨"},
    }


def _archive() -> dict:
    pub = _publication()
    return {"raceId": RID, "raceDate": DATE,
            "predictionStatus": pub["predictionStatus"],
            "predictionModelVersion": pub["predictionModelVersion"],
            "prediction": pub["prediction"],
            "predictionMarks": pub["predictionMarks"],
            "recommendedBets": pub["recommendedBets"]}


def _tombstoned_read() -> dict:
    """The worker projection's shape for a flipped stored detail."""
    pub = _publication()
    for key in ("prediction", "predictionMarks", "recommendedBets"):
        del pub[key]
    pub["predictionStatus"] = "disabled"
    pub["predictionModelVersion"] = "arvexq-prediction-removed"
    return pub


class ProjectionSeamTests(TestCase):
    def test_projection_shaped_write_cannot_flip_stored_status(self):
        old = _publication()
        incoming = _publication()
        # The display-compacted seed: identical publication, but the
        # top-level status carries the projection's vocabulary.
        incoming["predictionStatus"] = "unified-reference-ready"
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["predictionStatus"], "ready")
        self.assertEqual(out["predictionModelVersion"], MODEL_VERSION)
        self.assertEqual(out["prediction"], old["prediction"])
        self.assertEqual(out["predictionMarks"], old["predictionMarks"])
        self.assertEqual(out["recommendedBets"], old["recommendedBets"])

    def test_genuine_ready_publish_write_still_replaces(self):
        old = _publication()
        incoming = _publication()
        incoming["forecastText"] = "lane-reissued"
        incoming["preparedMeta"]["rewritePublish"] = dict(
            MARKER, publishedAt="2026-11-05T02:00:00+09:00",
            receiptSha256="b" * 64,
            firstPublishedAt=MARKER["publishedAt"],
            revision={"kind": "blend-upgrade", "reason": "blend-upgrade",
                      "revisedAt": "2026-11-05T02:00:00+09:00",
                      "revisionCount": 1,
                      "previousReceiptSha256": "a" * 64,
                      "previousAbilityLane": "v9b-cal-market",
                      "abilityLane": "v9b-cal-market"})
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["forecastText"], "lane-reissued")
        self.assertEqual(out["predictionStatus"], "ready")

    def test_tombstoned_read_restored_from_archive(self):
        old = _tombstoned_read()
        old["preoffStage64Archive"] = _archive()
        incoming = _publication()
        # A plain sync write carrying no forecast authority of its own.
        for key in ("prediction", "predictionMarks", "recommendedBets",
                    "predictionStatus", "predictionModelVersion",
                    "preRaceBet", "unifiedForecast"):
            del incoming[key]
        incoming["preparedMeta"] = {"liveUpdatedAtEpoch": 1760010001}
        incoming["oddsNote"] = "fresh"
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        archive = _archive()
        self.assertEqual(out["predictionStatus"], "ready")
        self.assertEqual(out["predictionModelVersion"], MODEL_VERSION)
        self.assertEqual(out["prediction"], archive["prediction"])
        self.assertEqual(out["predictionMarks"], archive["predictionMarks"])
        self.assertEqual(out["recommendedBets"], archive["recommendedBets"])
        # The publish marker survives via the preparedMeta field merge.
        self.assertEqual(
            out["preparedMeta"]["rewritePublish"], MARKER)
        self.assertEqual(out["oddsNote"], "fresh")

    def test_tombstoned_read_without_archive_fails_closed(self):
        old = _tombstoned_read()
        incoming = _publication()
        with self.assertRaises(RuntimeError):
            protect_detail(deepcopy(old), deepcopy(incoming))

    def test_tombstoned_read_with_unverifiable_archive_fails_closed(self):
        old = _tombstoned_read()
        archive = _archive()
        archive["predictionMarks"] = archive["predictionMarks"][:4]
        archive["prediction"]["predictionMarks"] = archive["predictionMarks"]
        old["preoffStage64Archive"] = archive
        incoming = _publication()
        with self.assertRaises(RuntimeError):
            protect_detail(deepcopy(old), deepcopy(incoming))


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _json_response(payload: dict) -> _FakeResponse:
    return _FakeResponse(json.dumps(payload).encode("utf-8"))


class FetchCurrentTombstoneTests(TestCase):
    def test_tombstone_read_falls_back_to_display_restore(self):
        tombstone = _tombstoned_read()
        restored = _publication()
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            if "view=display" in req.full_url:
                return _json_response({"ok": True, "detail": restored})
            return _json_response({"ok": True, "detail": tombstone})

        with patch.object(protect_sync.urllib.request, "urlopen",
                          fake_urlopen):
            got = fetch_current("https://example.invalid", RID)
        self.assertEqual(got["predictionStatus"], "ready")
        self.assertEqual(got["prediction"], restored["prediction"])
        self.assertEqual(len(calls), 2)

    def test_tombstone_read_without_display_restore_fails_closed(self):
        tombstone = _tombstoned_read()

        def fake_urlopen(req, timeout=None):
            return _json_response({"ok": True, "detail": tombstone})

        with patch.object(protect_sync.urllib.request, "urlopen",
                          fake_urlopen):
            with self.assertRaises(RuntimeError):
                fetch_current("https://example.invalid", RID)

    def test_healthy_read_needs_no_display_fallback(self):
        healthy = _publication()
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            return _json_response({"ok": True, "detail": healthy})

        with patch.object(protect_sync.urllib.request, "urlopen",
                          fake_urlopen):
            got = fetch_current("https://example.invalid", RID)
        self.assertEqual(got["predictionStatus"], "ready")
        self.assertEqual(len(calls), 1)
