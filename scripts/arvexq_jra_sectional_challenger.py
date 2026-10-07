#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from arvexq.prediction.final_marks import apply_core_marks
from arvexq.prediction.jra_sectional_evidence import horse_sectional_evidence
import scripts.arvexq_current_prediction_audit as base

API_BASE = os.environ.get("ARVEXQ_API_BASE", base.API_BASE).rstrip("/")
END_DATE = os.environ.get("ARVEXQ_END_DATE", "2026-10-05")
DAYS = max(1, int(os.environ.get("ARVEXQ_DAYS", "7") or 7))


def marks(detail: dict[str, Any]) -> dict[int, str]:
    out = {}
    for h in detail.get("horses") or []:
        if not isinstance(h, dict):
            continue
        no = base.iv(h.get("horseNumber"))
        ev = h.get("integratedEvaluation") if isinstance(h.get("integratedEvaluation"), dict) else {}
        mark = str(ev.get("mark") or "")
        if no > 0 and mark:
            out[no] = mark
    return out


def rank(detail: dict[str, Any]) -> list[int]:
    rows = detail.get("factorRanking") if isinstance(detail.get("factorRanking"), list) else []
    return [base.iv(x.get("horseNumber")) for x in rows if isinstance(x, dict) and base.iv(x.get("horseNumber")) > 0]


def inject_sectional(detail: dict[str, Any]) -> int:
    if str(detail.get("circuit") or "") != "中央":
        return 0
    count = 0
    for h in detail.get("horses") or []:
        if not isinstance(h, dict):
            continue
        shadow = horse_sectional_evidence(h, detail)
        value = shadow.get("recentMedian")
        if value is None:
            continue
        ev = h.setdefault("integratedEvaluation", {})
        audit = ev.setdefault("v218Audit", {})
        if audit.get("sectional") in (None, ""):
            audit["sectional"] = float(value)
            audit["sectionalSource"] = shadow.get("modelVersion")
            count += 1
    return count


def pos(order: list[int], no: int) -> int:
    return order.index(no) + 1 if no in order else 999


def main() -> None:
    end = datetime.strptime(END_DATE, "%Y-%m-%d").date()
    dates = [(end - timedelta(days=i)).isoformat() for i in range(DAYS - 1, -1, -1)]
    current_total = base.init_metrics()
    challenger_total = base.init_metrics()
    current_by = defaultdict(base.init_metrics)
    challenger_by = defaultdict(base.init_metrics)
    changes = defaultdict(lambda: {"compared":0,"changed":0,"improved":0,"worsened":0,"equal":0,"currentWins":0,"challengerWins":0})
    injected_by = defaultdict(int)

    for ds in dates:
        payload = base.api_json(API_BASE + "/api/day?" + urllib.parse.urlencode({"date": ds, "details":"1"}))
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
            injected_by[circuit] += inject_sectional(challenger)
            apply_core_marks(challenger)
            cr, xr = rank(current), rank(challenger)
            if not cr or not xr:
                continue
            cm, xm = marks(current), marks(challenger)
            base.add_metrics(current_total, order, cr, cm)
            base.add_metrics(challenger_total, order, xr, xm)
            base.add_metrics(current_by[circuit], order, cr, cm)
            base.add_metrics(challenger_by[circuit], order, xr, xm)
            c, x = cr[0], xr[0]
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
        "version":"arvexq-jra-sectional-challenger-v1",
        "start":dates[0],"end":dates[-1],
        "current":base.rates(current_total),
        "challenger":base.rates(challenger_total),
        "currentByCircuit":{k:base.rates(v) for k,v in sorted(current_by.items())},
        "challengerByCircuit":{k:base.rates(v) for k,v in sorted(challenger_by.items())},
        "changesByCircuit":dict(sorted(changes.items())),
        "sectionalInjectedHorsesByCircuit":dict(sorted(injected_by.items())),
        "warning":"Retrospective challenger. Only historical race-relative closing percentile is injected; raw closing seconds are never compared across races."
    }
    print("ARVEXQ_JRA_SECTIONAL_CHALLENGER_JSON="+json.dumps(out,ensure_ascii=False,separators=(",",":")))


if __name__=="__main__":
    main()
