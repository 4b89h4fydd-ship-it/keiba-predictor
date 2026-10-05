from __future__ import annotations

from typing import Any

from arvexq.core.runner_status import normalize_runner_status
from arvexq.prediction.ability import apply_ability_ranking


def normalize_race_detail(detail: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(detail, dict):
        return detail
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        horse["status"] = normalize_runner_status(
            horse.get("status"),
            scratched=bool(horse.get("scratched")),
            withdrawn=bool(horse.get("withdrawn")),
        )
    return detail


def prepare_race_detail(detail: dict[str, Any]) -> dict[str, Any]:
    """Stable orchestration boundary used by app/API code.

    Keep source acquisition, normalization, feature building and prediction internals
    behind this service so app.py does not need to know their implementation details.
    """
    detail = normalize_race_detail(detail)
    detail = apply_ability_ranking(detail)
    return detail
