"""Extracted legacy behavior; network and stores stay outside this module."""
from __future__ import annotations

import json


def _snapshot_final(detail: dict) -> bool:
    result=detail.get("result") or {}
    return result.get("status")=="確定" and bool(result.get("finishers"))


def _result_has_podium(detail: dict | None) -> bool:
    result=(detail or {}).get("result") or {}
    ranks={int(x.get("finish") or 0) for x in (result.get("finishers") or []) if isinstance(x,dict)}
    return all(i in ranks for i in (1,2,3))


def _bootstrap_display_ready(d:dict|None)->bool:
    """Enough data to open/render the race immediately."""
    if not isinstance(d,dict):return False
    return bool((d.get("horses") or []) or d.get("result"))


def _bootstrap_detail_ready(d:dict|None)->bool:
    return _bootstrap_display_ready(d)


def _merge_card_rows_preserve(base:dict, fresh_rows:list[dict])->dict:
    """Refresh today's card fields without deleting history/metrics already collected."""
    old_horses=base.get("horses") or []
    by_no={int(h.get("horseNumber") or 0):h for h in old_horses if int(h.get("horseNumber") or 0)>0}
    by_name={str(h.get("name") or ""):h for h in old_horses if h.get("name")}
    merged=[]
    for fresh in fresh_rows or []:
        no=int(fresh.get("horseNumber") or 0)
        old=by_no.get(no) or by_name.get(str(fresh.get("name") or "")) or {}
        z=json.loads(json.dumps(old,ensure_ascii=False,default=str)) if old else {}
        for k,v in fresh.items():
            if k in {"recentRaces","allPastRuns","precomputedMetrics","integratedEvaluation",
                     "jockeyStats","trainerStats","jockeyProfile","trainerProfile","prizeMoneyAtRace"}:
                continue
            if v not in (None,"",[],{}):z[k]=v
        # preserve rich local data
        for k in ("recentRaces","allPastRuns","precomputedMetrics","integratedEvaluation",
                  "jockeyStats","trainerStats","jockeyProfile","trainerProfile","prizeMoneyAtRace",
                  "pedigree","representativeRun"):
            if old.get(k) not in (None,"",[],{}):z[k]=old.get(k)
        z.setdefault("recentRaces",[])
        z.setdefault("jockeyStats",{})
        z.setdefault("trainerStats",{})
        z.setdefault("jockeyProfile",{})
        z.setdefault("trainerProfile",{})
        merged.append(z)
    if merged:
        base["horses"]=merged
        base["fieldSize"]=len(merged)
    return base

