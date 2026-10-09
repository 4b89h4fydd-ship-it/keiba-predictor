"""Only evaluate the original pre-off immutable research-factor challenger."""
from __future__ import annotations

import hashlib
import json
from typing import Any
from arvexq.prediction.prerace_archive import sealed_lock
from arvexq.prediction.factor_challenger import VERSION


def evaluate(detail: dict[str, Any]) -> dict[str, Any] | None:
    if sealed_lock(detail) is None:
        return None
    model = detail.get("researchFactorShadow")
    if not isinstance(model, dict) or model.get("version") != VERSION:
        return None
    source = {k: v for k, v in model.items() if k != "hash"}
    digest = hashlib.sha256(json.dumps(source, sort_keys=True,
                     ensure_ascii=False, separators=(",", ":"), default=str).encode()).hexdigest()
    if model.get("hash") != digest or model.get("raceId") != str(detail.get("id") or ""):
        return None
    if not model.get("sufficient") or not model.get("candidateWinner"):
        return None
    result = detail.get("result") or {}
    if str(result.get("status") or "") != "確定":
        return None
    order = []
    for item in result.get("finishers") or []:
        if not isinstance(item, dict):
            continue
        try:
            finish, no = int(item.get("finish")), int(item.get("horseNumber"))
        except (TypeError, ValueError):
            continue
        if finish > 0 and no > 0:
            order.append((finish, no))
    order.sort()
    if len(order) < 3 or [x[0] for x in order[:3]] != [1, 2, 3]:
        return None
    actual = [no for _, no in order[:3]]
    winner = int(model["candidateWinner"])
    top3 = [int(x) for x in model["candidateTop3"]]
    baseline = sealed_lock(detail).get("winnerNo")
    try:
        baseline = int(baseline) if baseline is not None else None
    except (TypeError, ValueError):
        baseline = None
    return {"version": VERSION, "raceId": model["raceId"], "actual": actual,
            "shadowWinner": winner, "shadowWinnerHit": winner == actual[0],
            "shadowTopThreeCoverage": len(set(top3).intersection(actual)),
            "baselineWinner": baseline,
            "baselineWinnerHit": baseline == actual[0] if baseline else None,
            "storedShadowHash": model["hash"], "usedPostoffRecalculation": False}


def aggregate(reports: list[dict[str, Any]]) -> dict[str, Any]:
    unique = {str(x["raceId"]): x for x in reports if isinstance(x, dict)
              and x.get("version") == VERSION and x.get("raceId")}
    n = len(unique)
    both = [x for x in unique.values() if x.get("baselineWinnerHit") is not None]
    return {"version": "arvexq-14-factor-shadow-performance-v1",
            "raceCount": n,
            "shadowWinHitRate": sum(bool(x["shadowWinnerHit"]) for x in unique.values()) / n if n else None,
            "shadowAverageTop3Coverage": sum(x["shadowTopThreeCoverage"] for x in unique.values()) / n if n else None,
            "baselineComparedRaces": len(both),
            "baselineWinHitRate": sum(bool(x["baselineWinnerHit"]) for x in both) / len(both) if both else None,
            "researchOnly": True,
            "notProductionReady": n < 100 or len(both) < 100}
