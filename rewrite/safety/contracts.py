"""Strict pre-race input contract; unknown values remain unknown."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite


class Segment(str, Enum):
    JRA_FLAT = 'jra_flat'
    NAR = 'nar'
    DEBUT = 'debut'
    JUMPS = 'jumps'


def aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('timezone required')


@dataclass(frozen=True)
class Observation:
    source: str
    observed_at: datetime
    available_at: datetime
    value: float | str | None
    missing_reason: str | None = None

    def validate(self, cutoff: datetime) -> None:
        for value in (self.observed_at, self.available_at, cutoff):
            aware(value)
        if not self.source.strip():
            raise ValueError('source required')
        if self.observed_at > cutoff or self.available_at > cutoff:
            raise ValueError('future information')
        if self.value is None and not self.missing_reason:
            raise ValueError('missing reason required')
        if self.value is not None and self.missing_reason:
            raise ValueError('present value marked missing')
        if isinstance(self.value, (float, int)) and not isfinite(self.value):
            raise ValueError('nonfinite observation')


@dataclass(frozen=True)
class Runner:
    horse_id: str
    number: int
    name: str
    cancelled: bool
    evidence: tuple[Observation, ...]


@dataclass(frozen=True)
class RaceCard:
    race_id: str
    venue: str
    segment: Segment
    starts_at: datetime
    cutoff: datetime
    declared_count: int
    runners: tuple[Runner, ...]

    def validate(self) -> None:
        aware(self.starts_at)
        aware(self.cutoff)
        if self.cutoff >= self.starts_at:
            raise ValueError('not a pre-race card')
        if self.venue.strip().casefold() in {'帯広', '帯広ば', '帯広ばんえい', 'obihiro', 'banei'}:
            raise ValueError('excluded venue')
        if not self.race_id.strip() or not self.venue.strip():
            raise ValueError('race identity required')
        if not isinstance(self.segment, Segment):
            raise ValueError('unknown model segment')
        if self.declared_count != len(self.runners) or self.declared_count < 2:
            raise ValueError('incomplete field')
        if len({r.horse_id for r in self.runners}) != len(self.runners):
            raise ValueError('duplicate horse')
        if len({r.number for r in self.runners}) != len(self.runners):
            raise ValueError('duplicate number')
        for runner in self.runners:
            if not runner.horse_id.strip() or not runner.name.strip() or runner.number < 1:
                raise ValueError('runner identity required')
            if not runner.evidence:
                raise ValueError('runner evidence absent')
            for observation in runner.evidence:
                observation.validate(self.cutoff)
        if sum(not r.cancelled for r in self.runners) < 2:
            raise ValueError('insufficient active runners')
