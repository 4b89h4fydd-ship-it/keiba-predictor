#!/usr/bin/env python3
"""Run ability + pace analysis over races stored by the ingest step.

Usage: python scripts/arvexq_rewrite_analyze.py <db_path> [out_json]
Writes a summary (coverage counts only) and, with out_json, the full
per-race analysis for inspection. Scores are prior-weight rankings,
explicitly labelled unfitted — not calibrated probabilities.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.analysis.ability import MODEL_VERSION, analyze_race  # noqa: E402
from rewrite.analysis.pace import forecast_pace  # noqa: E402
from rewrite.data.store import Store  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    store = Store(sys.argv[1])
    try:
        races = store.load_races()
    finally:
        store.close()
    full = []
    scored_races = 0
    pace_complete = 0
    for race in races:
        ability = analyze_race(race)
        pace = forecast_pace(race)
        if any(r.score is not None for r in ability):
            scored_races += 1
        if all(pace.stages[s].order for s in ("start", "corner3", "corner4", "straight")):
            pace_complete += 1
        full.append({
            "race_id": race.race_id,
            "segment": race.segment.value,
            "ability_model": MODEL_VERSION,
            "ability": [
                {"number": r.number, "name": r.name, "score": r.score,
                 "status": r.status, "evidence_runs": r.features.evidence_runs,
                 "raw": r.features.raw, "normalized": r.normalized}
                for r in ability
            ],
            "pace": {
                "pace_label": pace.pace_label,
                "pace_pressure": pace.pace_pressure,
                "front_runners": list(pace.front_runners),
                "unknown_runners": list(pace.unknown_runners),
                "stages": {s: list(o.order) for s, o in pace.stages.items()},
                "scenarios": {
                    name: {"straight_order": list(sc["straight_order"].order)}
                    for name, sc in pace.scenarios.items()
                },
            },
        })
    summary = {
        "races": len(races),
        "races_with_ability_scores": scored_races,
        "races_with_complete_pace": pace_complete,
        "ability_model": MODEL_VERSION,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(
            json.dumps({"summary": summary, "races": full}, ensure_ascii=False, indent=2)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
