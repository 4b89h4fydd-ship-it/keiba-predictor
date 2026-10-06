from __future__ import annotations

from typing import Any

TRAINING_VERSION = "arvexq-race-selectability-training-v1"


def _i(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _confirmed_finishers(detail: dict[str, Any]) -> list[dict[str, Any]]:
    result = detail.get("result") if isinstance(detail.get("result"), dict) else {}
    if str(result.get("status") or "") != "確定":
        return []
    rows = result.get("finishers") or result.get("results") or []
    out = [r for r in rows if isinstance(r, dict) and _i(r.get("finish", r.get("rank"))) > 0]
    return sorted(out, key=lambda r: _i(r.get("finish", r.get("rank")), 999))


def _locked_marks(detail: dict[str, Any]) -> dict[int, str]:
    lock = detail.get("preRacePrediction") if isinstance(detail.get("preRacePrediction"), dict) else {}
    rows = lock.get("horses") if isinstance(lock.get("horses"), list) else []
    marks: dict[int, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        no = _i(row.get("horseNumber"))
        mark = str(row.get("mark") or "").strip()
        if no > 0 and mark:
            marks[no] = mark
    return marks


def frozen_selectability_training_row(detail: dict[str, Any]) -> dict[str, Any] | None:
    """Join frozen pre-race selectability evidence with final labels only.

    Feature values are read exclusively from raceSelectabilitySnapshot. No feature is
    rebuilt from the finalized race object.
    """
    if not isinstance(detail, dict):
        return None
    snap = detail.get("raceSelectabilitySnapshot")
    if not isinstance(snap, dict) or not snap.get("featureHash"):
        return None
    features = snap.get("features") if isinstance(snap.get("features"), dict) else None
    if not features or not features.get("available"):
        return None
    finishers = _confirmed_finishers(detail)
    marks = _locked_marks(detail)
    if not finishers or not marks:
        return None

    winner = _i(finishers[0].get("horseNumber"))
    top3 = {_i(r.get("horseNumber")) for r in finishers[:3]}
    honmei = next((no for no, mark in marks.items() if mark == "◎"), 0)
    if winner <= 0 or honmei <= 0:
        return None

    return {
        "trainingVersion": TRAINING_VERSION,
        "featureHash": snap.get("featureHash"),
        "raceId": snap.get("raceId") or detail.get("id") or detail.get("raceId"),
        "date": snap.get("date") or detail.get("date"),
        "circuit": snap.get("circuit") or detail.get("circuit"),
        "features": dict(features),
        "labels": {
            "honmeiWin": int(honmei == winner),
            "honmeiTop3": int(honmei in top3),
            "winnerCoreMark": int(marks.get(winner) in {"◎", "○", "▲"}),
            "winnerAnyMark": int(bool(marks.get(winner))),
        },
        "lockedHonmeiHorseNumber": honmei,
        "winnerHorseNumber": winner,
    }
