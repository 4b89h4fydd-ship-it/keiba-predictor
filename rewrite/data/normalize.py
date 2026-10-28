"""Normalization of production-API payloads into rewrite records.

Rules enforced here:
- Unknown stays unknown: empty strings, the literal "不明", nulls and a
  zero ``updated_at`` become ``Obs(value=None, missing_reason=...)``.
  Nothing is filled with guesses.
- Leakage guard: a past run dated on/after the race date is rejected
  and counted, never silently used.
- Banei (帯広) is rejected at the door, like the safety contracts.
- Segment separation: JRA flat / NAR / debut / jumps are distinct.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from ..safety.contracts import Segment

UNKNOWN_LITERALS = {"", "不明", "未定", "-", "なし"}
BANEI_TRACKS = {"帯広", "帯広ば", "帯広ばんえい"}


@dataclass(frozen=True)
class Obs:
    """One field value with provenance and an explicit missing reason."""

    value: Any
    source: str
    missing_reason: Optional[str] = None

    @property
    def present(self) -> bool:
        return self.value is not None and self.missing_reason is None


def obs(value: Any, source: str) -> Obs:
    if value is None:
        return Obs(None, source, "null")
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in UNKNOWN_LITERALS:
            reason = "empty_string" if stripped == "" else f"unknown_literal:{stripped}"
            return Obs(None, source, reason)
        return Obs(stripped, source)
    return Obs(value, source)


def obs_timestamp(value: Any, source: str) -> Obs:
    if not value:
        return Obs(None, source, "zero_or_null_timestamp")
    try:
        return Obs(datetime.fromtimestamp(float(value), tz=timezone.utc), source)
    except (TypeError, ValueError, OSError):
        return Obs(None, source, "unparsable_timestamp")


@dataclass(frozen=True)
class PastRun:
    date: str
    track: Obs
    distance: Obs
    surface: Obs
    finish: Obs
    field_size: Obs
    corner_positions: tuple
    margin_text: Obs
    time_seconds: Obs
    jockey: Obs
    race_title: Obs = Obs(None, "normalize", "not_captured")
    condition: Obs = Obs(None, "normalize", "not_captured")
    weather: Obs = Obs(None, "normalize", "not_captured")
    time_behind_winner: Obs = Obs(None, "normalize", "not_captured")
    margin_seconds: Obs = Obs(None, "normalize", "not_captured")
    carried_weight: Obs = Obs(None, "normalize", "not_captured")


@dataclass(frozen=True)
class RunnerRecord:
    number: int
    horse_id: Obs
    name: Obs
    frame_number: Obs
    age: Obs
    sex: Obs
    jockey: Obs
    trainer: Obs
    carried_weight: Obs
    body_weight: Obs
    body_weight_change: Obs
    win_odds: Obs
    scratched: bool
    past_runs: tuple[PastRun, ...]
    rejected_future_runs: int = 0


@dataclass(frozen=True)
class RaceRecord:
    race_id: str
    date: str
    circuit: Obs
    track: str
    race_number: Obs
    title: Obs
    start_time: Obs
    distance: Obs
    surface: Obs
    weather: Obs
    condition: Obs
    updated_at: Obs
    segment: Segment
    source: str
    runners: tuple[RunnerRecord, ...] = field(default_factory=tuple)

    @property
    def active_runners(self) -> tuple[RunnerRecord, ...]:
        return tuple(r for r in self.runners if not r.scratched)


def _first(*values: Any) -> Any:
    """First non-None value; empty strings are data (missing) facts, kept."""
    for value in values:
        if value is not None:
            return value
    return None


def classify_segment(circuit: Optional[str], title: Optional[str]) -> Segment:
    text = title or ""
    if "障害" in text:
        return Segment.JUMPS
    if "新馬" in text or "初出走" in text:
        return Segment.DEBUT
    if circuit == "中央":
        return Segment.JRA_FLAT
    return Segment.NAR


def _past_run(row: dict, source: str) -> PastRun:
    corners = row.get("cornerPositions")
    corners = tuple(c for c in corners if isinstance(c, int)) if isinstance(corners, list) else ()
    return PastRun(
        date=str(row.get("date") or ""),
        track=obs(row.get("track"), source),
        distance=obs(row.get("distance"), source),
        surface=obs(row.get("surface"), source),
        finish=obs(row.get("finish"), source),
        field_size=obs(row.get("fieldSize"), source),
        corner_positions=corners,
        margin_text=obs(row.get("marginText"), source),
        time_seconds=obs(row.get("timeSeconds"), source),
        jockey=obs(row.get("jockey"), source),
        condition=obs(row.get("condition"), source),
        weather=obs(row.get("weather"), source),
        time_behind_winner=obs(row.get("timeBehindWinner"), source),
        margin_seconds=obs(row.get("marginSeconds"), source),
        carried_weight=obs(row.get("carriedWeight"), source),
        race_title=obs(row.get("title"), source),
    )


def normalize_runner(row: dict, race_date: str, source: str) -> RunnerRecord:
    raw_runs = row.get("allPastRuns") or row.get("recentRaces") or []
    kept: list[PastRun] = []
    rejected = 0
    for run in raw_runs:
        if not isinstance(run, dict):
            continue
        run_date = str(run.get("date") or "")
        if not run_date or run_date >= race_date:
            rejected += 1  # same-day/future information is not pre-race evidence
            continue
        kept.append(_past_run(run, source))
    kept.sort(key=lambda r: r.date, reverse=True)
    return RunnerRecord(
        number=int(row.get("horseNumber") or 0),
        horse_id=obs(row.get("id"), source),
        name=obs(row.get("name"), source),
        frame_number=obs(row.get("frameNumber"), source),
        age=obs(row.get("age"), source),
        sex=obs(row.get("sex"), source),
        jockey=obs(row.get("jockey"), source),
        trainer=obs(row.get("trainer"), source),
        carried_weight=obs(row.get("carriedWeight"), source),
        body_weight=obs(row.get("bodyWeight"), source),
        body_weight_change=obs(row.get("bodyWeightChange"), source),
        win_odds=obs(row.get("winOdds"), source),
        scratched=bool(row.get("scratched")),
        past_runs=tuple(kept),
        rejected_future_runs=rejected,
    )


def normalize_race(summary: dict, detail: Optional[dict], source: str) -> RaceRecord:
    """Build one normalized race from an /api/races row plus its detail."""
    track = str(summary.get("track") or (detail or {}).get("track") or "").strip()
    if track in BANEI_TRACKS:
        raise ValueError("banei excluded")
    date = str(summary.get("race_date") or summary.get("date") or (detail or {}).get("date") or "")
    circuit_raw = summary.get("circuit") or (detail or {}).get("circuit")
    title_raw = summary.get("title") or (detail or {}).get("title")
    runners: tuple[RunnerRecord, ...] = ()
    if detail:
        horses = detail.get("horses") or []
        runners = tuple(
            normalize_runner(h, date, source) for h in horses if isinstance(h, dict)
        )
        runners = tuple(sorted(runners, key=lambda r: r.number))
    return RaceRecord(
        race_id=str(summary.get("race_id") or summary.get("id") or (detail or {}).get("id") or ""),
        date=date,
        circuit=obs(circuit_raw, source),
        track=track,
        race_number=obs(summary.get("race_no") or summary.get("raceNumber"), source),
        title=obs(title_raw, source),
        start_time=obs(summary.get("start_time") or summary.get("startTime"), source),
        distance=obs(_first(summary.get("distance"), (detail or {}).get("distance")), source),
        surface=obs(_first(summary.get("surface"), (detail or {}).get("surface")), source),
        weather=obs(_first(summary.get("weather"), (detail or {}).get("weather")), source),
        condition=obs(_first(summary.get("condition"), (detail or {}).get("condition")), source),
        updated_at=obs_timestamp(summary.get("updated_at"), source),
        segment=classify_segment(
            circuit_raw if isinstance(circuit_raw, str) else None,
            title_raw if isinstance(title_raw, str) else None,
        ),
        source=source,
        runners=runners,
    )
