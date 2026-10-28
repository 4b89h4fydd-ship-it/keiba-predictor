#!/usr/bin/env python3
"""Produce per-race forecasts (probabilities + marks) for stored races.

Usage: python scripts/arvexq_rewrite_forecast.py <db_path> [out_json]
Probabilities are uncalibrated priors until the backtest step fits and
validates them; every record carries that status explicitly.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.analysis.forecast import forecast_race  # noqa: E402
from rewrite.data.store import Store  # noqa: E402

MARK_SYMBOLS = ("◎", "○", "▲", "△", "☆")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    store = Store(sys.argv[1])
    try:
        races = store.load_races()
    finally:
        store.close()
    out = []
    full_marks = 0
    for race in races:
        forecast = forecast_race(race)
        marks = {r.mark for r in forecast.runners if r.mark}
        if marks == set(MARK_SYMBOLS):
            full_marks += 1
        out.append({
            "race_id": forecast.race_id,
            "status": forecast.status,
            "probability_status": forecast.probability_status,
            "beta": forecast.beta,
            "runners": [
                {"number": r.number, "name": r.name, "mark": r.mark,
                 "p_win": r.p_win, "p_top2": r.p_top2, "p_top3": r.p_top3,
                 "ability_score": r.ability_score,
                 "pace_adjustment": r.pace_adjustment,
                 "pace_reasons": list(r.pace_reasons), "status": r.status}
                for r in forecast.runners
            ],
        })
    summary = {
        "races": len(out),
        "races_ok": sum(1 for r in out if r["status"] == "ok"),
        "races_with_full_marks": full_marks,
        "probability_status": "uncalibrated-prior",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(
            json.dumps({"summary": summary, "races": out}, ensure_ascii=False, indent=2)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
