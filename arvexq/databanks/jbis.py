from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .registry import DataSource, SourceCapabilities


def build_jbis_source(
    *,
    horse_history: Callable[..., Any] | None = None,
    pedigree: Callable[..., Any] | None = None,
) -> DataSource:
    fetchers = {
        k: v
        for k, v in {
            "horse_history": horse_history,
            "pedigree": pedigree,
        }.items()
        if v is not None
    }
    return DataSource(
        name="jbis",
        circuit="both",
        priority=20,
        capabilities=SourceCapabilities(**{key: key in fetchers for key in SourceCapabilities.__dataclass_fields__}),
        fetchers=fetchers,
    )
