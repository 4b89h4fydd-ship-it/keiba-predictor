#!/usr/bin/env python3
"""Fit ability feature weights (and beta) per segment on training days.

Usage:
  python scripts/arvexq_rewrite_fit.py <db_dir> <train_dates> <out_json>

Discipline:
- Only the listed training dates are read. Nothing from evaluation
  dates is touched; pair this with arvexq_rewrite_backtest.py run on
  disjoint later dates.
- Objective is winner log loss under the Plackett-Luce win marginal
  (p_win(i) = strength_i / sum(strengths)), with the same pace factors
  and unscored-runner floor the forecast layer uses.
- Coordinate ascent over feature-weight multipliers, starting from
  the declared priors; beta is grid-searched afterwards per segment.
- A feature fitted to zero is dropped from the output weights (the
  ability layer treats absent keys as unavailable, which also matches
  how the score gate counts available features).
"""
from __future__ import annotations

import json
import sys
from math import exp, log
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.analysis.ability import SEGMENT_WEIGHTS, analyze_race  # noqa: E402
from rewrite.analysis.forecast import FLOOR_FRACTION, _pace_adjustments  # noqa: E402
from rewrite.analysis.pace import forecast_pace  # noqa: E402
from rewrite.data.store import Store  # noqa: E402
from rewrite.safety.contracts import Segment  # noqa: E402

import os

# Dropping a feature to zero changes which runners pass the >=3
# available-features gate, which changes the evaluated race set and
# makes train/test comparisons selection-biased. v1 (with dropping)
# showed exactly that failure, so dropping is opt-in only.
MULTIPLIERS = (
    [0.0, 0.5, 0.75, 1.5, 2.0] if os.environ.get("FIT_ALLOW_DROP")
    else [0.5, 0.75, 1.5, 2.0]
)
BETA_GRID = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
EPS = 1e-12


def load_labelled(db_dir: Path, dates: list[str]) -> list[dict]:
    prepared = []
    for date in dates:
        store = Store(db_dir / f"rewrite-{date}.sqlite3")
        try:
            races = store.load_races()
            results = {}
            for kind, key, body in store.db.execute(
                "SELECT kind, race_key, body FROM raw_snapshots WHERE kind='api_race_detail'"
            ):
                payload = json.loads(body)
                result = (payload.get("detail") or {}).get("result") or {}
                if result.get("status") == "確定":
                    results[key] = result
        finally:
            store.close()
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
            ability = {a.number: a for a in analyze_race(race)}
            scored = {n for n, a in ability.items() if a.score is not None}
            if len(scored) < 3:
                continue
            adjustments = _pace_adjustments(race, forecast_pace(race))
            active = {r.number for r in race.active_runners}
            prepared.append({
                "race_id": race.race_id,
                "segment": race.segment.value,
                "normalized": {
                    n: {k: v for k, v in ability[n].normalized.items() if v is not None}
                    for n in scored
                },
                "pace_factor": {n: adjustments.get(n, (1.0, ()))[0] for n in scored},
                "floored": sorted(active - scored),
                "winner": finishers[0]["horseNumber"],
            })
    return prepared


def score(weights: dict, normalized: dict) -> float | None:
    available = {k: v for k, v in normalized.items() if weights.get(k, 0.0) > 0}
    if len(available) < 3:
        return None
    total = sum(weights[k] for k in available)
    return sum(available[k] * weights[k] for k in available) / total


def race_strengths(weights: dict, beta: float, entry: dict) -> dict[int, float] | None:
    scored = {}
    for n, normalized in entry["normalized"].items():
        s = score(weights, normalized)
        if s is not None:
            scored[n] = s
    if len(scored) < 3:
        return None
    if entry["winner"] not in scored and entry["winner"] not in entry["floored"]:
        return None
    mean = sum(scored.values()) / len(scored)
    strengths = {
        n: exp(beta * (s - mean)) * entry["pace_factor"].get(n, 1.0)
        for n, s in scored.items()
    }
    if entry["floored"]:
        floor = FLOOR_FRACTION * min(strengths.values())
        for n in entry["floored"]:
            strengths[n] = floor
    return strengths


def mean_log_loss(weights: dict, beta: float, entries: list[dict]) -> tuple[float, int]:
    total, used = 0.0, 0
    for entry in entries:
        strengths = race_strengths(weights, beta, entry)
        if not strengths or entry["winner"] not in strengths:
            continue
        p = strengths[entry["winner"]] / sum(strengths.values())
        total += -log(max(p, EPS))
        used += 1
    return (total / used if used else float("inf")), used


def fit_segment(entries: list[dict], priors: dict) -> dict:
    weights = dict(priors)
    best, used = mean_log_loss(weights, 2.0, entries)
    history = [{"step": "prior", "log_loss": round(best, 4)}]
    for _pass in range(2):
        improved = False
        for feature in list(priors):
            current = weights[feature]
            for mult in MULTIPLIERS:
                if mult == 1.0:
                    continue
                trial = dict(weights)
                trial[feature] = current * mult if mult else 0.0
                loss, _ = mean_log_loss(trial, 2.0, entries)
                if loss < best - 1e-4:
                    best, weights = loss, trial
                    improved = True
            history.append({
                "step": f"pass{_pass}:{feature}", "log_loss": round(best, 4),
            })
        if not improved:
            break
    beta_results = []
    best_beta, best_beta_loss = None, float("inf")
    for beta in BETA_GRID:
        loss, _ = mean_log_loss(weights, beta, entries)
        beta_results.append({"beta": beta, "log_loss": round(loss, 4)})
        if loss < best_beta_loss:
            best_beta, best_beta_loss = beta, loss
    fitted = {k: round(v, 4) for k, v in weights.items() if v > 0}
    return {
        "weights": fitted,
        "dropped_features": sorted(k for k, v in weights.items() if v <= 0),
        "beta": best_beta,
        "train_log_loss_at_beta2": round(best, 4),
        "train_log_loss": round(best_beta_loss, 4),
        "beta_grid": beta_results,
        "train_races_used": used,
        "history_tail": history[-6:],
    }


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    db_dir, dates, out_path = Path(sys.argv[1]), sys.argv[2].split(","), Path(sys.argv[3])
    prepared = load_labelled(db_dir, dates)
    by_segment: dict[str, list[dict]] = {}
    for entry in prepared:
        by_segment.setdefault(entry["segment"], []).append(entry)
    report = {"train_dates": dates, "segments": {}}
    for segment in (Segment.JRA_FLAT, Segment.NAR, Segment.JUMPS):
        entries = by_segment.get(segment.value, [])
        priors = SEGMENT_WEIGHTS.get(segment, {})
        if len(entries) < 20 or not priors:
            report["segments"][segment.value] = {
                "status": "skipped", "races": len(entries),
                "reason": "fewer than 20 labelled train races or no prior weights",
            }
            continue
        prior_loss, _ = mean_log_loss(dict(priors), 2.0, entries)
        fitted = fit_segment(entries, priors)
        fitted["prior_weights"] = priors
        fitted["prior_train_log_loss_at_beta2"] = round(prior_loss, 4)
        fitted["status"] = "fitted-on-train-only"
        report["segments"][segment.value] = fitted
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
