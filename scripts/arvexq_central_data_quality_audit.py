#!/usr/bin/env python3
from __future__ import annotations

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
PILLARS = ("ability", "record", "suitability", "pace", "support")


def init() -> dict[str, float]:
    d: dict[str, float] = {
        "races": 0,
        "horses": 0,
        "horsesNoRuns": 0,
        "horsesLt3Runs": 0,
        "horsesGe5Runs": 0,
        "runs": 0,
        "runsFinish": 0,
        "runsFieldSize": 0,
        "runsSpeedIndex": 0,
        "runsTimed": 0,
        "runsOpponentLevel": 0,
        "runsPrize": 0,
        "horsesAudit": 0,
        "horsesResearch": 0,
        "raceDistance": 0,
        "raceSurface": 0,
        "raceCondition": 0,
    }
    for p in PILLARS:
        d[f"familySum_{p}"] = 0
        d[f"familyNonzero_{p}"] = 0
    return d


def add(target: dict[str, float], detail: dict[str, Any]) -> None:
    target["races"] += 1
    target["raceDistance"] += int(float(detail.get("distance") or 0) > 0)
    target["raceSurface"] += int(bool(str(detail.get("surface") or "").strip()))
    target["raceCondition"] += int(bool(str(detail.get("condition") or detail.get("going") or "").strip()))

    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)]
    target["horses"] += len(horses)
    for h in horses:
        runs = h.get("allPastRuns") or h.get("recentRaces") or []
        runs = [r for r in runs if isinstance(r, dict)]
        n = len(runs)
        target["horsesNoRuns"] += int(n == 0)
        target["horsesLt3Runs"] += int(n < 3)
        target["horsesGe5Runs"] += int(n >= 5)
        target["runs"] += n
        ev = h.get("integratedEvaluation") if isinstance(h.get("integratedEvaluation"), dict) else {}
        target["horsesAudit"] += int(isinstance(ev.get("v218Audit") or ev.get("v217Audit"), dict) and bool(ev.get("v218Audit") or ev.get("v217Audit")))
        target["horsesResearch"] += int(isinstance(ev.get("researchFactors"), dict) and bool(ev.get("researchFactors")))
        for r in runs:
            target["runsFinish"] += int(float(r.get("finish") or r.get("finishPosition") or r.get("rank") or 0) > 0)
            target["runsFieldSize"] += int(float(r.get("fieldSize") or 0) > 0)
            target["runsSpeedIndex"] += int(r.get("speedIndex") not in (None, ""))
            target["runsTimed"] += int(float(r.get("timeSeconds") or 0) > 0 and float(r.get("distance") or 0) > 0)
            target["runsOpponentLevel"] += int(float(r.get("opponentLevel") or r.get("levelScore") or 0) > 0)
            target["runsPrize"] += int(float(r.get("racePrize1") or 0) > 0)

    ranking = detail.get("factorRanking") if isinstance(detail.get("factorRanking"), list) else []
    for row in ranking:
        if not isinstance(row, dict):
            continue
        fam = row.get("evidenceFamilyCounts") if isinstance(row.get("evidenceFamilyCounts"), dict) else {}
        for p in PILLARS:
            v = int(fam.get(p) or 0)
            target[f"familySum_{p}"] += v
            target[f"familyNonzero_{p}"] += int(v > 0)


def normalize(d: dict[str, float]) -> dict[str, Any]:
    races = max(1.0, d["races"])
    horses = max(1.0, d["horses"])
    runs = max(1.0, d["runs"])
    out: dict[str, Any] = dict(d)
    out.update({
        "avgFieldSize": round(d["horses"] / races, 3),
        "avgRunsPerHorse": round(d["runs"] / horses, 3),
        "horseNoRunsRate": round(d["horsesNoRuns"] / horses, 4),
        "horseLt3RunsRate": round(d["horsesLt3Runs"] / horses, 4),
        "horseGe5RunsRate": round(d["horsesGe5Runs"] / horses, 4),
        "runFinishRate": round(d["runsFinish"] / runs, 4),
        "runFieldSizeRate": round(d["runsFieldSize"] / runs, 4),
        "runSpeedIndexRate": round(d["runsSpeedIndex"] / runs, 4),
        "runTimedRate": round(d["runsTimed"] / runs, 4),
        "runOpponentLevelRate": round(d["runsOpponentLevel"] / runs, 4),
        "runPrizeRate": round(d["runsPrize"] / runs, 4),
        "horseAuditRate": round(d["horsesAudit"] / horses, 4),
        "horseResearchRate": round(d["horsesResearch"] / horses, 4),
        "raceDistanceRate": round(d["raceDistance"] / races, 4),
        "raceSurfaceRate": round(d["raceSurface"] / races, 4),
        "raceConditionRate": round(d["raceCondition"] / races, 4),
    })
    for p in PILLARS:
        out[f"avgFamilies_{p}"] = round(d[f"familySum_{p}"] / horses, 3)
        out[f"familyCoverage_{p}"] = round(d[f"familyNonzero_{p}"] / horses, 4)
    return out


def main() -> None:
    end = datetime.strptime(END_DATE, "%Y-%m-%d").date()
    dates = [(end - timedelta(days=i)).isoformat() for i in range(DAYS - 1, -1, -1)]
    by_circuit: dict[str, dict[str, float]] = defaultdict(init)
    usable = 0
    for ds in dates:
        url = API_BASE + "/api/day?" + urllib.parse.urlencode({"date": ds, "details": "1"})
        payload = base.api_json(url)
        for detail in payload.get("details") or []:
            if not isinstance(detail, dict) or not base.finish_order(detail):
                continue
            replay = base.scrub_for_replay(detail, ds)
            apply_core_marks(replay)
            circuit = str(replay.get("circuit") or "unknown")
            add(by_circuit[circuit], replay)
            usable += 1
    out = {
        "version": "arvexq-data-quality-audit-v1",
        "start": dates[0],
        "end": dates[-1],
        "usableRaces": usable,
        "byCircuit": {k: normalize(v) for k, v in sorted(by_circuit.items())},
        "warning": "Retrospective saved-detail completeness audit. It identifies source/evidence gaps but is not an exact contemporaneous feature snapshot.",
    }
    print("ARVEXQ_DATA_QUALITY_JSON=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
