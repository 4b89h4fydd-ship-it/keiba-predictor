"""Paired forward grading of *frozen* v9b and master shadow forecasts.

Accepts published race details with outcome results attached after the off.
The evaluation must never influence scores already frozen for the same race.
Missing / unverifiable pre-off timestamps are excluded, not guessed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import log
import json

JST = timezone(timedelta(hours=9))
EPS = 1e-12


def _timestamp(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp if stamp.tzinfo else stamp.replace(tzinfo=JST)
    except (TypeError, ValueError):
        return None


def _off_time(detail):
    date = detail.get("date")
    time = detail.get("startTime") or detail.get("start_time")
    if not isinstance(date, str) or not isinstance(time, str):
        return None
    if "T" in time:
        return _timestamp(time)
    return _timestamp(f"{date}T{time}")


def _distribution(rows, key, id_key="horseNumber"):
    try:
        probs = {int(r[id_key]): float(r[key]) for r in rows}
    except (KeyError, TypeError, ValueError):
        return None
    if (len(probs) != len(rows) or len(probs) < 3
            or any(p <= 0 or p >= 1 for p in probs.values())
            or abs(sum(probs.values()) - 1) > 0.005):
        return None
    return probs


def _score(probs, winner, top3):
    honmei = max(probs, key=lambda n: (probs[n], -n))
    return {
        "honmei": honmei,
        "win": int(honmei == winner),
        "top3": int(honmei in top3),
        "logLoss": -log(max(probs[winner], EPS)),
        "brier": sum((p - int(n == winner)) ** 2 for n, p in probs.items()),
    }


def grade_master_pairs(details: list[dict]) -> dict:
    """Score exactly matched, verifiably pre-off race pairs.

    This expects a full race detail (not an API summary) with:
    preRaceBet.fixedBeforePost, prediction.capturedAt + stages.probability
    win vector, masterAnalysis.runners and frozen unified receipt.
    """
    exclusions = Counter()
    paired = []
    seen = set()
    for detail in details:
        rid = str(detail.get("id") or detail.get("raceId") or "")
        if not rid or rid in seen:
            exclusions["missing-or-duplicate-race"] += 1
            continue
        seen.add(rid)
        if detail.get("track") in ("帯広", "帯広ば", "帯広ばんえい"):
            exclusions["excluded-banei"] += 1
            continue
        prediction = detail.get("prediction") or {}
        bet = detail.get("preRaceBet") or {}
        receipt = (detail.get("unifiedForecast") or {}).get("receiptSha256")
        off = _off_time(detail)
        captured = _timestamp(prediction.get("capturedAt"))
        if not (bet.get("fixedBeforePost") is True and receipt
                and off and captured and captured < off):
            exclusions["unverified-preoff"] += 1
            continue
        result = detail.get("result") or {}
        if result.get("status") != "確定":
            exclusions["pending-result"] += 1
            continue
        finishers = result.get("finishers") or []
        winners = [r["horseNumber"] for r in finishers
                   if r.get("finish") == 1 and isinstance(r.get("horseNumber"), int)]
        top3 = {r["horseNumber"] for r in finishers
                if isinstance(r.get("finish"), int) and 1 <= r["finish"] <= 3
                and isinstance(r.get("horseNumber"), int)}
        if len(winners) != 1 or len(top3) != 3:
            exclusions["incomplete-results"] += 1
            continue
        incumbent = (prediction.get("stages") or {}).get("probability") or {}
        base = (incumbent.get("value") or {}).get("win") or {}
        candidate = detail.get("masterAnalysis") or {}
        if candidate.get("status") != "shadow-candidate" or candidate.get("validated") is not False:
            exclusions["no-shadow-candidate"] += 1
            continue
        digest = candidate.get("contentSha256")
        unsigned = {k: v for k, v in candidate.items() if k != "contentSha256"}
        actual = sha256(json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode("utf-8")).hexdigest()
        if candidate.get("capturedAt") != prediction.get("capturedAt") or digest != actual:
            exclusions["shadow-seal-mismatch"] += 1
            continue
        try:
            base_probs = {int(n): float(p) for n, p in base.items()}
        except (ValueError, TypeError):
            exclusions["invalid-incumbent-probabilities"] += 1
            continue
        challenger_probs = _distribution(candidate.get("runners") or [], "pWin")
        if (challenger_probs is None or set(base_probs) != set(challenger_probs)
                or abs(sum(base_probs.values()) - 1) > 0.005
                or any(p <= 0 or p >= 1 for p in base_probs.values())
                or winners[0] not in base_probs):
            exclusions["probabilities-or-roster-mismatch"] += 1
            continue
        winner = winners[0]
        paired.append({
            "raceId": rid, "date": detail.get("date"),
            "circuit": detail.get("circuit"),
            "incumbent": _score(base_probs, winner, top3),
            "candidate": _score(challenger_probs, winner, top3),
        })

    def summary(rows):
        if not rows:
            return {"races": 0, "verdict": "insufficient-sample"}
        n = len(rows)
        def metrics(arm):
            return {
                "honmeiWinRate": round(sum(r[arm]["win"] for r in rows) / n, 4),
                "honmeiTop3Rate": round(sum(r[arm]["top3"] for r in rows) / n, 4),
                "meanLogLoss": round(sum(r[arm]["logLoss"] for r in rows) / n, 4),
                "meanBrier": round(sum(r[arm]["brier"] for r in rows) / n, 4),
            }
        return {
            "races": n, "incumbent": metrics("incumbent"),
            "candidate": metrics("candidate"),
            "candidateMinusIncumbent": {
                metric: round(metrics("candidate")[metric] - metrics("incumbent")[metric], 4)
                for metric in ("honmeiWinRate", "honmeiTop3Rate", "meanLogLoss", "meanBrier")
            },
            "verdict": "comparison-only-not-adoption",
        }

    by_circuit = defaultdict(list)
    for row in paired:
        by_circuit[row["circuit"]].append(row)
    return {
        "status": "paired-frozen-forward-only",
        "overall": summary(paired),
        "byCircuit": {key: summary(value) for key, value in sorted(by_circuit.items())},
        "excluded": dict(exclusions),
        "caveat": "No ticket ROI, calibration fit, confidence interval, or adoption verdict",
    }
