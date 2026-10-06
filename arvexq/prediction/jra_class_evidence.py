from __future__ import annotations

import re
from typing import Any

MODEL_VERSION = "arvexq-jra-class-evidence-v1"

# Ordered only. The absolute gaps are intentionally meaningless; the four-pillar
# engine converts these values to within-race relative ranks before comparison.
_CLASS_PATTERNS: tuple[tuple[int, re.Pattern[str]], ...] = (
    (9, re.compile(r"(?:G\s*1|GⅠ|GI)(?!I)", re.I)),
    (8, re.compile(r"(?:G\s*2|GⅡ|GII)(?!I)", re.I)),
    (7, re.compile(r"(?:G\s*3|GⅢ|GIII)", re.I)),
    (6, re.compile(r"(?:リステッド|Listed|\bL\b)", re.I)),
    (5, re.compile(r"(?:オープン|\bOP\b)", re.I)),
    (4, re.compile(r"3\s*勝")),
    (3, re.compile(r"2\s*勝")),
    (2, re.compile(r"1\s*勝")),
    (1, re.compile(r"(?:未勝利|新馬)")),
)


def class_ordinal(title: Any) -> int | None:
    text = str(title or "").strip()
    if not text:
        return None
    for ordinal, pattern in _CLASS_PATTERNS:
        if pattern.search(text):
            return ordinal
    return None


def attach_jra_class_evidence(detail: dict[str, Any]) -> int:
    """Attach source-backed class order to missing historical opponentLevel fields.

    This does not create a weighted score and does not touch non-JRA races. The
    ordinal is only meaningful by ordering; production factor_model later converts
    it to race-relative rank percentiles.
    """
    if not isinstance(detail, dict) or str(detail.get("circuit") or "") != "中央":
        return 0
    attached = 0
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        rows = horse.get("recentRaces") or horse.get("allPastRuns") or []
        for run in rows:
            if not isinstance(run, dict):
                continue
            if run.get("opponentLevel") not in (None, "", 0, 0.0):
                continue
            ordinal = class_ordinal(run.get("title") or run.get("raceName"))
            if ordinal is None:
                continue
            run["opponentLevel"] = ordinal
            run["opponentLevelSource"] = MODEL_VERSION
            attached += 1
    return attached
