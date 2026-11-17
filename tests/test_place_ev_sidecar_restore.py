"""Pristine masterAnalysis restore for the place-EV upgrade.

The place-EV upgrade is surgical like the ticket narrowings: it
applies on top of a deep copy of the stored detail, so the
masterAnalysis sidecar it carries is inherited from the lane's
API read — but the public projection does not preserve the
sidecar's signed bytes, so the read copy's contentSha256 no
longer re-hashes, and protect_detail strict-verifies any
marker-advancing publish write.

The pristine-sidecar restore (_restore_pristine_sidecar) was
wired only for the ticket kinds (ticket-r24-upgrade /
ticket-pool4-upgrade). A sidecar-carrying race that qualified
for the place-EV upgrade therefore died at the protect seam
with "masterAnalysis signature or capture mismatch" on EVERY
publish cycle: the write never landed, so the one-time
qualification (no placeExpectedValues in the stored plan)
never cleared and the race failed forever — Tokyo 6R/7R on
2026-11-15, whose two permanent failures also failed every
publish run's exit code. These tests pin the defect and the
fix: the restore gate covers every surgical revision kind,
and protect_detail is NOT weakened — with the pristine bytes
restored, its strict verification passes on the merits.
"""
import copy
import json
from hashlib import sha256
from unittest import TestCase
from unittest.mock import patch

import scripts.arvexq_rewrite_publish as pub
from scripts.arvexq_rewrite_publish import (
    _apply_place_ev_upgrade,
    _place_ev_upgrade_info,
    _restore_pristine_sidecar,
)
from tests.test_place_ev import NOW, stored_detail

CAPTURED_AT = "2026-11-03T21:05:00+09:00"


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


def _place_ev_new(old_raw):
    info = _place_ev_upgrade_info(old_raw, NOW)
    assert info is not None
    info["receipt"] = old_raw["unifiedForecast"]["receiptSha256"]
    new, _receipt = _apply_place_ev_upgrade(
        old_raw, info, NOW.isoformat(timespec="seconds"))
    assert new is not None
    return new


def _export_response(stored):
    return {"rows": [{"payload": json.dumps(stored,
                                             ensure_ascii=False)}]}


class PlaceEvSidecarRestoreTests(TestCase):
    def test_protect_rejects_projected_sidecar_without_restore(self):
        # The production defect, pinned: a place-EV re-issue
        # built from the projected read dies at the protect seam
        # with the exact error Tokyo 6R/7R hit every cycle.
        old_raw = _stored_with(mangled_sidecar())
        new = _place_ev_new(copy.deepcopy(old_raw))
        revision = new["preparedMeta"]["rewritePublish"]["revision"]
        self.assertEqual(revision["kind"], "place-ev-upgrade")
        protect_detail = pub._load_protect()
        with self.assertRaisesRegex(
                ValueError, "masterAnalysis signature or capture mismatch"):
            protect_detail(old_raw, new)

    def test_restore_gate_covers_the_place_ev_kind(self):
        # The publish loop (and the slim reissue process) restore
        # the pristine sidecar for the kinds in this set; the
        # place-EV kind the build produces must be one of them.
        new = _place_ev_new(_stored_with(mangled_sidecar()))
        revision = new["preparedMeta"]["rewritePublish"]["revision"]
        kind = revision.get("kind") or revision.get("reason")
        self.assertIn(kind, pub.SURGICAL_SIDECAR_RESTORE_KINDS)

    def test_restore_makes_protect_pass_with_pristine_bytes(self):
        stored = _stored_with(pristine_sidecar())
        old_raw = _stored_with(mangled_sidecar())
        new = _place_ev_new(copy.deepcopy(old_raw))
        with patch.object(pub, "_get_admin",
                          return_value=_export_response(stored)):
            ok, reason = _restore_pristine_sidecar(new, "token")
            self.assertTrue(ok, reason)
        self.assertEqual(new["masterAnalysis"], pristine_sidecar())
        protect_detail = pub._load_protect()
        final = protect_detail(old_raw, new)  # must not raise
        self.assertEqual(final["masterAnalysis"], pristine_sidecar())
        # The upgrade itself is untouched by the restore.
        plan = final["unifiedForecast"]["ticketPlan"]
        self.assertIn("placeExpectedValues", plan)

    def test_missing_token_fails_closed(self):
        new = _place_ev_new(_stored_with(mangled_sidecar()))
        ok, reason = _restore_pristine_sidecar(new, None)
        self.assertFalse(ok)
        self.assertEqual(reason, "no-token")
