"""Bounded, redacted breakdown of oversized D1 race detail JSON.

Reports field names, byte lengths and multiplicity only. Never logs horse names,
full results, identifiers beyond the race ID already printed by sync, or payload.
No mutation; use this to distinguish redundant analysis from genuine career runs.
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Any


def encoded_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))


def summarize_detail(detail: dict[str, Any], *, limit: int = 8) -> dict[str, Any]:
    if not isinstance(detail, dict):
        raise ValueError("detail must be dict")
    top: Counter[str] = Counter()
    for key, value in detail.items():
        if key == "horses":
            continue
        top[key] += encoded_size(value)
    horse_totals: Counter[str] = Counter()
    horses = [h for h in detail.get("horses") or [] if isinstance(h, dict)]
    for horse in horses:
        for key, value in horse.items():
            horse_totals[key] += encoded_size(value)
    return {
        "totalBytes": encoded_size(detail),
        "horses": len(horses),
        "topFields": top.most_common(limit),
        "horseFields": horse_totals.most_common(limit),
        "historyArchiveBytes": horse_totals.get("careerArchive", 0),
        "allPastRunsBytes": horse_totals.get("allPastRuns", 0),
        "recentRacesBytes": horse_totals.get("recentRaces", 0),
        "analysisBytes": sum(v for k, v in horse_totals.items()
                             if k in ("integratedEvaluation", "analysis", "allHorseDiagnostics",
                                      "precomputedMetrics", "pastPerformance", "careerProfile")),
    }


def print_size_audit(detail: dict[str, Any], *, max_detail_bytes: int = 1_500_000) -> dict[str, Any]:
    audit = summarize_detail(detail)
    if audit["totalBytes"] >= max_detail_bytes:
        # Do not print horse names, raw payload values, or URLs.
        race = str(detail.get("id") or "")[:100].replace("\n", "")
        print("D1_DETAIL_SIZE_BREAKDOWN",
              "race="+race,
              "total="+str(audit["totalBytes"]),
              "horses="+str(audit["horses"]),
              "archive="+str(audit["historyArchiveBytes"]),
              "allPastRuns="+str(audit["allPastRunsBytes"]),
              "recentRaces="+str(audit["recentRacesBytes"]),
              "analysis="+str(audit["analysisBytes"]),
              "top="+str(audit["topFields"]),
              "horsesTop="+str(audit["horseFields"]))
    return audit
