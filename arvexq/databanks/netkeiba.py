from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .registry import DataSource, SourceCapabilities


def build_netkeiba_source(
    *,
    odds: Callable[..., Any] | None = None,
    results: Callable[..., Any] | None = None,
    track_weather: Callable[..., Any] | None = None,
) -> DataSource:
    fetchers = {
        key: value
        for key, value in {
            "odds": odds,
            "results": results,
            "track_weather": track_weather,
        }.items()
        if value is not None
    }
    return DataSource(
        name="netkeiba_supplemental",
        circuit="JRA",
        priority=50,
        capabilities=SourceCapabilities(**{key: key in fetchers for key in SourceCapabilities.__dataclass_fields__}),
        fetchers=fetchers,
    )
