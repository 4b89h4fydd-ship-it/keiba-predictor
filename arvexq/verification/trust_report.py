"""Truthful buyer-facing history from immutable, pre-off original forecasts.

Missing originals and missing official payouts are disclosed; neither are
reconstructed after the race. ROI is hypothetical flat-stake return, not a
claim of actual betting profit. This module never creates a prediction.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from math import sqrt
from typing import Any

from arvexq.backtest.ticket_metrics import summarize_frozen_ticket_metrics
from arvexq.prediction.prerace_archive import evaluate_frozen_result, sealed_lock, post_at

VERSION = "arvexq-trust-report-v1"


def verify_original_seal(detail: dict[str, Any]) -> dict[str, Any] | None:
    """Admit only immutable original hashes sealed strictly before the off.

    A self-consistent digest is *not* third-party proof of when the server
    wrote the record; immutable external publication is still required for
    independently certified commercial performance.
    """
    lock = sealed_lock(detail)
    if lock is None or lock.get("freezePolicy") != "arvexq-server-prerace-seal-v1":
        return None
    post = post_at(detail)
    sealed = lock.get("sealedAtEpoch")
    captured = lock.get("capturedAtEpoch")
    if (type(sealed) is not int or type(captured) is not int
            or post is None or not captured <= sealed < int(post.timestamp())):
        return None
    payload = {
        "raceId": lock["raceId"], "date": lock["raceDate"],
        "captured": captured, "sealed": sealed, "horses": lock["horses"],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), default=str).encode()
    if sha256(raw).hexdigest() != lock.get("sealRevision"):
        return None
    return lock


def _wilson(hits: int, attempts: int) -> list[float] | None:
    if not attempts:
        return None
    z = 1.959963984540054
    p = hits / attempts
    denominator = 1 + z * z / attempts
    center = (p + z * z / (2 * attempts)) / denominator
    radius = z * sqrt((p * (1 - p) + z * z / (4 * attempts)) / attempts) / denominator
    return [round(max(0, center - radius), 4), round(min(1, center + radius), 4)]


def build_trust_report(details: list[dict[str, Any]]) -> dict[str, Any]:
    """Assess *all* supplied races; no filtering on wins, venue or odds.

    Financial returns rely on genuine frozen stake receipts and official
    payouts. Coverage is separately reported to expose missing records.
    """
    if not isinstance(details, list):
        raise ValueError("race list required")
    race_ids = set()
    all_rows: list[dict[str, Any]] = []
    audits = []
    scope = defaultdict(lambda: {"total": 0, "verified": 0, "honmeiWins": 0,
                                 "honmeiPodiums": 0, "missingOriginal": 0})
    for detail in sorted(details, key=lambda r: (str(r.get("date") or ""), str(r.get("id") or ""))):
        if not isinstance(detail, dict):
            raise ValueError("invalid race detail")
        race_id, day = detail.get("id"), detail.get("date")
        if not race_id or not day or race_id in race_ids:
            raise ValueError("missing or duplicate race identity")
        race_ids.add(race_id)
        circuit = str(detail.get("circuit") or "unclassified")
        key = circuit + "/" + str(day)[:7]
        scope[key]["total"] += 1
        locked = verify_original_seal(detail)
        status = "missing-preoff-original"
        audit = None
        if locked is not None:
            audit = evaluate_frozen_result(detail)
            status = "verified-final" if audit is not None else "pending-official-final"
        if audit is not None:
            audits.append(audit)
            scope[key]["verified"] += 1
            scope[key]["honmeiWins"] += int(audit["honmeiWinHit"])
            scope[key]["honmeiPodiums"] += int(audit["honmeiTop3Hit"])
        elif locked is None:
            scope[key]["missingOriginal"] += 1
        all_rows.append({
            "raceId": race_id, "date": str(day), "circuit": circuit,
            "status": status,
            "originalRevision": (locked.get("sealRevision") or locked.get("revision"))
                               if locked else None,
            "honmeiWinHit": audit["honmeiWinHit"] if audit is not None else None,
            "honmeiTop3Hit": audit["honmeiTop3Hit"] if audit is not None else None,
            "trifectaHit": audit["trifectaHit"] if audit is not None else None,
            "ticketEvaluations": audit["ticketEvaluations"] if audit is not None else [],
        })
    n = len(audits)
    win = sum(int(a["honmeiWinHit"]) for a in audits if a.get("honmeiPresent"))
    podium = sum(int(a["honmeiTop3Hit"]) for a in audits if a.get("honmeiPresent"))
    honmei_n = sum(int(a.get("honmeiPresent", False)) for a in audits)
    monthly = {}
    for group, stats in sorted(scope.items()):
        denominator = stats["verified"]
        monthly[group] = {**stats,
                          "winRate": stats["honmeiWins"] / denominator if denominator else None,
                          "top3Rate": stats["honmeiPodiums"] / denominator if denominator else None}
    return {
        "version": VERSION,
        "population": {"suppliedRaces": len(details),
                       "withVerifiedOriginalAndOfficialFinal": n,
                       "missingOrInvalidOriginal": sum(s["missingOriginal"] for s in scope.values()),
                       "unsettledVerifiedOriginal": sum(1 for row in all_rows if row["status"] == "pending-official-final")},
        "honmei": {"sampleRaces": honmei_n, "wins": win, "top3Hits": podium,
                   "winRate": win / honmei_n if honmei_n else None,
                   "top3Rate": podium / honmei_n if honmei_n else None,
                   "winWilson95": _wilson(win, honmei_n),
                   "top3Wilson95": _wilson(podium, honmei_n)},
        "ticketMetrics": summarize_frozen_ticket_metrics(audits),
        "byCircuitAndMonth": monthly,
        "everyRace": all_rows,
        "disclosure": "全対象レースを掲載。発走前固定記録のないレースは成績計算せず欠測表示。"
                      "回収率は公式払戻による100円均等賭けの仮想収支であり、実際の購入利益ではない。",
        "verifiedProfitClaim": False,
    }
