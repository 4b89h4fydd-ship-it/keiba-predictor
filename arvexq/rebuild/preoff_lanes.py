"""Research-only six-lane readiness for *independently captured* pre-off facts.

This module does not load a trained model, make picks, compute probabilities,
change any original snapshot, fetch new facts or write to D1. The former
prediction engine remains retired.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from typing import Any

from arvexq.forecast.frozen_research_input import from_frozen_snapshot

VERSION = "arvexq-six-lane-evidence-gate-v1"
LANES = ("ability", "running_style", "pace_scenarios",
         "probabilities", "marks", "tickets")
ABILITY_METRICS = frozenset({
    "finish_quality", "speed", "clock_speed", "opponent_level",
    "margin", "win_flag", "top2_flag", "top3_flag",
})
STYLE_METRICS = frozenset({"early_speed", "position_quality", "late_speed"})
PACE_METRICS = frozenset({"early_speed", "position_quality", "late_speed"})
FORBIDDEN_SNAPSHOT_KEYS = frozenset({
    "result", "results", "finishers", "payouts", "payout", "winner",
    "labelWin", "labelTop2", "labelTop3", "finish", "finalOrder",
})
FORBIDDEN_ROW_KEYS = frozenset({
    "finish", "rank", "labelWin", "labelTop2", "labelTop3",
    "result", "payouts", "predMark", "preRacePrediction",
})


def _digest(data: dict[str, Any]) -> str:
    return sha256(json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _checked_receipt(snapshot: dict[str, Any], receipt: dict[str, Any]) -> None:
    if not isinstance(snapshot, dict) or not isinstance(receipt, dict):
        raise ValueError("frozen snapshot and separate receipt required")
    if receipt.get("version") != "arvexq-preoff-raw-evidence-v1":
        raise ValueError("unknown preoff capture receipt version")
    digest = receipt.get("receiptHash")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("retained capture receipt hash required")
    if digest != _digest({k: v for k, v in receipt.items() if k != "receiptHash"}):
        raise ValueError("capture receipt hash does not match original")
    if FORBIDDEN_SNAPSHOT_KEYS.intersection(snapshot):
        raise ValueError("outcome-dependent key in preoff snapshot")
    rows = snapshot.get("rows")
    roster = receipt.get("activeHorseNumbers")
    if (not isinstance(rows, list) or type(snapshot.get("horseCount")) is not int
            or snapshot["horseCount"] != len(rows) or len(rows) < 3
            or not isinstance(roster, list) or len(roster) != len(rows)):
        raise ValueError("complete independently declared starting field required")
    ids = []
    for row in rows:
        if not isinstance(row, dict) or FORBIDDEN_ROW_KEYS.intersection(row):
            raise ValueError("invalid or result-derived frozen runner row")
        no = row.get("horseNumber")
        if type(no) is not int or no <= 0 or not str(row.get("name") or "").strip():
            raise ValueError("frozen runner number and name required")
        ids.append(no)
    if (len(set(ids)) != len(ids) or len(set(roster)) != len(roster)
            or set(ids) != set(roster)):
        raise ValueError("frozen rows must equal official active field")


def _metric_features(features: dict[str, float], metrics: frozenset[str]) -> list[str]:
    """Only observed historical measurements; never invented feature defaults."""
    used = []
    for name in features:
        parts = name.split("::")
        if len(parts) == 5 and parts[0] == "history" and parts[3] in metrics:
            used.append(name)
    return sorted(used)


def _lane_evidence(horses: list[dict[str, Any]],
                   metrics: frozenset[str]) -> dict[str, Any]:
    rows = []
    with_evidence = 0
    for h in horses:
        names = _metric_features(h["features"], metrics)
        with_evidence += bool(names)
        rows.append({
            "horseNumber": h["horseNumber"],
            "observedFeatureCount": len(names),
            "sampleFeatureNames": names[:8],
        })
    return {
        "status": "evidence_only" if with_evidence == len(horses) else "partial_evidence",
        "horsesWithEvidence": with_evidence,
        "horseCount": len(horses),
        "horses": rows,
        "isPredictedRanking": False,
    }


def _run(snapshot: dict[str, Any], receipt: dict[str, Any],
         *, circuit: str, prefix: str, model_family: str) -> dict[str, Any]:
    _checked_receipt(snapshot, receipt)
    race = from_frozen_snapshot(snapshot, receipt)
    race_id = str(race["raceId"])
    day = str(race["date"])
    if (race["circuit"] != circuit or not race_id.startswith(prefix)
            or day not in race_id
            or date.fromisoformat(day).isoformat() != day):
        raise ValueError("JRA/NAR race identity and circuit mismatch")
    if race["family"] != "flat":
        raise ValueError("only JRA and NAR flat racing; Banei/jumps require separate models")
    if any(label in str(snapshot.get("track") or "") for label in ("帯広", "帯広ば")):
        raise ValueError("retired Obihiro/Banei venue excluded")
    if str(snapshot.get("circuit") or "") != circuit:
        raise ValueError("frozen snapshot circuit mismatch")
    horses = race["horses"]
    ability = _lane_evidence(horses, ABILITY_METRICS)
    style = _lane_evidence(horses, STYLE_METRICS)
    pace = _lane_evidence(horses, PACE_METRICS)
    # Coverage is factual. Without approved future-held-out models, evidence
    # coverage must not silently turn into calibrated probabilities or marks.
    return {
        "version": VERSION,
        "status": "research_only_not_publishable",
        "modelFamily": model_family,
        "circuit": circuit,
        "raceId": race_id,
        "raceDate": day,
        "snapshotHash": race["snapshotHash"],
        "capturedAtEpoch": race["capturedAtEpoch"],
        "postAtEpoch": race["postAtEpoch"],
        "independentStorageTimestampVerified": False,
        "horseNumbers": [h["horseNumber"] for h in horses],
        "lanes": {
            "ability": ability,
            "running_style": style,
            "pace_scenarios": {
                "status": "blocked_no_verified_scenario_model",
                "inputEvidence": pace,
                "predictedScenarios": [],
            },
            "probabilities": {
                "status": "blocked_no_future_holdout_and_calibration",
                "win": None, "top2": None, "top3": None,
            },
            "marks": {
                "status": "blocked_no_approved_probabilities",
                "items": [],
            },
            "tickets": {
                "status": "blocked_no_calibrated_joint_probabilities_and_preoff_odds",
                "items": [],
            },
        },
    }


def inspect_jra(snapshot: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    """Central flat route; never silently ingest NAR or Banei."""
    return _run(snapshot, receipt, circuit="中央", prefix="jra-", model_family="jra-flat")


def inspect_nar(snapshot: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    """Local flat route; never silently ingest JRA or Banei."""
    return _run(snapshot, receipt, circuit="地方", prefix="nar-", model_family="nar-flat")


def inspect_preoff(snapshot: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    """Explicit dispatch based on frozen circuit; unmatched input fails closed."""
    if not isinstance(snapshot, dict):
        raise ValueError("frozen snapshot required")
    circuit = snapshot.get("circuit")
    if circuit == "中央":
        return inspect_jra(snapshot, receipt)
    if circuit == "地方":
        return inspect_nar(snapshot, receipt)
    raise ValueError("unsupported racing circuit; no cross-circuit fallback")
