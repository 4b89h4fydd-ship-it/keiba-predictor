from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SelectionPolicy:
    min_samples: int = 0
    min_honmei_win_rate: float | None = None
    min_roi: float | None = None
    allow_segments: set[str] | None = None


def qualifies(segment_stats: dict[str, Any], policy: SelectionPolicy) -> bool:
    samples = int(segment_stats.get("races") or segment_stats.get("samples") or 0)
    if samples < policy.min_samples:
        return False
    if policy.min_honmei_win_rate is not None:
        if float(segment_stats.get("honmeiWinRate") or 0.0) < policy.min_honmei_win_rate:
            return False
    if policy.min_roi is not None:
        if float(segment_stats.get("roi") or 0.0) < policy.min_roi:
            return False
    return True


def selected_reason(segment_stats: dict[str, Any], policy: SelectionPolicy) -> dict[str, Any]:
    return {
        "qualified": qualifies(segment_stats, policy),
        "samples": int(segment_stats.get("races") or segment_stats.get("samples") or 0),
        "honmeiWinRate": float(segment_stats.get("honmeiWinRate") or 0.0),
        "roi": float(segment_stats.get("roi") or 0.0),
    }
