#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from arvexq.prediction.final_marks import apply_core_marks
from arvexq.prediction.jra_class_evidence import attach_jra_class_evidence
import scripts.arvexq_current_prediction_audit as base

API_BASE = os.environ.get("ARVEXQ_API_BASE", base.API_BASE).rstrip("/")
END_DATE = os.environ.get("ARVEXQ_END_DATE", "2026-10-05")
DAYS = max(1, int(os.environ.get("ARVEXQ_DAYS", "7") or 7))


def init_change() -> dict[str, int]:
    return {"compared": 0, "changed": 0, "improved": 0, "worsened": 0, "equal": 0, "currentWins": 0, "challengerWins": 0}


def rank(detail: dict[str, Any]) -> list[int]:
    rows = detail.get("factorRanking") if isinstance(detail.get("factorRanking"), list) else []
    return [base.iv(x.get("horseNumber")) for x in rows if isinstance(x, dict) and base.iv(x.get("horseNumber")) > 0]


def marks(detail: dict[str, Any]) -> dict[int, str]:
    out: dict[int, str] = {}
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        no = base.iv(horse.get("horseNumber"))
        ev = horse.get("integratedEvaluation") if isinstance(horse.get("integratedEvaluation"), dict) else {}
        mark = str(ev.get("mark") or "")
        if no > 0 and mark:
            out[no] = mark
    return out


def honmei(detail: dict[str, Any]) -> int:
    rr = rank(detail)
    if rr:
        return rr[0]
    for no, mark in marks(detail).items():
        if mark == "◎":
            return no
    return 0


def pos(order: list[int], no: int) -> int:
    return order.index(no) + 1 if no in order else 999


def main() -> None:
    end = datetime.strptime(END_DATE, "%Y-%m-%d").date()
    dates = [(end - timedelta(days=i)).isoformat() for i in range(DAYS - 1, -1, -1)]
    current_total = base.init_metrics()
    challenger_total = base.init_metrics()
    current_by: dict[str, dict[str, int]] = defaultdict(base.init_metrics)
    challenger_by: dict[str, dict[str, int]] = defaultdict(base.init_metrics)
    changes: dict[str, dict[str, int]] = defaultdict(init_change)
    injected_runs: dict[str, int] = defaultdict(int)
    races = 0

    for ds in dates:
        payload = base.api_json(API_BASE + "/api/day?" + urllib.parse.urlencode({"date": ds, "details": "1"}))
        for detail in payload.get("details") or []:
            if not isinstance(detail, dict):
                continue
            order = base.finish_order(detail)
            if not order:
                continue
            circuit = str(detail.get("circuit") or "unknown")
            current = base.scrub_for_replay(detail, ds)
            challenger = base.scrub_for_replay(detail, ds)
            apply_core_marks(current)
            injected = attach_jra_class_evidence(challenger)
            apply_core_marks(challenger)

            cr = rank(current)
            xr = rank(challenger)
            if not cr or not xr:
                continue
            races += 1
            cm = marks(current)
            xm = marks(challenger)
            base.add_metrics(current_total, order, cr, cm)
            base.add_metrics(challenger_total, order, xr, xm)
            base.add_metrics(current_by[circuit], order, cr, cm)
            base.add_metrics(challenger_by[circuit], order, xr, xm)
            injected_runs[circuit] += injected

            c = honmei(current)
            x = honmei(challenger)
            ch = changes[circuit]
            ch["compared"] += 1
            ch["currentWins"] += int(c == order[0])
            ch["challengerWins"] += int(x == order[0])
            if c != x:
                ch["changed"] += 1
                cp, xp = pos(order, c), pos(order, x)
                if xp < cp:
                    ch["improved"] += 1
                elif xp > cp:
                    ch["worsened"] += 1
                else:
                    ch["equal"] += 1

    out = {
        "version": "arvexq-jra-class-challenger-v1",
        "start": dates[0],
        "end": dates[-1],
        "races": races,
        "current": base.rates(current_total),
        "challenger": base.rates(challenger_total),
        "currentByCircuit": {k: base.rates(v) for k, v in sorted(current_by.items())},
        "challengerByCircuit": {k: base.rates(v) for k, v in sorted(challenger_by.items())},
        "honmeiChangesByCircuit": dict(sorted(changes.items())),
        "classEvidenceInjectedRunsByCircuit": dict(sorted(injected_runs.items())),
        "warning": "Retrospective challenger only. Class order is parsed from pre-race historical race titles, but the saved detail is not an immutable contemporaneous feature snapshot. Do not promote from this same-period result alone.",
    }
    print("ARVEXQ_JRA_CLASS_CHALLENGER_JSON=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
