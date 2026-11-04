"""Regression: the rewritePublish marker seam (2026-11-04).

The marker in preparedMeta.rewritePublish is the only canonical
record of a published forecast's post-processing (blendApplied and
the revision chain live nowhere else), and the publish lane's
upgrade guards and freeze decision key on it. Two depths of the
same overwrite seam damaged it on 2026-11-04:

- Depth B (marker loss): the realtime sync's re-analysis replaced
  preparedMeta with a lightweight fast-diagnosis snapshot (no
  rewritePublish). protect_detail restored the forecast blocks but
  let preparedMeta through untouched, so four races (each venue's
  1R) lost the marker entirely — unfreezing them and blocking every
  marker-keyed upgrade guard.
- Depth A (rollback): a prefetch prepared payload seeded BEFORE a
  blend upgrade was re-applied AFTER it. The seed carries a
  complete, current-version marker over the OLD forecast, so the
  old marker+completeness check passed it as a genuine publish
  write and 13 races rolled back to their first-published state.

These tests pin the fix in scripts/arvexq_protect_sync.py:
- a marker-carrying write replaces the stored publication only
  when it advances the marker chain (see _rewrite_marker_fresh);
- any other write field-merges preparedMeta: incoming stays the
  base, rewritePublish is carried over from the stored detail.
"""
from __future__ import annotations

from copy import deepcopy
from unittest import TestCase

from arvexq.prediction.unified_product import MODEL_VERSION
from scripts.arvexq_protect_sync import protect_detail

FIRST_AT = "2026-11-04T00:13:22+09:00"
UPGRADE_AT = "2026-11-04T02:36:30+09:00"
PLACE_AT = "2026-11-04T09:40:00+09:00"
RECEIPT0 = "a" * 64
RECEIPT1 = "b" * 64
RECEIPT2 = "c" * 64


def _post_processing(blend: bool) -> dict:
    return {"type": "temperature+market-blend", "temperature": 0.6692,
            "blendWeight": 0.5, "blendApplied": blend}


def _marker_first() -> dict:
    return {"modelVersion": MODEL_VERSION, "publishedAt": FIRST_AT,
            "receiptSha256": RECEIPT0, "abilityLane": "v9b-cal-market",
            "temperature": 0.6692, "blendApplied": False,
            "postProcessing": _post_processing(False)}


def _marker_blend_upgraded() -> dict:
    marker = _marker_first()
    marker.update({"publishedAt": UPGRADE_AT, "receiptSha256": RECEIPT1,
                   "blendApplied": True,
                   "postProcessing": _post_processing(True),
                   "firstPublishedAt": FIRST_AT,
                   "revision": {
                       "kind": "blend-upgrade", "reason": "blend-upgrade",
                       "revisedAt": UPGRADE_AT, "revisionCount": 1,
                       "previousReceiptSha256": RECEIPT0,
                       "previousAbilityLane": "v9b-cal-market",
                       "abilityLane": "v9b-cal-market"}})
    return marker


def _detail(marker: dict, receipt: str, flavour: str) -> dict:
    return {
        "id": "nar-2026-11-04-金沢-06", "date": "2026-11-04",
        "preparedMeta": {"dataVersion": "v1",
                         "prefetchedAtEpoch": 1760000000,
                         "rewritePublish": deepcopy(marker)},
        "unifiedForecast": {"receiptSha256": receipt, "flavour": flavour},
        "prediction": {"modelVersion": MODEL_VERSION, "flavour": flavour},
        "predictionMarks": [{"horseNumber": 8, "mark": "◎"}],
        "recommendedBets": [{"kind": "単勝", "flavour": flavour}],
        "forecastText": flavour,
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preRaceBet": {"decision": "推奨", "flavour": flavour},
        "horses": [],
    }


