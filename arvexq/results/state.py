from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any

JST = timezone(timedelta(hours=9))
TERMINAL_NO_PAYOUT = {"中止", "取止", "取消", "不成立"}


def start_minutes(row: dict[str, Any]) -> int:
    raw = str(row.get("startTime") or row.get("scheduledStartTime") or "")
    try:
        hh, mm = raw.split(":", 1)
        return int(hh) * 60 + int(mm[:2])
    except Exception:
        return 9999


def row_date(row: dict[str, Any]) -> str:
    return str(row.get("date") or row.get("race_date") or row.get("raceDate") or "")


def podium_final(result: Any) -> bool:
    """Accept normal and dead-heat podiums once the source marks them final."""
    if not isinstance(result, dict) or str(result.get("status") or "") != "確定":
        return False
    finishes: list[int] = []
    for row in result.get("finishers") or []:
        if not isinstance(row, dict):
            continue
        try:
            finish = int(row.get("finish") or 0)
        except Exception:
            finish = 0
        if finish > 0:
            finishes.append(finish)
    return 1 in finishes and sum(1 for finish in finishes if finish <= 3) >= 3


def result_state(detail: dict[str, Any] | None) -> tuple[bool, bool, str]:
    d = detail if isinstance(detail, dict) else {}
    result = d.get("result") if isinstance(d.get("result"), dict) else {}
    status = str(result.get("status") or "")
    if status in TERMINAL_NO_PAYOUT:
        return True, True, status
    payouts = result.get("payouts") if isinstance(result.get("payouts"), list) else []
    return podium_final(result), bool(payouts), status


def started(summary: dict[str, Any], now: datetime) -> bool:
    race_date = row_date(summary)
    today = now.strftime("%Y-%m-%d")
    if race_date:
        if race_date < today:
            return True
        if race_date > today:
            return False
    sm = start_minutes(summary)
    now_minutes = now.hour * 60 + now.minute
    return sm < 9999 and now_minutes >= sm + 2


def merge_result(old: Any, new: Any) -> dict[str, Any]:
    old_r = copy.deepcopy(old) if isinstance(old, dict) else {}
    new_r = new if isinstance(new, dict) else {}
    if not new_r:
        return old_r
    old_final = podium_final(old_r)
    new_final = podium_final(new_r)
    out = old_r
    for key, value in new_r.items():
        if value in (None, "", [], {}):
            continue
        if old_final and not new_final and key in {"status", "finishers"}:
            continue
        out[key] = copy.deepcopy(value)
    return out


def merge_detail(old: dict[str, Any] | None, new: dict[str, Any] | None) -> dict[str, Any]:
    """Merge refreshed result data without degrading a precomputed rich card."""
    if not old:
        return copy.deepcopy(new or {})
    if not new:
        return copy.deepcopy(old)

    out = copy.deepcopy(old)
    protected = {
        "horses",
        "preparedMeta",
        "preRacePrediction",
        "predictionAudit",
        "aiEvaluation",
        "pace",
        "pacePrediction",
        "volatility",
    }
    for key, value in new.items():
        if key in protected or key == "result":
            continue
        if value not in (None, "", [], {}):
            out[key] = copy.deepcopy(value)

    if isinstance(new.get("result"), dict) and new.get("result"):
        out["result"] = merge_result(old.get("result"), new.get("result"))

    for key in protected:
        if key in old:
            out[key] = copy.deepcopy(old[key])
    return out
