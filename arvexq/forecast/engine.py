"""Production adapter for the independently separated Stage64 forecast.

Stage64 remains the only calculator.  This module only enforces the public
pre-off boundary and adapts the race-detail payload to its input contract.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from arvexq.research.stage64.pipeline import predict

VERSION = "arvexq-stage64-product-v1"
JST = ZoneInfo("Asia/Tokyo")


def _has_result_evidence(value):
    """Allow only empty, explicitly pending result placeholders before the off."""
    if not value:
        return False
    if not isinstance(value, dict):
        return True
    if set(value) - {"status", "finishers", "payouts"}:
        return True
    if value.get("finishers") or value.get("payouts"):
        return True
    return str(value.get("status") or "").strip() not in {"", "未確定", "未取得", "発走前", "未発走"}


def _preoff(facts, now):
    if not isinstance(facts, dict) or not isinstance(facts.get("date"), str):
        return False
    if _has_result_evidence(facts.get("result")) or str(facts.get("raceStatus") or "") in {"速報", "確定", "終了"}:
        return False
    start = facts.get("scheduledStartTime") or facts.get("startTime")
    if not isinstance(start, str) or len(start) < 5:
        return False
    try:
        scheduled = datetime.fromisoformat(f"{facts['date']}T{start[:5]}:00").replace(tzinfo=JST)
        current = now or datetime.now(JST)
        if current.tzinfo is None:
            current = current.replace(tzinfo=JST)
        else:
            current = current.astimezone(JST)
        return facts["date"] >= "2026-10-23" and current < scheduled
    except (TypeError, ValueError):
        return False


def build_prediction(facts, now=None):
    if not _preoff(facts, now):
        return None
    circuit = {"中央": "jra", "地方": "nar"}.get(facts.get("circuit"), facts.get("circuit"))
    if circuit not in {"jra", "nar"}:
        return None
    race = dict(facts)
    race["circuit"] = circuit
    # NAR snapshots may retain the same pre-off history under allPastRuns.
    # The display adapter already uses this alias; pass it to Stage64 without
    # modifying stored rows or changing the model / missing-data policy.
    if circuit == "nar" and isinstance(race.get("horses"), list):
        race["horses"] = [
            {**h, "recentRaces": h["allPastRuns"]}
            if isinstance(h, dict) and not h.get("recentRaces")
            and isinstance(h.get("allPastRuns"), list) and h["allPastRuns"]
            else h
            for h in race["horses"]
        ]
    try:
        result = predict(race, expected_circuit=circuit)
    except (KeyError, TypeError, ValueError):
        return None
    if result.get("blockers") or any(result["stages"][name]["value"] is None
                                     for name in ("ability", "runningStyle", "pace", "probability", "marks", "tickets")):
        return None
    result["stage64ModelVersion"] = result.get("modelVersion")
    result["modelVersion"] = VERSION
    result["productionEligible"] = True
    result["predictionStatus"] = "ready"
    return result
