"""Ability-trial evidence for debutants (researchEvidence v3).

A first starter has no past runs, so the observed mineta/margin factors
stay unavailable and the horse renders evidence-empty even when it holds
a verified official ability-trial pass. attach_evidence must surface
that pass as a dedicated "trial" factors item — a factual record with
its grounds (date / track / distance / raw time / pass), never a
converted score and never disguised as a past run.
"""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from arvexq.prediction.race_intelligence import (
    RESEARCH_EVIDENCE_VERSION,
    attach_evidence,
    trial_records_from_extras_payload,
)

PORTA = {  # nar-2026-11-25-名古屋-04 #2, supplemented 2026-11-25
    "date": "2026-11-13", "track": "名古屋", "distance": 900,
    "timeSeconds": 57.2, "passed": True,
    "source": "nagoyakeiba.com capability sheet", "sourceRef": "https://example.invalid/sheet.pdf",
}


def _detail(horses, race_id="nar-2026-11-25-名古屋-04", date="2026-11-25"):
    return {"id": race_id, "date": date, "track": "名古屋", "circuit": "地方",
            "distance": 1400, "condition": "良", "horses": horses}


def _debutant(number=2, name="ポルタデリオーキ"):
    return {"horseNumber": number, "name": name, "recentRaces": [],
            "integratedEvaluation": {}}


def _available(horse):
    items = horse["researchEvidence"]["factors"]["items"]
    return [it for it in items if it.get("available")]


class TrialEvidenceAttachTests(unittest.TestCase):
    def test_debutant_with_trial_record_gains_trial_item(self):
        detail = _detail([_debutant()])
        attach_evidence(detail, trial_records={2: dict(PORTA)})
        h = detail["horses"][0]
        items = h["researchEvidence"]["factors"]["items"]
        self.assertEqual([it["key"] for it in items], ["mineta", "margin", "trial"])
        trial = items[-1]
        self.assertTrue(trial["available"])
        self.assertEqual(trial["label"], "能試")
        self.assertNotIn("weight", trial, "trial is not part of the 60/40 model")
        self.assertEqual(trial["value"], 57.2)
        self.assertEqual(trial["valueKind"], "trial-time-seconds")
        grounds = {m["key"]: m["value"] for m in trial["measurements"]}
        self.assertEqual(grounds, {"実施日": "2026-11-13", "競馬場": "名古屋",
                                   "距離": "900m", "タイム": "57.2秒", "結果": "合格"})
        self.assertEqual(trial["trial"]["track"], "名古屋")
        self.assertTrue(trial["trial"]["passed"])
        # The past-run factors stay honestly unavailable.
        self.assertFalse(items[0]["available"])
        self.assertFalse(items[1]["available"])
        self.assertEqual(len(_available(h)), 1)

    def test_debutant_without_trial_record_stays_empty(self):
        detail = _detail([_debutant()])
        attach_evidence(detail, trial_records={})
        items = detail["horses"][0]["researchEvidence"]["factors"]["items"]
        self.assertEqual([it["key"] for it in items], ["mineta", "margin"])
        self.assertEqual(_available(detail["horses"][0]), [])

    def test_horse_with_past_runs_gets_no_trial_item(self):
        horse = _debutant()
        horse["recentRaces"] = [{"date": "2026-10-01", "finish": 3, "fieldSize": 10,
                                 "distance": 1400, "track": "名古屋", "timeSeconds": 92.0}]
        detail = _detail([horse])
        attach_evidence(detail, trial_records={2: dict(PORTA)})
        keys = [it["key"] for it in detail["horses"][0]["researchEvidence"]["factors"]["items"]]
        self.assertNotIn("trial", keys)

    def test_attach_is_idempotent(self):
        detail = _detail([_debutant()])
        attach_evidence(detail, trial_records={2: dict(PORTA)})
        attach_evidence(detail, trial_records={2: dict(PORTA)})
        keys = [it["key"] for it in detail["horses"][0]["researchEvidence"]["factors"]["items"]]
        self.assertEqual(keys.count("trial"), 1)

    def test_extras_payload_parsing(self):
        payload = {
            "date": "2026-11-25",
            "provenance": {"2026-11-25": {"trialSpd2Supplements": {
                "horses": [
                    {"race": "nar-2026-11-25-名古屋-04", "number": 2, "name": "ポルタデリオーキ",
                     "trial_date": "2026-11-13", "trial_track": "名古屋", "trial_distance": 900,
                     "trial_time_seconds": 57.2, "trial_source": "nagoyakeiba.com capability sheet",
                     "trial_source_ref": "https://example.invalid/sheet.pdf", "spd2": 0.05},
                    {"race": "nar-2026-11-25-園田-09", "number": 7, "name": "別馬",
                     "trial_date": "2026-11-09", "trial_track": "園田", "trial_distance": 1400,
                     "trial_time_seconds": 92.8, "trial_source": "sonoda", "spd2": -1.3},
                ],
                "notSupplemented": [
                    {"race": "nar-2026-11-25-名古屋-04", "number": 5, "name": "par無し合格馬",
                     "trial_date": "2026-11-13", "trial_track": "名古屋", "trial_distance": 900,
                     "trial_time_seconds": 58.0, "trial_source": "nagoyakeiba.com capability sheet",
                     "reason": "no par"},
                    {"race": "nar-2026-11-25-名古屋-04", "number": 6, "name": "記録なし馬",
                     "reason": "no trial pass record found"},
                ],
            }}},
        }
        records = trial_records_from_extras_payload(payload, "nar-2026-11-25-名古屋-04")
        self.assertEqual(sorted(records), [2, 5])
        self.assertEqual(records[2]["timeSeconds"], 57.2)
        self.assertEqual(records[5]["track"], "名古屋")
        other = trial_records_from_extras_payload(payload, "nar-2026-11-25-園田-09")
        self.assertEqual(sorted(other), [7])

    def test_loader_via_extras_dir_env(self):
        payload = {
            "date": "2026-11-25",
            "provenance": {"2026-11-25": {"trialSpd2Supplements": {
                "horses": [
                    {"race": "nar-2026-11-25-名古屋-04", "number": 2, "name": "ポルタデリオーキ",
                     "trial_date": "2026-11-13", "trial_track": "名古屋", "trial_distance": 900,
                     "trial_time_seconds": 57.2, "trial_source": "nagoyakeiba.com capability sheet",
                     "trial_source_ref": None, "spd2": 0.05},
                ],
                "notSupplemented": [],
            }}},
        }
        with tempfile.TemporaryDirectory() as td:
            Path(td, "2026-11-25.json").write_text(json.dumps(payload, ensure_ascii=False))
            old = os.environ.get("ARVEXQ_V8_EXTRAS_DIR")
            os.environ["ARVEXQ_V8_EXTRAS_DIR"] = td
            try:
                detail = _detail([_debutant()])
                attach_evidence(detail)  # no explicit records: loader path
            finally:
                if old is None:
                    os.environ.pop("ARVEXQ_V8_EXTRAS_DIR", None)
                else:
                    os.environ["ARVEXQ_V8_EXTRAS_DIR"] = old
        keys = [it["key"] for it in detail["horses"][0]["researchEvidence"]["factors"]["items"]]
        self.assertIn("trial", keys)

    def test_version_bumped(self):
        self.assertEqual(RESEARCH_EVIDENCE_VERSION, "arvexq-race-intelligence-v3")


if __name__ == "__main__":
    unittest.main()
