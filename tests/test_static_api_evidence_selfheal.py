"""Static API pack builder: research evidence self-heal guard.

Regression for the recurring unevaluated-horses incidents
(2026-11-22..26).  Carry-over (test_static_api_evidence_carryover)
can only restore evidence a race's pack carried before; on
2026-11-26, 47 of 48 races had never carried evidence in any
committed pack version, because the prefetch analyze stage — the
only place attach_evidence ran — only publishes its decorated
detail for races whose diagnosis succeeded, and discards the
decoration otherwise.  The build is the one point every lane's
packs pass through, so it must run the decoration procedure itself
as a final stage on any detail whose horses still lack evidence,
and must report every horse that remains evidence-empty to
evidence-residual/<date>.json instead of publishing silently.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from arvexq.prediction.race_intelligence import RESEARCH_EVIDENCE_VERSION
from scripts import arvexq_static_api_build as b

DATE = "2026-11-26"
RID1 = f"nar-{DATE}-浦和-01"
RID2 = f"nar-{DATE}-浦和-02"

TRIAL = {"trial_date": "2026-11-13", "trial_track": "浦和",
         "trial_distance": 800, "trial_time_seconds": 50.4,
         "trial_source": "nankan official", "trial_source_ref": "sheet"}


def summary(rid):
    return {"id": rid, "date": DATE, "circuit": "地方", "track": "浦和",
            "raceNumber": 1, "startTime": "11:00", "title": "1R",
            "surface": "ダート", "distance": 1400, "weather": "晴",
            "condition": "良", "volatility": {"label": "", "score": None},
            "raceStatus": "", "updatedAtEpoch": 0}


def sync_payload(details):
    return {"summaries": [summary(d["id"]) for d in details],
            "details": details, "odds_current": []}


def debutant(number, name):
    return {"horseNumber": number, "name": name, "recentRaces": [],
            "integratedEvaluation": {}}


def trial_detail(rid):
    """A detail no lane decorated, whose debutants hold official
    ability-trial passes stamped by the extras supplement."""
    detail = {"id": rid, "date": DATE, "track": "浦和", "circuit": "地方",
              "raceNumber": 1, "distance": 1400, "condition": "良",
              "horses": [debutant(1, "甲"), debutant(2, "乙")],
              "trialEvidenceRecords": [dict(TRIAL, number=1),
                                       dict(TRIAL, number=2)],
              "preparedMeta": {"diagnosisReady": False}}
    return detail


def sentinel_evidence(value=0.99):
    return {"factors": {"version": "sentinel",
                        "items": [{"key": "mineta", "weight": .60,
                                   "value": value, "available": True}],
                        "calibrated": False},
            "sectionals": {}, "status": "sentinel"}


def empty_block():
    """A block that exists but has no available item — the shape the
    2026-11-26 Urawa 3R residual horse actually carried (mineta and
    margin both unavailable), which a missing-block heal never sees."""
    return {"factors": {"version": "arvexq-empirical-fusion-v1",
                        "items": [{"key": "mineta", "weight": .60,
                                   "value": None, "available": False},
                                  {"key": "margin", "weight": .40,
                                   "value": None, "available": False}],
                        "calibrated": False},
            "sectionals": {}, "status": "nar-observed-only"}


def available_items(horse):
    items = (horse.get("researchEvidence") or {}).get("factors", {}).get("items") or []
    return [it for it in items if it.get("available")]


class EvidenceSelfHealTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name) / "packs"

    def tearDown(self):
        self._tmp.cleanup()

    def _residual_body(self):
        path = self.out / "evidence-residual" / f"{DATE}.json"
        self.assertTrue(path.is_file(), "residual report must be written")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_heal_attaches_missing_evidence(self):
        model = b.model_from_sync_payload(sync_payload([trial_detail(RID1)]))
        report = b.heal_missing_research_evidence(model, self.out)
        self.assertEqual(report["healStatus"], "ok")
        self.assertEqual(report["healedRaces"], [RID1])
        detail = model.details[RID1]
        self.assertEqual(detail["researchEvidenceVersion"],
                         RESEARCH_EVIDENCE_VERSION)
        self.assertEqual(detail["researchEvidenceHorses"], 2)
        for h in detail["horses"]:
            self.assertIn("researchEvidence", h)
            keys = [it["key"] for it in available_items(h)]
            self.assertEqual(keys, ["trial"])
        self.assertEqual(report["residualCount"], 0)
        body = self._residual_body()
        self.assertEqual(body["residualCount"], 0)
        self.assertEqual(body["residual"], [])

    def test_existing_evidence_is_never_rewritten(self):
        detail = trial_detail(RID1)
        detail["horses"][0]["researchEvidence"] = sentinel_evidence()
        detail["researchEvidenceVersion"] = "sentinel-version"
        detail["biasProvenance"] = {"version": "sentinel-prov"}
        model = b.model_from_sync_payload(sync_payload([detail]))
        b.heal_missing_research_evidence(model, self.out)
        healed = model.details[RID1]
        self.assertEqual(healed["horses"][0]["researchEvidence"],
                         sentinel_evidence())
        self.assertEqual(healed["researchEvidenceVersion"], "sentinel-version")
        self.assertEqual(healed["biasProvenance"], {"version": "sentinel-prov"})
        # The horse that lacked a block gained one.
        self.assertIn("researchEvidence", healed["horses"][1])
        self.assertEqual([it["key"] for it in available_items(healed["horses"][1])],
                         ["trial"])

    def test_forecast_and_result_blocks_untouched(self):
        detail = trial_detail(RID1)
        detail["unifiedForecast"] = {"marks": {"1": "◎"}, "winProb": {"1": 0.4}}
        detail["prediction"] = {"version": "v9b", "scores": {"1": 12.3}}
        detail["predictionMarks"] = {"1": "◎"}
        detail["recommendedBets"] = {"items": [{"kind": "単勝", "number": 1}]}
        detail["result"] = {"status": "確定", "order": [1, 2]}
        keys = ("unifiedForecast", "prediction", "predictionMarks",
                "recommendedBets", "result")
        before = {k: b._canonical(detail[k]) for k in keys}
        model = b.model_from_sync_payload(sync_payload([detail]))
        b.heal_missing_research_evidence(model, self.out)
        healed = model.details[RID1]
        for k in keys:
            self.assertEqual(b._canonical(healed[k]), before[k], k)
        self.assertIn("researchEvidence", healed["horses"][0])

    def test_residual_report_lists_zero_available_horse(self):
        detail = {"id": RID2, "date": DATE, "track": "浦和", "circuit": "地方",
                  "raceNumber": 2, "distance": 1400, "condition": "良",
                  "horses": [debutant(5, "無材料")],
                  "preparedMeta": {"diagnosisReady": False}}
        model = b.model_from_sync_payload(sync_payload([detail]))
        report = b.heal_missing_research_evidence(model, self.out)
        self.assertEqual(report["healStatus"], "ok")
        # The block is attached, but with no past runs and no trial
        # record nothing in it is available: the horse must surface
        # in the residual report, by name, instead of passing silently.
        self.assertIn("researchEvidence", model.details[RID2]["horses"][0])
        self.assertEqual(report["residualCount"], 1)
        entry = report["residual"][0]
        self.assertEqual(entry["raceId"], RID2)
        self.assertEqual(entry["horseNumber"], 5)
        self.assertEqual(entry["name"], "無材料")
        self.assertEqual(entry["reason"], "no-past-runs-or-trial-record")
        body = self._residual_body()
        self.assertEqual(body["residual"], report["residual"])
        self.assertEqual(body["version"], b.EVIDENCE_RESIDUAL_VERSION)

    def test_residual_report_written_explicitly_on_clean_day(self):
        detail = trial_detail(RID1)
        for h in detail["horses"]:
            h["researchEvidence"] = sentinel_evidence(0.5)
        detail["researchEvidenceVersion"] = RESEARCH_EVIDENCE_VERSION
        detail["researchEvidenceHorses"] = 2
        model = b.model_from_sync_payload(sync_payload([detail]))
        report = b.heal_missing_research_evidence(model, self.out)
        self.assertEqual(report["healStatus"], "not-needed")
        self.assertEqual(report["healedRaces"], [])
        body = self._residual_body()
        self.assertEqual(body["residualCount"], 0)
        self.assertEqual(body["residual"], [])
        self.assertEqual(body["healStatus"], "not-needed")

    def test_heal_is_idempotent(self):
        model = b.model_from_sync_payload(sync_payload([trial_detail(RID1)]))
        b.heal_missing_research_evidence(model, self.out)
        once = b._canonical(model.details[RID1])
        report2 = b.heal_missing_research_evidence(model, self.out)
        twice = b._canonical(model.details[RID1])
        self.assertEqual(once, twice)
        self.assertEqual(report2["healStatus"], "not-needed")
        self.assertEqual(report2["residualCount"], 0)

    def test_heal_replaces_empty_block_when_recompute_yields_items(self):
        detail = trial_detail(RID1)
        detail["horses"][0]["researchEvidence"] = empty_block()
        model = b.model_from_sync_payload(sync_payload([detail]))
        report = b.heal_missing_research_evidence(model, self.out)
        self.assertEqual(report["healStatus"], "ok")
        self.assertEqual(report["healedRaces"], [RID1])
        healed = model.details[RID1]["horses"][0]
        self.assertNotEqual(healed["researchEvidence"], empty_block())
        self.assertEqual([it["key"] for it in available_items(healed)],
                         ["trial"])
        self.assertEqual(report["residualCount"], 0)

    def test_empty_block_kept_verbatim_when_recompute_yields_nothing(self):
        detail = {"id": RID2, "date": DATE, "track": "浦和", "circuit": "地方",
                  "raceNumber": 2, "distance": 1400, "condition": "良",
                  "horses": [dict(debutant(5, "無材料"),
                                  researchEvidence=empty_block())],
                  "preparedMeta": {"diagnosisReady": False}}
        model = b.model_from_sync_payload(sync_payload([detail]))
        report = b.heal_missing_research_evidence(model, self.out)
        self.assertEqual(report["healStatus"], "ok")
        # Nothing could be computed, so the original block must
        # survive byte-for-byte and the horse must surface in the
        # residual report instead of passing silently.
        self.assertEqual(model.details[RID2]["horses"][0]["researchEvidence"],
                         empty_block())
        self.assertEqual(report["residualCount"], 1)
        entry = report["residual"][0]
        self.assertEqual(entry["raceId"], RID2)
        self.assertEqual(entry["horseNumber"], 5)
        self.assertEqual(entry["reason"], "no-past-runs-or-trial-record")

    def test_healthy_block_untouched_beside_empty_block(self):
        detail = trial_detail(RID1)
        detail["horses"][0]["researchEvidence"] = sentinel_evidence()
        detail["horses"][1]["researchEvidence"] = empty_block()
        model = b.model_from_sync_payload(sync_payload([detail]))
        b.heal_missing_research_evidence(model, self.out)
        healed = model.details[RID1]
        self.assertEqual(healed["horses"][0]["researchEvidence"],
                         sentinel_evidence())
        self.assertEqual([it["key"] for it in available_items(healed["horses"][1])],
                         ["trial"])

    def test_empty_block_heal_is_idempotent(self):
        detail = trial_detail(RID1)
        detail["horses"][0]["researchEvidence"] = empty_block()
        model = b.model_from_sync_payload(sync_payload([detail]))
        b.heal_missing_research_evidence(model, self.out)
        once = b._canonical(model.details[RID1])
        report2 = b.heal_missing_research_evidence(model, self.out)
        self.assertEqual(b._canonical(model.details[RID1]), once)
        self.assertEqual(report2["healStatus"], "not-needed")
        self.assertEqual(report2["residualCount"], 0)

    def test_unfillable_empty_block_heal_is_idempotent(self):
        detail = {"id": RID2, "date": DATE, "track": "浦和", "circuit": "地方",
                  "raceNumber": 2, "distance": 1400, "condition": "良",
                  "horses": [dict(debutant(5, "無材料"),
                                  researchEvidence=empty_block())],
                  "preparedMeta": {"diagnosisReady": False}}
        model = b.model_from_sync_payload(sync_payload([detail]))
        b.heal_missing_research_evidence(model, self.out)
        once = b._canonical(model.details[RID2])
        b.heal_missing_research_evidence(model, self.out)
        self.assertEqual(b._canonical(model.details[RID2]), once)

    def test_build_writes_healed_pack_and_residual_file(self):
        model = b.model_from_sync_payload(sync_payload([trial_detail(RID1)]))
        b.carry_over_forecast_blocks(model, self.out)
        b.carry_over_research_evidence(model, self.out)
        b.carry_over_day_statuses(model, self.out)
        b.heal_missing_research_evidence(model, self.out)
        b.build(model, self.out, "2026-11-26T09:00:00+09:00")
        pack = json.loads((self.out / "race" / f"{RID1}.json")
                          .read_text(encoding="utf-8"))
        for h in pack["detail"]["horses"]:
            self.assertIn("researchEvidence", h)
            self.assertEqual([it["key"] for it in available_items(h)],
                             ["trial"])
        self.assertEqual(self._residual_body()["residualCount"], 0)


if __name__ == "__main__":
    unittest.main()
