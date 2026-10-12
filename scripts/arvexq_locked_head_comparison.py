#!/usr/bin/env python3
"""Compare only authentic pre-off locked candidate heads on equal races.

Pure audit, never changes marks. Post-race integration data are NOT features.
A candidate is scored only where the original sealed snapshot stored it before
the race, with real official 1st/2nd/3rd finishers.
"""
from __future__ import annotations
import json
import os
from collections import defaultdict
from datetime import date, timedelta
from scripts.arvexq_role_mark_audit import api_json, finish_order, iv

BASE=os.environ.get("ARVEXQ_API_BASE","https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
DAYS=int(os.environ.get("ARVEXQ_DAYS","7"))
END=date.fromisoformat(os.environ.get("ARVEXQ_END_DATE") or (date.today()-timedelta(days=1)).isoformat())
FIELDS=("baseline","coreRank","winHeadRank","p1Score")
def tally():
    return {x:{"races":0,"win":0,"top3":0,"sameAsBaseline":0} for x in FIELDS}
def locked_race(detail):
    lock=detail.get("preRacePrediction") or {}
    if lock.get("frozen") is not True or str(lock.get("raceId") or "") != str(detail.get("id") or ""):
        return None
    if str(lock.get("raceDate") or "") != str(detail.get("date") or ""):
        return None
    ds=str(detail.get("date") or "")
    tm=str(detail.get("startTime") or detail.get("scheduledStartTime") or "")[:5]
    try:
        from datetime import datetime
        post=datetime.fromisoformat(ds+"T"+tm+":00+09:00").timestamp()
        if not (0<int(lock.get("capturedAtEpoch") or 0)<post):
            return None
    except (ValueError,TypeError):
        return None
    order=finish_order(detail)
    if len(order)<3 or len({*order[:3]})<3:
        return None
    rows=lock.get("horses") or []
    if len(rows)<3:return None
    seen=set();original=[];candidates={}
    for item in rows:
        if not isinstance(item,dict):return None
        no=iv(item.get("horseNumber"))
        if not no or no in seen:return None
        seen.add(no)
        original.append(item)
    hon=[iv(x.get("horseNumber")) for x in original if x.get("mark")=="◎"]
    if len(hon)!=1:return None
    candidates["baseline"]=hon[0]
    def ranked(key,minimum=None):
        arr=[]
        for x in original:
            v=(x.get("lockedEvaluation") or {}).get(key)
            try:
                value=float(v)
                if not (value==value):return None
                if minimum is not None and value<minimum:return None
                arr.append((value,iv(x["horseNumber"])))
            except (ValueError,TypeError):
                return None
        if len(arr)<3:return None
        arr.sort(key=lambda z:(z[0],z[1]))
        if arr[0][0]==arr[1][0]:return None
        return arr[0][1]
    for key,out in [("coreAbilityRank","coreRank"),("winHeadRank","winHeadRank")]:
        got=ranked(key,1)
        if got:candidates[out]=got
    # P1 is a score, higher is better; tied field is not evidence of superiority.
    scores=[]
    for item in original:
        v=(item.get("lockedEvaluation") or {}).get("p1Score")
        try:scores.append((float(v),iv(item["horseNumber"])))
        except (ValueError,TypeError):scores=[];break
    if len(scores)>=3:
        scores.sort(key=lambda z:(-z[0],z[1]))
        if scores[0][0]>scores[1][0]:candidates["p1Score"]=scores[0][1]
    return order,candidates

def main():
    stats=defaultdict(tally)
    detail_counts=defaultdict(int)
    for i in range(DAYS-1,-1,-1):
        day=(END-timedelta(days=i)).isoformat()
        payload=api_json(BASE+"/api/day?date="+day+"&details=1")
        details=payload.get("details") or []
        for detail in details:
            if not isinstance(detail,dict):continue
            item=locked_race(detail)
            if not item:continue
            order,choices=item
            circ=str(detail.get("circuit") or "unknown")
            period="early" if i>=3 else "recent"
            for group in ("all",circ,period,circ+":"+period):
                detail_counts[group]+=1
                s=stats[group]
                for head,n in choices.items():
                    o=s[head];o["races"]+=1
                    o["win"]+=int(n==order[0])
                    o["top3"]+=int(n in order[:3])
                    o["sameAsBaseline"]+=int(n==choices["baseline"])
        print("LOCKED_HEAD_DAY",day,"detailCount",len(details))
    def summary(group):
        return {k:{**v,"winRate":round(v["win"]/v["races"],4) if v["races"] else None,
                       "top3Rate":round(v["top3"]/v["races"],4) if v["races"] else None}
                for k,v in stats[group].items()}
    results={"version":"arvexq-locked-head-comparison-v1",
             "period":str(END-timedelta(days=DAYS-1))+"/"+str(END),
             "dateSplit":"early=older four days/recent=latest three",
             "sampleCounts":dict(detail_counts),
             "all":summary("all"),"early":summary("early"),"recent":summary("recent"),
             "central":summary("中央"),"local":summary("地方"),
             "notes":"Only frozen preoff data. Coverage differs by head; NOT causal and not a model patch."}
    print("ARVEXQ_LOCKED_HEAD_JSON="+json.dumps(results,ensure_ascii=False,separators=(",",":")))
if __name__=="__main__":
    main()
