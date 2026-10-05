from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

Fetcher = Callable[..., Any]


@dataclass(slots=True)
class SourceCapabilities:
    schedule: bool = False
    race_detail: bool = False
    horse_history: bool = False
    odds: bool = False
    results: bool = False
    payouts: bool = False
    track_weather: bool = False
    body_weight: bool = False
    scratches: bool = False
    jockey_trainer: bool = False
    pedigree: bool = False


@dataclass(slots=True)
class DataSource:
    name: str
    circuit: str
    priority: int
    capabilities: SourceCapabilities
    fetchers: dict[str, Fetcher] = field(default_factory=dict)

    def supports(self, domain: str) -> bool:
        return bool(getattr(self.capabilities, domain, False)) and domain in self.fetchers


class DataBankRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, DataSource] = {}

    def register(self, source: DataSource) -> None:
        self._sources[source.name] = source

    def get(self, name: str) -> DataSource | None:
        return self._sources.get(name)

    def providers(self, domain: str, *, circuit: str | None = None) -> list[DataSource]:
        rows = [s for s in self._sources.values() if s.supports(domain)]
        if circuit:
            rows = [s for s in rows if s.circuit in {circuit, "both"}]
        return sorted(rows, key=lambda s: (s.priority, s.name))

    def names(self) -> list[str]:
        return sorted(self._sources)

    def capability_map(self) -> dict[str, list[str]]:
        domains = SourceCapabilities.__dataclass_fields__.keys()
        return {domain: [s.name for s in self.providers(domain)] for domain in domains}


registry = DataBankRegistry()
