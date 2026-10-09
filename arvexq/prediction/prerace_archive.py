"""Immutable, provenance-checked pre-race forecast archive.

Never create a forecast once a race has begun.  Absence of a timely snapshot is
an explicit missing state, not permission to reconstruct from results.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
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
    # Shadow is generated from the same original pre-off payload. Subsequent
    # result, odds and body-weight updates must not rewrite this evidence.
    if isinstance(old.get("researchShadow"), dict):
        out["researchShadow"] = copy.deepcopy(old["researchShadow"])
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
    from arvexq.prediction.official_course_revision import latest_pre_off_marks
    mark_snapshot = latest_pre_off_marks(detail) or lock
    marks = {int(h["horseNumber"]): str(h.get("mark") or "")
             for h in mark_snapshot.get("horses") or []}
    marked = {n for n, m in marks.items() if m and m in MARKS}
    hon = next((n for n, m in marks.items() if m == "◎"), None)
    bet = detail.get("preRaceBet") or {}
    # Per-100-yen actual payout only when the official result contains a
    # complete parseable entry for the specific ticket kind. Never impute
    # returns from win odds or missing payout types.
    official_payouts = {}
    payout_invalid = set()
    for row in result.get("payouts") or []:
        if not isinstance(row, dict):
            continue
        kind = str(row.get("type") or "")
        if not kind:
            continue
        raw = str(row.get("combination") or "")
        numbers = [int(x) for x in re.findall(r"\d+", raw)]
        expected = 3 if kind in {"3連単", "3連複"} else 2 if kind in {"ワイド", "馬連", "馬単"} else 1 if kind == "単勝" else 0
        raw_amount = row.get("amount")
        try:
            amount = int(str(raw_amount).replace(",", "").replace("円", "").replace("¥", "").strip())
        except (TypeError, ValueError):
            amount = -1
        if not expected or len(numbers) != expected or amount < 0:
            payout_invalid.add(kind)
            continue
        if kind in {"ワイド", "馬連", "3連複"}:
            numbers.sort()
        official_payouts.setdefault(kind, {})[tuple(numbers)] = amount

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
        prices = official_payouts.get(kind)
        payout = None
        if prices and kind not in payout_invalid:
            payout = 0
            for raw in combos:
                try:
                    values = [int(x) for x in raw]
                except (TypeError, ValueError):
                    payout = None
                    break
                if kind in {"ワイド", "馬連", "3連複"}:
                    values.sort()
                payout += prices.get(tuple(values), 0)
        tickets.append({"kind": kind, "level": str(item.get("level") or ""),
                        "hit": hit, "points": len(combos),
                        "stakeYenAt100": 100 * len(combos),
                        "payoutYenAt100": payout})
    return {
        "version": "arvexq-frozen-result-audit-v1",
        "raceId": str(detail.get("id") or ""),
        "revision": lock.get("sealRevision") or lock.get("revision") or "",
        "marksSnapshotSource": mark_snapshot.get("version") or lock.get("freezePolicy") or "",
        "marksRevisionAt": mark_snapshot.get("revisedAt") or mark_snapshot.get("fixedAt") or "",
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



def summarize_frozen_ticket_metrics(audits: list[dict[str, Any]]) -> dict[str, Any]:
    """Kind-specific historical performance for validated sealed, final races.

    A hit rate here is an observed sample fraction, never an AI-predicted chance.
    ROI is a simulated flat 100-yen-per-ticket return, NOT actual purchases.
    One missing payout invalidates the entire kind's return estimate.
    """
    kinds: dict[str, dict[str, Any]] = {}
    for audit in audits:
        if not isinstance(audit, dict) or audit.get("version") != "arvexq-frozen-result-audit-v1":
            continue
        for item in audit.get("ticketEvaluations") or []:
            if not isinstance(item, dict) or not item.get("kind"):
                continue
            kind = str(item["kind"])
            points = int(item.get("points") or 0)
            if points < 1:
                continue
            group = kinds.setdefault(kind, {"races": 0, "hits": 0,
                "points": 0, "stakeYenAt100": 0, "payoutYenAt100": 0,
                "completePayouts": True, "payoutObserved": 0})
            group["races"] += 1
            group["hits"] += int(bool(item.get("hit")))
            group["points"] += points
            group["stakeYenAt100"] += 100 * points
            amount = item.get("payoutYenAt100")
            if amount is None:
                group["completePayouts"] = False
            else:
                group["payoutYenAt100"] += int(amount)
                group["payoutObserved"] += 1
    response: dict[str, Any] = {}
    for kind, group in sorted(kinds.items()):
        complete = group["completePayouts"] and group["payoutObserved"] == group["races"]
        response[kind] = {
            "sampleRaces": group["races"],
            "hits": group["hits"],
            "observedHitRate": group["hits"] / group["races"],
            "averagePoints": group["points"] / group["races"],
            "stakeYenAt100": group["stakeYenAt100"],
            "payoutYenAt100": group["payoutYenAt100"] if complete else None,
            "flatStakeReturnRate": (
                group["payoutYenAt100"] / group["stakeYenAt100"]
                if complete and group["stakeYenAt100"] else None
            ),
            "completePayouts": complete,
        }
    return {"version": "arvexq-archived-ticket-metrics-v1",
            "stakeBasis": "simulated-100-yen-per-combination-not-real-purchases",
            "byKind": response}
