#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from arvexq.prediction.final_marks import apply_core_marks
from arvexq.selection.race_selectability import build_race_selectability_features
import scripts.arvexq_current_prediction_audit as base

API_BASE = os.environ.get("ARVEXQ_API_BASE", base.API_BASE).rstrip("/")
END_DATE = os.environ.get("ARVEXQ_END_DATE", "2026-10-05")
DAYS = max(1, int(os.environ.get("ARVEXQ_DAYS", "7") or 7))


def init() -> dict[str, int]:
    return {"races": 0, "honmeiWin": 0, "honmeiTop3": 0, "winnerCoreMark": 0}


def add(m: dict[str, int], detail: dict[str, Any], order: list[int]) -> None:
    if not order:
        return
    marks: dict[int, str] = {}
    honmei = 0
    for h in detail.get("horses") or []:
        if not isinstance(h, dict):
            continue
        no = base.iv(h.get("horseNumber"))
        ev = h.get("integratedEvaluation") if isinstance(h.get("integratedEvaluation"), dict) else {}
        mark = str(ev.get("mark") or "")
        if no > 0 and mark:
            marks[no] = mark
        if mark == "◎":
            honmei = no
    if honmei <= 0:
        return
    pos = order.index(honmei) + 1 if honmei in order else 999
    winner = order[0]
    m["races"] += 1
    m["honmeiWin"] += int(pos == 1)
    m["honmeiTop3"] += int(pos <= 3)
    m["winnerCoreMark"] += int(marks.get(winner) in {"◎", "○", "▲"})


def rates(m: dict[str, int]) -> dict[str, Any]:
    n = m["races"]
    return {
        **m,
        "honmeiWinRate": round(m["honmeiWin"] / n, 4) if n else None,
        "honmeiTop3Rate": round(m["honmeiTop3"] / n, 4) if n else None,
        "winnerCoreMarkRate": round(m["winnerCoreMark"] / n, 4) if n else None,
    }


def main() -> None:
    end = datetime.strptime(END_DATE, "%Y-%m-%d").date()
    dates = [(end - timedelta(days=i)).isoformat() for i in range(DAYS - 1, -1, -1)]
    groups: dict[str, dict[str, dict[str, int]]] = {
        "allDecisionHeadsAgree": defaultdict(init),
        "coreWinAgree": defaultdict(init),
        "coreStrengthAgree": defaultdict(init),
        "leaderPrimaryRank1Count": defaultdict(init),
        "leaderPrimaryPillarAvailable": defaultdict(init),
        "circuit": defaultdict(init),
    }
    total = init()
    gap_rows: list[tuple[float, int, int, int]] = []

    for ds in dates:
        payload = base.api_json(API_BASE + "/api/day?" + urllib.parse.urlencode({"date": ds, "details": "1"}))
        for detail in payload.get("details") or []:
            if not isinstance(detail, dict):
                continue
            order = base.finish_order(detail)
            if not order:
                continue
            replay = base.scrub_for_replay(detail, ds)
            apply_core_marks(replay)
            feat = build_race_selectability_features(replay)
            if not feat.get("available"):
                continue
            add(total, replay, order)
            circuit = str(replay.get("circuit") or "unknown")
            keys = {
                "allDecisionHeadsAgree": str(bool(feat.get("allDecisionHeadsAgree"))),
                "coreWinAgree": str(bool(feat.get("coreWinAgree"))),
                "coreStrengthAgree": str(bool(feat.get("coreStrengthAgree"))),
                "leaderPrimaryRank1Count": str(int(feat.get("leaderPrimaryRank1Count") or 0)),
                "leaderPrimaryPillarAvailable": str(int(feat.get("leaderPrimaryPillarAvailable") or 0)),
                "circuit": circuit,
            }
            for group, key in keys.items():
                add(groups[group][key], replay, order)

            gap = feat.get("winnerGap")
            if isinstance(gap, (int, float)):
                marks = {base.iv(h.get("horseNumber")): str((h.get("integratedEvaluation") or {}).get("mark") or "") for h in replay.get("horses") or [] if isinstance(h, dict)}
                honmei = next((no for no, mk in marks.items() if mk == "◎"), 0)
                pos = order.index(honmei) + 1 if honmei in order else 999
                gap_rows.append((float(gap), int(pos == 1), int(pos <= 3), int(marks.get(order[0]) in {"◎", "○", "▲"})))

    gap_rows.sort(key=lambda x: x[0])
    gap_quartiles: list[dict[str, Any]] = []
    if gap_rows:
        n = len(gap_rows)
        for q in range(4):
            lo = q * n // 4
            hi = (q + 1) * n // 4
            chunk = gap_rows[lo:hi]
            if not chunk:
                continue
            gap_quartiles.append({
                "quartile": q + 1,
                "races": len(chunk),
                "minGap": round(chunk[0][0], 6),
                "maxGap": round(chunk[-1][0], 6),
                "honmeiWinRate": round(sum(x[1] for x in chunk) / len(chunk), 4),
                "honmeiTop3Rate": round(sum(x[2] for x in chunk) / len(chunk), 4),
                "winnerCoreMarkRate": round(sum(x[3] for x in chunk) / len(chunk), 4),
            })

    out = {
        "version": "arvexq-selectability-audit-v1",
        "start": dates[0],
        "end": dates[-1],
        "total": rates(total),
        "groups": {
            group: {key: rates(value) for key, value in sorted(values.items())}
            for group, values in groups.items()
        },
        "winnerGapQuartiles": gap_quartiles,
        "warning": "Exploratory retrospective audit. These same-period groups must not be promoted as production thresholds; use future frozen raceSelectabilitySnapshot data for calibration/holdout validation.",
    }
    print("ARVEXQ_SELECTABILITY_AUDIT_JSON=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
