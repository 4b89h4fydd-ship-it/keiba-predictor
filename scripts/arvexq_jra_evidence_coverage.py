#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

API_BASE = os.environ.get("ARVEXQ_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
DAYS = max(1, int(os.environ.get("ARVEXQ_DAYS", "7") or 7))
END_DATE = os.environ.get("ARVEXQ_END_DATE", "")

RUN_FIELDS: dict[str, tuple[str, ...]] = {
    "date": ("date", "raceDate", "day"),
    "finish": ("finish", "finishPosition", "rank"),
    "fieldSize": ("fieldSize", "field", "runners"),
    "time": ("timeSeconds", "time", "resultTime"),
    "speedIndex": ("speedIndex",),
    "last3F": ("last3F", "last3FSeconds", "last3FIndex", "sectionalIndex", "closingIndex", "lateSpeedIndex"),
    "earlyPace": ("earlySpeedIndex", "first3FIndex", "paceIndex", "first3F", "early3F"),
    "corners": ("cornerPositions", "corners", "passingOrder"),
    "corner4": ("corner4", "fourthCorner", "position4", "lastCornerPosition"),
    "track": ("track",),
    "distance": ("distance",),
    "surface": ("surface",),
    "condition": ("condition", "going"),
    "racePrize1": ("racePrize1", "firstPrize", "prize"),
    "opponentLevel": ("opponentLevel", "levelScore", "raceLevel"),
    "carriedWeight": ("carriedWeight", "weight", "assignedWeight"),
    "bodyWeight": ("bodyWeight",),
}

AUDIT_FIELDS = ("trueRun", "sectional", "positionScenario", "stateConsistency", "trackSpeedFit", "hiddenEffort", "evidence", "conditions")
RESEARCH_FIELDS = ("ability", "classLevel", "form", "pace", "suitability", "connections", "pedigree")
COMPONENT_FIELDS = ("lapScore", "distanceFit", "courseFit", "trackFit", "goingFit", "conditionFit", "opponentLevelScore", "racePerformance", "representative")
BIAS_FIELDS = ("sameDayMarkAdjustment", "biasScore", "trackBiasScore")


def present(value: Any) -> bool:
    if value is None or value == "" or value == [] or value == {}:
        return False
    try:
        if isinstance(value, float) and value != value:
            return False
    except Exception:
        pass
    return True


def alias_present(row: dict[str, Any], aliases: tuple[str, ...]) -> bool:
    return any(present(row.get(key)) for key in aliases)


def first_value(row: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for key in aliases:
        if present(row.get(key)):
            return row.get(key)
    return None


def run_key(run: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(first_value(run, ("date", "raceDate", "day")) or ""),
        str(run.get("track") or ""),
        str(run.get("raceNumber") or run.get("raceNo") or ""),
        str(run.get("distance") or ""),
        str(run.get("raceName") or run.get("title") or ""),
    )


def merged_union(all_runs: list[dict[str, Any]], recent_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str, str, str, str], int] = {}
    for run in [*all_runs, *recent_runs]:
        if not isinstance(run, dict):
            continue
        key = run_key(run)
        # Empty identity is not safe to merge; preserve it independently.
        if not any(key):
            out.append(dict(run))
            continue
        idx = by_key.get(key)
        if idx is None:
            by_key[key] = len(out)
            out.append(dict(run))
            continue
        merged = dict(out[idx])
        for field, value in run.items():
            if not present(merged.get(field)) and present(value):
                merged[field] = value
        out[idx] = merged
    return out


def final_order(detail: dict[str, Any]) -> list[int]:
    result = detail.get("result") if isinstance(detail.get("result"), dict) else {}
    rows = result.get("finishers") or result.get("results") or result.get("top5") or []
    found: list[tuple[int, int]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            rank = int(float(row.get("finish", row.get("rank", row.get("position", 0))) or 0))
            no = int(float(row.get("horseNumber", row.get("number", row.get("horseNo", 0))) or 0))
        except (TypeError, ValueError):
            continue
        if rank > 0 and no > 0:
            found.append((rank, no))
    return [no for rank, no in sorted(found)]


def api_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"user-agent": "ARVEXQ-jra-evidence-audit/1.0", "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def rate_map(counts: Counter[str], denominator: int) -> dict[str, dict[str, float | int]]:
    return {
        key: {"count": int(counts.get(key, 0)), "rate": round(counts.get(key, 0) / denominator, 4) if denominator else None}
        for key in sorted(counts)
    }


def resolved_end() -> date:
    if END_DATE:
        return datetime.strptime(END_DATE, "%Y-%m-%d").date()
    return date.today() - timedelta(days=1)


def main() -> None:
    end = resolved_end()
    dates = [(end - timedelta(days=i)).isoformat() for i in range(DAYS - 1, -1, -1)]

    races = finals = horses = 0
    all_only = recent_only = both_lists = neither = 0
    current_runs_total = union_runs_total = 0
    current_run_field = Counter()
    union_run_field = Counter()
    current_horse_any = Counter()
    union_horse_any = Counter()
    eval_audit = Counter()
    eval_research = Counter()
    eval_components = Counter()
    eval_bias = Counter()
    list_gain_horses = Counter()
    winner_context = defaultdict(lambda: Counter(races=0, winnerHasAudit=0, winnerHasResearch=0, winnerHasClass=0, winnerHasSectional=0, winnerHasCorners=0))

    for ds in dates:
        url = API_BASE + "/api/day?" + urllib.parse.urlencode({"date": ds, "details": "1"})
        payload = api_json(url)
        for detail in payload.get("details") or []:
            if not isinstance(detail, dict) or str(detail.get("circuit") or "") != "中央":
                continue
            races += 1
            order = final_order(detail)
            if order:
                finals += 1
            by_no = {}
            for horse in detail.get("horses") or []:
                if not isinstance(horse, dict):
                    continue
                horses += 1
                try:
                    no = int(float(horse.get("horseNumber") or 0))
                except (TypeError, ValueError):
                    no = 0
                if no > 0:
                    by_no[no] = horse

                all_runs = [r for r in (horse.get("allPastRuns") or []) if isinstance(r, dict)]
                recent_runs = [r for r in (horse.get("recentRaces") or []) if isinstance(r, dict)]
                if all_runs and recent_runs:
                    both_lists += 1
                elif all_runs:
                    all_only += 1
                elif recent_runs:
                    recent_only += 1
                else:
                    neither += 1

                current = all_runs or recent_runs
                union = merged_union(all_runs, recent_runs)
                current_runs_total += len(current)
                union_runs_total += len(union)
                if len(union) > len(current):
                    list_gain_horses["moreRuns"] += 1

                current_any = set()
                union_any = set()
                for run in current:
                    for field, aliases in RUN_FIELDS.items():
                        if alias_present(run, aliases):
                            current_run_field[field] += 1
                            current_any.add(field)
                for run in union:
                    for field, aliases in RUN_FIELDS.items():
                        if alias_present(run, aliases):
                            union_run_field[field] += 1
                            union_any.add(field)
                for field in current_any:
                    current_horse_any[field] += 1
                for field in union_any:
                    union_horse_any[field] += 1
                for field in RUN_FIELDS:
                    if field not in current_any and field in union_any:
                        list_gain_horses[field] += 1

                ev = horse.get("integratedEvaluation") if isinstance(horse.get("integratedEvaluation"), dict) else {}
                audit = ev.get("v218Audit") or ev.get("v217Audit") or {}
                if not isinstance(audit, dict):
                    audit = {}
                research = ev.get("researchFactors") if isinstance(ev.get("researchFactors"), dict) else {}
                components = ev.get("components") if isinstance(ev.get("components"), dict) else {}
                for field in AUDIT_FIELDS:
                    if present(audit.get(field)):
                        eval_audit[field] += 1
                for field in RESEARCH_FIELDS:
                    if present(research.get(field)):
                        eval_research[field] += 1
                for field in COMPONENT_FIELDS:
                    if present(components.get(field)) or present(horse.get(field)):
                        eval_components[field] += 1
                for field in BIAS_FIELDS:
                    if present(ev.get(field)) or present(horse.get(field)):
                        eval_bias[field] += 1

            if order and order[0] in by_no:
                winner = by_no[order[0]]
                ctx = winner_context[str(detail.get("track") or "unknown")]
                ctx["races"] += 1
                ev = winner.get("integratedEvaluation") if isinstance(winner.get("integratedEvaluation"), dict) else {}
                audit = ev.get("v218Audit") or ev.get("v217Audit") or {}
                research = ev.get("researchFactors") if isinstance(ev.get("researchFactors"), dict) else {}
                components = ev.get("components") if isinstance(ev.get("components"), dict) else {}
                wruns = merged_union(
                    [r for r in (winner.get("allPastRuns") or []) if isinstance(r, dict)],
                    [r for r in (winner.get("recentRaces") or []) if isinstance(r, dict)],
                )
                if isinstance(audit, dict) and any(present(audit.get(k)) for k in AUDIT_FIELDS):
                    ctx["winnerHasAudit"] += 1
                if isinstance(research, dict) and any(present(research.get(k)) for k in RESEARCH_FIELDS):
                    ctx["winnerHasResearch"] += 1
                if (isinstance(components, dict) and present(components.get("opponentLevelScore"))) or any(alias_present(r, RUN_FIELDS["opponentLevel"]) or alias_present(r, RUN_FIELDS["racePrize1"]) for r in wruns):
                    ctx["winnerHasClass"] += 1
                if any(alias_present(r, RUN_FIELDS["last3F"]) for r in wruns):
                    ctx["winnerHasSectional"] += 1
                if any(alias_present(r, RUN_FIELDS["corners"]) or alias_present(r, RUN_FIELDS["corner4"]) for r in wruns):
                    ctx["winnerHasCorners"] += 1

    output = {
        "version": "arvexq-jra-evidence-coverage-v1",
        "start": dates[0] if dates else None,
        "end": dates[-1] if dates else None,
        "races": races,
        "finalRaces": finals,
        "horses": horses,
        "historyLists": {
            "both": both_lists,
            "allPastOnly": all_only,
            "recentOnly": recent_only,
            "neither": neither,
            "currentChosenRuns": current_runs_total,
            "mergedUnionRuns": union_runs_total,
            "unionExtraRuns": union_runs_total - current_runs_total,
        },
        "currentRunFieldCoverage": rate_map(current_run_field, current_runs_total),
        "unionRunFieldCoverage": rate_map(union_run_field, union_runs_total),
        "currentHorseAnyCoverage": rate_map(current_horse_any, horses),
        "unionHorseAnyCoverage": rate_map(union_horse_any, horses),
        "horsesGainingEvidenceFromUnion": dict(sorted(list_gain_horses.items())),
        "evaluationCoverage": {
            "audit": rate_map(eval_audit, horses),
            "research": rate_map(eval_research, horses),
            "components": rate_map(eval_components, horses),
            "bias": rate_map(eval_bias, horses),
        },
        "winnerEvidenceByTrack": {track: dict(counts) for track, counts in sorted(winner_context.items())},
        "warning": "Coverage audit only. It does not infer missing values, create synthetic lap data, or alter production prediction.",
    }
    print("ARVEXQ_JRA_EVIDENCE_COVERAGE_JSON=" + json.dumps(output, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
