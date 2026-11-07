"""Research-only pace x market ablation on the frozen v8/v9b lane.

No production caller imports this module. Existing seals are immutable.
Only historical corners/finishes are allowed; never current-race results,
post-off odds or unverified video. Unknown runners get multiplier 1.
"""
from __future__ import annotations

from math import exp, fsum, isfinite

from ..safety.contracts import Segment
from ..safety.probability import distribution, marginals
from .forecast import RaceForecast, RunnerForecast, _assign_marks
from .pace import forecast_pace, style_profile
from .shadow_v9 import (
    TEMPERATURE, BLEND_WEIGHT, blend_probs, market_probs,
    postprocess_forecast, temperature_probs, usable_market,
)

VERSION = "arvexq-research-pace-market-v1"
SCENARIOS = ("normal", "fast", "slow")


def _scenario_weights(front_count: int) -> dict[str, float]:
    """Prespecified hypotheses, not fitted pace probabilities."""
    if front_count <= 1:
        return {"normal": .35, "fast": .15, "slow": .50}
    if front_count == 2:
        return {"normal": .50, "fast": .25, "slow": .25}
    return {"normal": .35, "fast": .50, "slow": .15}


def _pace_evidence(race) -> tuple[dict[str, dict[int, float]], dict]:
    active = list(race.active_runners)
    if any(run.date >= race.date for r in active for run in r.past_runs):
        raise ValueError("current/future past-run evidence is forbidden")
    pace = forecast_pace(race)
    profiles = {r.number: style_profile(r) for r in active}
    observed = {
        n for n, p in profiles.items()
        if p.basis_runs >= 2 and p.corner4_ratio is not None
        and p.finish_ratio is not None
    }
    coverage = len(observed) / len(active) if active else 0.0
    info = {
        "paceCoverage": round(coverage, 4),
        "paceObservedRunners": len(observed),
        "paceEligible": len(observed) >= 3 and coverage >= 0.5,
        "frontCount": len(pace.front_runners),
        "scenarioWeights": _scenario_weights(len(pace.front_runners)),
    }
    if not info["paceEligible"]:
        return {}, info
    edges: dict[str, dict[int, float]] = {}
    for scenario in SCENARIOS:
        ordered = [
            n for n, _ratio in pace.scenarios[scenario]["straight_order"].order
            if n in observed
        ]
        if len(ordered) != len(observed):
            raise ValueError("pace scenario lost historical evidence")
        # Field-relative race-specific ordinal evidence; no target finish.
        size = len(ordered)
        edges[scenario] = {
            n: (size - 1 - 2 * i) / (size - 1)
            for i, n in enumerate(ordered)
        }
    return edges, info


def postprocess_pace_market_candidate(
    race,
    base_forecast: RaceForecast,
    *,
    win_odds: dict[int, float] | None,
    pace_scale: float,
    market_weight: float = BLEND_WEIGHT,
) -> tuple[RaceForecast, dict]:
    """Only scale=0, market_weight=.5 reproduces v9b exactly.

    Other configurations are research-only until matched forward B-bet
    hit-rate, ROI and proper scoring-rule metrics are evaluated.
    """
    if (isinstance(pace_scale, bool) or not isinstance(pace_scale, (int, float))
            or not isfinite(pace_scale) or not 0.0 <= pace_scale <= 1.0):
        raise ValueError("invalid pace_scale")
    if (isinstance(market_weight, bool)
            or not isinstance(market_weight, (int, float))
            or not isfinite(market_weight)
            or not 0.0 <= market_weight <= 0.5):
        raise ValueError("invalid market_weight")
    info = {
        "version": VERSION, "paceScale": float(pace_scale),
        "marketWeight": float(market_weight),
        "paceApplied": False, "blendApplied": False,
    }
    if race.segment not in (Segment.JRA_FLAT, Segment.NAR):
        raise ValueError("candidate only for ordinary JRA/NAR, not debut/jumps")
    if base_forecast.race_id != race.race_id:
        raise ValueError("race/forecast identity mismatch")
    if base_forecast.status != "ok":
        info["passthrough"] = base_forecast.status
        return base_forecast, info
    strengths = {
        r.number: r.strength for r in base_forecast.runners
        if r.strength is not None and r.strength > 0
    }
    if set(strengths) != {r.number for r in race.active_runners}:
        raise ValueError("base forecast and active field must agree")
    if len(strengths) < 3:
        raise ValueError("too few strengths")
    if pace_scale == 0 and market_weight == BLEND_WEIGHT:
        control, control_info = postprocess_forecast(
            base_forecast, arm="v9b", win_odds=win_odds)
        info.update({
            "blendApplied": control_info["blendApplied"],
            "paceCoverage": None, "baselineExact": True,
        })
        return control, info

    edges, evidence = _pace_evidence(race)
    info.update(evidence)
    ws = evidence["scenarioWeights"]
    if pace_scale > 0 and edges:
        scenario_probs = {}
        for scenario in SCENARIOS:
            adjusted = {
                n: s * exp(pace_scale * edges[scenario].get(n, 0.0))
                for n, s in strengths.items()
            }
            scenario_probs[scenario] = temperature_probs(
                adjusted, TEMPERATURE)
        model_prob = {
            n: fsum(ws[s] * scenario_probs[s][n] for s in SCENARIOS)
            for n in strengths
        }
        info["paceApplied"] = True
    else:
        model_prob = temperature_probs(strengths, TEMPERATURE)

    final = model_prob
    if (market_weight > 0 and win_odds
            and usable_market(win_odds, strengths)):
        final = blend_probs(
            model_prob, market_probs(win_odds, strengths),
            weight=market_weight)
        info["blendApplied"] = True

    probs = marginals(distribution(final))
    order = sorted(probs, key=lambda n: (-probs[n][0], -probs[n][2], n))
    marks = _assign_marks(order, probs)
    runners = []
    for r in base_forecast.runners:
        p = probs[r.number]
        reasons = r.pace_reasons
        if info["paceApplied"] and any(r.number in edges[s] for s in SCENARIOS):
            reasons = reasons + ("research-scenario-interaction",)
        runners.append(RunnerForecast(
            number=r.number, name=r.name, ability_score=r.ability_score,
            strength=round(final[r.number], 6),
            pace_adjustment=r.pace_adjustment,
            pace_reasons=reasons,
            p_win=round(p[0], 4), p_top2=round(p[1], 4),
            p_top3=round(p[2], 4), mark=marks.get(r.number, ""),
            status=r.status,
        ))
    return RaceForecast(
        base_forecast.race_id, base_forecast.beta,
        base_forecast.probability_status, tuple(runners), "ok"), info
