"""Four-stage pace (展開) forecasting with pace scenarios.

Stage mapping from a past run's corner positions (recorded in running
order): start -> first corner, 3C -> the third-corner entry (index 2
when four corners are recorded, otherwise the last-but-one), 4C -> last
corner, straight -> historical finish ratio blended with the 4C
position and adjusted by the scenario's pace pressure.

The forecast is per race and per horse, derived only from that horse's
own recorded positions — never a shared generic text. Horses without
corner evidence are reported as unknown, not placed by guesswork.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..data.normalize import RaceRecord, RunnerRecord

STAGES = ("start", "corner3", "corner4", "straight")
FRONT_RATIO = 0.35


@dataclass(frozen=True)
class StyleProfile:
    number: int
    name: Optional[str]
    start_ratio: Optional[float]
    corner3_ratio: Optional[float]
    corner4_ratio: Optional[float]
    finish_ratio: Optional[float]
    closing_gain: Optional[float]
    basis_runs: int


def _mean(values: list[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def style_profile(runner: RunnerRecord) -> StyleProfile:
    starts, c3s, c4s, finishes, closings = [], [], [], [], []
    for run in runner.past_runs:
        field = run.field_size.value
        finish = run.finish.value
        corners = run.corner_positions
        if not isinstance(field, (int, float)) or field < 2:
            continue
        if corners:
            starts.append(corners[0] / field)
            if len(corners) >= 3:
                c3s.append(corners[2] / field)
            elif len(corners) == 2:
                c3s.append(corners[1] / field)
            c4s.append(corners[-1] / field)
            if isinstance(finish, (int, float)):
                closings.append(corners[-1] / field - finish / field)
        if isinstance(finish, (int, float)):
            finishes.append(finish / field)
    return StyleProfile(
        number=runner.number,
        name=runner.name.value if runner.name.present else None,
        start_ratio=_mean(starts),
        corner3_ratio=_mean(c3s),
        corner4_ratio=_mean(c4s),
        finish_ratio=_mean(finishes),
        closing_gain=_mean(closings),
        basis_runs=len(starts),
    )


@dataclass(frozen=True)
class StageOrder:
    stage: str
    order: tuple  # tuple[tuple[number, ratio|None], ...] front to back


@dataclass(frozen=True)
class PaceForecast:
    race_id: str
    field_size: int
    front_runners: tuple
    pace_pressure: float
    pace_label: str
    stages: dict  # normal scenario: stage -> StageOrder
    scenarios: dict  # name -> {"straight_order": StageOrder, "note": str}
    unknown_runners: tuple


def _order(profiles: list[StyleProfile], key) -> tuple:
    known = sorted((p for p in profiles if key(p) is not None),
                   key=lambda p: (key(p), p.number))
    return tuple((p.number, round(key(p), 3)) for p in known)


def forecast_pace(race: RaceRecord) -> PaceForecast:
    active = list(race.active_runners)
    profiles = [style_profile(r) for r in active]
    known = [p for p in profiles if p.start_ratio is not None]
    unknown = tuple(p.number for p in profiles if p.start_ratio is None)
    front = tuple(p.number for p in known if p.start_ratio <= FRONT_RATIO)
    pressure = len(front) / len(known) if known else 0.0
    if len(front) >= 3:
        label = "ハイペース想定"
    elif len(front) <= 1:
        label = "スローペース想定"
    else:
        label = "平均ペース想定"

    def straight_ratio(p: StyleProfile, scenario: str) -> Optional[float]:
        if p.corner4_ratio is None or p.finish_ratio is None:
            return None
        base = 0.6 * p.corner4_ratio + 0.4 * p.finish_ratio
        is_front = p.start_ratio is not None and p.start_ratio <= FRONT_RATIO
        closing = p.closing_gain or 0.0
        if scenario == "fast":
            if is_front:
                base += 0.10 * pressure * 2
            if closing > 0.05:
                base -= 0.08
        elif scenario == "slow":
            if is_front and len(front) <= 1:
                base -= 0.06
            if closing > 0.05:
                base += 0.05
        return base

    stages = {
        "start": StageOrder("start", _order(known, lambda p: p.start_ratio)),
        "corner3": StageOrder("corner3", _order(known, lambda p: p.corner3_ratio)),
        "corner4": StageOrder("corner4", _order(known, lambda p: p.corner4_ratio)),
        "straight": StageOrder(
            "straight", _order(known, lambda p: straight_ratio(p, "normal"))
        ),
    }
    scenarios = {
        name: {
            "straight_order": StageOrder(
                "straight", _order(known, lambda p, s=name: straight_ratio(p, s))
            ),
            "front_runners": front,
            "pace_pressure": round(pressure, 3),
        }
        for name in ("normal", "fast", "slow")
    }
    return PaceForecast(
        race_id=race.race_id,
        field_size=len(active),
        front_runners=front,
        pace_pressure=round(pressure, 3),
        pace_label=label,
        stages=stages,
        scenarios=scenarios,
        unknown_runners=unknown,
    )
