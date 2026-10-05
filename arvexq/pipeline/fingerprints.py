from __future__ import annotations

import hashlib
import json
from typing import Any


_INACTIVE_STATUS_WORDS = (
    "出走取消",
    "競走取消",
    "取消",
    "競走除外",
    "除外",
    "欠場",
)


def is_inactive_horse(horse: dict[str, Any]) -> bool:
    status = str(horse.get("status") or "")
    return bool(
        horse.get("scratched")
        or horse.get("withdrawn")
        or any(word in status for word in _INACTIVE_STATUS_WORDS)
    )


def active_horses(detail: dict[str, Any]) -> list[dict[str, Any]]:
    horses = [
        h for h in (detail.get("horses") or [])
        if isinstance(h, dict) and int(h.get("horseNumber") or 0) > 0
    ]
    # Never fall back to inactive runners. A race with no active runners must stay
    # empty so scratched/withdrawn horses cannot leak into prediction inputs.
    return [h for h in horses if not is_inactive_horse(h)]


def analysis_input_hash(detail: dict[str, Any]) -> str:
    """Fingerprint only inputs that can change the ARVEXQ pre-race analysis."""
    horse_rows = []
    for horse in sorted(active_horses(detail), key=lambda h: int(h.get("horseNumber") or 999)):
        horse_rows.append({
            "horseNumber": horse.get("horseNumber"),
            "name": horse.get("name"),
            "sex": horse.get("sex"),
            "age": horse.get("age"),
            "carriedWeight": horse.get("carriedWeight") or horse.get("weight"),
            "jockey": horse.get("jockey"),
            "trainer": horse.get("trainer"),
            "bodyWeight": horse.get("bodyWeight"),
            "bodyWeightChange": horse.get("bodyWeightChange"),
            "status": horse.get("status"),
            "scratched": bool(horse.get("scratched")),
            "withdrawn": bool(horse.get("withdrawn")),
            "recentRaces": horse.get("recentRaces") or [],
            "allPastRuns": horse.get("allPastRuns") or [],
            "careerStats": horse.get("careerStats") or {},
            "integratedEvaluation": horse.get("integratedEvaluation") or {},
            "pedigree": horse.get("pedigree") or horse.get("bloodline") or {},
        })
    value = {
        "id": detail.get("id"),
        "track": detail.get("track"),
        "surface": detail.get("surface"),
        "distance": detail.get("distance"),
        "weather": detail.get("weather"),
        "condition": detail.get("condition"),
        "horses": horse_rows,
    }
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()
