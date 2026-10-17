"""Independent pre-off evidence capture. No marks, tickets or legacy prediction lock.

The returned snapshot and receipt must be written together to append-only
storage by an authenticated scheduler. A local in-memory receipt by itself
cannot prove the acquisition time to an external auditor.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib
import json

from arvexq.prediction.mass_feature_snapshot import build_mass_feature_snapshot
from .frozen_research_input import from_frozen_snapshot

JST = timezone(timedelta(hours=9))
CAPTURE_VERSION = "arvexq-preoff-raw-evidence-v1"


def _time_of_post(detail):
    try:
        day = str(detail.get("date") or "")
        time = str(detail.get("startTime") or detail.get("scheduledStartTime") or "")[:5]
        return datetime.strptime(day + " " + time, "%Y-%m-%d %H:%M").replace(tzinfo=JST)
    except (ValueError, TypeError):
        raise ValueError("exact scheduled post date and time required") from None


def capture_preoff_features(detail, official_active_numbers, *, now=None):
    """Extract evidence ONLY before post time without invoking predictor or marks.

    Caller must supply the independently verified, current official active list
    and durably commit both returned objects at the actual acquisition time.
    """
    if not isinstance(detail, dict) or not detail.get("id"):
        raise ValueError("race identity required")
    if "result" in detail or "results" in detail or "payouts" in detail:
        raise ValueError("post-race fields cannot enter pre-off capture")
    clock = now if now is not None else datetime.now(JST)
    if not isinstance(clock, datetime) or clock.tzinfo is None:
        raise ValueError("timezone-aware acquisition clock required")
    clock = clock.astimezone(JST)
    post = _time_of_post(detail)
    if clock >= post:
        raise ValueError("race has already started")
    if not isinstance(official_active_numbers, list) or len(official_active_numbers) < 3:
        raise ValueError("official active field required")
    if (any(type(n) is not int or n <= 0 for n in official_active_numbers)
            or len(set(official_active_numbers)) != len(official_active_numbers)):
        raise ValueError("invalid official active field")
    rows = {}
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict) or type(horse.get("horseNumber")) is not int:
            raise ValueError("invalid incoming horse identity")
        no = horse["horseNumber"]
        if no in rows:
            raise ValueError("duplicated input horse")
        rows[no] = horse
    if not all(n in rows for n in official_active_numbers):
        raise ValueError("active horse missing from source")
    # Do not let provider-only scratch/withdrawal metadata silently override the
    # external official roster. It must be reconciled before this boundary.
    if any(any(rows[n].get(k) for k in ("scratched", "withdrawn", "cancelled"))
           for n in official_active_numbers):
        raise ValueError("inactive horse present on official active roster")
    captured = deepcopy(detail)
    captured["horses"] = [deepcopy(rows[n]) for n in official_active_numbers]
    for horse in captured["horses"]:
        for key in ("mark", "predMark", "integratedEvaluation", "honmeiRole",
                    "modelProbabilities", "betRecommendations", "preRacePrediction"):
            horse.pop(key, None)
    for key in ("preRacePrediction", "preRaceBet", "aiEvaluation", "factorRanking",
                "abilityRanking", "honmeiDecision"):
        captured.pop(key, None)
    snapshot = build_mass_feature_snapshot(captured)
    receipt = {"version": CAPTURE_VERSION, "source": "preoff-acquisition-log",
               "attestedPreOff": True, "raceId": snapshot["raceId"],
               "featureHash": snapshot["featureHash"],
               "activeHorseNumbers": list(official_active_numbers),
               "capturedAtEpoch": int(clock.timestamp()),
               "postAtEpoch": int(post.timestamp())}
    # Self-check the research contract before a caller can persist the two objects.
    from_frozen_snapshot(snapshot, receipt)
    raw = json.dumps(receipt, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    receipt["receiptHash"] = hashlib.sha256(raw).hexdigest()
    return snapshot, receipt
