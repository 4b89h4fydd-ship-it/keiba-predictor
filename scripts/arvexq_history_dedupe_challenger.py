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
import scripts.arvexq_current_prediction_audit as base

API_BASE = os.environ.get("ARVEXQ_API_BASE", base.API_BASE).rstrip("/")
END_DATE = os.environ.get("ARVEXQ_END_DATE", "2026-10-05")
DAYS = max(1, int(os.environ.get("ARVEXQ_DAYS", "7") or 7))


def iv(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def present(key: str, value: Any) -> bool:
    if value in (None, "", [], {}, "不明"):
        return False
    if key in {"finish", "fieldSize", "distance", "timeSeconds", "carriedWeight", "racePrize1", "raceNumber"}:
        try:
            return float(value) > 0
        except (TypeError, ValueError):
            return False
    return True


def run_key(run: dict[str, Any]) -> tuple[Any, ...]:
    day = str(run.get("date") or run.get("raceDate") or run.get("day") or "")
    track = str(run.get("track") or "")
    distance = iv(run.get("distance"))
    if day:
        return day, track, distance
    return day, track, distance, str(run.get("title") or ""), str(run.get("raceId") or "")


def merge_runs(*collections: Any) -> list[dict[str, Any]]:
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    order: list[tuple[Any, ...]] = []
    for collection in collections:
        for run in collection if isinstance(collection, list) else []:
            if not isinstance(run, dict):
                continue
            key = run_key(run)
            if key not in merged:
                merged[key] = copy.deepcopy(run)
                order.append(key)
                continue
            row = merged[key]
            for field, value in run.items():
                if not present(field, row.get(field)) and present(field, value):
                    row[field] = copy.deepcopy(value)
                elif field == "cornerPositions" and isinstance(value, list) and len(value) > len(row.get(field) or []):
                    row[field] = copy.deepcopy(value)
    rows = [merged[k] for k in order]
    rows.sort(key=lambda r: str(r.get("date") or r.get("raceDate") or ""), reverse=True)
    return rows


def canonicalize_history(detail: dict[str, Any]) -> dict[str, Any]:
    d = copy.deepcopy(detail)
    for horse in d.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        merged = merge_runs(horse.get("allPastRuns"), horse.get("recentRaces"))
        if merged:
            horse["recentRaces"] = copy.deepcopy(merged)
            horse["allPastRuns"] = copy.deepcopy(merged)
        else:
            horse["recentRaces"] = []
            horse["allPastRuns"] = []
    return d


def metrics_from_detail(detail: dict[str, Any], order: list[int], target: dict[str, int]) -> int:
    rows = base.mark_rows(detail.get("horses"), lock=False)
    marks = {x["no"]: x["mark"] for x in rows if x.get("mark")}
    rank = base.replay_rank(detail)
    honmei = next((no for no, mark in marks.items() if mark == "◎"), rank[0] if rank else 0)
    if rank and honmei:
        base.add_metrics(target, order, rank, marks)
    return honmei


def init_change() -> dict[str, int]:
    return {"compared": 0, "changed": 0, "improved": 0, "worsened": 0, "equal": 0, "currentWins": 0, "challengerWins": 0}


def compare_honmei(change: dict[str, int], order: list[int], current_no: int, challenger_no: int) -> None:
    if not current_no or not challenger_no:
        return
    change["compared"] += 1
    change["currentWins"] += int(order and current_no == order[0])
    change["challengerWins"] += int(order and challenger_no == order[0])
    if current_no == challenger_no:
        return
    change["changed"] += 1
    current_pos = order.index(current_no) + 1 if current_no in order else 999
    challenger_pos = order.index(challenger_no) + 1 if challenger_no in order else 999
    if challenger_pos < current_pos:
        change["improved"] += 1
    elif challenger_pos > current_pos:
        change["worsened"] += 1
    else:
        change["equal"] += 1


def main() -> None:
    end = datetime.strptime(END_DATE, "%Y-%m-%d").date()
    dates = [(end - timedelta(days=i)).isoformat() for i in range(DAYS - 1, -1, -1)]
    current_total = base.init_metrics()
    challenger_total = base.init_metrics()
    current_by_circuit: dict[str, dict[str, int]] = defaultdict(base.init_metrics)
    challenger_by_circuit: dict[str, dict[str, int]] = defaultdict(base.init_metrics)
    changes: dict[str, dict[str, int]] = defaultdict(init_change)
    before_runs = after_runs = 0
    races = 0

    for ds in dates:
        url = API_BASE + "/api/day?" + urllib.parse.urlencode({"date": ds, "details": "1"})
        payload = base.api_json(url)
        for detail in payload.get("details") or []:
            if not isinstance(detail, dict):
                continue
            order = base.finish_order(detail)
            if not order:
                continue
            circuit = str(detail.get("circuit") or "unknown")
            replay = base.scrub_for_replay(detail, ds)
            try:
                apply_core_marks(replay)
            except Exception as exc:
                print("CURRENT_ERROR", ds, detail.get("id"), type(exc).__name__, str(exc)[:120])
                continue
            current_no = metrics_from_detail(replay, order, current_total)
            metrics_from_detail(replay, order, current_by_circuit[circuit])

            challenger = canonicalize_history(replay)
            for horse in replay.get("horses") or []:
                if isinstance(horse, dict):
                    before_runs += len(horse.get("allPastRuns") or horse.get("recentRaces") or [])
            for horse in challenger.get("horses") or []:
                if isinstance(horse, dict):
                    after_runs += len(horse.get("allPastRuns") or horse.get("recentRaces") or [])
            try:
                apply_core_marks(challenger)
            except Exception as exc:
                print("CHALLENGER_ERROR", ds, detail.get("id"), type(exc).__name__, str(exc)[:120])
                continue
            challenger_no = metrics_from_detail(challenger, order, challenger_total)
            metrics_from_detail(challenger, order, challenger_by_circuit[circuit])
            compare_honmei(changes[circuit], order, current_no, challenger_no)
            races += 1

    output = {
        "version": "arvexq-history-dedupe-challenger-v1",
        "start": dates[0],
        "end": dates[-1],
        "races": races,
        "historyRows": {"before": before_runs, "after": after_runs, "removed": before_runs - after_runs},
        "current": base.rates(current_total),
        "challenger": base.rates(challenger_total),
        "currentByCircuit": {k: base.rates(v) for k, v in sorted(current_by_circuit.items())},
        "challengerByCircuit": {k: base.rates(v) for k, v in sorted(challenger_by_circuit.items())},
        "honmeiChangesByCircuit": {k: dict(v) for k, v in sorted(changes.items())},
        "warning": "Retrospective challenger only. Results/payouts and target-day history are scrubbed, but saved detail is not an immutable historical feature snapshot. Do not promote from this result alone without checking exact future pre-race locks.",
    }
    print("ARVEXQ_HISTORY_DEDUPE_CHALLENGER_JSON=" + json.dumps(output, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
