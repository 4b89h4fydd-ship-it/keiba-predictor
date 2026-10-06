#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable

API_BASE = os.environ.get("ARVEXQ_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
END_DATE = os.environ.get("ARVEXQ_END_DATE", "2026-10-05")
DAYS = max(1, int(os.environ.get("ARVEXQ_DAYS", "7") or 7))


def iv(v: Any, default: int = 0) -> int:
    try: return int(float(v))
    except (TypeError, ValueError): return default


def fv(v: Any) -> float | None:
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def api_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"user-agent": "ARVEXQ-saved-role-signal-audit/1.0", "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def finish_order(detail: dict[str, Any]) -> list[int]:
    result = detail.get("result") if isinstance(detail.get("result"), dict) else {}
    rows = result.get("finishers") or result.get("top5") or []
    found=[]
    for row in rows:
        if not isinstance(row, dict): continue
        rank=iv(row.get("finish", row.get("rank", row.get("position"))))
        no=iv(row.get("horseNumber", row.get("number", row.get("horseNo"))))
        if rank>0 and no>0: found.append((rank,no))
    return [no for _,no in sorted(found)]


def locked_marks(detail: dict[str, Any]) -> dict[int,str]:
    lock=detail.get("preRacePrediction") if isinstance(detail.get("preRacePrediction"),dict) else {}
    rows=lock.get("horses") if isinstance(lock.get("horses"),list) else []
    out={}
    for row in rows:
        if not isinstance(row,dict): continue
        no=iv(row.get("horseNumber",row.get("number",row.get("horseNo"))))
        mark=str(row.get("mark") or "").strip()
        if no>0 and mark: out[no]=mark
    return out


def evaluation(h: dict[str,Any]) -> dict[str,Any]:
    e=h.get("integratedEvaluation")
    return e if isinstance(e,dict) else {}


def value(e: dict[str,Any], *keys: str) -> float | None:
    for k in keys:
        x=fv(e.get(k))
        if x is not None: return x
    return None


def audit(e: dict[str,Any]) -> dict[str,Any]:
    for k in ("v218Audit","v217Audit"):
        a=e.get(k)
        if isinstance(a,dict): return a
    return {}


# Signals are existing saved model outputs only. No result-derived feature is constructed here.
SIGNALS: dict[str, tuple[str, Callable[[dict[str,Any]], float | None]]] = {
    "p1Score": ("high", lambda h: value(evaluation(h),"p1Score","legacyP1Score")),
    "p1Utility": ("high", lambda h: value(evaluation(h),"v218P1Utility","v217P1Utility","v215P1Utility","v213P1Utility")),
    "p2Score": ("high", lambda h: value(evaluation(h),"p2Score")),
    "p2Utility": ("high", lambda h: value(evaluation(h),"v213P2Utility")),
    "p3Score": ("high", lambda h: value(evaluation(h),"p3Score")),
    "p3Utility": ("high", lambda h: value(evaluation(h),"v213P3Utility")),
    "winnerConsensus": ("high", lambda h: value(evaluation(h),"winnerDecisionProbability","winnerConsensusProbability")),
    "coreAbilityRank": ("low", lambda h: value(evaluation(h),"coreAbilityRank")),
    "strengthHeadRank": ("low", lambda h: value(evaluation(h),"strengthHeadRank") or value(evaluation(h).get("multiHead") if isinstance(evaluation(h).get("multiHead"),dict) else {},"strengthRank")),
    "winHeadRank": ("low", lambda h: value(evaluation(h),"winHeadRank") or value(evaluation(h).get("multiHead") if isinstance(evaluation(h).get("multiHead"),dict) else {},"winRank")),
    "upsideHeadRank": ("low", lambda h: value(evaluation(h),"upsideHeadRank") or value(evaluation(h).get("multiHead") if isinstance(evaluation(h).get("multiHead"),dict) else {},"upsideRank")),
    "trueRun": ("high", lambda h: value(audit(evaluation(h)),"trueRun")),
    "sectional": ("high", lambda h: value(audit(evaluation(h)),"sectional")),
    "scenario": ("high", lambda h: value(audit(evaluation(h)),"positionScenario")),
}


def best_horse(horses:list[dict[str,Any]], signal:str, exclude:set[int]|None=None)->int:
    direction, fn=SIGNALS[signal]
    exclude=exclude or set()
    vals=[]
    for h in horses:
        no=iv(h.get("horseNumber"))
        if no<=0 or no in exclude: continue
        x=fn(h)
        if x is None: continue
        vals.append((x,no))
    if not vals: return 0
    vals.sort(key=(lambda z:(-z[0],z[1])) if direction=="high" else (lambda z:(z[0],z[1])))
    return vals[0][1]


def init()->dict[str,int]:
    return {"available":0,"exact":0,"top2":0,"top3":0,"winnerMarked":0}


def rate(d:dict[str,int],key:str)->float|None:
    n=d["available"]
    return round(d[key]/n,4) if n else None


def summary(d:dict[str,int])->dict[str,Any]:
    return {**d,"exactRate":rate(d,"exact"),"top2Rate":rate(d,"top2"),"top3Rate":rate(d,"top3")}


def main()->None:
    end=datetime.strptime(END_DATE,"%Y-%m-%d").date()
    dates=[(end-timedelta(days=i)).isoformat() for i in range(DAYS-1,-1,-1)]
    metrics={role:{sig:init() for sig in SIGNALS} for role in ("P1","P2_lockedAxisExcluded","P3_lockedCoreExcluded")}
    by_circuit=defaultdict(lambda:{role:{sig:init() for sig in SIGNALS} for role in metrics})
    locked_current={"races":0,"honmeiWin":0,"maruSecond":0,"triangleThird":0}
    combo={"pUtility":init(),"score":init()}
    availability=defaultdict(int)

    for ds in dates:
        payload=api_json(API_BASE+"/api/day?"+urllib.parse.urlencode({"date":ds,"details":"1"}))
        for detail in payload.get("details") or []:
            if not isinstance(detail,dict): continue
            order=finish_order(detail)
            marks=locked_marks(detail)
            if len(order)<3 or not marks: continue
            horses=[h for h in detail.get("horses") or [] if isinstance(h,dict)]
            circuit=str(detail.get("circuit") or "unknown")
            locked_current["races"]+=1
            honmei=next((n for n,m in marks.items() if m=="◎"),0)
            maru=next((n for n,m in marks.items() if m=="○"),0)
            tri=next((n for n,m in marks.items() if m=="▲"),0)
            locked_current["honmeiWin"]+=int(honmei==order[0])
            locked_current["maruSecond"]+=int(maru==order[1])
            locked_current["triangleThird"]+=int(tri==order[2])

            for sig in SIGNALS:
                p1=best_horse(horses,sig)
                if p1:
                    availability[sig]+=1
                    for bucket in (metrics["P1"][sig],by_circuit[circuit]["P1"][sig]):
                        bucket["available"]+=1;bucket["exact"]+=int(p1==order[0]);bucket["top2"]+=int(p1 in order[:2]);bucket["top3"]+=int(p1 in order[:3])
                p2=best_horse(horses,sig,{honmei} if honmei else set())
                if p2:
                    for bucket in (metrics["P2_lockedAxisExcluded"][sig],by_circuit[circuit]["P2_lockedAxisExcluded"][sig]):
                        bucket["available"]+=1;bucket["exact"]+=int(p2==order[1]);bucket["top2"]+=int(p2 in order[:2]);bucket["top3"]+=int(p2 in order[:3])
                ex={x for x in (honmei,maru) if x}
                p3=best_horse(horses,sig,ex)
                if p3:
                    for bucket in (metrics["P3_lockedCoreExcluded"][sig],by_circuit[circuit]["P3_lockedCoreExcluded"][sig]):
                        bucket["available"]+=1;bucket["exact"]+=int(p3==order[2]);bucket["top2"]+=int(p3 in order[:2]);bucket["top3"]+=int(p3 in order[:3])

            # Full role chain using existing dedicated utilities/scores, no fitted blend.
            for label, trio in (("pUtility",("p1Utility","p2Utility","p3Utility")),("score",("p1Score","p2Score","p3Score"))):
                a=best_horse(horses,trio[0]);b=best_horse(horses,trio[1],{a} if a else set());c=best_horse(horses,trio[2],{x for x in (a,b) if x})
                if a and b and c:
                    q=combo[label];q["available"]+=1;q["exact"]+=int([a,b,c]==order[:3]);q["top2"]+=int(a==order[0] and b==order[1]);q["top3"]+=int(set((a,b,c))==set(order[:3]))

    n=max(1,locked_current["races"])
    out={
        "version":"arvexq-saved-role-signal-audit-v1",
        "start":dates[0],"end":dates[-1],"lockedRaces":locked_current["races"],
        "lockedCurrent":{**locked_current,"honmeiWinRate":round(locked_current["honmeiWin"]/n,4),"maruSecondRate":round(locked_current["maruSecond"]/n,4),"triangleThirdRate":round(locked_current["triangleThird"]/n,4)},
        "signals":{role:{sig:summary(v) for sig,v in rows.items()} for role,rows in metrics.items()},
        "byCircuit":{c:{role:{sig:summary(v) for sig,v in rows.items()} for role,rows in roles.items()} for c,roles in by_circuit.items()},
        "roleChains":{k:summary(v) for k,v in combo.items()},
        "warning":"Signal values are read from saved detail fields and compared only on races with exact preRacePrediction locks. Availability is reported per signal; saved detail fields are not guaranteed immutable snapshots, so this is a challenger diagnostic, not promotion evidence by itself.",
    }
    print("ARVEXQ_SAVED_ROLE_SIGNAL_AUDIT_JSON="+json.dumps(out,ensure_ascii=False,separators=(",",":")))


if __name__=="__main__": main()
