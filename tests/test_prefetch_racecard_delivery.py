"""Racecard delivery must never be held hostage by isolated AI/roster failures."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import arvexq_select_prefetch_repairs as repair
from scripts import arvexq_prefetch as prefetch


def race(rid: str, numbers: tuple[int, ...], ai: bool = True) -> dict:
    return {
        "id": rid,
        "track": "大井",
        "date": "2026-10-08",
        "horses": [{"horseNumber": n, "name": f"馬{n}"} for n in numbers],
        "preparedMeta": {"diagnosisReady": ai},
    }


class PrefetchRacecardDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.id = "nar-2026-10-08-大井-04"

    def test_fact_stage_does_not_rewrite_only_for_model_or_marks(self) -> None:
        prepared = race(self.id, (1, 2, 3), ai=True)
        existing = copy.deepcopy(prepared)
        prepared["predictionStatus"] = "ready"
        prepared["predictionModelVersion"] = "arvexq-three-analysis-vnext-1"
        prepared["predictionMarks"] = [{"horseNumber": 1, "mark": "◎"}]
        prepared["recommendedBets"] = [{"kind": "馬連", "horseNumbers": [1, 2]}]
        prepared["preparedMeta"]["analysisInputHash"] = "recent"
        existing["predictionStatus"] = "disabled"
        existing["predictionModelVersion"] = "legacy"
        existing["preparedMeta"]["analysisInputHash"] = "old"
        self.assertEqual(repair.repair_reason(prepared, existing, facts_only=True), "")
        self.assertEqual(repair.repair_reason(prepared, existing),
                         "new_method_products_not_persisted")

    def test_fact_stage_still_repairs_missing_roster_and_real_history(self) -> None:
        prepared = race(self.id, (1, 2, 3))
        existing = copy.deepcopy(prepared)
        prepared["horses"][0]["recentRaces"] = [
            {"date": "2026-10-01", "track": "佐賀", "raceNumber": 2,
             "finish": 2, "fieldSize": 11}]
        self.assertEqual(repair.repair_reason(prepared, existing, facts_only=True),
                         "career_history_missing_observations")
        existing["horses"] = existing["horses"][:-1]
        self.assertEqual(repair.repair_reason(prepared, existing, facts_only=True),
                         "roster_incomplete")

    def test_workflow_facts_only_and_later_prediction_overlay_remain_separate(self) -> None:
        workflow = Path(".github/workflows/arvexq-prefetch.yml").read_text(encoding="utf-8")
        fact_stage = workflow.split("Persist collected facts using the existing D1 sync pipeline",1)[1].split(
            "Read D1 facts back and require identical horse/history evidence",1)[0]
        forecast_stage = workflow.split("Select only missing or thin D1 details",1)[1].split(
            "Push prepared day repairs to D1 in safe batches",1)[0]
        self.assertIn("--facts-only", fact_stage)
        self.assertNotIn("--facts-only", forecast_stage)

    def test_partial_roster_with_ai_is_still_a_repair(self) -> None:
        prepared = race(self.id, (1, 2, 3, 4))
        current = race(self.id, (1, 2))
        self.assertTrue(repair.rich(current))
        self.assertEqual(repair.repair_reason(prepared, current), "roster_incomplete")

    def test_missing_ai_does_not_make_the_roster_unavailable(self) -> None:
        prepared = race(self.id, (1, 2, 3, 4), ai=False)
        self.assertEqual(len(repair.named_roster(prepared)), 4)
        self.assertEqual(repair.repair_reason(prepared, None), "missing")

    def test_existing_complete_snapshot_unchanged(self) -> None:
        prepared = race(self.id, (1, 2, 3))
        existing = race(self.id, (1, 2, 3))
        self.assertEqual(repair.repair_reason(prepared, existing), "")

    def test_missing_analysis_can_be_repaired_without_erasing_roster(self) -> None:
        prepared = race(self.id, (1, 2, 3))
        existing = race(self.id, (1, 2, 3), ai=False)
        self.assertEqual(repair.repair_reason(prepared, existing), "thin")

    def test_repair_selection_does_not_erase_known_horses(self) -> None:
        rid2 = "nar-2026-10-08-大井-05"
        rid3 = "nar-2026-10-08-園田-03"
        source = [
            race(self.id, (1, 2, 3), ai=True),
            race(rid2, (1, 2), ai=True),
            race(rid3, (1, 2), ai=False),
        ]
        current = [
            race(self.id, (1, 2), ai=True),
            race(rid2, (1, 2, 3), ai=True),
        ]
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            prepared_file = directory / "prepared.json"
            current_file = directory / "current.json"
            output_file = directory / "out.json"
            report_file = directory / "report.json"
            prepared_file.write_text(json.dumps({
                "summaries": [{"id": d["id"]} for d in source],
                "details": source,
                "meta": {"race_count": 3},
            }, ensure_ascii=False), encoding="utf-8")
            current_file.write_text(json.dumps({"details": current}, ensure_ascii=False), encoding="utf-8")
            argv = ["prefetch", "--prepared", str(prepared_file), "--current", str(current_file),
                    "--out", str(output_file), "--report", str(report_file)]
            with patch.object(sys, "argv", argv):
                self.assertEqual(repair.main(), 0)
            payload = json.loads(output_file.read_text(encoding="utf-8"))
            report = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual({d["id"] for d in payload["details"]}, {self.id, rid3})
            self.assertEqual(len(payload["summaries"]), 3)
            self.assertEqual(report["repair_count"], 2)
            self.assertIn("source_roster_missing_known_horses",
                          [r["reason"] for r in report["repairs"]])

    def test_incomplete_field_is_never_misclassified_as_ready(self) -> None:
        detail = {"id": self.id, "date": "2026-10-08", "fieldSize": 12,
                  "horses": [{"horseNumber": i, "name": f"馬{i}",
                              "jockey": "騎手", "carriedWeight": 56}
                             for i in range(1, 4)]}
        self.assertFalse(prefetch._card_usable(detail),
                         "three visible horses are not a complete twelve-runner roster")
        detail["horses"].extend(
            {"horseNumber": i, "name": f"馬{i}", "jockey": "騎手",
             "carriedWeight": 56} for i in range(4, 13))
        self.assertTrue(prefetch._card_usable(detail))
        detail["horses"].pop()
        self.assertFalse(prefetch._card_usable(detail))

    def test_reuse_verified_prior_roster_inside_same_prefetch(self) -> None:
        source = {"date": "2026-10-08", "races": [{
            "id": self.id, "date": "2026-10-08", "fieldSize": 4,
            "horses": [{"horseNumber": n, "name": f"horse{n}",
                         "jockey": "騎手", "carriedWeight": 56}
                        for n in range(1, 5)]}]}
        with patch.object(prefetch, "_read", return_value=source):
            recovered = prefetch._recover_existing_racecards("2026-10-08")
        self.assertEqual(len(recovered[self.id]["horses"]), 4)
        incoming = {"id": self.id, "fieldSize": 4,
                    "horses": [{"horseNumber": 1, "name": "horse1",
                                "jockey": "騎手", "carriedWeight": 56,
                                "recentRaces": [{"date":"2026-09-01","finish":2}]}],
                    "preRaceBet": {"fixedAt": "2026-10-08T10:05:00+09:00",
                                    "items": ["保存原本"]}}
        merged = prefetch._merge_detail(recovered[self.id], incoming)
        self.assertTrue(prefetch._card_usable(merged))
        self.assertEqual(len(merged["horses"]), 4)
        self.assertEqual(len(merged["horses"][0]["recentRaces"]), 1)
        self.assertEqual(merged["preRaceBet"], incoming["preRaceBet"])

    def test_fully_observed_nar_6040_is_current_without_full_lifetime(self) -> None:
        from arvexq.prediction.observed_model import apply_nar_marks, MODEL_VERSION
        rows = []
        for no in range(1, 6):
            runs = [
                {"date": f"2026-10-{day:02d}", "track": "大井",
                 "distance": 1400, "surface": "ダート", "fieldSize": 8,
                 "finish": no, "cornerPositions": [no, no],
                 "timeBehindWinner": .25 * (no - 1), "opponentLevel": .6}
                for day in (1, 2, 3, 4, 5)
            ]
            rows.append({"horseNumber": no, "frameNumber": no,
                         "name": f"馬{no}", "recentRaces": runs})
        detail = {"id": "nar-2026-10-15-大井-01", "date": "2026-10-15",
                  "circuit": "地方", "track": "大井", "surface": "ダート",
                  "distance": 1400, "horses": rows,
                  "preparedMeta": {"diagnosisReady": True, "careerReady": False}}
        apply_nar_marks(detail)
        self.assertEqual(detail["predictionModelVersion"], MODEL_VERSION)
        self.assertTrue(prefetch._analysis_ready(detail))
        detail["preparedMeta"]["analysisInputHash"] = prefetch.analysis_input_hash(detail)
        self.assertTrue(prefetch._analysis_current(detail))
        detail["preparedMeta"]["diagnosisReady"] = False
        self.assertFalse(prefetch._analysis_ready(detail))
        self.assertFalse(prefetch._analysis_current(detail))
        detail["preparedMeta"]["diagnosisReady"] = True
        detail["predictionModelVersion"] = "arvexq-retired-nar-scores"
        # An obsolete prediction cannot block observed data diagnostics.
        self.assertTrue(prefetch._analysis_ready(detail))

    def test_network_enrichment_is_bounded_and_preserves_failed_card(self) -> None:
        from threading import Lock
        from time import sleep
        active = 0
        max_active = 0
        lock = Lock()
        ids = [f"race-{i}" for i in range(7)]
        cards = {rid: {"id": rid, "horses": [{"horseNumber": 1, "name": rid}]}
                 for rid in ids}
        def fetch(card):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            sleep(.012)
            with lock:
                active -= 1
            if card["id"] == "race-3":
                raise RuntimeError("provider timed out")
            card["evidenceReady"] = True
            return card
        with patch.object(prefetch, "_supplement_missing", side_effect=fetch):
            output = prefetch._enrich_cards_concurrently(cards, workers=3)
        self.assertEqual(set(output), set(cards))
        self.assertTrue(1 < max_active <= 3)
        self.assertFalse(output["race-3"].get("evidenceReady"))
        self.assertTrue(output["race-4"]["evidenceReady"])
        self.assertFalse(any(card.get("evidenceReady") for card in cards.values()))

    def test_official_d1_day_exists_before_heavy_prefetch(self) -> None:
        workflow = Path(".github/workflows/arvexq-prefetch.yml").read_text(encoding="utf-8")
        early = workflow.index("Publish official day summaries before heavy prediction work")
        collect = workflow.index("Collect racecards and full careers without running predictions")
        heavy = workflow.index("Analyze only persisted D1 data")
        cold = workflow.index("D1_EARLY_SUMMARIES_WRITE")
        verify = workflow.index("D1_EARLY_SUMMARIES_VERIFY")
        persist = workflow.index("D1_STORED_EVIDENCE_VERIFIED")
        self.assertLess(early, cold)
        self.assertLess(cold, verify)
        self.assertLess(verify, collect)
        self.assertLess(collect, persist)
        self.assertLess(persist, heavy)
        self.assertIn("--file initial-day-summaries.json", workflow)
        self.assertIn("D1_EARLY_SUMMARIES_INCOMPLETE", workflow)
        self.assertEqual(workflow.count("arvexq-cold-start-race-summaries-v1"), 1,
                         "retire the old post-analysis cold-start publisher")

    def test_d1_readback_checks_prepared_active_ids_not_legacy_day_totals(self) -> None:
        # A D1 calendar manifest can retain retired races with 404 details.
        # The regression contract is exact identity/completeness of every
        # prepared active race, without silently discarding missing active IDs.
        workflow = Path(".github/workflows/arvexq-prefetch.yml").read_text(encoding="utf-8")
        self.assertIn("D1_PREFETCH_ACTIVE_ID_READBACK", workflow)
        self.assertIn("D1_PREFETCH_ACTIVE_SCOPE", workflow)
        self.assertIn("missing_prepared_ids=sorted(expected_ids-set(expected))", workflow)
        self.assertIn("missing_summary_ids=sorted(expected_ids-actual_ids)", workflow)
        self.assertIn("missing_cards.extend((rid,'no prepared source detail')", workflow)
        self.assertIn("d=returned.get(rid)", workflow)
        self.assertIn("raise SystemExit('D1 racecard delivery incomplete:", workflow)
        self.assertNotIn('if [ "$ACTUAL" -lt "$EXPECTED" ]', workflow)
        self.assertNotIn('if [ "$DETAILS" -lt "$EXPECTED" ]', workflow)

    def test_pipeline_still_publishes_when_analysis_fails(self) -> None:
        workflow = Path(".github/workflows/arvexq-prefetch.yml").read_text(encoding="utf-8")
        self.assertIn("Publish lightweight racecards independent of D1 capacity", workflow)
        self.assertIn("D1_STORED_EVIDENCE_VERIFIED", workflow)
        self.assertIn("D1_MISSING_CARDS", workflow)
        self.assertIn("FAILED_BATCHES=$((FAILED_BATCHES + 1))", workflow)
        self.assertLess(workflow.index("Publish lightweight racecards independent of D1 capacity"),
                        workflow.index("Analyze only persisted D1 data"))
        self.assertLess(workflow.index("Read D1 facts back and require identical horse/history evidence"),
                        workflow.index("Analyze only persisted D1 data"))


if __name__ == "__main__":
    unittest.main()
