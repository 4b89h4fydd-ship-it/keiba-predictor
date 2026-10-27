#!/usr/bin/env python3
"""Generate ticket plans for stored races.

Usage: python scripts/arvexq_rewrite_tickets.py <db_path> [out_json]
EV tickets stay empty until calibration is validated on held-out
races; the plan records the suppression reason instead of staying
silently empty like the current production API.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.analysis.forecast import forecast_race  # noqa: E402
from rewrite.analysis.tickets import generate_tickets  # noqa: E402
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
    plans = []
    kind_counts: Counter = Counter()
    suppression_counts: Counter = Counter()
    for race in races:
        forecast = forecast_race(race)
        win_odds = {
            r.number: r.win_odds.value
            for r in race.runners
            if r.win_odds.present and isinstance(r.win_odds.value, (int, float))
        }
        plan = generate_tickets(forecast, win_odds, calibration_validated=False)
        kind_counts.update(t.kind for t in plan.probability_tickets)
        suppression_counts.update(
            {k: 1 for k in plan.suppressed}
        )
        plans.append({
            "race_id": plan.race_id,
            "ev_tickets": [t.__dict__ for t in plan.ev_tickets],
            "probability_tickets": [t.__dict__ for t in plan.probability_tickets],
            "suppressed": plan.suppressed,
        })
    summary = {
        "races": len(plans),
        "races_with_probability_tickets": sum(
            1 for p in plans if p["probability_tickets"]
        ),
        "probability_tickets_by_kind": dict(kind_counts),
        "ev_tickets_total": sum(len(p["ev_tickets"]) for p in plans),
        "ev_suppression_reasons": dict(suppression_counts),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(
            json.dumps({"summary": summary, "plans": plans}, ensure_ascii=False, indent=2)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
