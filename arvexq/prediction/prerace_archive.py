"""Immutable, provenance-checked pre-race forecast archive.

Never create a forecast once a race has begun.  Absence of a timely snapshot is
an explicit missing state, not permission to reconstruct from results.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

JST = timezone(timedelta(hours=9))
MARKS = {"◎", "○", "▲", "☆+", "☆", "△", "注", ""}
SEALED_VERSION = "arvexq-server-prerace-seal-v1"


def post_at(detail: dict[str, Any]) -> datetime | None:
    date = str(detail.get("date") or "")
    clock = str(detail.get("startTime") or detail.get("scheduledStartTime") or "")[:5]
    try:
        return datetime.strptime(date + " " + clock, "%Y-%m-%d %H:%M").replace(tzinfo=JST)
    except (TypeError, ValueError):
        return None


def pre_off(lock: Any, detail: dict[str, Any]) -> bool:
    post = post_at(detail)
    if not isinstance(lock, dict) or not post:
        return False
    if str(lock.get("raceId") or "") != str(detail.get("id") or ""):
        return False
    if str(lock.get("raceDate") or "") != str(detail.get("date") or ""):
        return False
    try:
        captured = int(lock.get("capturedAtEpoch") or 0)
    except (ValueError, TypeError):
        return False
    if captured <= 0 or captured >= int(post.timestamp()):
        return False
    rows = lock.get("horses")
    if not isinstance(rows, list) or len(rows) < 2:
        return False
    nos: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            return False
        try:
            no = int(row.get("horseNumber") or 0)
        except (ValueError, TypeError):
            return False
        if no <= 0 or no in nos or str(row.get("mark") or "") not in MARKS:
            return False
        nos.add(no)
    return True


def sealed_lock(detail: dict[str, Any]) -> dict[str, Any] | None:
    lock = detail.get("preRacePrediction")
    if pre_off(lock, detail) and lock.get("frozen"):
        return lock
    return None


def restore_seal(existing: dict[str, Any] | None, updated: dict[str, Any] | None) -> dict[str, Any]:
    """Keep the first sealed pre-race forecast even across later updates."""
    out = copy.deepcopy(updated) if isinstance(updated, dict) else {}
    old = existing if isinstance(existing, dict) else {}
    old_lock = sealed_lock(old)
    if not old_lock:
        return out
    if str(old.get("id") or "") != str(out.get("id") or ""):
        return out
    out["preRacePrediction"] = copy.deepcopy(old_lock)
    if isinstance(old.get("preRaceBet"), dict):
        out["preRaceBet"] = copy.deepcopy(old["preRaceBet"])
    pm = dict(out.get("preparedMeta") or {})
    old_pm = old.get("preparedMeta") or {}
    for name in ("preRaceSealEpoch", "preRaceSealRevision", "preRaceSealVersion"):
        if name in old_pm:
            pm[name] = old_pm[name]
    out["preparedMeta"] = pm
    return out


def seal_detail(detail: dict[str, Any], lock: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Materialize a validated, immutable server snapshot without mutating input."""
    out = copy.deepcopy(detail)
    post = post_at(out)
    now = now.astimezone(JST)
    if not post or now >= post:
        raise ValueError("race already started or scheduled post unknown")
    if not pre_off(lock, out):
        raise ValueError("forecast was not captured before post or has invalid runner marks")
    if sealed_lock(out):
        return out
    record = copy.deepcopy(lock)
    record.update({
        "frozen": True, "freezeSource": "scheduled-server-D1",
        "freezePolicy": SEALED_VERSION, "sealedAtEpoch": int(now.timestamp()),
        "sealedAtJst": now.isoformat(timespec="seconds"),
        "minutesToPostAtSeal": max(0, int((post - now).total_seconds() / 60)),
        "axisMeaning": "top-three-betting-axis-not-necessarily-winner",
        "winOnlyMeaning": "first-place-upside-independent-from-axis",
    })
    # Snapshot evaluated grades, odds-independent ranking heads and marks.
    original_horses = {int(h.get("horseNumber") or 0): h for h in out.get("horses") or [] if isinstance(h, dict)}
    for item in record["horses"]:
        h = original_horses.get(int(item["horseNumber"]), {})
        e = h.get("integratedEvaluation") or {}
        item["lockedEvaluation"] = {
            key: copy.deepcopy(e[key])
            for key in ("mark", "grade", "score", "coreAbilityRank",
                        "coreAbilityScore", "p1Score", "p2Score", "p3Score",
                        "podiumAxisScore", "winHeadRank", "strengthHeadRank")
            if key in e
        }
    raw = json.dumps({
        "raceId": record["raceId"], "date": record["raceDate"],
        "captured": record["capturedAtEpoch"], "sealed": record["sealedAtEpoch"],
        "horses": record["horses"],
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
    record["sealRevision"] = hashlib.sha256(raw).hexdigest()
    out["preRacePrediction"] = record
    # Pure shadow analysis of pre-off data; no impact on final marks or bets.
    # If it fails, the original authoritative seal still remains valid.
    try:
        from arvexq.prediction.research_shadow import build_shadow
        out["researchShadow"] = build_shadow(out)
    except (TypeError, ValueError, ArithmeticError):
        out["researchShadowUnavailable"] = True
    pm = dict(out.get("preparedMeta") or {})
    pm.update({
        "preRaceSealVersion": SEALED_VERSION,
        "preRaceSealEpoch": record["sealedAtEpoch"],
        "preRaceSealRevision": record["sealRevision"],
    })
    out["preparedMeta"] = pm
    return out

def evaluate_frozen_result(detail: dict[str, Any]) -> dict[str, Any] | None:
    """Evaluate a stored pre-off opinion against final order, never relabel it.

    Separate axis top-three accuracy, winning accuracy, podium coverage and
    ticket correctness. No metric is populated from post-race recomputation.
    """
    lock = sealed_lock(detail)
    result = detail.get("result") or {}
    if not lock or str(result.get("status") or "") != "確定":
        return None
    finish = [f for f in result.get("finishers") or []
              if isinstance(f, dict) and int(f.get("finish") or 0) > 0]
    finish.sort(key=lambda q: (int(q.get("finish") or 99), int(q.get("horseNumber") or 99)))
    podium = [int(f.get("horseNumber") or 0) for f in finish[:3]]
    if len(podium) < 3 or not all(podium):
        return None
    marks = {int(h["horseNumber"]): str(h.get("mark") or "")
             for h in lock.get("horses") or []}
    marked = {n for n, m in marks.items() if m and m in MARKS}
    hon = next((n for n, m in marks.items() if m == "◎"), None)
    bet = detail.get("preRaceBet") or {}
    tickets = []
    for item in bet.get("items") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        combos = item.get("combos") or []
        hit = False
        for raw in combos:
            try:
                combo = [int(n) for n in raw]
            except (ValueError, TypeError):
                continue
            if (kind == "単勝" and combo[:1] == podium[:1]
                or kind == "馬単" and combo[:2] == podium[:2]
                or kind == "馬連" and len(combo) == 2 and set(combo) == set(podium[:2])
                or kind == "ワイド" and len(combo) == 2 and len(set(combo)) == 2
                   and set(combo).issubset(set(podium))
                or kind == "3連複" and len(combo) == 3 and set(combo) == set(podium)
                or kind == "3連単" and combo[:3] == podium and len(combo) == 3):
                hit = True
        tickets.append({"kind": kind, "hit": hit, "points": len(combos)})
    return {
        "version": "arvexq-frozen-result-audit-v1",
        "raceId": str(detail.get("id") or ""),
        "revision": lock.get("sealRevision") or lock.get("revision") or "",
        "top3Finishers": podium,
        "honmeiPresent": hon is not None,
        "honmeiHorseNumber": hon or 0,
        "honmeiTop3Hit": bool(hon in podium) if hon else False,
        "honmeiWinHit": bool(hon == podium[0]) if hon else False,
        "markedPodiumCount": sum(no in marked for no in podium),
        "allThreeMarked": all(no in marked for no in podium),
        "ticketEvaluations": tickets,
        "trifectaHit": any(t["kind"] == "3連単" and t["hit"] for t in tickets),
        "ticketsHit": any(t["hit"] for t in tickets),
    }
