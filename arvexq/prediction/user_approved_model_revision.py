"""One-time user-approved update to past-five model marks, not an official course report.

Applies to October 9, 2026 only, on or after the explicit approval time and
strictly before each off. The immutable original and any ticket already sealed
are never changed. Revisions use a distinct provenance namespace.
"""
from __future__ import annotations

import copy
import json
import subprocess
from datetime import datetime
from typing import Any, Callable

from arvexq.prediction.prerace_archive import JST, post_at, sealed_lock

REVISION_VERSION = "arvexq-user-model-mark-revision-v1"
APPROVAL_ID = "user-approved-past-five-from-2026-10-09-20-10-jst"
SWITCH_DATE = "2026-10-09"
SWITCH_TIME = datetime.fromisoformat("2026-10-09T20:10:00+09:00")
MODEL = "arvexq-axis-reliability-v2-past-context"
VALID_MARKS = {"", "◎", "○", "▲", "☆+", "☆", "△", "注"}


def enabled(now: datetime) -> bool:
    return bool(now.tzinfo and now.astimezone(JST) >= SWITCH_TIME
                and now.astimezone(JST).date().isoformat() == SWITCH_DATE)


def valid_revision(detail: dict[str, Any], candidate: Any) -> bool:
    if not isinstance(candidate, dict) or candidate.get("version") != REVISION_VERSION:
        return False
    if candidate.get("approvalId") != APPROVAL_ID or candidate.get("modelVersion") != MODEL:
        return False
    if str(detail.get("date") or "") != SWITCH_DATE or str(candidate.get("raceId") or "") != str(detail.get("id") or ""):
        return False
    if str(candidate.get("raceDate") or "") != SWITCH_DATE:
        return False
    try:
        at = datetime.fromisoformat(str(candidate["revisedAt"]).replace("Z", "+00:00"))
        fixed = datetime.fromisoformat(str(detail["morningMarkSnapshot"]["fixedAt"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return False
    post = post_at(detail)
    if (not post or at.tzinfo is None or fixed.tzinfo is None
            or not (SWITCH_TIME <= at.astimezone(JST) < post)
            or fixed >= at):
        return False
    snap = detail.get("morningMarkSnapshot") or {}
    if (snap.get("version") != "arvexq-morning-marks-v1"
            or str(snap.get("raceId") or "") != str(detail.get("id") or "")):
        return False
    horses = candidate.get("horses")
    if not isinstance(horses, list) or len(horses) < 3:
        return False
    original = snap.get("horses") or []
    original_nos = {int(x.get("horseNumber") or 0) for x in original if isinstance(x, dict)}
    seen: set[int] = set()
    for h in horses:
        if not isinstance(h, dict):
            return False
        try:
            no = int(h.get("horseNumber") or 0)
        except (TypeError, ValueError):
            return False
        if no < 1 or no in seen or str(h.get("mark") or "") not in VALID_MARKS:
            return False
        seen.add(no)
    return bool(original_nos and original_nos == seen)


def update_marks(detail: dict[str, Any], *, now: datetime,
                 calculate: Callable[[dict[str, Any]], list[dict[str, Any]]] | None = None
                 ) -> tuple[dict[str, Any], str]:
    """Compute once if still pre-off and neither forecast nor ticket is sealed."""
    output = copy.deepcopy(detail)
    if not enabled(now) or str(detail.get("date") or "") != SWITCH_DATE:
        return output, "outside-approval-window"
    post = post_at(detail)
    if not post or now.astimezone(JST) >= post:
        return output, "already-started"
    if sealed_lock(detail) or isinstance(detail.get("preRaceBet"), dict) and detail["preRaceBet"].get("fixedAt"):
        return output, "already-sealed-no-changes"
    original = detail.get("morningMarkSnapshot") or {}
    if original.get("version") != "arvexq-morning-marks-v1":
        return output, "original-not-available"
    previous = list(detail.get("modelMarkRevisions") or [])
    if any(isinstance(x, dict) and x.get("approvalId") == APPROVAL_ID for x in previous):
        return output, "already-revised"
    if calculate is None:
        def calculate(d: dict[str, Any]) -> list[dict[str, Any]]:
            p = subprocess.run(["node", "scripts/arvexq_capture_course_revised_marks.js"],
                               input=json.dumps(d, ensure_ascii=False), text=True,
                               capture_output=True, timeout=22, check=True)
            result = json.loads(p.stdout)
            return result["horses"]
    try:
        marks = calculate(output)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError,
            json.JSONDecodeError) as exc:
        return output, "compute-failed:" + type(exc).__name__
    candidate = {
        "version": REVISION_VERSION, "approvalId": APPROVAL_ID,
        "modelVersion": MODEL, "raceId": str(detail.get("id") or ""),
        "raceDate": SWITCH_DATE, "revisedAt": now.isoformat(timespec="seconds"),
        "reason": "ユーザー承認：過去5走の分析方式へ更新（公式馬場変更ではない）",
        "source": "explicit-user-request", "horses": marks,
    }
    if not valid_revision(detail, candidate):
        return output, "invalid-preoff-revision"
    old_marks = {int(x["horseNumber"]): str(x.get("mark") or "") for x in original["horses"]}
    new_marks = {int(x["horseNumber"]): str(x.get("mark") or "") for x in marks}
    affected = sorted(no for no in new_marks if new_marks[no] != old_marks.get(no, ""))
    if not affected:
        return output, "no-mark-change"
    candidate["affectedHorseNumbers"] = affected
    output["modelMarkRevisions"] = previous + [candidate]
    return output, "changed:" + ",".join(map(str, affected))
