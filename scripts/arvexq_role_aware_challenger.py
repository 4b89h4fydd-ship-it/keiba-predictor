#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import statistics
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from arvexq.prediction.factor_model import rank_factor_model
from arvexq.prediction.multi_head import attach_multi_head_signals
from arvexq.prediction.final_marks import apply_core_marks
import scripts.arvexq_current_prediction_audit as base

API_BASE = os.environ.get("ARVEXQ_API_BASE", base.API_BASE).rstrip("/")
END_DATE = os.environ.get("ARVEXQ_END_DATE", "2026-10-05")
DAYS = max(1, int(os.environ.get("ARVEXQ_DAYS", "7") or 7))
MARK_ORDER = ("◎", "○", "▲", "☆+", "☆", "△", "注")


def f(v: Any) -> float | None:
    try:
        x=float(v); return x if x==x else None
    except (TypeError,ValueError): return None


def iv(v: Any, default:int=0)->int:
    try:return int(float(v))
    except (TypeError,ValueError):return default


def med(vals:list[float|None])->float|None:
    a=[float(v) for v in vals if v is not None]
    return float(statistics.median(a)) if a else None


def rel(values:list[float|None])->list[float|None]:
    valid=sorted(v for v in values if v is not None)
    if not valid:return [None]*len(values)
    if len(valid)==1:return [.5 if v is not None else None for v in values]
    out=[]
    for v in values:
        if v is None:out.append(None);continue
        less=sum(x<v for x in valid);eq=sum(x==v for x in valid)
        out.append((less+(eq-1)/2)/(len(valid)-1))
    return out


def history_roles(h:dict[str,Any])->tuple[float|None,float|None,float|None]:
    runs=h.get("allPastRuns") or h.get("recentRaces") or []
    top2=top3=done=0;late=[]
    for rr in (runs[:5] if isinstance(runs,list) else []):
        if not isinstance(rr,dict):continue
        fin=iv(rr.get("finish",rr.get("finishPosition",rr.get("rank"))))
        if fin>0:
            done+=1;top2+=int(fin<=2);top3+=int(fin<=3)
        field=max(0,iv(rr.get("fieldSize")))
        cp=rr.get("cornerPositions") if isinstance(rr.get("cornerPositions"),list) else []
        if field>=4 and cp and fin>0:
            last=iv(cp[-1])
            if last>0:
                late.append(max(0.0,min(1.0,.5+(last-fin)/max(3,field-1))))
    return (top2/done if done else None,top3/done if done else None,med(late))


def prepare_rows(detail:dict[str,Any])->list[dict[str,Any]]:
    rows=rank_factor_model(detail.get("horses") or [],detail)
    if not rows:return []
    attach_multi_head_signals(rows)
    h2=[];h3=[];late=[]
    for row in rows:
        a,b,c=history_roles(row["horse"]);h2.append(a);h3.append(b);late.append(c)
    r2=rel(h2);r3=rel(h3);rl=rel(late)
    for i,row in enumerate(rows):
        mh=row.get("multiHead") or {}
        # Role heads are medians of distinct pre-race evidence routes, never odds/popularity.
        # P2 emphasises repeatable strength + recent top-two history + suitability/pace.
        row["p2RoleScore"]=med([r2[i],row.get("record"),row.get("suitability"),row.get("pace"),row.get("strengthHeadScore")])
        # P3 emphasises repeatable top-three history + suitability + pace/support + late recovery.
        row["p3RoleScore"]=med([r3[i],row.get("record"),row.get("suitability"),row.get("pace"),row.get("support"),rl[i]])
        row["coverageRoleScore"]=max(v for v in [row.get("p2RoleScore"),row.get("p3RoleScore"),row.get("winHeadScore"),row.get("upsideHeadScore")] if v is not None)
        row["winRank"]=iv(mh.get("winRank"),999)
        row["strengthRank"]=iv(mh.get("strengthRank"),999)
        row["upsideRank"]=iv(mh.get("upsideRank"),999)
    return rows


def pick(rows:list[dict[str,Any]],key:str,exclude:set[int])->dict[str,Any]|None:
    candidates=[r for r in rows if iv((r.get("horse") or {}).get("horseNumber")) not in exclude and r.get(key) is not None]
    candidates.sort(key=lambda r:(-float(r[key]),iv((r.get("horse") or {}).get("horseNumber"),999)))
    return candidates[0] if candidates else None


def marks_from_variant(detail:dict[str,Any],variant:str)->dict[int,str]:
    d=copy.deepcopy(detail)
    rows=prepare_rows(d)
    if not rows:return {}
    core=sorted(rows,key=lambda r:(iv(r.get("rank"),999),iv((r.get("horse") or {}).get("horseNumber"),999)))
    win=sorted(rows,key=lambda r:(iv(r.get("winRank"),999),iv(r.get("strengthRank"),999),iv((r.get("horse") or {}).get("horseNumber"),999)))
    used:set[int]=set();out:dict[int,str]={}
    def take(row:dict[str,Any]|None,mark:str)->None:
        if not row:return
        no=iv((row.get("horse") or {}).get("horseNumber"))
        if no>0 and no not in used:out[no]=mark;used.add(no)
    if variant.startswith("coreWinner"):
        take(core[0],"◎")
    else:
        take(win[0],"◎")
    take(pick(rows,"p2RoleScore",used),"○")
    take(pick(rows,"p3RoleScore",used),"▲")

    # ☆+ remains a genuine win-upside lane, not a generic fourth rank.
    plus=[r for r in rows if iv((r.get("horse") or {}).get("horseNumber")) not in used and (r.get("multiHead") or {}).get("upsideCandidate")]
    plus.sort(key=lambda r:(iv(r.get("upsideRank"),999),iv(r.get("winRank"),999),iv((r.get("horse") or {}).get("horseNumber"),999)))
    if plus:take(plus[0],"☆+")

    if variant.endswith("Recall"):
        rest=sorted([r for r in rows if iv((r.get("horse") or {}).get("horseNumber")) not in used],key=lambda r:(-float(r.get("coverageRoleScore") if r.get("coverageRoleScore") is not None else -1),iv(r.get("rank"),999),iv((r.get("horse") or {}).get("horseNumber"),999)))
    else:
        rest=[r for r in core if iv((r.get("horse") or {}).get("horseNumber")) not in used]
    for mark,row in zip(("☆","△","注"),rest[:3]):take(row,mark)
    return out


