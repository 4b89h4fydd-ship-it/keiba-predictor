from __future__ import annotations

from copy import deepcopy
from statistics import median
from typing import Any, Iterable

MODEL_VERSION = "arvexq-contextual-evidence-v1"


def _f(value: Any) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if x == x else None


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _med(values: Iterable[float | None]) -> float | None:
    vals = [float(v) for v in values if v is not None]
    return float(median(vals)) if vals else None


def _runs(horse: dict[str, Any]) -> list[dict[str, Any]]:
    rows = horse.get("allPastRuns") or horse.get("recentRaces") or []
    return [row for row in rows if isinstance(row, dict)]


def _finish_quality(run: dict[str, Any]) -> float | None:
    finish = _f(run.get("finish", run.get("finishPosition", run.get("rank"))))
    field = _f(run.get("fieldSize"))
    if finish is None or field is None or field < 2 or finish <= 0 or finish > field:
        return None
    return _clamp01(1.0 - (finish - 1.0) / (field - 1.0))


def _corner_values(run: dict[str, Any]) -> list[float]:
    raw = run.get("cornerPositions") or run.get("corners") or []
    if isinstance(raw, str):
        raw = raw.replace("→", "-").replace(",", "-").split("-")
    if not isinstance(raw, (list, tuple)):
        return []
    out: list[float] = []
    for value in raw:
        x = _f(value)
        if x is not None and x > 0:
            out.append(x)
    return out


def _last_corner_quality(run: dict[str, Any]) -> float | None:
    corners = _corner_values(run)
    field = _f(run.get("fieldSize"))
    if not corners or field is None or field < 2:
        return None
    pos = corners[-1]
    if pos > field:
        return None
    return _clamp01(1.0 - (pos - 1.0) / (field - 1.0))


def _first_corner_quality(run: dict[str, Any]) -> float | None:
    corners = _corner_values(run)
    field = _f(run.get("fieldSize"))
    if not corners or field is None or field < 2:
        return None
    pos = corners[0]
    if pos > field:
        return None
    return _clamp01(1.0 - (pos - 1.0) / (field - 1.0))


def _advance_score(run: dict[str, Any]) -> float | None:
    """Map position-to-finish gain to [0,1] without a learned or hand-weighted coefficient.

    0.5 = held position, >0.5 = advanced relative to field, <0.5 = lost position.
    The divisor is the field's full rank span, so it is determined by race geometry.
    """
    finish = _f(run.get("finish", run.get("finishPosition", run.get("rank"))))
    field = _f(run.get("fieldSize"))
    corners = _corner_values(run)
    if finish is None or field is None or field < 2 or not corners:
        return None
    last = corners[-1]
    if finish <= 0 or finish > field or last <= 0 or last > field:
        return None
    gain = (last - finish) / (field - 1.0)
    return _clamp01(0.5 + gain / 2.0)


def _position_stability(values: list[float]) -> float | None:
    if not values:
        return None
    center = float(median(values))
    mad = float(median(abs(v - center) for v in values))
    # For values bounded to [0,1], MAD cannot exceed 0.5 around a median.
    return _clamp01(1.0 - mad / 0.5)


def build_contextual_evidence(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    """Build objective pre-race context evidence from saved historical runs.

    This module deliberately does not manufacture pseudo-lap times, class ratings,
    bias scores or paddock scores when they are absent. It only derives signals whose
    inputs exist in the saved run itself: field size, finish and corner positions.
    Existing measured/researched audit values remain authoritative.
    """
    runs = _runs(horse)
    finish_q = [_finish_quality(r) for r in runs]
    last_q = [_last_corner_quality(r) for r in runs]
    first_q = [_first_corner_quality(r) for r in runs]
    advance = [_advance_score(r) for r in runs]

    valid_last = [v for v in last_q if v is not None]
    valid_first = [v for v in first_q if v is not None]
    valid_advance = [v for v in advance if v is not None]
    valid_finish = [v for v in finish_q if v is not None]

    pace_position = _med(valid_last)
    early_position = _med(valid_first)
    hidden_effort = _med(valid_advance)
    state_consistency = _position_stability(valid_last)

    # TRUE RUN fallback uses only two distinct observed families: actual finish quality
    # and position-to-finish gain. Equal-family median avoids an arbitrary percentage.
    true_run = _med([_med(valid_finish), hidden_effort])

    return {
        "modelVersion": MODEL_VERSION,
        "samples": len(runs),
        "finishSamples": len(valid_finish),
        "cornerSamples": len(valid_last),
        "advanceSamples": len(valid_advance),
        "trueRunFallback": true_run,
        "positionScenarioFallback": pace_position,
        "earlyPositionFallback": early_position,
        "stateConsistencyFallback": state_consistency,
        "hiddenEffortFallback": hidden_effort,
        "evidenceCoverage": (
            sum(v is not None for v in (true_run, pace_position, state_consistency, hidden_effort)) / 4.0
        ),
    }


def attach_contextual_evidence(detail: dict[str, Any], *, copy_detail: bool = False) -> dict[str, Any]:
    """Attach conservative fallbacks without overwriting measured legacy/research evidence."""
    if not isinstance(detail, dict):
        return detail
    out = deepcopy(detail) if copy_detail else detail
    attached = 0
    for horse in out.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        evidence = build_contextual_evidence(horse, out)
        horse["contextualEvidence"] = evidence
        ev = horse.setdefault("integratedEvaluation", {})
        audit = ev.get("v218Audit") or ev.get("v217Audit") or {}
        audit = dict(audit) if isinstance(audit, dict) else {}
        changed = False
        fallback_map = {
            "trueRun": "trueRunFallback",
            "positionScenario": "positionScenarioFallback",
            "stateConsistency": "stateConsistencyFallback",
            "hiddenEffort": "hiddenEffortFallback",
        }
        for target, source in fallback_map.items():
            if audit.get(target) is None and evidence.get(source) is not None:
                audit[target] = evidence[source]
                changed = True
        if changed:
            audit["contextFallbackVersion"] = MODEL_VERSION
            audit["contextFallbackOnly"] = True
            ev["v218Audit"] = audit
            attached += 1
    out["contextualEvidenceVersion"] = MODEL_VERSION
    out["contextualEvidenceAttachedHorses"] = attached
    return out
