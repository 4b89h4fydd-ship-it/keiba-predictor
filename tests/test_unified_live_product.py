"""Genuine same-model display safety for central and local forecast receipts."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

from test_learned_scenarios import training_race, target
from arvexq.prediction.learned_scenarios import fit_model
from arvexq.prediction.unified_product import generate, verified, VERSION
from arvexq.prediction.prerace_archive import JST
from arvexq.forecast.publication import public_race
from scripts.arvexq_protect_sync import protect_detail


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.fromisoformat("2026-10-26T09:00:00+09:00")


class UnifiedLiveTests(TestCase):
    def test_both_circuits_marks_pace_and_bets_share_one_locked_source(self):
        for circuit in ("中央", "地方"):
            with self.subTest(circuit=circuit):
                source = target(circuit)
                source.update({"id": circuit+"-2026-10-26-01",
                               "date": "2026-10-26", "startTime": "14:00",
                               "title": "一般平地", "track": "京都" if circuit == "中央" else "園田",
                               "surface": "芝" if circuit == "中央" else "ダート"})
                before = deepcopy(source)
                model = fit_model([training_race(circuit)], circuit=circuit,
                                  epochs=5)
                with patch("arvexq.prediction.new_forecast.datetime", FixedDateTime):
                    out = generate(source, model,
                                   now=datetime.fromisoformat("2026-10-26T09:00:00+09:00"))
                self.assertEqual(before, source)
                self.assertIsNotNone(verified(dict(source, unifiedForecast=out)))
                self.assertEqual(out["modelHash"], model["modelHash"])
                self.assertEqual(out["circuit"], circuit)
                self.assertEqual(out["modelFamily"], "flat")
                self.assertEqual(out["honmeiHorseNumber"],
                                 next(row["horseNumber"] for row in out["marks"]
                                      if row["markSymbol"] == "◎"))
                self.assertIn("likelyForwardNumbers", out["pace"])
                self.assertTrue(out["ticketPlan"]["sameModelAndMarks"])
                self.assertEqual(out["ticketPlan"]["items"], [])
                self.assertFalse(out["probabilitiesCalibrated"])
                projection = public_race(dict(source, unifiedForecast=out))
                self.assertEqual(projection["predictionStatus"], "unified-reference-ready")
                self.assertEqual({r["horseNumber"]: r["mark"] for r in projection["predictionMarks"]},
                                 {r["horseNumber"]: r["markSymbol"] for r in out["marks"]})
                self.assertEqual(projection["recommendedBets"], [])

    def test_receipt_fails_closed_on_renamed_horse_changed_mark_or_late_clock(self):
        source = target("地方")
        source.update({"id": "nar-2026-10-26-園田-05",
                       "date": "2026-10-26", "startTime": "13:00", "track": "園田"})
        model = fit_model([training_race("地方")], circuit="地方", epochs=3)
        with patch("arvexq.prediction.new_forecast.datetime", FixedDateTime):
            valid = generate(source, model,
                             now=datetime.fromisoformat("2026-10-26T09:00:00+09:00"))
        wrong = deepcopy(source)
        wrong["horses"][0]["name"] = "別の馬"
        self.assertIsNone(verified(dict(wrong, unifiedForecast=valid)))
        hacked = deepcopy(valid)
        hacked["marks"][0]["markSymbol"] = "☆"
        self.assertIsNone(verified(dict(source, unifiedForecast=hacked)))
        hacked = deepcopy(valid)
        hacked["capturedAt"] = "2026-10-26T14:00:00+09:00"
        self.assertIsNone(verified(dict(source, unifiedForecast=hacked)))
        base = dict(source, unifiedForecast=valid)
        update = deepcopy(source)
        preserved = protect_detail(base, update)
        self.assertEqual(preserved["unifiedForecast"], valid)
        update["unifiedForecast"] = hacked
        retained = protect_detail(base, update)
        self.assertEqual(retained["unifiedForecast"], valid)

    def test_never_materialize_after_off_or_from_future_results(self):
        row = target("地方")
        row.update({"id": "nar-2026-10-26-園田-09",
                    "date": "2026-10-26", "startTime": "13:00"})
        model = fit_model([training_race("地方")], circuit="地方", epochs=3)
        with self.assertRaisesRegex(ValueError, "upcoming"):
            generate(row, model,
                     now=datetime.fromisoformat("2026-10-26T13:01:00+09:00"))
        row["result"] = {"status": "確定", "finishers": [{"horseNumber": 1, "finish": 1}]}
        with self.assertRaisesRegex(ValueError, "upcoming"):
            generate(row, model,
                     now=datetime.fromisoformat("2026-10-26T09:00:00+09:00"))
