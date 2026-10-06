#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

PATH = Path("app.py")
text = PATH.read_text(encoding="utf-8")
original = text

old_merge = '''def _jra_merge_runs(a:list[dict],b:list[dict],limit:int=5)->list[dict]:
    allr=[];seen=set()
    for r in list(a or [])+list(b or []):
        if not isinstance(r,dict):continue
        key=(str(r.get("date") or ""),str(r.get("track") or ""),str(r.get("title") or ""),int(r.get("distance") or 0))
        if key in seen:continue
        seen.add(key);allr.append(r)
    allr.sort(key=lambda r:str(r.get("date") or ""),reverse=True)
    return allr[:limit]
'''
new_merge = '''def _jra_run_key(r:dict)->tuple:
    """Stable horse-start key across JRA/profile/supplemental sources.

    A horse cannot run twice at the same track on the same date, so title wording
    must not prevent two representations of the same start from being merged.
    """
    date=str(r.get("date") or "");track=str(r.get("track") or "");distance=int(r.get("distance") or 0)
    if date:return (date,track,distance)
    return (date,track,distance,str(r.get("title") or ""),str(r.get("raceId") or ""))


def _jra_run_value_present(key:str,value)->bool:
    if value in (None,"",[],{},"不明"):return False
    if key in {"finish","fieldSize","distance","timeSeconds","carriedWeight","racePrize1","raceNumber"}:
        try:return float(value)>0
        except (TypeError,ValueError):return False
    return True


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
'''
if old_merge in text:
    text = text.replace(old_merge, new_merge, 1)
elif "def _jra_merge_run_fields(" not in text:
    raise SystemExit("JRA merge block not found")

old_supplement = '''    if supplement_profiles:
        def supplement(h):
            if len(h.get("recentRaces") or [])>=5 or h.get("_jraCareerComplete"):return h
            extra=_jra_profile_runs(h.get("_jraHorseCname") or "",date,5)
            h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],extra,5)
            return h
'''
new_supplement = '''    if supplement_profiles:
        def supplement(h):
            existing=h.get("recentRaces") or []
            if _jra_history_complete(existing,bool(h.get("_jraCareerComplete"))):return h
            extra=_jra_profile_runs(h.get("_jraHorseCname") or "",date,5)
            h["recentRaces"]=_jra_merge_runs(existing,extra,5)
            return h
'''
if old_supplement in text:
    text = text.replace(old_supplement, new_supplement, 1)
elif "if _jra_history_complete(existing,bool(h.get(\"_jraCareerComplete\"))):return h" not in text:
    raise SystemExit("JRA profile supplement block not found")

# Relax whitespace/punctuation assumptions in JRA past-start cards.
text = text.replace(
    'fm=re.search(r"(?:^|\\s)(\\d{1,2})着(?:\\s|$)",txt)',
    'fm=re.search(r"(?<!\\d)(\\d{1,2})\\s*着(?!\\d)",txt)',
    1,
)
text = text.replace('fsm=re.search(r"(\\d{1,2})頭",txt)', 'fsm=re.search(r"(\\d{1,2})\\s*頭",txt)', 1)

# Official JRA result pages also carry first-prize data. Preserve it in the
# canonical race so later central-history snapshots can supply class strength.
old_result_tail = '''    payouts=_parse_payouts(soup)
    status="確定" if payouts or re.search(r"確定",full) else "速報"
    return {"date":date,"track":track,"raceNumber":race_no,"title":title,"distance":distance,"surface":surface,"condition":condition,"weather":weather,"fieldSize":len(finishers),"startTime":start,"scheduledStartTime":start,"result":{"status":status,"finishers":finishers,"source":"JRA公式","payouts":payouts},"resultCname":result_cname,"source":"JRA公式結果"}
'''
new_result_tail = '''    payouts=_parse_payouts(soup)
    status="確定" if payouts or re.search(r"確定",full) else "速報"
    prize1=0
    pm=re.search(r"1着\\s*([\\d,.]+)",full)
    if pm:
        try:prize1=int(float(pm.group(1).replace(",",""))*10000)
        except (TypeError,ValueError):prize1=0
    return {"date":date,"track":track,"raceNumber":race_no,"title":title,"distance":distance,"surface":surface,"condition":condition,"weather":weather,"fieldSize":len(finishers),"racePrize1":prize1,"startTime":start,"scheduledStartTime":start,"result":{"status":status,"finishers":finishers,"source":"JRA公式","payouts":payouts},"resultCname":result_cname,"source":"JRA公式結果"}
'''
if old_result_tail in text:
    text = text.replace(old_result_tail, new_result_tail, 1)
elif '"racePrize1":prize1,"startTime":start' not in text:
    raise SystemExit("JRA result return block not found")

old_merge_result = 'for k in ("title","distance","surface","condition","weather","fieldSize","startTime","scheduledStartTime","resultCname"):'
new_merge_result = 'for k in ("title","distance","surface","condition","weather","fieldSize","racePrize1","startTime","scheduledStartTime","resultCname"):'
if old_merge_result in text:
    text = text.replace(old_merge_result, new_merge_result, 1)
elif new_merge_result not in text:
    raise SystemExit("official result merge field list not found")

PATH.write_text(text, encoding="utf-8")
print("JRA history quality patch", "updated" if text != original else "already-current")
