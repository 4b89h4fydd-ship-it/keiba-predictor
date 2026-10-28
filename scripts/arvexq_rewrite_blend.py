#!/usr/bin/env python3
"""Blend model probabilities with market (win odds) probabilities.

Usage:
  python scripts/arvexq_rewrite_blend.py <db_dir> <train_dates> <test_dates> <fit_json>

Discipline:
- Blend weight w is selected on TRAIN dates only, by winner log loss.
- Evaluation subset: races where EVERY active runner has win odds
  (a market distribution cannot be formed otherwise). Coverage is
  reported; model-only and market-only references use the same subset.
- Odds caveat: the stored odds are the final displayed odds, not a
  frozen pre-off snapshot, so market strength here is an upper bound.
- Two blend forms: linear (arithmetic pool) and geometric (log pool).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from math import exp, log, sqrt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.analysis.ability import analyze_race  # noqa: E402
from rewrite.analysis.forecast import FLOOR_FRACTION, _pace_adjustments  # noqa: E402
from rewrite.analysis.pace import forecast_pace  # noqa: E402
from rewrite.safety.probability import distribution, marginals  # noqa: E402

EPS = 1e-12
W_GRID = [i / 20 for i in range(21)]


def _backtest_module():
    spec = importlib.util.spec_from_file_location(
        "bt", Path(__file__).with_name("arvexq_rewrite_backtest.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BT = _backtest_module()


def load_day(db_path: Path):
    return _BT.load_day(db_path)


def build_entries(db_dir, dates, weights_by_segment, beta_by_segment, payout_for):
    entries = []
    for date in dates:
        races, results = load_day(db_dir / f"rewrite-{date}.sqlite3")
        for race in races:
            result = results.get(race.race_id)
            if not result:
                continue
            finishers = sorted(
                (f for f in result.get("finishers") or [] if isinstance(f.get("finish"), int)),
                key=lambda f: f["finish"],
            )
            if len(finishers) < 3:
                continue
            segment = race.segment.value
            weights = weights_by_segment.get(segment)
            ability = analyze_race(race, weights=weights)
            scored = {a.number: a.score for a in ability if a.score is not None}
            if len(scored) < 3:
                continue
            adjustments = _pace_adjustments(race, forecast_pace(race))
            mean = sum(scored.values()) / len(scored)
            beta = beta_by_segment.get(segment, 2.0)
            strengths = {
                n: exp(beta * (s - mean)) * adjustments.get(n, (1.0, ()))[0]
                for n, s in scored.items()
            }
            active = [r.number for r in race.active_runners]
            if set(active) - set(strengths):
                floor = FLOOR_FRACTION * min(strengths.values())
                for n in set(active) - set(strengths):
                    strengths[n] = floor
            outcomes = distribution(strengths)
            p_model = {n: m[0] for n, m in marginals(outcomes).items()}
            odds = {
                r.number: r.win_odds.value for r in race.runners
                if r.win_odds.present and isinstance(r.win_odds.value, (int, float))
                and r.win_odds.value > 0
            }
            p_market = None
            if all(n in odds for n in active):
                raw = {n: 1.0 / odds[n] for n in active}
                total = sum(raw.values())
                p_market = {n: v / total for n, v in raw.items()}
            entries.append({
                "date": date, "segment": segment,
                "p_model": p_model, "p_market": p_market,
                "winner": finishers[0]["horseNumber"],
                "top3": tuple(f["horseNumber"] for f in finishers[:3]),
                "payouts": result.get("payouts") or [],
                "win_odds": odds,
            })
    return entries, payout_for


def blend(p_model: dict, p_market: dict, w: float, form: str) -> dict:
    numbers = p_model.keys()
    if form == "linear":
        mixed = {n: w * p_market[n] + (1 - w) * p_model[n] for n in numbers}
    else:
        mixed = {
            n: exp(w * log(max(p_market[n], EPS)) + (1 - w) * log(max(p_model[n], EPS)))
            for n in numbers
        }
    total = sum(mixed.values())
    return {n: v / total for n, v in mixed.items()}


def evaluate(entries: list[dict], w: float, form: str, payout_for) -> dict:
    losses, wins, top3_hits, stake, returned = 0.0, 0, 0, 0.0, 0.0
    for e in entries:
        p = e["p_market"] if w == 1.0 else e["p_model"] if w == 0.0 else blend(
            e["p_model"], e["p_market"], w, form)
        losses += -log(max(p[e["winner"]], EPS))
        pick = max(p, key=lambda n: (p[n], -n))
        wins += 1 if pick == e["winner"] else 0
        top3_hits += 1 if pick in e["top3"] else 0
        stake += 100
        returned += payout_for(e["payouts"], "win", (pick,))
    n = len(entries)
    return {
        "races": n,
        "log_loss": round(losses / n, 4) if n else None,
        "pick_win_rate": round(wins / n, 4) if n else None,
        "pick_top3_rate": round(top3_hits / n, 4) if n else None,
        "pick_win_bet_roi": round(returned / stake, 4) if stake else None,
    }


def main() -> int:
    if len(sys.argv) < 5:
        print(__doc__)
        return 2
    db_dir = Path(sys.argv[1])
    train_dates, test_dates = sys.argv[2].split(","), sys.argv[3].split(",")
    fit = json.loads(Path(sys.argv[4]).read_text())
    weights_by_segment, beta_by_segment = {}, {}
    for seg, s in (fit.get("segments") or {}).items():
        if s.get("status") == "fitted-on-train-only":
            weights_by_segment[seg] = s["weights"]
            beta_by_segment[seg] = s["beta"]
    payout_for = _BT.payout_for
    train_all, _ = build_entries(db_dir, train_dates, weights_by_segment, beta_by_segment, payout_for)
    test_all, _ = build_entries(db_dir, test_dates, weights_by_segment, beta_by_segment, payout_for)
    train = [e for e in train_all if e["p_market"]]
    test = [e for e in test_all if e["p_market"]]
    report = {
        "train_dates": train_dates, "test_dates": test_dates,
        "coverage": {
            "train_races_with_full_odds": len(train), "train_races_total": len(train_all),
            "test_races_with_full_odds": len(test), "test_races_total": len(test_all),
        },
        "odds_caveat": "final displayed odds (upper-bound market), not frozen pre-off snapshots",
        "references_test": {
            "model_only_w0": evaluate(test, 0.0, "linear", payout_for),
            "market_only_w1": evaluate(test, 1.0, "linear", payout_for),
        },
        "forms": {},
    }
    for form in ("linear", "geometric"):
        grid = []
        for w in W_GRID:
            m = evaluate(train, w, form, payout_for)
            grid.append({"w": w, "train_log_loss": m["log_loss"]})
        best = min(grid, key=lambda g: g["train_log_loss"])
        report["forms"][form] = {
            "train_grid": grid,
            "selected_w": best["w"],
            "test_at_selected_w": evaluate(test, best["w"], form, payout_for),
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
