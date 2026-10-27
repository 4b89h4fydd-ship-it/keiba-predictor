#!/usr/bin/env python3
"""Time-split backtest of the rewrite forecast over stored race days.

Usage:
  python scripts/arvexq_rewrite_backtest.py <db_dir> <train_dates> <test_dates>
  e.g. ... var/backtest 2026-10-21,2026-10-22,2026-10-23 2026-10-24,...,2026-10-27

Method and limits (printed in the report, never hidden):
- Inputs are the histories as currently stored by the production API.
  Past runs dated on/after the race date are excluded by the ingest
  guard, but a history may have been backfilled after the race; this
  is NOT a frozen pre-off snapshot backtest.
- Odds used for market comparison are the final displayed win odds.
- Payouts are the official ones stored in each race's result.
- Beta (strength temperature) is fitted on the training dates only;
  the split is enforced by rewrite.analysis.calibration.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.analysis.ability import analyze_race  # noqa: E402
from rewrite.analysis.calibration import (  # noqa: E402
    LabelledRace, brier, fit_beta, honmei_record, log_loss, reliability,
)
from rewrite.analysis.forecast import forecast_race  # noqa: E402
from rewrite.analysis.pace import forecast_pace  # noqa: E402
from rewrite.analysis.tickets import generate_tickets  # noqa: E402
from rewrite.data.store import Store  # noqa: E402
from rewrite.safety.probability import distribution, marginals  # noqa: E402

PAYOUT_KIND = {
    "win": "単勝", "place": "複勝", "wide": "ワイド", "quinella": "馬連",
    "exacta": "馬単", "trio": "3連複", "trifecta": "3連単",
}


def load_day(db_path: Path):
    store = Store(db_path)
    try:
        races = store.load_races()
        results = {}
        for kind, race_key, body in store.db.execute(
            "SELECT kind, race_key, body FROM raw_snapshots WHERE kind='api_race_detail'"
        ):
            payload = json.loads(body)
            result = (payload.get("detail") or {}).get("result") or {}
            if result.get("status") == "確定":
                results[race_key] = result
    finally:
        store.close()
    return races, results


def combo_key(kind: str, selection: tuple) -> str:
    if kind in ("win", "place"):
        return str(selection[0])
    if kind in ("wide", "quinella", "trio"):
        return "-".join(str(n) for n in sorted(selection))
    return "-".join(str(n) for n in selection)  # exacta / trifecta ordered


def payout_for(payouts: list, kind: str, selection: tuple) -> float:
    label = PAYOUT_KIND[kind]
    key = combo_key(kind, selection)
    total = 0.0
    for row in payouts:
        if row.get("type") == label and str(row.get("combination")) == key:
            total += float(row.get("amount") or 0)
    return total


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    db_dir = Path(sys.argv[1])
    train_dates = sys.argv[2].split(",")
    test_dates = sys.argv[3].split(",")
    all_dates = train_dates + test_dates

    # Precompute per-race ability/pace factors and labels.
    prepared = {}  # race_id -> dict
    for date in all_dates:
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
            ability = analyze_race(race)
            pace = forecast_pace(race)
            from rewrite.analysis.forecast import _pace_adjustments
            adjustments = _pace_adjustments(race, pace)
            scored = {a.number: a.score for a in ability if a.score is not None}
            if len(scored) < 3:
                continue
            mean_score = sum(scored.values()) / len(scored)
            active_numbers = {r.number for r in race.active_runners}
            prepared[race.race_id] = {
                "date": date,
                "segment": race.segment.value,
                "base": {
                    n: (score - mean_score, adjustments.get(n, (1.0, ()))[0])
                    for n, score in scored.items()
                },
                "floored": sorted(active_numbers - set(scored)),
                "winner": finishers[0]["horseNumber"],
                "top3": tuple(f["horseNumber"] for f in finishers[:3]),
                "payouts": result.get("payouts") or [],
                "race": race,
            }

    def p_win_at(beta: float, entry: dict) -> dict:
        from math import exp

        from rewrite.analysis.forecast import FLOOR_FRACTION
        strengths = {
            n: exp(beta * delta) * factor for n, (delta, factor) in entry["base"].items()
        }
        if entry["floored"]:
            floor = FLOOR_FRACTION * min(strengths.values())
            for n in entry["floored"]:
                strengths[n] = floor
        outcomes = distribution(strengths)
        return {n: round(m[0], 6) for n, m in marginals(outcomes).items()}

    def labelled(dates: list[str], beta: float) -> list[LabelledRace]:
        return [
            LabelledRace(e["date"], p_win_at(beta, e), e["winner"], e["top3"])
            for e in prepared.values() if e["date"] in dates
        ]

    # Fit beta on train only. The grid search uses the same split
    # discipline as calibration.fit_beta, enforced via _check_split:
    # selection never touches test dates.
    from rewrite.analysis.calibration import _check_split
    candidates = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
    scored_betas = []
    for beta in candidates:
        scored_betas.append((log_loss(labelled(train_dates, beta)), beta))
    scored_betas.sort()
    best_beta = scored_betas[0][1]
    _check_split(labelled(train_dates, best_beta), labelled(test_dates, best_beta))
    test_labelled = labelled(test_dates, best_beta)
    train_at_best = labelled(train_dates, best_beta)

    # Market baseline on test dates: favourite = lowest final win odds.
    market_picks = {"races": 0, "wins": 0, "top3": 0, "stake": 0.0, "returned": 0.0}
    ours = {"stake": 0.0, "returned": 0.0}
    ticket_stats = {}
    for entry in (e for e in prepared.values() if e["date"] in test_dates):
        race = entry["race"]
        odds = {
            r.number: r.win_odds.value for r in race.runners
            if r.win_odds.present and isinstance(r.win_odds.value, (int, float))
        }
        if odds:
            favourite = min(odds, key=lambda n: (odds[n], n))
            market_picks["races"] += 1
            market_picks["wins"] += 1 if favourite == entry["winner"] else 0
            market_picks["top3"] += 1 if favourite in entry["top3"] else 0
            market_picks["stake"] += 100
            market_picks["returned"] += payout_for(entry["payouts"], "win", (favourite,))
        forecast = forecast_race(race, beta=best_beta)
        by_number = {r.number: r for r in forecast.runners}
        honmei = max(
            (r for r in forecast.runners if r.p_win is not None),
            key=lambda r: (r.p_win, -r.number), default=None,
        )
        if honmei is not None:
            ours["stake"] += 100
            ours["returned"] += payout_for(entry["payouts"], "win", (honmei.number,))
        plan = generate_tickets(forecast, odds, calibration_validated=False)
        for ticket in plan.probability_tickets:
            stats = ticket_stats.setdefault(
                ticket.kind, {"tickets": 0, "hits": 0, "stake": 0.0, "returned": 0.0}
            )
            stats["tickets"] += 1
            stats["stake"] += 100
            pay = payout_for(entry["payouts"], ticket.kind, ticket.selection)
            stats["returned"] += pay
            stats["hits"] += 1 if pay > 0 else 0
    for stats in ticket_stats.values():
        stats["hit_rate"] = round(stats["hits"] / stats["tickets"], 4) if stats["tickets"] else None
        stats["roi"] = round(stats["returned"] / stats["stake"], 4) if stats["stake"] else None

    segments: dict[str, list[LabelledRace]] = {}
    for entry in (e for e in prepared.values() if e["date"] in test_dates):
        segments.setdefault(entry["segment"], []).append(
            LabelledRace(entry["date"], p_win_at(best_beta, entry),
                         entry["winner"], entry["top3"])
        )
    segment_report = {
        seg: {"log_loss": round(log_loss(rows), 4), "honmei": honmei_record(rows)}
        for seg, rows in sorted(segments.items())
    }

    report = {
        "train_dates": train_dates,
        "test_dates": test_dates,
        "prepared_races_total": len(prepared),
        "train_races": sum(1 for e in prepared.values() if e["date"] in train_dates),
        "test_races": sum(1 for e in prepared.values() if e["date"] in test_dates),
        "beta_candidates_train_log_loss": [
            {"beta": b, "log_loss": round(loss, 4)} for loss, b in sorted(scored_betas, key=lambda x: x[1])
        ],
        "beta_selected": best_beta,
        "train_at_selected": {
            "log_loss": round(log_loss(train_at_best), 4),
            "honmei": honmei_record(train_at_best),
        },
        "test": {
            "log_loss": round(log_loss(test_labelled), 4),
            "brier": round(brier(test_labelled), 4),
            "honmei": honmei_record(test_labelled),
            "reliability": reliability(test_labelled),
        },
        "market_favourite_baseline_test": {
            **market_picks,
            "win_rate": round(market_picks["wins"] / market_picks["races"], 4) if market_picks["races"] else None,
            "top3_rate": round(market_picks["top3"] / market_picks["races"], 4) if market_picks["races"] else None,
            "win_bet_roi": round(market_picks["returned"] / market_picks["stake"], 4) if market_picks["stake"] else None,
        },
        "our_honmei_win_bet_test": {
            **ours,
            "roi": round(ours["returned"] / ours["stake"], 4) if ours["stake"] else None,
        },
        "probability_tickets_test": ticket_stats,
        "test_by_segment": segment_report,
        "caveats": [
            "histories are current stored versions, not frozen pre-off snapshots",
            "win odds are final displayed odds",
            "beta fitted on train dates only; test dates untouched by fitting",
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
