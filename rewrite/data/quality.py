"""Field-level quality accounting for normalized races.

A race is eligible for prediction only when its identity, field and
per-runner evidence clear explicit gates. Missing data lowers coverage
numbers; it never gets silently patched.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .normalize import Obs, RaceRecord

RUNNER_FIELDS = (
    "name", "jockey", "trainer", "carried_weight", "body_weight", "win_odds",
)
RACE_FIELDS = ("circuit", "title", "start_time", "distance", "surface", "weather", "condition")


def _rate(present: int, total: int) -> float | None:
    return round(present / total, 4) if total else None


@dataclass(frozen=True)
class RaceQuality:
    race_id: str
    runners: int
    active_runners: int
    runners_with_past_runs: int
    field_coverage: dict
    race_field_coverage: dict
    eligible: bool
    blocking_reasons: tuple


def race_quality(race: RaceRecord) -> RaceQuality:
    active = race.active_runners
    coverage: dict[str, float | None] = {}
    for name in RUNNER_FIELDS:
        field_obs: list[Obs] = [getattr(r, name) for r in active]
        coverage[name] = _rate(sum(1 for o in field_obs if o.present), len(field_obs))
    race_coverage = {
        name: (1.0 if getattr(race, name).present else 0.0) for name in RACE_FIELDS
    }
    with_runs = sum(1 for r in active if r.past_runs)
    blocking: list[str] = []
    if len(active) < 2:
        blocking.append("fewer_than_2_active_runners")
    if not race.race_id or not race.date or not race.track:
        blocking.append("race_identity_incomplete")
    if active and with_runs == 0 and race.segment.value != "debut":
        blocking.append("no_runner_has_past_runs")
    unnamed = [r.number for r in active if not r.name.present]
    if unnamed:
        blocking.append(f"unnamed_runners:{unnamed}")
    return RaceQuality(
        race_id=race.race_id,
        runners=len(race.runners),
        active_runners=len(active),
        runners_with_past_runs=with_runs,
        field_coverage=coverage,
        race_field_coverage=race_coverage,
        eligible=not blocking,
        blocking_reasons=tuple(blocking),
    )


def day_quality(races: Iterable[RaceRecord]) -> dict:
    races = list(races)
    per_race = [race_quality(r) for r in races]
    total_runners = sum(q.active_runners for q in per_race)
    missing_rates: dict[str, float | None] = {}
    for name in RUNNER_FIELDS:
        present = 0
        for race in races:
            present += sum(1 for r in race.active_runners if getattr(r, name).present)
        missing_rates[name] = (
            round(1 - present / total_runners, 4) if total_runners else None
        )
    race_missing = {
        name: _rate(sum(1 for r in races if not getattr(r, name).present), len(races))
        for name in RACE_FIELDS
    }
    return {
        "races": len(races),
        "runners": total_runners,
        "eligible_races": sum(1 for q in per_race if q.eligible),
        "ineligible_races": [q.race_id for q in per_race if not q.eligible],
        "runner_field_missing_rate": missing_rates,
        "race_field_missing_rate": race_missing,
        "runners_with_past_runs": sum(q.runners_with_past_runs for q in per_race),
        "rejected_future_runs": sum(
            r.rejected_future_runs for race in races for r in race.runners
        ),
        "per_race": [q.__dict__ for q in per_race],
    }
