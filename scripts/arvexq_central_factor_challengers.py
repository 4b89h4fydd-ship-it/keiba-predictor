#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import statistics
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import arvexq.prediction.factor_model as fm
from arvexq.prediction.final_marks import apply_core_marks
import scripts.arvexq_current_prediction_audit as base

API_BASE = os.environ.get("ARVEXQ_API_BASE", base.API_BASE).rstrip("/")
END_DATE = os.environ.get("ARVEXQ_END_DATE", "2026-10-05")
DAYS = max(1, int(os.environ.get("ARVEXQ_DAYS", "7") or 7))


def f(v: Any) -> float | None:
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def clip(v: float) -> float:
    return max(0.0, min(1.0, v))


def strict_finish_quality(run: dict[str, Any]) -> float | None:
    finish = f(run.get("finish", run.get("finishPosition", run.get("rank"))))
    field = f(run.get("fieldSize"))
    if finish is None or field is None or field < 2 or finish <= 0 or finish > field:
        return None
    return clip(1.0 - (finish - 1.0) / (field - 1.0))


def run_position_metrics(run: dict[str, Any]) -> tuple[float, float] | None:
    field = f(run.get("fieldSize"))
    corners = run.get("cornerPositions") if isinstance(run.get("cornerPositions"), list) else []
    vals: list[float] = []
    if field is None or field < 2:
        return None
    for raw in corners:
        pos = f(raw)
        if pos is None or pos <= 0 or pos > field:
            continue
        vals.append(clip(1.0 - (pos - 1.0) / (field - 1.0)))
    if not vals:
        return None
    last = vals[-1]
    gain = clip(0.5 + (vals[-1] - vals[0]) / 2.0) if len(vals) >= 2 else 0.5
    return last, gain


def inject_objective_pace(detail: dict[str, Any]) -> dict[str, Any]:
    d = copy.deepcopy(detail)
    if str(d.get("circuit") or "") != "中央":
        return d
    for horse in d.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        runs = horse.get("allPastRuns") or horse.get("recentRaces") or []
        positions: list[float] = []
        gains: list[float] = []
        for run in runs if isinstance(runs, list) else []:
            if not isinstance(run, dict):
                continue
            m = run_position_metrics(run)
            if m is None:
                continue
            positions.append(m[0]); gains.append(m[1])
        if not positions:
            continue
        ev = horse.setdefault("integratedEvaluation", {})
        if not isinstance(ev, dict):
            ev = {}; horse["integratedEvaluation"] = ev
        audit = ev.get("v218Audit") if isinstance(ev.get("v218Audit"), dict) else {}
        audit = dict(audit)
        # Each is an observed [0,1] statistic. No fitted coefficient is introduced.
        audit.setdefault("positionScenario", statistics.median(positions))
        audit.setdefault("hiddenEffort", statistics.median(gains))
        ev["v218Audit"] = audit
    return d


def metrics(detail: dict[str, Any], order: list[int], target: dict[str, int]) -> int:
    rows = base.mark_rows(detail.get("horses"), lock=False)
    marks = {x["no"]: x["mark"] for x in rows if x.get("mark")}
    rank = base.replay_rank(detail)
    honmei = next((no for no, mark in marks.items() if mark == "◎"), rank[0] if rank else 0)
    if rank and honmei:
        base.add_metrics(target, order, rank, marks)
    return honmei


def change_bucket() -> dict[str, int]:
    return {"compared": 0, "changed": 0, "improved": 0, "worsened": 0, "equal": 0}


def compare(change: dict[str, int], order: list[int], old: int, new: int) -> None:
    if not old or not new:
        return
    change["compared"] += 1
    if old == new:
        return
    change["changed"] += 1
    op = order.index(old) + 1 if old in order else 999
    np = order.index(new) + 1 if new in order else 999
    if np < op: change["improved"] += 1
    elif np > op: change["worsened"] += 1
    else: change["equal"] += 1


def evaluate_variant(replay: dict[str, Any], order: list[int], *, pace: bool, strict_field: bool) -> tuple[dict[str, Any], int]:
    d = inject_objective_pace(replay) if pace else copy.deepcopy(replay)
    original = fm._finish_quality
    if strict_field:
        fm._finish_quality = strict_finish_quality
    try:
        apply_core_marks(d)
    finally:
        fm._finish_quality = original
    tmp = base.init_metrics()
    honmei = metrics(d, order, tmp)
    return d, honmei


def main() -> None:
    end = datetime.strptime(END_DATE, "%Y-%m-%d").date()
    dates = [(end - timedelta(days=i)).isoformat() for i in range(DAYS - 1, -1, -1)]
    names = ("current", "paceOnly", "strictFieldOnly", "paceAndStrictField")
    totals = {name: base.init_metrics() for name in names}
    central = {name: base.init_metrics() for name in names}
    changes = {name: change_bucket() for name in names if name != "current"}
    races = central_races = 0

    for ds in dates:
        payload = base.api_json(API_BASE + "/api/day?" + urllib.parse.urlencode({"date": ds, "details": "1"}))
        for detail in payload.get("details") or []:
            if not isinstance(detail, dict):
                continue
            order = base.finish_order(detail)
            if not order:
                continue
            replay = base.scrub_for_replay(detail, ds)
            variants: dict[str, dict[str, Any]] = {}
            specs = {
                "current": (False, False),
                "paceOnly": (True, False),
                "strictFieldOnly": (False, True),
                "paceAndStrictField": (True, True),
            }
            honmei: dict[str, int] = {}
            for name, (pace, strict) in specs.items():
                d, h = evaluate_variant(replay, order, pace=pace, strict_field=strict)
                variants[name] = d; honmei[name] = h
                metrics(d, order, totals[name])
                if str(detail.get("circuit") or "") == "中央":
                    metrics(d, order, central[name])
            if str(detail.get("circuit") or "") == "中央":
                central_races += 1
                for name in changes:
                    compare(changes[name], order, honmei["current"], honmei[name])
            races += 1

    out = {
        "version": "arvexq-central-factor-challengers-v1",
        "start": dates[0], "end": dates[-1], "races": races, "centralRaces": central_races,
        "overall": {k: base.rates(v) for k, v in totals.items()},
        "central": {k: base.rates(v) for k, v in central.items()},
        "centralHonmeiChanges": changes,
        "notes": {
            "paceOnly": "中央のみ。fieldSizeがある過去走の最終コーナー相対位置中央値と、最初→最後コーナーの進出度中央値を独立PACE証拠として追加。係数学習なし。",
            "strictFieldOnly": "fieldSize不明時に12頭立てを仮定せず、finish qualityを欠損扱い。",
            "paceAndStrictField": "上記2修正の併用。",
        },
        "warning": "Retrospective challenger only; saved detail is not an immutable historical feature snapshot. Production is unchanged.",
    }
    print("ARVEXQ_CENTRAL_FACTOR_CHALLENGERS_JSON=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
