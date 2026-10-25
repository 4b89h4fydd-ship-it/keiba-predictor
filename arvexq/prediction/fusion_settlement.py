"""Audit real, immutable pre-off opinion receipts against official payouts.

This is a component of the EXISTING six-stage fusion's evaluation path.
It never invents earlier capture times, odds, stake, or independently
recorded expert/AI opinions from a later race-result snapshot.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Mapping

from arvexq.prediction.empirical_fusion import _arms, _probs, _timestamp, fit_weights

VERSION = "arvexq-fusion-official-win-settlement-v1"


def _finishers(detail):
    result = detail.get("result")
    if not isinstance(result, dict) or result.get("status") != "確定":
        raise ValueError("final official result required")
    rows = result.get("finishers")
    if not isinstance(rows, list) or len(rows) < 3:
        raise ValueError("complete official finishing order required")
    valid = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid official finisher")
        number, place = row.get("horseNumber"), row.get("finish")
        if type(number) is int and type(place) is int and number > 0 and place > 0:
            valid.append((place, number))
    valid.sort()
    if (len(valid) < 3 or valid[0][0] != 1 or
            len({no for _, no in valid}) != len(valid) or
            len({place for place, _ in valid}) != len(valid)):
        raise ValueError("ambiguous finishing order, scratched runners or dead heats")
    return [no for _, no in valid]


def _official_single_win_payout(detail):
    payouts = (detail.get("result") or {}).get("payouts")
    if not isinstance(payouts, list):
        raise ValueError("official win payout missing")
    entries = [(str(r.get("combination") or "").strip(), r.get("amount"))
               for r in payouts if isinstance(r, dict) and r.get("type") == "単勝"]
    if len(entries) != 1 or not entries[0][0].isdigit():
        raise ValueError("ambiguous win payout; do not settle coupled entries")
    no, amount = int(entries[0][0]), entries[0][1]
    if type(amount) not in (float, int) or amount < 0 or not float(amount) < float("inf"):
        raise ValueError("invalid official payout per 100 yen")
    return no, float(amount)


def settle_frozen_race(detail, captured):
    """Build one same-race evaluation record from five pre-off opinion originals.

    Original opinions and timestamps must exist in a frozen receipt. The result
    snapshot only supplies outcomes and JRA/NAR-authoritative ¥100 payouts.
    All methods stake exactly ¥100 on their own highest win-probability pick.
    This common comparison avoids comparing radically different bet sizes.
    """
    if not isinstance(detail, dict) or not isinstance(captured, dict):
        raise ValueError("official race and frozen pre-off opinions required")
    rid, day = detail.get("id"), detail.get("date")
    if not rid or captured.get("raceId") != rid or captured.get("raceDate") != day:
        raise ValueError("result and frozen forecast race identity mismatch")
    if captured.get("circuit") != detail.get("circuit") or captured.get("circuit") not in ("中央", "地方"):
        raise ValueError("circuit must match; central and local remain separate")
    scheduled_off = captured.get("scheduledOffAt")
    frozen_at = captured.get("capturedAt")
    if _timestamp(frozen_at) >= _timestamp(scheduled_off):
        raise ValueError("not a genuine pre-off capture")
    if captured.get("sourceKind") != "original-frozen-preoff-method-opinions":
        raise ValueError("missing independent sealed source provenance")
    opinions = captured.get("arms")
    _arms(opinions)
    if set(opinions) != set(captured.get("sourceVersions") or {}):
        raise ValueError("method versions missing")
    if any(captured["sourceVersions"][name] != opinion.get("modelVersion")
           for name, opinion in opinions.items()):
        raise ValueError("frozen model version mismatch")
    roster = captured.get("roster")
    if (not isinstance(roster, list) or len(roster) < 5
            or any(type(n) is not int or n <= 0 for n in roster)
            or len(set(roster)) != len(roster)):
        raise ValueError("invalid frozen starter field")
    names = {int(h.get("horseNumber")) for h in detail.get("horses") or []
             if isinstance(h, dict) and type(h.get("horseNumber")) is int}
    if not set(roster).issubset(names):
        raise ValueError("historical frozen field not found in official race")
    finishers = _finishers(detail)
    winner, payout = _official_single_win_payout(detail)
    if finishers[0] != winner:
        raise ValueError("winner conflicts with official win-payout horse")
    if not set(finishers).issubset(roster):
        raise ValueError("official finishers not all in frozen field")
    settled = {}
    for name, opinion in opinions.items():
        if opinion.get("raceId") != rid or _timestamp(opinion.get("capturedAt")) >= _timestamp(scheduled_off):
            raise ValueError("post-off or cross-race method opinion")
        win = _probs(opinion.get("win"), roster)
        _probs(opinion.get("top3"), roster, three=True)
        best = min(roster, key=lambda n: (-win[n], n))
        settled[name] = {
            **deepcopy(opinion),
            # Settlement fields are DERIVED solely from official result/payout.
            "stakeYen": 100.,
            "returnYen": payout if best == winner else 0.,
        }
    return {
        "raceId": rid, "raceDate": day, "circuit": detail["circuit"],
        "capturedAt": frozen_at, "scheduledOffAt": scheduled_off,
        "finishers": finishers, "roster": list(roster),
        "arms": settled, "settlementVersion": VERSION,
        "payoutSource": (detail.get("result") or {}).get("source") or "",
        "officialWinner": winner, "officialWinPayoutPer100Yen": payout,
        "originalOpinionSource": "immutable-frozen-preoff-only",
    }


def train_from_frozen_results(snapshots, frozen_receipts, *, target_date, circuit, min_races=30):
    """Fit ONLY on races with genuine per-method pre-off originals and results."""
    if circuit not in ("中央", "地方"):
        raise ValueError("explicit circuit selection required")
    if not isinstance(snapshots, list) or not isinstance(frozen_receipts, Mapping):
        raise ValueError("source snapshots and receipts required")
    matched, skipped = [], {}
    for detail in snapshots:
        if not isinstance(detail, dict) or detail.get("circuit") != circuit:
            continue
        rid = str(detail.get("id") or "")
        if str(detail.get("date") or "") >= target_date:
            continue
        receipt = frozen_receipts.get(rid)
        if not isinstance(receipt, dict):
            skipped[rid] = "no-original-preoff-opinions"
            continue
        try:
            matched.append(settle_frozen_race(detail, receipt))
        except (TypeError, KeyError, ValueError) as exc:
            skipped[rid] = str(exc)
    fitted = fit_weights(matched, target_date=target_date, min_races=min_races)
    return {
        "calibration": fitted, "matchedRaces": len(matched),
        "skipped": skipped,
        "source": "official-settlement-of-original-preoff-opinions",
        "notHistoricalAccuracyClaimWithoutReceipts": True,
    }
