"""Verify existing Stage64 JRA/NAR six-stage pre-off research contract.

Synthetic fixtures only: this test never constitutes a witnessed future forecast,
a production mark, or a verified hit-rate result.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from arvexq.research.stage64.pipeline import STAGES
from arvexq.research.stage64.protocol import ARMS, make_plan, verify_local, freeze_batch
from arvexq.research.stage64.evaluation import evaluate
from scripts.arvexq_stage64_auto_capture import select_future


NOW = datetime(2026, 10, 22, 3, tzinfo=timezone.utc)  # 12:00 JST


def example(owner):
    circuit = "中央" if owner == "jra" else "地方"
    track = "東京" if owner == "jra" else "名古屋"
    return {
        "id": f"{owner}-2026-10-22-{track}-01",
        "date": "2026-10-22",
        "circuit": circuit,
        "track": track,
        "surface": "芝" if owner == "jra" else "ダート",
        "analysisMode": "平地",
        "startTime": "14:00",
        "fieldSize": 4,
        "horses": [
            {"horseNumber": n, "recentRaces": [
                {"date": "2026-10-15", "fieldSize": 4, "finish": n,
                 "cornerPositions": [n], "track": track, "surface": "芝" if owner == "jra" else "ダート",
                 "analysisMode": "平地"}]}
            for n in (1, 2, 3, 4)
        ],
    }


class CompleteShadowChain(unittest.TestCase):
    def test_both_circuits_from_existing_saved_input_to_research_only_scoring(self):
        source = {"details": [example("jra"), example("nar")]}
        untouched = deepcopy(source)
        with tempfile.TemporaryDirectory() as folder:
            for owner in ("jra", "nar"):
                with self.subTest(owner=owner):
                    plan = make_plan(owner, [])
                    selected, audit = select_future(source, owner, plan, NOW)
                    self.assertEqual(len(selected), 1)
                    self.assertEqual(audit["selected"], [selected[0]["id"]])
                    self.assertFalse(audit["independentlyVerifiedPreoff"])
                    target = Path(folder) / (owner + ".json")
                    with patch("arvexq.research.stage64.protocol.datetime") as clock:
                        clock.now.return_value = NOW
                        clock.fromisoformat.side_effect = datetime.fromisoformat
                        batch = freeze_batch(target, selected, plan)
                    self.assertTrue(target.exists())
                    self.assertEqual(batch["cohort"], [selected[0]["id"]])
                    receipt = batch["receipts"][0]
                    self.assertTrue(verify_local(receipt, plan)["localIntegrityVerified"])
                    self.assertFalse(verify_local(receipt, plan)["independentlyVerifiedPreoff"])
                    self.assertEqual(set(receipt["snapshot"]["predictions"]), set(ARMS))
                    for method in ARMS:
                        prediction = receipt["snapshot"]["predictions"][method]
                        self.assertEqual(tuple(prediction["stages"]), STAGES)
                        self.assertTrue(all(s["value"] is not None
                                            for s in prediction["stages"].values()))
                        self.assertEqual(len(prediction["stages"]["pace"]["value"]),
                                         1 if owner == "jra" else 4)
                        self.assertAlmostEqual(
                            sum(prediction["stages"]["probability"]["value"]["win"].values()), 1)
                        self.assertIsNone(prediction["stages"]["marks"]["value"]["productMarks"])
                        self.assertIsNone(prediction["stages"]["tickets"]["value"]["recommendedBets"])
                        self.assertFalse(prediction["productionEligible"])
                    result = [{"raceId": selected[0]["id"], "date": selected[0]["date"],
                               "circuit": owner, "status": "confirmed",
                               "orders": [[1, 2, 3]], "payouts": None}]
                    scored = evaluate(batch, result)
                    self.assertEqual(set(scored["byCircuit"]), {owner})
                    for method in ARMS:
                        counts = scored["byCircuit"][owner][method]
                        self.assertEqual(counts["cohortRaces"], 1)
                        self.assertEqual(counts["scoredRaces"], 1)
                        self.assertEqual(counts["unscoredRaces"], 0)
                        self.assertIsNone(counts["roiPct"])
                    self.assertFalse(scored["independentlyVerifiedPreoff"])
                    self.assertFalse(scored["productionEligible"])
        self.assertEqual(source, untouched)

    def test_existing_full_batch_freeze_rejects_postrace_leak_without_writing(self):
        plan = make_plan("nar", [])
        first = example("nar")
        poisoned = deepcopy(first)
        poisoned["id"] = "nar-2026-10-22-名古屋-02"
        poisoned["result"] = {"status": "確定", "finishers": [{"horseNumber": 1, "finish": 1}]}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "batch.json"
            with patch("arvexq.research.stage64.protocol.datetime") as clock:
                clock.now.return_value = NOW
                clock.fromisoformat.side_effect = datetime.fromisoformat
                with self.assertRaisesRegex(ValueError, "target outcome present"):
                    freeze_batch(target, [first, poisoned], plan)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
