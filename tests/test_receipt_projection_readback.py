"""Read-back verification through the production API projection.

Publish run #294 (2026-11-12) failed all 48 fresh publications with
"read-back content does not verify (receipt-content-mismatch)" while
the pre-post protected check passed and the writes themselves landed.
Root cause, reproduced from the stored rows: the live API worker wraps
every GET response in a display projection (public-race.js, applied
by the entry's withCors) that recursively deletes a fixed set of
retired key names at every nesting level — including the literal key
"tickets" inside the sealed product's analysisStages block
(rewrite/output/api_shape.py always emits it). The D1 payload and the
sealed product are intact; the read-back copy the publish gate
re-hashes simply lacks that one EV-status block, so the digest could
never match. Re-issues never hit it (the freeze decision is marker /
receipt-string based), which is why only first publications failed —
the same shape as the 2026-11-11 audit's "first publications fail,
re-seals verify" observation.

verified() now also accepts the serving form: the product with
analysisStages.tickets restored to any of its three legitimate
status values (the closed set api_shape can stamp). Every other leaf
stays digest-bound, so post-seal drift is still detected. These tests
pin both halves: the projected read-back verifies, and tampering —
including inside ticketPlan or another stage block — still fails.
"""
from __future__ import annotations

import copy
import json
from unittest import TestCase

from arvexq.prediction.unified_product import (
    canonical_receipt, verified as verified_unified)
from scripts.arvexq_protect_sync import protect_detail
from tests.test_publish_mass_feature_archive import build, fresh_detail

# The retired key set of the live worker's display projection
# (workers/live-bundle public-race.js RETIRED_KEYS), verbatim.
RETIRED_KEYS = {
    "aiEvaluation", "integratedEvaluation", "factorRanking",
    "honmeiDecision", "preRacePrediction", "preRaceBet",
    "predictionAudit", "frozenPredictionAudit", "winnerLearningProfile",
    "betRecommendations", "recommendedBets", "tickets", "buyList",
    "bets", "markMethod", "markEngineVersion", "predictionModelVersion",
    "mark", "predMark", "印", "honmeiRole", "modelProbabilities",
    "forecastRevisions", "currentForecastRevisionId",
    "preoffStage64Archive", "morningMarkSnapshot",
    "officialMarkRevisions", "modelMarkRevisions",
    "savedForecastRevision", "_savedPreoffOriginal",
    "legacyPredictionAudit", "preRaceAudit", "observedModelCoverage",
}

TICKET_STAGE_STATUSES = (
    "probability-only-ev-suppressed",
    "win-ev-uncalibrated-estimate",
    "win-ev-calibrated-estimate",
)


def project(value):
    """The projection's key deletion, modelled for verified()'s inputs.

    publicRace additionally rebuilds the top-level marks blocks around
    the authorized five marks, but verified() reads only the race's
    identity fields, its horses (number / name / scratch status — none
    of them retired keys) and unifiedForecast, so recursive retired-key
    deletion is the faithful transform for this check.
    """
    if isinstance(value, dict):
        return {k: project(v) for k, v in value.items()
                if k not in RETIRED_KEYS}
    if isinstance(value, list):
        return [project(v) for v in value]
    return value


def js_round_trip(value):
    """The worker's JSON.parse -> JSON.stringify cycle, modelled:
    integral floats come back as ints, everything else is unchanged."""
    def jsify(v):
        if isinstance(v, float) and v == v and abs(v) < 2 ** 53 \
                and v.is_integer():
            return int(v)
        if isinstance(v, dict):
            return {k: jsify(x) for k, x in v.items()}
        if isinstance(v, list):
            return [jsify(x) for x in v]
        return v
    return jsify(json.loads(json.dumps(value, ensure_ascii=False)))


def read_back_form(detail):
    """What publish_date's read-back verification actually receives:
    the stored detail after the worker's JSON cycle and the API
    display projection."""
    return project(js_round_trip(detail))


class ProjectionReadBackTests(TestCase):
    def published(self):
        detail = fresh_detail()
        new, receipt = build(detail)
        self.assertIsNotNone(new, receipt)
        # The #294 publications carried the mass-feature archive; the
        # failure had nothing to do with it, and the fixed read-back
        # must pass with it attached.
        self.assertIsInstance(new.get("massFeatureArchive"), dict)
        return detail, protect_detail(detail, new), receipt

    def test_unprojected_forms_still_verify(self):
        _, final, _ = self.published()
        self.assertIsNotNone(verified_unified(final))
        self.assertIsNotNone(verified_unified(js_round_trip(final)))

    def test_projected_read_back_verifies(self):
        _, final, receipt = self.published()
        back = read_back_form(final)
        # The projection really did strip the sealed block, and the
        # receipt string survived untouched — the exact #294 shape.
        self.assertNotIn("tickets",
                         back["unifiedForecast"]["analysisStages"])
        self.assertEqual(back["unifiedForecast"]["receiptSha256"], receipt)
        self.assertIsNotNone(verified_unified(back))

    def test_every_ticket_stage_status_verifies(self):
        _, final, _ = self.published()
        product = copy.deepcopy(final["unifiedForecast"])
        for status in TICKET_STAGE_STATUSES:
            product["analysisStages"]["tickets"] = {"status": status}
            product["receiptSha256"] = canonical_receipt(product)
            race = dict(final, unifiedForecast=product)
            self.assertIsNotNone(verified_unified(read_back_form(race)),
                                 status)

    def test_projection_does_not_mask_tampering(self):
        _, final, _ = self.published()

        def tampered(mutate):
            back = read_back_form(final)
            mutate(back["unifiedForecast"])
            return verified_unified(back)

        self.assertIsNone(tampered(
            lambda u: u["marks"][0].update(
                winProbability=u["marks"][0]["winProbability"] + 0.01)))
        self.assertIsNone(tampered(lambda u: u["marks"].reverse()))
        self.assertIsNone(tampered(
            lambda u: u["analysisStages"]["ability"].update(
                status="forged")))
        self.assertIsNone(tampered(
            lambda u: u["ticketPlan"].update(status="forged")))
        self.assertIsNone(tampered(
            lambda u: u["roster"][0].update(name="別人")))

    def test_stripped_block_stays_bound_in_sealed_form(self):
        # In the unprojected (sealed) form the tickets block is part of
        # the digest like everything else: rewriting its status without
        # re-sealing must still fail.
        _, final, _ = self.published()
        forged = copy.deepcopy(final)
        forged["unifiedForecast"]["analysisStages"]["tickets"] = {
            "status": "win-ev-calibrated-estimate"}
        if verified_unified(final) is not None and \
                final["unifiedForecast"]["analysisStages"]["tickets"] != \
                forged["unifiedForecast"]["analysisStages"]["tickets"]:
            self.assertIsNone(verified_unified(forged))


if __name__ == "__main__":
    import unittest
    unittest.main()
