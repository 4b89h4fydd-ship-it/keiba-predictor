"""Per-runner ability features and within-race composite scoring.

Phase 1 extracts raw, individually meaningful features from a runner's
own pre-race past runs. Phase 2 normalizes each feature inside the
race (the instruction: compare every horse within the same race) and
combines the available ones with segment-specific prior weights.
Features without evidence stay unavailable and the remaining weights
are renormalized — nothing is imputed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type
from math import sqrt
from typing import Optional

from ..data.normalize import PastRun, RaceRecord, RunnerRecord
from ..safety.contracts import Segment

MODEL_VERSION = "ability-prior-v1-unfitted"

# Prior weights (NOT fitted). Keys are raw feature names.
SEGMENT_WEIGHTS: dict[Segment, dict[str, float]] = {
    Segment.JRA_FLAT: {
        "form": 0.30, "speed": 0.20, "distance": 0.10, "track": 0.05,
        "surface": 0.10, "condition": 0.05, "jockey": 0.10,
        "closing": 0.05, "consistency": 0.05,
    },
    Segment.NAR: {
        "form": 0.32, "speed": 0.20, "distance": 0.10, "track": 0.08,
        "surface": 0.05, "condition": 0.05, "jockey": 0.10,
        "closing": 0.05, "consistency": 0.05,
    },
    Segment.JUMPS: {
        "form": 0.35, "speed": 0.10, "distance": 0.10, "track": 0.10,
        "surface": 0.05, "condition": 0.05, "jockey": 0.10,
        "closing": 0.05, "consistency": 0.10,
    },
    Segment.DEBUT: {},
}
LOWER_IS_BETTER = {"speed"}
RECENCY_DECAY = 0.85
MAX_RUNS = 8


def _finish_pct(run: PastRun) -> Optional[float]:
    finish, field = run.finish.value, run.field_size.value
    if not isinstance(finish, (int, float)) or not isinstance(field, (int, float)):
        return None
    if field < 2 or finish < 1 or finish > field:
        return None
    return (field - finish) / (field - 1)


def _weighted_mean(pairs: list[tuple[float, float]]) -> Optional[float]:
    if not pairs:
        return None
    total = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / total if total else None


def _subset_pct(runs: list[PastRun], keep) -> tuple[Optional[float], int]:
    pairs = []
    for index, run in enumerate(runs):
        pct = _finish_pct(run)
        if pct is not None and keep(run):
            pairs.append((pct, RECENCY_DECAY ** index))
    return _weighted_mean(pairs), len(pairs)


@dataclass(frozen=True)
class RunnerFeatures:
    number: int
    name: Optional[str]
    evidence_runs: int
    raw: dict[str, Optional[float]]
    evidence_counts: dict[str, int]
    rest_days: Optional[int]
    carried_weight_delta: Optional[float]


def extract_features(race: RaceRecord, runner: RunnerRecord) -> RunnerFeatures:
    runs = list(runner.past_runs[:MAX_RUNS])
    race_distance = race.distance.value if race.distance.present else None
    race_surface = race.surface.value if race.surface.present else None
    race_condition = race.condition.value if race.condition.present else None
    jockey = runner.jockey.value if runner.jockey.present else None

    form, form_n = _subset_pct(runs, lambda r: True)
    speed_pairs: list[tuple[float, float]] = []
    closing_pairs: list[tuple[float, float]] = []
    for index, run in enumerate(runs):
        weight = RECENCY_DECAY ** index
        behind = run.time_behind_winner.value
        if isinstance(behind, (int, float)) and behind >= 0:
            speed_pairs.append((float(behind), weight))
        corners = run.corner_positions
        field = run.field_size.value
        finish = run.finish.value
        if corners and isinstance(field, (int, float)) and field >= 2 \
                and isinstance(finish, (int, float)):
            last_corner_ratio = corners[-1] / field
            finish_ratio = finish / field
            closing_pairs.append((last_corner_ratio - finish_ratio, weight))
    speed = _weighted_mean(speed_pairs)
    closing = _weighted_mean(closing_pairs)

    distance, distance_n = _subset_pct(
        runs,
        lambda r: isinstance(race_distance, (int, float))
        and isinstance(r.distance.value, (int, float))
        and abs(r.distance.value - race_distance) <= 200,
    )
    track, track_n = _subset_pct(runs, lambda r: r.track.value == race.track)
    surface, surface_n = _subset_pct(
        runs, lambda r: race_surface is not None and r.surface.value == race_surface
    )
    condition, condition_n = _subset_pct(
        runs, lambda r: race_condition is not None and r.condition.value == race_condition
    )
    jockey_f, jockey_n = _subset_pct(
        runs, lambda r: jockey is not None and r.jockey.value == jockey
    )
    pcts = [p for p in (_finish_pct(r) for r in runs) if p is not None]
    consistency = None
    if len(pcts) >= 3:
        mean = sum(pcts) / len(pcts)
        consistency = max(0.0, 1.0 - sqrt(sum((p - mean) ** 2 for p in pcts) / len(pcts)))

    rest_days = None
    if runs:
        try:
            last = date_type.fromisoformat(runs[0].date)
            race_day = date_type.fromisoformat(race.date)
            rest_days = (race_day - last).days
        except ValueError:
            rest_days = None
    weight_delta = None
    if runs and runner.carried_weight.present \
            and isinstance(runs[0].carried_weight.value, (int, float)) \
            and isinstance(runner.carried_weight.value, (int, float)):
        weight_delta = float(runner.carried_weight.value) - float(runs[0].carried_weight.value)

    raw = {
        "form": form, "speed": speed, "distance": distance, "track": track,
        "surface": surface, "condition": condition, "jockey": jockey_f,
        "closing": closing, "consistency": consistency,
    }
    counts = {
        "form": form_n, "speed": len(speed_pairs), "distance": distance_n,
        "track": track_n, "surface": surface_n, "condition": condition_n,
        "jockey": jockey_n, "closing": len(closing_pairs),
        "consistency": len(pcts),
    }
    return RunnerFeatures(
        number=runner.number,
        name=runner.name.value if runner.name.present else None,
        evidence_runs=len(runs),
        raw=raw,
        evidence_counts=counts,
        rest_days=rest_days,
        carried_weight_delta=weight_delta,
    )


@dataclass(frozen=True)
class AbilityResult:
    number: int
    name: Optional[str]
    score: Optional[float]
    normalized: dict[str, Optional[float]]
    features: RunnerFeatures
    status: str


def _minmax(values: dict[int, float], lower_is_better: bool) -> dict[int, float]:
    if not values:
        return {}
    low, high = min(values.values()), max(values.values())
    if high == low:
        return {n: 0.5 for n in values}
    out = {}
    for n, v in values.items():
        scaled = (v - low) / (high - low)
        out[n] = 1.0 - scaled if lower_is_better else scaled
    return out


def analyze_race(
    race: RaceRecord,
    weights: Optional[dict[str, float]] = None,
) -> list[AbilityResult]:
    """Rank active runners of one race. Debut runners get no score.

    ``weights`` overrides the segment prior weights (used by offline
    fitting); feature availability and within-race normalization do
    not depend on the weights, only the combination does.
    """
    active = [r for r in race.active_runners]
    features = {r.number: extract_features(race, r) for r in active}
    if weights is None:
        weights = SEGMENT_WEIGHTS.get(race.segment, {})
    normalized_by_feature: dict[str, dict[int, float]] = {}
    for feature in weights:
        present = {
            n: f.raw[feature] for n, f in features.items() if f.raw.get(feature) is not None
        }
        normalized_by_feature[feature] = _minmax(present, feature in LOWER_IS_BETTER)

    results: list[AbilityResult] = []
    for number, feat in features.items():
        if race.segment is Segment.DEBUT or feat.evidence_runs == 0:
            results.append(AbilityResult(
                number, feat.name, None,
                {k: None for k in weights}, feat,
                "no-past-runs-debut" if race.segment is Segment.DEBUT
                else "insufficient-evidence",
            ))
            continue
        available = {
            k: normalized_by_feature[k][number]
            for k in weights if number in normalized_by_feature.get(k, {})
        }
        if len(available) < 3:
            results.append(AbilityResult(
                number, feat.name, None,
                {k: available.get(k) for k in weights}, feat,
                "insufficient-features",
            ))
            continue
        total_weight = sum(weights[k] for k in available)
        score = sum(available[k] * weights[k] for k in available) / total_weight
        results.append(AbilityResult(
            number, feat.name, round(score, 4),
            {k: (round(v, 4) if (v := available.get(k)) is not None else None)
             for k in weights},
            feat, "scored-prior-weights",
        ))
    results.sort(key=lambda r: (r.score is None, -(r.score or 0.0), r.number))
    return results