def current_marks(detail:dict[str,Any])->dict[int,str]:
    d=copy.deepcopy(detail);apply_core_marks(d);out={}
    for h in d.get("horses") or []:
        if not isinstance(h,dict):continue
        no=iv(h.get("horseNumber"));e=h.get("integratedEvaluation") if isinstance(h.get("integratedEvaluation"),dict) else {};mark=str(e.get("mark") or "")
        if no>0 and mark:out[no]=mark
    return out


def empty()->dict[str,int]:
    return {"races":0,"honmeiWin":0,"maruSecond":0,"triangleThird":0,"honmeiTop3":0,"maruTop3":0,"triangleTop3":0,"podiumAllMarked":0,"podiumAtLeast2Marked":0,"winnerMarked":0,"secondMarked":0,"thirdMarked":0,"markSetSize":0}


def add(m:dict[str,int],order:list[int],marks:dict[int,str])->None:
    if len(order)<3 or not marks:return
    def horse(mark:str)->int:return next((n for n,x in marks.items() if x==mark),0)
    a,b,c=horse("◎"),horse("○"),horse("▲");top3=order[:3];covered=sum(bool(marks.get(n)) for n in top3)
    m["races"]+=1;m["honmeiWin"]+=int(a==top3[0]);m["maruSecond"]+=int(b==top3[1]);m["triangleThird"]+=int(c==top3[2]);m["honmeiTop3"]+=int(a in top3);m["maruTop3"]+=int(b in top3);m["triangleTop3"]+=int(c in top3);m["podiumAllMarked"]+=int(covered==3);m["podiumAtLeast2Marked"]+=int(covered>=2);m["winnerMarked"]+=int(bool(marks.get(top3[0])));m["secondMarked"]+=int(bool(marks.get(top3[1])));m["thirdMarked"]+=int(bool(marks.get(top3[2])));m["markSetSize"]+=len(marks)


def rates(m:dict[str,int])->dict[str,Any]:
    n=m["races"];out=dict(m)
    for k in ("honmeiWin","maruSecond","triangleThird","honmeiTop3","maruTop3","triangleTop3","podiumAllMarked","podiumAtLeast2Marked","winnerMarked","secondMarked","thirdMarked"):
        out[k+"Rate"]=round(m[k]/n,4) if n else None
    out["avgMarkSetSize"]=round(m["markSetSize"]/n,3) if n else None
    return out


def main()->None:
    end=datetime.strptime(END_DATE,"%Y-%m-%d").date();dates=[(end-timedelta(days=i)).isoformat() for i in range(DAYS-1,-1,-1)]
    variants=("current","coreWinnerRoles","coreWinnerRolesRecall","winWinnerRoles","winWinnerRolesRecall")
    total={v:empty() for v in variants};circuits=defaultdict(lambda:{v:empty() for v in variants});days={d:{v:empty() for v in variants} for d in dates}
    compared=0
    for ds in dates:
        payload=base.api_json(API_BASE+"/api/day?"+urllib.parse.urlencode({"date":ds,"details":"1"}))
        for detail in payload.get("details") or []:
            if not isinstance(detail,dict):continue
            order=base.finish_order(detail)
            if len(order)<3:continue
            replay=base.scrub_for_replay(detail,ds);circuit=str(detail.get("circuit") or "unknown")
            variant_marks={"current":current_marks(replay)}
            for v in variants[1:]:variant_marks[v]=marks_from_variant(replay,v)
            if not all(variant_marks[v] for v in variants):continue
            compared+=1
            for v in variants:
                add(total[v],order,variant_marks[v]);add(circuits[circuit][v],order,variant_marks[v]);add(days[ds][v],order,variant_marks[v])
    out={"version":"arvexq-role-aware-challenger-v1","start":dates[0],"end":dates[-1],"comparedRaces":compared,"overall":{v:rates(total[v]) for v in variants},"byCircuit":{c:{v:rates(m) for v,m in q.items()} for c,q in circuits.items()},"byDay":{d:{v:rates(m) for v,m in q.items()} for d,q in days.items()},"variantNotes":{"current":"current four-pillar marks","coreWinnerRoles":"keep current core ◎; ○/▲ use semantic P2/P3 medians; lower marks follow core","coreWinnerRolesRecall":"same core ◎/role ○▲; lower marks prioritize max role coverage","winWinnerRoles":"◎ uses multi-head win head; ○/▲ role heads; lower core","winWinnerRolesRecall":"win-head ◎ + role ○▲ + role-recall lower marks"},"warning":"Retrospective challenger. Result fields and target-date history are scrubbed, but saved detail is not an immutable historical feature snapshot. No production promotion from this result alone."}
    print("ARVEXQ_ROLE_AWARE_CHALLENGER_JSON="+json.dumps(out,ensure_ascii=False,separators=(",",":")))


if __name__=="__main__":main()
