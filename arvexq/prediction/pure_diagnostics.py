"""Pure, standalone prediction-quality and observation utilities.

Moved verbatim from app.py; the corresponding app-level names remain imported.
No external API, DB, or live racing access is performed at import time.
"""

def _central_detail_coverage(detail: dict) -> dict:
    horses = detail.get("horses", []) or []
    counts = {str(h.get("name") or ""): min(5, len(h.get("recentRaces") or [])) for h in horses if h.get("name")}
    complete = {str(h.get("name") or ""): bool(h.get("_jraCareerComplete")) for h in horses if h.get("name")}
    vals = list(counts.values())
    resolved = sum(1 for name,v in counts.items() if v >= 5 or complete.get(name, False))
    return {
        "totalHorses": len(counts),
        "horsesWithHistory": sum(1 for v in vals if v > 0),
        "horsesWith4Plus": sum(1 for v in vals if v >= 4),
        "horsesWith5Plus": sum(1 for v in vals if v >= 5),
        "horsesResolved": resolved,
        "horsesCareerComplete": sum(1 for name in counts if complete.get(name, False)),
        "totalRuns": sum(vals),
        "counts": counts,
        "underFive": [name for name, v in counts.items() if v < 5 and not complete.get(name, False)],
    }


def _diagnosis_history_quality(detail:dict)->dict:
    horses=detail.get("horses") or []
    total=len(horses)
    if not total:return {"ready":False,"total":0,"withHistory":0,"runs":0}
    if str(detail.get("analysisMode") or "")=="新馬":
        return {"ready":True,"total":total,"withHistory":0,"runs":0,"debut":True}
    counts=[]
    for h in horses:
        runs=h.get("allPastRuns") or h.get("recentRaces") or []
        counts.append(len(runs))
    with_history=sum(1 for c in counts if c>0)
    runs=sum(min(c,5) for c in counts)
    # Enough to prevent arbitrary horse-number rankings while still handling young races.
    need=max(2,int((total*.50)+.999))
    ready=with_history>=need and runs>=max(4,total)
    return {"ready":ready,"total":total,"withHistory":with_history,"runs":runs,"need":need}


def _audit_axes_from_eval(e:dict)->dict:
    a=(e or {}).get("v218Audit") or (e or {}).get("v217Audit") or {}
    def u(key,default=.5):
        try:return round(max(0.0,min(1.0,float(a.get(key) if a.get(key) is not None else default))),6)
        except Exception:return default
    pp=a.get("positionPressure") if isinstance(a.get("positionPressure"),dict) else {}
    try:frag=max(0.0,min(1.0,float(pp.get("local") or 0)))
    except Exception:frag=0.0
    return {
        "pure":u("pure"),"trueRun":u("trueRun"),"sectional":u("sectional"),
        "positionScenario":u("positionScenario"),"conditions":u("conditions"),
        "opponentLevel":u("opponentLevel"),"stateConsistency":u("stateConsistency"),
        "evidence":u("evidence",.0),"sevenAxisScore":u("sevenAxisScore"),"fragility":round(frag,6),
    }


def _learning_date_split(races:list[dict])->dict:
    """Split on whole race dates so one day's track state never straddles train/test blocks."""
    dates=sorted({str(x.get("date") or "") for x in races if x.get("date")})
    if len(dates)<4:return {"dates":dates,"train":races,"tune":[],"promotion":[],"shadow":[]}
    nd=len(dates)
    i1=max(1,min(nd-3,int(round(nd*.55))))
    i2=max(i1+1,min(nd-2,int(round(nd*.75))))
    i3=max(i2+1,min(nd-1,int(round(nd*.90))))
    d1=set(dates[:i1]);d2=set(dates[i1:i2]);d3=set(dates[i2:i3]);d4=set(dates[i3:])
    pick=lambda ds:[x for x in races if str(x.get("date") or "") in ds]
    return {"dates":dates,"train":pick(d1),"tune":pick(d2),"promotion":pick(d3),"shadow":pick(d4),
            "dateBlocks":{"train":sorted(d1),"tune":sorted(d2),"promotion":sorted(d3),"shadow":sorted(d4)}}


def _pc_time_index(rr: dict, target_dist: int) -> float | None:
    try:
        sec=float(rr.get("timeSeconds") or 0); dist=int(rr.get("distance") or 0)
    except Exception:
        return None
    if sec <= 0 or dist <= 0:return None
    speed=dist/sec
    penalty=1-min(.28,abs(dist-target_dist)/max(600,target_dist)*.55)
    cond=str(rr.get("condition") or "")
    adj=.985 if ("重" in cond or "不" in cond) else (.993 if "稍" in cond else 1.0)
    return speed*penalty/adj


def _prob_vector(values:list[float])->list[float]:
    clean=[]
    for v in values:
        try:x=max(0.0,float(v or 0))
        except Exception:x=0.0
        clean.append(x)
    sm=sum(clean)
    if sm<=0:
        return ([1.0/len(clean)]*len(clean)) if clean else []
    return [x/sm for x in clean]


def _history_is_enough(cov: dict, months_done: int) -> bool:
    total = int(cov.get("totalHorses") or 0)
    if total <= 0:
        return True
    # v39: do not stop because "most" horses are covered.  The race prediction waits until
    # every runner has five prior starts in the local official-history store.  A horse with
    # fewer than five career starts can only be confirmed after the configured lookback is
    # exhausted; until then the crawler keeps going.
    five = int(cov.get("horsesWith5Plus") or 0)
    return five >= total


def _pc_season(iso_date: str) -> str:
    try:
        month=int(str(iso_date).split("-")[1])
    except Exception:
        month=0
    if 3 <= month <= 5:return "春"
    if 6 <= month <= 8:return "夏"
    if 9 <= month <= 11:return "秋"
    return "冬"


def _reference_weight_from_horse(h:dict)->tuple[int|None,str]:
    for rr in (h.get('recentRaces') or []):
        try:w=int(rr.get('bodyWeight') or 0)
        except Exception:w=0
        if 250<w<800:return w,str(rr.get('date') or '')
    return None,''