class MarkerSeamTests(TestCase):
    def test_depth_b_lightweight_prepared_meta_keeps_marker(self):
        old = _detail(_marker_blend_upgraded(), RECEIPT1, "blended")
        incoming = _detail(_marker_blend_upgraded(), RECEIPT1, "blended")
        # The realtime-sync overwrite: a fast-diagnosis snapshot's
        # lightweight preparedMeta (14 keys, no rewritePublish).
        incoming["preparedMeta"] = {
            "prepared": True, "preparedAtEpoch": 1760010000,
            "liveUpdatedAtEpoch": 1760010001, "displayCompact": True}
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(
            out["preparedMeta"]["rewritePublish"], _marker_blend_upgraded())
        # The incoming lane's own bookkeeping still lands.
        self.assertEqual(out["preparedMeta"]["liveUpdatedAtEpoch"],
                         1760010001)
        self.assertEqual(out["unifiedForecast"]["flavour"], "blended")

    def test_depth_a_stale_seed_does_not_roll_back_upgrade(self):
        old = _detail(_marker_blend_upgraded(), RECEIPT1, "blended")
        # A prepared payload seeded before the blend upgrade: complete
        # forecast blocks and a complete current-version marker, but
        # the FIRST-published state (older publishedAt, no revision).
        incoming = _detail(_marker_first(), RECEIPT0, "calibration-only")
        incoming["preparedMeta"]["diagnosisPreparedAtEpoch"] = 1760005000
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["unifiedForecast"]["flavour"], "blended")
        marker = out["preparedMeta"]["rewritePublish"]
        self.assertEqual(marker, _marker_blend_upgraded())
        self.assertTrue(marker["blendApplied"])
        self.assertEqual(marker["revision"]["kind"], "blend-upgrade")

    def test_genuine_blend_upgrade_replaces(self):
        old = _detail(_marker_first(), RECEIPT0, "calibration-only")
        incoming = _detail(_marker_blend_upgraded(), RECEIPT1, "blended")
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["unifiedForecast"]["flavour"], "blended")
        self.assertEqual(out["preparedMeta"]["rewritePublish"],
                         _marker_blend_upgraded())

    def test_genuine_place_ev_upgrade_replaces(self):
        old = _detail(_marker_blend_upgraded(), RECEIPT1, "blended")
        marker = _marker_blend_upgraded()
        marker.update({"publishedAt": PLACE_AT, "receiptSha256": RECEIPT2})
        marker["revision"] = {
            "kind": "place-ev-upgrade", "reason": "place-ev-upgrade",
            "revisedAt": PLACE_AT, "revisionCount": 2,
            "previousReceiptSha256": RECEIPT1,
            "previousAbilityLane": "v9b-cal-market",
            "abilityLane": "v9b-cal-market"}
        incoming = _detail(marker, RECEIPT2, "blended+place")
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["unifiedForecast"]["flavour"], "blended+place")
        self.assertEqual(
            out["preparedMeta"]["rewritePublish"]["revision"]["kind"],
            "place-ev-upgrade")

    def test_second_roster_reissue_chain_accepted(self):
        # The lane stamps a roster re-issue's firstPublishedAt from
        # the CURRENT marker's publishedAt; a second roster change
        # therefore points firstPublishedAt at the intermediate
        # publication. The chain must still be accepted.
        first = _marker_first()
        revised = dict(first, publishedAt=UPGRADE_AT,
                       receiptSha256=RECEIPT1, firstPublishedAt=FIRST_AT,
                       revision={"reason": "roster-change",
                                 "revisedAt": UPGRADE_AT, "revisionCount": 1,
                                 "previousReceiptSha256": RECEIPT0,
                                 "rosterAdded": [], "rosterRemoved": [],
                                 "rosterRenamed": []})
        old = _detail(revised, RECEIPT1, "reissued-1")
        marker2 = dict(revised, publishedAt=PLACE_AT,
                       receiptSha256=RECEIPT2, firstPublishedAt=UPGRADE_AT,
                       revision={"reason": "roster-change",
                                 "revisedAt": PLACE_AT, "revisionCount": 2,
                                 "previousReceiptSha256": RECEIPT1,
                                 "rosterAdded": [9], "rosterRemoved": [],
                                 "rosterRenamed": []})
        incoming = _detail(marker2, RECEIPT2, "reissued-2")
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["unifiedForecast"]["flavour"], "reissued-2")

    def test_broken_receipt_chain_rejected(self):
        old = _detail(_marker_first(), RECEIPT0, "calibration-only")
        marker = _marker_blend_upgraded()
        marker["revision"] = dict(marker["revision"],
                                   previousReceiptSha256="z" * 64)
        incoming = _detail(marker, RECEIPT1, "blended")
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["unifiedForecast"]["flavour"],
                         "calibration-only")
        self.assertEqual(out["preparedMeta"]["rewritePublish"],
                         _marker_first())

    def test_revisionless_write_never_succeeds_revised_marker(self):
        old = _detail(_marker_blend_upgraded(), RECEIPT1, "blended")
        marker = _marker_first()
        marker.update({"publishedAt": PLACE_AT, "receiptSha256": RECEIPT2,
                       "blendApplied": True,
                       "postProcessing": _post_processing(True)})
        incoming = _detail(marker, RECEIPT2, "forged-fresh")
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["unifiedForecast"]["flavour"], "blended")
        self.assertEqual(out["preparedMeta"]["rewritePublish"],
                         _marker_blend_upgraded())

    def test_first_publication_without_stored_marker_accepted(self):
        old = _detail(_marker_first(), RECEIPT0, "x")
        del old["preparedMeta"]["rewritePublish"]
        incoming = _detail(_marker_first(), RECEIPT0, "calibration-only")
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["unifiedForecast"]["flavour"],
                         "calibration-only")
        self.assertEqual(out["preparedMeta"]["rewritePublish"],
                         _marker_first())

    def test_cross_version_fresh_publish_accepted(self):
        legacy = _marker_first()
        legacy["modelVersion"] = "arvexq-rewrite-v2-legacy"
        old = _detail(legacy, RECEIPT0, "legacy")
        incoming = _detail(_marker_first(), RECEIPT0, "calibration-only")
        incoming["preparedMeta"]["rewritePublish"]["publishedAt"] = (
            "2026-11-04T01:00:00+09:00")
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["unifiedForecast"]["flavour"],
                         "calibration-only")

    def test_idempotent_resend_replaces(self):
        old = _detail(_marker_blend_upgraded(), RECEIPT1, "blended")
        incoming = _detail(_marker_blend_upgraded(), RECEIPT1, "blended")
        incoming["recommendedBets"] = [{"kind": "単勝", "flavour": "same"}]
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["recommendedBets"], incoming["recommendedBets"])
        self.assertEqual(out["preparedMeta"]["rewritePublish"],
                         _marker_blend_upgraded())
