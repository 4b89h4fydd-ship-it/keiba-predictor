"""Run an approved, separately trained top-three model through the six lanes.

The callable does not estimate model parameters or make up probabilities.
Training/holdout/approval must have occurred independently beforehand.  An
approved manifest comes from a deployment-controlled registry, NOT a race API.
Never pass a raw post-race detail, old forecast, or result into this boundary.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any

from arvexq.forecast.frozen_research_input import from_frozen_snapshot
from arvexq.prediction.recommendation_engine import rank_marks, evaluate_tickets

VERSION = "arvexq-verified-six-lane-runtime-v1"
PUBLIC_VERSION = "arvexq-approved-forecast-v1"
JRA = "中央"
NAR = "地方"
MARKS = {"◎", "○", "▲", "△", "☆", "注"}


def _model_manifest(manifest: dict, race: dict) -> str:
    if not isinstance(manifest, dict) or manifest.get("publishApproved") is not True:
        raise ValueError("deployment registry has not approved the model")
    family = "jra-flat" if race["circuit"] == JRA else "nar-flat"
    if (race["family"] != "flat" or
            manifest.get("family") != family or
            not isinstance(manifest.get("modelId"), str) or
            not manifest["modelId"] or
            not isinstance(manifest.get("holdoutArtifactSha256"), str) or
            len(manifest["holdoutArtifactSha256"]) != 64 or
            not isinstance(manifest.get("calibrationArtifactSha256"), str) or
            len(manifest["calibrationArtifactSha256"]) != 64):
        raise ValueError("separate JRA/NAR flat calibration and holdout artifacts required")
    return manifest["modelId"]


def _validate_orders(orders: list[dict], runner_ids: set[int]) -> list[tuple[tuple[str, ...], float]]:
    if not isinstance(orders, list) or not orders:
        raise ValueError("out-of-sample calibrated top-three joint orders required")
    total = 0.0
    seen = set()
    full_order = []
    sorted_field = sorted(runner_ids)
    for record in orders:
        if not isinstance(record, dict):
            raise ValueError("invalid finishing order")
        numbers, value = record.get("horses"), record.get("probability")
        if (not isinstance(numbers, list) or len(numbers) != 3
                or any(type(v) is not int or v not in runner_ids for v in numbers)
                or len(set(numbers)) != 3
                or isinstance(value, bool) or not isinstance(value, (int, float))
                or not isfinite(value) or value < 0):
            raise ValueError("invalid joint top-three order or probability")
        key = tuple(numbers)
        if key in seen:
            raise ValueError("duplicate exact finishing order")
        seen.add(key)
        total += value
        # Pad after third ONLY to reuse the existing mark/ticket functions.
        # Finishing ranks after third are NOT model predictions.
        rest = [n for n in sorted_field if n not in key]
        full_order.append((tuple(str(n) for n in list(key) + rest), float(value)))
    if abs(total - 1.0) > 1e-6:
        raise ValueError("joint top-three mass must total exactly one")
    if not set(sorted_field).issubset(set(int(x) for x in full_order[0][0])):
        raise ValueError("runner field is incomplete")
    return full_order


def _pace(pace: dict, roster: set[int]) -> dict:
    if (not isinstance(pace, dict) or
            not isinstance(pace.get("stages"), list)):
        raise ValueError("trained four-stage pace scenarios required")
    stages = pace["stages"]
    if set(s.get("key") for s in stages if isinstance(s, dict)) != {
            "start", "turn3", "turn4", "straight"} or len(stages) != 4:
        raise ValueError("trained four-stage pace scenarios required")
    result = []
    for stage in stages:
        pack = stage.get("pack")
        if (not isinstance(pack, list) or len(pack) != len(roster)
                or any(not isinstance(row, dict) or type(row.get("no")) is not int
                       or row["no"] not in roster for row in pack)
                or set(row["no"] for row in pack) != roster):
            raise ValueError("four-stage formation must include all official runners")
        result.append({
            "key": stage["key"],
            "pack": [{"no": row["no"], "lane": max(-3, min(3, int(row.get("lane", 0))))}
                     for row in pack],
        })
    return {"stages": result, "scenario": dict(pace.get("scenario") or {}),
            "source": "trained-preoff"}


def _ticket_quotes(quotes: list[dict] | None, race: dict) -> dict:
    if not quotes:
        return {}
    out = {}
    post = int(race["postAtEpoch"])
    for item in quotes:
        if not isinstance(item, dict) or item.get("kind") != "trifecta":
            raise ValueError("only quoted exact three-horse tickets are supported")
        ids = item.get("horses")
        if not isinstance(ids, list) or len(ids) != 3 or any(type(n) is not int for n in ids):
            raise ValueError("invalid quoted ticket")
        quoted_at = item.get("quotedAtEpoch")
        if (type(quoted_at) is not int or quoted_at >= post or
                quoted_at < race["capturedAtEpoch"] or
                isinstance(item.get("odds"), bool)):
            raise ValueError("genuine pre-off odds and capture timestamp required")
        key = ("trifecta", tuple(str(x) for x in ids))
        if key in out:
            raise ValueError("duplicate quote")
        out[key] = float(item["odds"])
    return out


def forecast_from_approved_joint(
    snapshot: dict[str, Any],
    receipt: dict[str, Any],
    trained_top3_orders: list[dict[str, Any]],
    pace_stages: dict[str, Any],
    deployment_manifest: dict[str, Any],
    *,
    preoff_trifecta_quotes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Produce a *ready-to-display* forecast from genuinely approved ML outputs.

    The caller is responsible for authenticating append-only receipts and
    approved manifest signatures AT the storage boundary, before this call.
    Approval and training are never inferred from the input race or odds.
    """
    race = from_frozen_snapshot(snapshot, receipt)
    if race["circuit"] not in (JRA, NAR):
        raise ValueError("unsupported circuit")
    if race["family"] != "flat" or "帯広" in str(snapshot.get("track") or ""):
        raise ValueError("Banei/jumps excluded")
    model_id = _model_manifest(deployment_manifest, race)
    roster = {h["horseNumber"] for h in race["horses"]}
    if len(roster) != len(race["horses"]) or len(roster) < 5:
        raise ValueError("complete active field required")
    if set(receipt.get("activeHorseNumbers") or []) != roster:
        raise ValueError("race roster must equal independently preserved entry list")
    if int(race["capturedAtEpoch"]) >= int(race["postAtEpoch"]):
        raise ValueError("all predictions must be before scheduled post")
    rows = _validate_orders(trained_top3_orders, roster)
    formation = _pace(pace_stages, roster)
    marks_result = rank_marks(rows)
    rank = {int(n): mark for n, mark in marks_result["marks"].items()}
    probabilities = []
    for no in sorted(roster):
        key = str(no)
        win = sum(p for order, p in rows if order[0] == key)
        top2 = sum(p for order, p in rows if key in order[:2])
        top3 = marks_result["top3"].get(key, 0.0)
        probabilities.append({"horseNumber": no, "mark": rank.get(no, ""),
                              "win": round(win, 8), "top2": round(top2, 8),
                              "top3": round(top3, 8)})
    quotes = _ticket_quotes(preoff_trifecta_quotes, race)
    tickets = []
    if quotes:
        values = evaluate_tickets(rows, quotes)
        for row in values:
            if row.expected_return <= 1.0:
                continue
            tickets.append({
                "kind": "3連単",
                "level": "本線" if not tickets else "3連単チャレンジ",
                "combos": [[int(x) for x in row.horses]],
                "expectedReturn": round(row.expected_return, 8),
                "quotedOdds": row.odds,
                "hitProbability": round(row.win_probability, 8),
                "reason": "事前取得した実オッズと校正済み同時確率に基づく比較",
            })
            if len(tickets) >= 6:
                break
    return {
        "version": PUBLIC_VERSION, "modelId": model_id,
        "modelFamily": deployment_manifest["family"],
        "raceId": race["raceId"], "raceDate": race["date"],
        "circuit": race["circuit"], "snapshotHash": race["snapshotHash"],
        "capturedAtEpoch": race["capturedAtEpoch"], "postAtEpoch": race["postAtEpoch"],
        "fixedAt": datetime.fromtimestamp(
            race["capturedAtEpoch"], tz=timezone.utc).isoformat(),
        "horseNumbers": sorted(roster),
        "probabilities": probabilities,
        "scenarios": [{"horses": [int(x) for x in order[:3]], "probability": prob}
                      for order, prob in rows],
        "pace": formation,
        "tickets": tickets,
        "ticketStatus": "available" if tickets else "skip-no-positive-preoff-ev",
        "modelEvidence": {"holdoutArtifactSha256": deployment_manifest["holdoutArtifactSha256"],
                          "calibrationArtifactSha256": deployment_manifest["calibrationArtifactSha256"]},
        "publicationStatus": "approved-calibrated-preoff",
        "generatedBy": VERSION,
    }
