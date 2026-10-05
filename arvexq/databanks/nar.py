from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .registry import DataSource, SourceCapabilities


def build_nar_source(
    *,
    schedule: Callable[..., Any] | None = None,
    race_detail: Callable[..., Any] | None = None,
    horse_history: Callable[..., Any] | None = None,
    odds: Callable[..., Any] | None = None,
    results: Callable[..., Any] | None = None,
    payouts: Callable[..., Any] | None = None,
    track_weather: Callable[..., Any] | None = None,
    body_weight: Callable[..., Any] | None = None,
    scratches: Callable[..., Any] | None = None,
    jockey_trainer: Callable[..., Any] | None = None,
) -> DataSource:
    fetchers = {
        key: value
        for key, value in {
            "schedule": schedule,
            "race_detail": race_detail,
            "horse_history": horse_history,
            "odds": odds,
            "results": results,
            "payouts": payouts,
            "track_weather": track_weather,
            "body_weight": body_weight,
            "scratches": scratches,
            "jockey_trainer": jockey_trainer,
        }.items()
        if value is not None
    }
    return DataSource(
        name="nar_official",
        circuit="NAR",
        priority=10,
        capabilities=SourceCapabilities(**{key: key in fetchers for key in SourceCapabilities.__dataclass_fields__}),
        fetchers=fetchers,
    )
