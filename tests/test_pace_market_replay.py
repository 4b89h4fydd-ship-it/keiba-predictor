"""End-to-end replay input and payoff guards (synthetic examples only)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rewrite.analysis.shadow_v9 import postprocess_forecast
from scripts.arvexq_pace_market_ablation import _check_record, replay
from test_pace_market_candidate import sample, ODDS


def fixture():
    race, base = sample()
    published, _ = postprocess_forecast(base, arm="v9b", win_odds=ODDS)
    detail = {
        "id": race.race_id, "date": race.date, "circuit": "中央",
        "track": "東京", "title": "通常競走",
        "distance": 1600, "surface": "芝",
        "horses": [
            {"horseNumber": h.number, "name": h.name.value,
             "recentRaces": [
                 {"date": run.date, "fieldSize": run.field_size.value,
                  "finish": run.finish.value,
                  "cornerPositions": list(run.corner_positions)}
                 for run in h.past_runs]}
            for h in race.runners,
        ],
    }
    return {
        "detail": detail, "capturedAt": "2026-11-07T09:00:00+09:00",
        "postAt": "2026-11-07T12:00:00+09:00",
        "baseStrengthsAtSeal": {
            str(h.number): h.strength for h in base.runners},
        "v9bWinAtSeal": {
            str(h.number): h.p_win for h in published.runners},
        "winOddsAtSeal": {str(k): v for k, v in ODDS.items()},
        "result": {
            "finishOrder": [1, 2, 3, 4, 5],
            "trifectaPayoutPer100": 2100,
        },
    }


class MatchedReplayTests(TestCase):
    def test_synthetic_parity_and_true_b_denominator(self):
        row = fixture()
        _check_record(row)
        with TemporaryDirectory() as d:
            path = Path(d) / "sealed.jsonl"
            path.write_text(json.dumps(row, ensure_ascii=False),
                            encoding="utf-8")
            report = replay(path, "2026-11-05")
        control = report["results"]["中央"]["holdout"][
            "pace=0.0,market=0.5"]
        self.assertEqual(control["races"], 1)
        self.assertEqual(control["totalStakeYen"], 3600)
        self.assertEqual(control["totalPayoutYen"], 2100)
        self.assertAlmostEqual(control["bROI"], 2100 / 3600, places=4)

    def test_rejects_unmatched_v9b_archive(self):
        row = fixture()
        row["v9bWinAtSeal"]["1"] = .99
        with TemporaryDirectory() as d:
            path = Path(d) / "bad.jsonl"
            path.write_text(json.dumps(row), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "v9b original mismatch"):
                replay(path, "2026-11-05")

    def test_rejects_reconstructed_postrace(self):
        row = fixture()
        row["capturedAt"] = "2026-11-07T14:00:00+09:00"
        with self.assertRaisesRegex(ValueError, "before-off"):
            _check_record(row)
        row = fixture()
        row["detail"]["result"] = {"winner": 1}
        with self.assertRaisesRegex(ValueError, "post-race"):
            _check_record(row)
