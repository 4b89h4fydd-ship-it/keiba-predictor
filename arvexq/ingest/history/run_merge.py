"""Extracted legacy behavior; network and stores stay outside this module."""
from __future__ import annotations

from arvexq.ingest.pure_parsers import _jra_run_key, _jra_run_value_present


def _jra_merge_run_fields(base:dict,incoming:dict)->dict:
    """Merge duplicate starts field-by-field instead of discarding richer data."""
    out=dict(base or {})
    for key,value in (incoming or {}).items():
        if not _jra_run_value_present(key,out.get(key)) and _jra_run_value_present(key,value):out[key]=value
        elif key=="cornerPositions" and value and len(value)>len(out.get(key) or []):out[key]=value
    sources=[]
    for src in (str((base or {}).get("source") or ""),str((incoming or {}).get("source") or "")):
        if src and src not in sources:sources.append(src)
    if sources:out["source"]=" + ".join(sources)
    return out


def _jra_run_core_complete(r:dict)->bool:
    try:finish=int(r.get("finish") or 0);field=int(r.get("fieldSize") or 0);distance=int(r.get("distance") or 0)
    except (TypeError,ValueError):return False
    return bool(str(r.get("date") or "") and str(r.get("track") or "") and finish>0 and field>1 and distance>0)


def _jra_history_complete(runs:list[dict],career_complete:bool=False)->bool:
    rows=[r for r in (runs or []) if isinstance(r,dict)]
    target=min(5,len(rows)) if career_complete else 5
    if target==0:return bool(career_complete)
    return len(rows)>=target and sum(1 for r in rows[:target] if _jra_run_core_complete(r))>=target


def _jra_merge_runs(a:list[dict],b:list[dict],limit:int=5)->list[dict]:
    merged={};order=[]
    for r in list(a or [])+list(b or []):
        if not isinstance(r,dict):continue
        key=_jra_run_key(r)
        if key not in merged:
            merged[key]=dict(r);order.append(key)
        else:merged[key]=_jra_merge_run_fields(merged[key],r)
    allr=[merged[k] for k in order]
    allr.sort(key=lambda r:str(r.get("date") or ""),reverse=True)
    return allr[:limit]


def _merge_fast_history(detail:dict, history_rows:list[dict])->dict:
    by_no={int(h.get("horseNumber") or 0):h for h in detail.get("horses",[]) or []}
    by_name={str(h.get("name") or ""):h for h in detail.get("horses",[]) or [] if h.get("name")}
    for row in history_rows or []:
        h=by_no.get(int(row.get("horseNumber") or 0)) or by_name.get(str(row.get("name") or ""))
        if not h:continue
        runs=list(row.get("recentRaces") or [])
        if runs:
            old=list(h.get("allPastRuns") or h.get("recentRaces") or [])
            merged=_jra_merge_runs(old,runs,max(5,len(old)+len(runs)))
            h["recentRaces"]=merged[:5]
            h["allPastRuns"]=merged
    return detail

