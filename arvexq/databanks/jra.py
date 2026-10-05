from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .registry import DataSource, SourceCapabilities


def build_jra_source(
    *,
    racecard: Callable[..., Any] | None = None,
    horse_history: Callable[..., Any] | None = None,
    odds: Callable[..., Any] | None = None,
    results: Callable[..., Any] | None = None,
    track_weather: Callable[..., Any] | None = None,
    jockey_trainer: Callable[..., Any] | None = None,
) -> DataSource:
    fetchers = {
        k: v
        for k, v in {
            "racecard": racecard,
            "horse_history": horse_history,
            "odds": odds,
            "results": results,
            "track_weather": track_weather,
            "jockey_trainer": jockey_trainer,
        }.items()
        if v is not None
    }
    return DataSource(
        name="jra_official",
        circuit="JRA",
        priority=10,
        capabilities=SourceCapabilities(**{key: key in fetchers for key in SourceCapabilities.__dataclass_fields__}),
        fetchers=fetchers,
    )
