"""The masterAnalysis seal must bind values, not serializer spellings.

Root cause of the Saga 3R/4R publish failures (2026-11-21): the
publish lane seals the masterAnalysis sidecar with a sha256 over
Python's json.dumps spelling, but the detail reaches D1 through
the sync worker, which stores JSON.stringify(parsed body)
(workers/api_preserved.mjs). JS re-serialization collapses
integral floats to ints (score100 68.0 -> 68, a category's earned
14.0 -> 14), so the stored sidecar's contentSha256 never
re-hashed and _restore_pristine_sidecar failed every surgical
re-issue with "stored-digest-mismatch" — the pending one-time
place-EV upgrade never landed and the two stuck races failed
every publish run's exit code. The content was value-for-value
the sealed content throughout; the forecasts themselves were
published and live.

The fix mirrors the unified receipt's canonicalization
(2026-10-31): new sidecars are sealed value-canonically
(master_sidecar_digest) and every verifier (the pristine
restore, protect_detail, the master scoreboard) accepts the
value-canonical form, the legacy form of a never-reserialized
payload, and the legacy form reconstructed from a JS round trip
by restoring the float spelling at the leaves the sidecar's
single builder always emits as floats. These tests pin all
three forms — and that a changed VALUE still fails everywhere.
"""
import copy
import json
from hashlib import sha256
from unittest import TestCase
from unittest.mock import patch

import scripts.arvexq_rewrite_publish as pub
from arvexq.prediction.unified_product import (
    master_sidecar_digest,
    master_sidecar_verified,
)
from scripts.arvexq_rewrite_publish import (
    _apply_place_ev_upgrade,
    _place_ev_upgrade_info,
    _restore_pristine_sidecar,
)
from tests.test_place_ev import NOW, stored_detail

CAPTURED_AT = "2026-11-03T21:05:00+09:00"


def js_round_trip(value):
    """The sync worker's JSON.parse -> JSON.stringify spelling
    change, for the value shapes a sidecar carries: an integral
    float loses its fraction (68.0 -> 68); every other value is
    spelled identically."""
    if isinstance(value, float):
        return int(value) if value.is_integer() else value
    if isinstance(value, dict):
        return {k: js_round_trip(v) for k, v in value.items()}
    if isinstance(value, list):
        return [js_round_trip(v) for v in value]
    return value


