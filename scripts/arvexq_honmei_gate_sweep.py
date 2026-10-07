#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from arvexq.prediction.factor_model import rank_factor_model
from arvexq.prediction.multi_head import attach_multi_head_signals
import scripts.arvexq_current_prediction_audit as base

API_BASE=os.environ.get("ARVEXQ_API_BASE",base.API_BASE).rstrip("/")
END_DATE=os.environ.get("ARVEXQ_END_DATE","2026-10-05")
DAYS=max(1,int(os.environ.get("ARVEXQ_DAYS","7") or 7))
PRIMARY=("ability","record","suitability","pace")


def features(detail:dict[str,Any])->dict[str,Any]|None:
    rows=rank_factor_model(detail.get("horses") or [],detail)
    if not rows:return None
    summary=attach_multi_head_signals(rows)
    leader=rows[0];runner=rows[1] if len(rows)>1 else None
    mh=leader.get("multiHead") or {};pr=leader.get("pillarRanks") or {};fam=leader.get("evidenceFamilyCounts") or {}
    return {
        "horseNumber":base.iv((leader.get("horse") or {}).get("horseNumber")),
        "coreWinAgree":base.iv(summary.get("winnerHorseNumber"))==base.iv((leader.get("horse") or {}).get("horseNumber")) and base.iv(mh.get("winRank"),999)==1,
        "strengthRank":base.iv(mh.get("strengthRank"),999),
        "coverage":base.iv(leader.get("primaryPillarCoverage")),
        "pillarTop3":sum(base.iv(pr.get(p),999)<=3 for p in PRIMARY),
        "families":sum(base.iv(fam.get(p)) for p in PRIMARY),
        "paceFamilies":base.iv(fam.get("pace")),
        "sample":base.iv(leader.get("sample")),
        "winGap":float(summary.get("winnerGap")) if summary.get("winnerGap") is not None else None,
        "pairwiseMargin":base.iv(leader.get("pairwiseWins"))-base.iv((runner or {}).get("pairwiseWins")),
    }


def gate(name:str,f:dict[str,Any])->bool:
    current=bool(f["coreWinAgree"] and f["strengthRank"]<=2 and f["coverage"]>=4 and f["pillarTop3"]>=3 and f["winGap"] is not None and f["winGap"]>0 and f["pairwiseMargin"]>0 and f["sample"]>=2 and f["families"]>=4)
    if name=="current":return current
    if name=="strict1":return current and f["strengthRank"]==1 and f["pillarTop3"]==4 and f["sample"]>=3 and f["paceFamilies"]>=1
    if name=="strict2":return current and f["strengthRank"]==1 and f["pillarTop3"]==4 and f["sample"]>=5 and f["families"]>=8 and f["paceFamilies"]>=1
    if name=="strict3":return current and f["strengthRank"]==1 and f["pillarTop3"]==4 and f["sample"]>=5 and f["families"]>=10 and f["paceFamilies"]>=1 and f["pairwiseMargin"]>=2
    return False


def empty()->dict[str,int]:return {"eligible":0,"wins":0,"top2":0,"top3":0}
def add(m:dict[str,int],order:list[int],no:int)->None:
    m["eligible"]+=1;p=order.index(no)+1 if no in order else 999
    m["wins"]+=int(p==1);m["top2"]+=int(p<=2);m["top3"]+=int(p<=3)
def rates(m:dict[str,int])->dict[str,Any]:
    n=m["eligible"];return {**m,"winRate":round(m["wins"]/n,4) if n else None,"top2Rate":round(m["top2"]/n,4) if n else None,"top3Rate":round(m["top3"]/n,4) if n else None}


def main()->None:
    end=datetime.strptime(END_DATE,"%Y-%m-%d").date();dates=[(end-timedelta(days=i)).isoformat() for i in range(DAYS-1,-1,-1)]
    split=max(1,len(dates)-2)
    buckets=defaultdict(empty)
    for di,ds in enumerate(dates):
        phase="train" if di<split else "validation"
        payload=base.api_json(API_BASE+"/api/day?"+urllib.parse.urlencode({"date":ds,"details":"1"}))
        for raw in payload.get("details") or []:
            if not isinstance(raw,dict):continue
            order=base.finish_order(raw)
            if not order:continue
            d=base.scrub_for_replay(raw,ds);f=features(d)
            if not f or not f["horseNumber"]:continue
            circuit=str(d.get("circuit") or "unknown")
            for name in ("current","strict1","strict2","strict3"):
                if gate(name,f):
                    add(buckets[(phase,circuit,name)],order,f["horseNumber"])
                    add(buckets[("all",circuit,name)],order,f["horseNumber"])
    out={"version":"arvexq-honmei-gate-sweep-v1","start":dates[0],"end":dates[-1],"trainEnd":dates[split-1],"validationStart":dates[split] if split<len(dates) else None,"results":{}}
    for (phase,circuit,name),m in sorted(buckets.items()):
        out["results"].setdefault(phase,{}).setdefault(circuit,{})[name]=rates(m)
    print("ARVEXQ_HONMEI_GATE_SWEEP_JSON="+json.dumps(out,ensure_ascii=False,separators=(",",":")))


if __name__=="__main__":main()
