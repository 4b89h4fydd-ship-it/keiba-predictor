"""Evidence-only JRA debut/jump management boxes, not a prediction engine.

These annotations keep the two specialist populations separate. They do not
create marks, odds, historical predictions or inferred missing observations.
"""
from __future__ import annotations

import re
from typing import Any

from .debut import build_debut_box
from .jumps import build_jump_box

VERSION = "arvexq-special-race-boxes-v1"
_DEBUT = re.compile(r"新馬|メイクデビュー")
_JUMP = re.compile(r"障害|ジャンプ|(?:東京|京都|阪神|中山|新潟|福島|小倉)HJ|J[･・.]?G[ⅠⅡⅢ123]", re.I)


def special_race_type(detail: dict[str, Any]) -> str | None:
    """JRA only. Race title overrides an ambiguous flat-labelled jump surface."""
    if not isinstance(detail, dict) or str(detail.get("circuit") or "") not in ("中央", "JRA", "central"):
        return None
    title = str(detail.get("title") or detail.get("raceName") or "")
    mode = str(detail.get("analysisMode") or "")
    surface = str(detail.get("surface") or "")
    if mode == "障害" or "障" in surface or _JUMP.search(title):
        return "jumps"
    if mode == "新馬" or _DEBUT.search(title):
        return "debut"
    return None


def build_special_race_box(detail: dict[str, Any]) -> dict[str, Any] | None:
    family = special_race_type(detail)
    if family is None:
        return None
    box = build_debut_box(detail) if family == "debut" else build_jump_box(detail)
    return {
        "version": VERSION,
        "family": family,
        "raceId": str(detail.get("id") or ""),
        "date": str(detail.get("date") or ""),
        "scope": "JRA-specialist-evidence-only",
        "calibrated": False,
        "predictionApproved": False,
        **box,
    }