def legacy_sign(sidecar):
    sidecar["contentSha256"] = sha256(json.dumps(
        {k: v for k, v in sidecar.items() if k != "contentSha256"},
        sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()
    return sidecar


def realistic_sidecar():
    """A sidecar in the publish lane's build shape, carrying the
    integral floats production sidecars routinely contain: a
    score100 landing on a whole number, category earned points at
    their caps, and a modelHitProbability of exactly 1."""
    return {
        "version": "master-18-factor-shadow-v1",
        "status": "shadow-candidate",
        "probabilityStatus": "master-experimental-uncalibrated",
        "validated": False,
        "evidenceConfidence": "B",
        "marketStatus": "complete",
        "pace": {"label": "スローペース想定", "frontRunners": [2],
                 "unknown": [],
                 "scenarioOrder": {"slow": [2, 3], "normal": [2, 3],
                                   "fast": [3, 2]},
                 "scenarioProbabilities": None},
        "runners": [
            {"horseNumber": 2, "score100": 68.0, "coveragePoints": 80,
             "evidenceRuns": 5,
             "categories": {"ability": 15.93, "recent": 11.25,
                            "course_distance": 14.0,
                            "pace_robustness": 15.0,
                            "track_condition": None,
                            "weight_rotation": 3.0},
             "missingCategories": ["training_condition",
                                   "jockey_trainer", "gate"],
             "mark": "◎", "pWin": 0.1968, "pTop3": 0.5993,
             "marketRank": 2, "popularRisk": "not-assessed",
             "valueHypothesis": False},
            {"horseNumber": 3, "score100": 55.46, "coveragePoints": 82,
             "evidenceRuns": 4,
             "categories": {"ability": 17.03, "recent": 6.11,
                            "course_distance": 0.0,
                            "pace_robustness": 12.86,
                            "track_condition": 6.48,
                            "weight_rotation": 3.0},
             "missingCategories": ["training_condition",
                                   "jockey_trainer", "gate"],
             "mark": "○", "pWin": 0.2491, "pTop3": 0.9249,
             "marketRank": 1, "popularRisk": "A-candidate",
             "valueHypothesis": True},
        ],
        "ticketStyles": {
            "status": "conditional-research-only",
            "styles": {
                "hit_first": {"kind": "place", "selection": [2],
                              "modelHitProbability": 1.0,
                              "probabilityStatus":
                                  "experimental-uncalibrated",
                              "expectedReturn": None,
                              "minimumActualOdds": None,
                              "purchaseRecommended": False},
                "balanced": None, "outsider": None},
            "calibrationValidated": False, "stakeAllocationYen": None},
        "capturedAt": CAPTURED_AT,
    }


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


class SidecarSealFormsTests(TestCase):
    def test_legacy_seal_verifies_before_and_after_js_round_trip(self):
        sidecar = legacy_sign(realistic_sidecar())
        self.assertTrue(master_sidecar_verified(sidecar))
        self.assertTrue(master_sidecar_verified(js_round_trip(sidecar)))

    def test_new_seal_verifies_before_and_after_js_round_trip(self):
        sidecar = realistic_sidecar()
        sidecar["contentSha256"] = master_sidecar_digest(sidecar)
        self.assertTrue(master_sidecar_verified(sidecar))
        self.assertTrue(master_sidecar_verified(js_round_trip(sidecar)))

    def test_changed_value_fails_under_every_form(self):
        for sign in (legacy_sign,):
            sidecar = sign(realistic_sidecar())
            for mutate in (
                    lambda s: s["runners"][0].update(score100=69),
                    lambda s: s["runners"][0].update(score100=68.5),
                    lambda s: s["runners"][0]["categories"].update(
                        course_distance=13.0),
                    lambda s: s["runners"][1].update(pWin=0.25),
                    lambda s: s["ticketStyles"]["styles"]["hit_first"]
                        .update(modelHitProbability=0.99),
                    lambda s: s.update(evidenceConfidence="A")):
                tripped = js_round_trip(copy.deepcopy(sidecar))
                mutate(tripped)
                self.assertFalse(master_sidecar_verified(tripped))
        sidecar = realistic_sidecar()
        sidecar["contentSha256"] = master_sidecar_digest(sidecar)
        tripped = js_round_trip(sidecar)
        tripped["runners"][0]["score100"] = 69
        self.assertFalse(master_sidecar_verified(tripped))

    def test_missing_or_bogus_seal_fails_closed(self):
        sidecar = realistic_sidecar()
        self.assertFalse(master_sidecar_verified(sidecar))
        sidecar["contentSha256"] = "0" * 64
        self.assertFalse(master_sidecar_verified(sidecar))
        self.assertFalse(master_sidecar_verified(None))
        self.assertFalse(master_sidecar_verified("sidecar"))


def projection_strip(value):
    """The display projection's recursive retired-key deletion
    (arvexq.forecast.publication.public_race / the worker's
    public-race projection), for the one retired name a sidecar
    carries: every "mark" key, at every nesting level."""
    if isinstance(value, dict):
        return {k: projection_strip(v) for k, v in value.items()
                if k != "mark"}
    if isinstance(value, list):
        return [projection_strip(v) for v in value]
    return value


def marked_sidecar():
    """A sidecar in the publish lane's build shape whose runner
    marks are exactly what the builder's _assign_marks produces
    for its probabilities (the sealed marks are a deterministic
    function of pWin / pTop3 / horseNumber)."""
    from rewrite.analysis.forecast import _assign_marks
    probs = {2: (0.30, 0.55, 0.75), 3: (0.20, 0.40, 0.60),
             4: (0.15, 0.35, 0.55), 5: (0.10, 0.25, 0.45),
             6: (0.08, 0.20, 0.50), 7: (0.05, 0.15, 0.30)}
    ranking = sorted(probs, key=lambda n: (-probs[n][0],
                                           -probs[n][2], n))
    marks = _assign_marks(ranking, probs)
    runners = []
    for n in (2, 3, 4, 5, 6, 7):
        runners.append({
            "horseNumber": n,
            "score100": 68.0 if n == 2 else 40.0 + n,
            "coveragePoints": 80, "evidenceRuns": 5,
            "categories": {"ability": 14.0, "recent": 11.25},
            "missingCategories": ["gate"],
            "mark": marks.get(n, ""),
            "pWin": probs[n][0], "pTop3": probs[n][2],
            "marketRank": n - 1, "popularRisk": "not-assessed",
            "valueHypothesis": False})
    return {
        "version": "master-18-factor-shadow-v1",
        "status": "shadow-candidate",
        "probabilityStatus": "master-experimental-uncalibrated",
        "validated": False, "evidenceConfidence": "B",
        "marketStatus": "complete",
        "pace": {"label": "スローペース想定", "frontRunners": [2],
                 "unknown": [],
                 "scenarioOrder": {"slow": [2, 3], "normal": [2, 3],
                                   "fast": [3, 2]},
                 "scenarioProbabilities": None},
        "runners": runners,
        "ticketStyles": {
            "status": "conditional-research-only",
            "styles": {"hit_first": {
                "kind": "place", "selection": [2],
                "modelHitProbability": 1.0,
                "probabilityStatus": "experimental-uncalibrated",
                "expectedReturn": None, "minimumActualOdds": None,
                "purchaseRecommended": False},
                "balanced": None, "outsider": None},
            "calibrationValidated": False, "stakeAllocationYen": None},
        "capturedAt": CAPTURED_AT,
    }


class ProjectionStrippedSidecarTests(TestCase):
    """Stored sidecars are also missing a whole key the seal binds:
    the display projection recursively deletes the key name "mark",
    and stored production sidecars reach D1 without any runner's
    mark while the seal was computed over the builder's tree that
    carries it (Saga 4R/5R/6R/7R/10R still failing after the float
    fix; every stored sidecar of 2026-11-19/20/21 checked). The
    verifier restores the one mark assignment the sidecar's own
    sealed probabilities deterministically imply — a changed value
    still fails, exactly as for the float spellings."""

    def test_projection_stripped_legacy_sidecar_verifies(self):
        sidecar = legacy_sign(marked_sidecar())
        stored = projection_strip(js_round_trip(sidecar))
        self.assertNotIn("mark", stored["runners"][0])
        self.assertTrue(master_sidecar_verified(stored))

    def test_projection_stripped_new_seal_verifies(self):
        sidecar = marked_sidecar()
        sidecar["contentSha256"] = master_sidecar_digest(sidecar)
        stored = projection_strip(js_round_trip(sidecar))
        self.assertTrue(master_sidecar_verified(stored))

    def test_projection_stripped_tampering_still_fails(self):
        sidecar = legacy_sign(marked_sidecar())
        for mutate in (
                # A probability change re-derives different marks
                # and a different tree: no accepted form matches.
                lambda s: s["runners"][0].update(pWin=0.31),
                # Moving the star: horse 7's top-3 now beats horse
                # 6's, so the implied ☆ changes with the value.
                lambda s: s["runners"][5].update(pTop3=0.51),
                lambda s: s["runners"][1].update(score100=41.5),
                lambda s: s["runners"].pop(),
                # A mark that is present but wrong gets no restored
                # variant and does not match the seal either.
                lambda s: s["runners"][0].update(mark="○")):
            stored = projection_strip(js_round_trip(
                copy.deepcopy(sidecar)))
            mutate(stored)
            self.assertFalse(master_sidecar_verified(stored))

    def test_insufficient_style_sidecar_stripped_verifies(self):
        sidecar = marked_sidecar()
        for r in sidecar["runners"]:
            r["mark"] = None
            r["pWin"] = None
            r["pTop3"] = None
        sidecar = legacy_sign(sidecar)
        stored = projection_strip(js_round_trip(sidecar))
        self.assertTrue(master_sidecar_verified(stored))

    def test_projection_stripped_sidecar_restores_and_protects(self):
        stored = _stored_with(projection_strip(js_round_trip(
            legacy_sign(marked_sidecar()))))
        old_raw = _stored_with(projection_strip(js_round_trip(
            legacy_sign(marked_sidecar()))))
        new = _place_ev_new(copy.deepcopy(old_raw))
        with patch.object(pub, "_get_admin",
                          return_value=_export_response(stored)):
            ok, reason = _restore_pristine_sidecar(new, "token")
        self.assertTrue(ok, reason)
        self.assertEqual(new["masterAnalysis"],
                         stored["masterAnalysis"])
        protect_detail = pub._load_protect()
        final = protect_detail(old_raw, new)  # must not raise
        plan = final["unifiedForecast"]["ticketPlan"]
        self.assertIn("placeExpectedValues", plan)


class StoredDigestRestoreTests(TestCase):
    def test_js_spelled_stored_sidecar_restores_and_protect_passes(self):
        # The production state for Saga 3R/4R: sealed in Python,
        # stored JS-spelled. The restore must adopt the stored
        # sidecar and protect_detail must accept the write.
        stored = _stored_with(js_round_trip(legacy_sign(
            realistic_sidecar())))
        old_raw = _stored_with(js_round_trip(legacy_sign(
            realistic_sidecar())))
        new = _place_ev_new(copy.deepcopy(old_raw))
        with patch.object(pub, "_get_admin",
                          return_value=_export_response(stored)):
            ok, reason = _restore_pristine_sidecar(new, "token")
        self.assertTrue(ok, reason)
        self.assertEqual(new["masterAnalysis"],
                         stored["masterAnalysis"])
        protect_detail = pub._load_protect()
        final = protect_detail(old_raw, new)  # must not raise
        plan = final["unifiedForecast"]["ticketPlan"]
        self.assertIn("placeExpectedValues", plan)

    def test_js_spelled_stored_sidecar_with_changed_value_fails(self):
        stored_sidecar = js_round_trip(legacy_sign(realistic_sidecar()))
        stored_sidecar["runners"][0]["score100"] = 69
        stored = _stored_with(stored_sidecar)
        old_raw = _stored_with(js_round_trip(legacy_sign(
            realistic_sidecar())))
        new = _place_ev_new(copy.deepcopy(old_raw))
        with patch.object(pub, "_get_admin",
                          return_value=_export_response(stored)):
            ok, reason = _restore_pristine_sidecar(new, "token")
        self.assertFalse(ok)
        self.assertEqual(reason, "stored-digest-mismatch")

    def test_new_seal_stored_sidecar_restores_after_js_round_trip(self):
        sidecar = realistic_sidecar()
        sidecar["contentSha256"] = master_sidecar_digest(sidecar)
        stored = _stored_with(js_round_trip(sidecar))
        old_raw = _stored_with(js_round_trip(copy.deepcopy(sidecar)))
        new = _place_ev_new(copy.deepcopy(old_raw))
        with patch.object(pub, "_get_admin",
                          return_value=_export_response(stored)):
            ok, reason = _restore_pristine_sidecar(new, "token")
        self.assertTrue(ok, reason)
        protect_detail = pub._load_protect()
        protect_detail(old_raw, new)  # must not raise
