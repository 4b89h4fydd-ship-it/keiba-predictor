"""Pristine masterAnalysis restore for surgical ticket re-issues.

A surgical ticket re-issue (ticket-r24-upgrade / ticket-pool4-
upgrade) inherits the stored publication's masterAnalysis
sidecar from the lane's API read — but the public projection
does not preserve the sidecar's signed bytes, so the read
copy's contentSha256 no longer re-hashes, and protect_detail
strict-verifies any marker-advancing publish write: every
surgical re-issue of a sidecar-carrying publication was
rejected with "masterAnalysis signature or capture mismatch"
(first hit in production by the slim reissue run 43188158434,
2026-11-12, after PR #528).

_restore_pristine_sidecar fetches the D1 row verbatim through
the authenticated snapshot export and adopts its sidecar only
when the identity chains to the write (version + capturedAt,
stored receipt == the revision's previousReceiptSha256, and
the stored digest itself verifies). protect_detail is NOT
weakened: with the pristine bytes restored, its strict
verification passes on the merits.
"""
import copy
import json
from hashlib import sha256
from unittest import TestCase
from unittest.mock import patch

import scripts.arvexq_rewrite_publish as pub
from scripts.arvexq_rewrite_publish import (
    _apply_ticket_pool4_upgrade,
    _restore_pristine_sidecar,
    _ticket_pool4_upgrade_info,
)
from tests.test_ticket_pool4_upgrade_publish import NOW, stored_detail

CAPTURED_AT = "2026-11-12T09:38:29+09:00"


def pristine_sidecar():
    sidecar = {"version": "master-18-factor-shadow-v1",
               "status": "ok",
               "capturedAt": CAPTURED_AT,
               "runners": [{"horseNumber": 2, "score100": 55.5}],
               "ticketStyles": []}
    sidecar["contentSha256"] = sha256(json.dumps(
        sidecar, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()
    return sidecar


def mangled_sidecar():
    sidecar = pristine_sidecar()
    # The projection's doing: content changed under the same
    # stored digest, which no longer re-hashes.
    sidecar["runners"] = [{"horseNumber": 2, "score100": 55.6}]
    return sidecar


def _stored_with(sidecar):
    detail = stored_detail()
    detail["masterAnalysis"] = sidecar
    detail["prediction"]["capturedAt"] = CAPTURED_AT
    return detail


def _surgical_new(old_raw):
    info = _ticket_pool4_upgrade_info(old_raw, NOW)
    assert info is not None
    info["receipt"] = old_raw["unifiedForecast"]["receiptSha256"]
    new, _receipt = _apply_ticket_pool4_upgrade(
        old_raw, info, NOW.isoformat(timespec="seconds"))
    assert new is not None
    return new


def _export_response(stored):
    return {"rows": [{"payload": json.dumps(stored,
                                             ensure_ascii=False)}]}


class RestorePristineSidecarTests(TestCase):
    def test_protect_rejects_projected_sidecar_without_restore(self):
        # The production defect, pinned: a surgical re-issue
        # built from the projected read dies at the protect seam.
        old_raw = _stored_with(mangled_sidecar())
        new = _surgical_new(copy.deepcopy(old_raw))
        protect_detail = pub._load_protect()
        with self.assertRaises(ValueError):
            protect_detail(old_raw, new)

    def test_restore_makes_protect_pass_with_pristine_bytes(self):
        stored = _stored_with(pristine_sidecar())
        old_raw = _stored_with(mangled_sidecar())
        new = _surgical_new(copy.deepcopy(old_raw))
        with patch.object(pub, "_get_admin",
                          return_value=_export_response(stored)):
            ok, reason = _restore_pristine_sidecar(new, "token")
            self.assertTrue(ok, reason)
        self.assertEqual(new["masterAnalysis"], pristine_sidecar())
        protect_detail = pub._load_protect()
        final = protect_detail(old_raw, new)  # must not raise
        self.assertEqual(final["masterAnalysis"], pristine_sidecar())
        # The surgical narrowing itself is untouched by the restore.
        trifecta = next(b for b in final["recommendedBets"]
                        if b["kind"] == "3連単")
        self.assertEqual(trifecta["points"], 12)

    def test_no_sidecar_is_trivially_fine(self):
        ok, _reason = _restore_pristine_sidecar(
            {"id": "nar-2026-11-12-川崎-11"}, None)
        self.assertTrue(ok)

    def test_missing_token_fails_closed(self):
        new = _surgical_new(_stored_with(mangled_sidecar()))
        ok, reason = _restore_pristine_sidecar(new, None)
        self.assertFalse(ok)
        self.assertEqual(reason, "no-token")

    def test_stored_digest_must_verify(self):
        stored = _stored_with(mangled_sidecar())
        new = _surgical_new(_stored_with(mangled_sidecar()))
        with patch.object(pub, "_get_admin",
                          return_value=_export_response(stored)):
            ok, reason = _restore_pristine_sidecar(new, "token")
        self.assertFalse(ok)
        self.assertEqual(reason, "stored-digest-mismatch")

    def test_captured_at_mismatch_fails_closed(self):
        stored = _stored_with(pristine_sidecar())
        stored["masterAnalysis"] = pristine_sidecar()
        stored["masterAnalysis"]["capturedAt"] = "2026-11-12T08:00:00+09:00"
        stored["masterAnalysis"]["contentSha256"] = sha256(json.dumps(
            {k: v for k, v in stored["masterAnalysis"].items()
             if k != "contentSha256"},
            sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode("utf-8")).hexdigest()
        new = _surgical_new(_stored_with(mangled_sidecar()))
        with patch.object(pub, "_get_admin",
                          return_value=_export_response(stored)):
            ok, reason = _restore_pristine_sidecar(new, "token")
        self.assertFalse(ok)
        self.assertEqual(reason, "captured-at-mismatch")

    def test_receipt_chain_mismatch_fails_closed(self):
        stored = _stored_with(pristine_sidecar())
        stored["preparedMeta"]["rewritePublish"]["receiptSha256"] = "f" * 64
        new = _surgical_new(_stored_with(mangled_sidecar()))
        with patch.object(pub, "_get_admin",
                          return_value=_export_response(stored)):
            ok, reason = _restore_pristine_sidecar(new, "token")
        self.assertFalse(ok)
        self.assertEqual(reason, "receipt-chain-mismatch")

    def test_export_failure_fails_closed(self):
        new = _surgical_new(_stored_with(mangled_sidecar()))
        with patch.object(pub, "_get_admin",
                          side_effect=RuntimeError("boom")):
            ok, reason = _restore_pristine_sidecar(new, "token")
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("export-fetch"), reason)
