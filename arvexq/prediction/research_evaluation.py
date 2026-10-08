"""Independent evaluation of archived experimental forecasts against official results.

Strictly compares contemporaneously sealed snapshots. No replay from modern
racecards and no post-off feature construction are permitted.
"""
from __future__ import annotations
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime
from typing import Any
from arvexq.prediction.prerace_archive import sealed_lock
from arvexq.prediction.research_shadow import VERSION


def _n(v: Any) -> float | None:
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):
        return None


def _history_hash_ok(shadow: dict[str, Any]) -> bool:
    if not isinstance(shadow,dict):
        return False
    core={k:v for k,v in shadow.items() if k!="hash"}
    raw=json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode()
    return hashlib.sha256(raw).hexdigest()==shadow.get("hash")


def evaluate_race(detail: dict[str, Any]) -> dict[str, Any] | None:
    lock=sealed_lock(detail)
    shadow=detail.get("researchShadow")
    if lock is None or not isinstance(shadow,dict):
        return None
    if shadow.get("version")!=VERSION or shadow.get("raceId")!=detail.get("id"):
        return None
    if not _history_hash_ok(shadow):
        return None
    result=detail.get("result") or {}
    if str(result.get("status") or "")!="確定":
        return None
    finishes=result.get("finishers") or result.get("top5") or []
    ordered=[]
    for item in finishes:
        if not isinstance(item,dict):continue
        pos=_n(item.get("finish") or item.get("rank"))
        no=_n(item.get("horseNumber"))
        if pos is not None and no is not None and pos>=1 and no>0:
            ordered.append((int(pos),int(no)))
    ordered.sort()
    if len(ordered)<3 or [p for p,_ in ordered[:3]]!=[1,2,3]:
        return None
    actual=[no for _,no in ordered[:3]]
    rows=shadow.get("rows") or []
    if len(rows)<3:
        return None
    try:
        ids=[int(row["horseNumber"]) for row in rows]
        probs=[row["uncalibrated"] for row in rows]
        if len(ids)!=len(set(ids)) or not set(actual).issubset(set(ids)):
            return None
        if any(not isinstance(p,dict) for p in probs):
            return None
        for p in probs:
            if any(_n(p.get(k)) is None for k in ("p1","p2","p3","top3")):
                return None
        # All three roles must normalize over exactly the same field.
        if any(abs(sum(float(p[key]) for p in probs)-1.)>1e-5 for key in ("p1","p2","p3")):
            return None
    except (ValueError,TypeError,KeyError):
        return None
    maprows={i:float(p["p1"]) for i,p in zip(ids,probs)}
    ordered_triples=shadow.get("orderedTrifectaShadow") or []
    leader=max(ids,key=lambda no:(maprows[no],-no))
    by_top3={i:float(p["top3"]) for i,p in zip(ids,probs)}
    predicted_podium=set(sorted(ids,key=lambda no:(-by_top3[no],no))[:3])
    # Log loss uses a proper, exhaustive three-outcome tournament distribution
    # for first-place; Brier is measured separately for 1st and top-three events.
    logloss=-math.log(max(1e-12,maprows[actual[0]]))
    brier=sum((maprows[i]-float(i==actual[0]))**2 for i in ids)/len(ids)
    podium_brier=sum((by_top3[i]-float(i in actual))**2 for i in ids)/len(ids)
    exact_score=next((float(t.get("uncalibratedScore") or 0.) for t in ordered_triples
                      if [int(t.get("first") or 0),int(t.get("second") or 0),
                          int(t.get("third") or 0)]==actual),0.)
    marks={int(h["horseNumber"]):str(h.get("mark") or "") for h in lock.get("horses") or []}
    honmei=next((no for no,mark in marks.items() if mark=="◎"),0)
    return {
        "raceId":str(detail.get("id")),"date":str(detail.get("date") or ""),
        "circuit":str(detail.get("circuit") or ""),"track":str(detail.get("track") or ""),
        "raceCount":len(ids),"actual":actual,"modelWinner":leader,
        "shadowWinnerCorrect":leader==actual[0],
        "shadowTopThreeCoverage":len(predicted_podium.intersection(actual)),
        "shadowExactTrifectaTop24":exact_score>0,
        "shadowExactTrifectaScore":round(exact_score,9),
        "shadowLogLoss":round(logloss,8),
        "shadowBrierWin":round(brier,8),"shadowBrierTop3":round(podium_brier,8),
        "lockedHonmei":honmei,
        "lockedHonmeiTop3":honmei in actual if honmei else None,
        "baselineWinHorse":int(lock.get("winnerNo") or 0),
        "baselineWinnerCorrect":int(lock.get("winnerNo") or 0)==actual[0]
            if lock.get("winnerNo") else None,
        "version":VERSION,
    }


def summarize(reports: list[dict[str, Any]], min_races: int=100) -> dict[str, Any]:
    rows=[v for v in reports if isinstance(v,dict)]
    n=len(rows)
    baseline=[v for v in rows if v.get("baselineWinnerCorrect") is not None]
    axes=[v for v in rows if v.get("lockedHonmeiTop3") is not None]
    def avg(key: str)->float|None:
        return round(sum(float(r[key]) for r in rows)/n,6) if n else None
    dates=sorted(set(str(r.get("date") or "") for r in rows))
    latest=dates[-1] if dates else None
    first=dates[0] if dates else None
    circuits=defaultdict(list)
    for row in rows:circuits[row.get("circuit") or "unknown"].append(row)
    return {
        "version":"arvexq-research-shadow-evaluation-v1",
        "strictContemporaneousSealRequired":True,
        "inputRaceCount":n,"dateRange":{"from":first,"to":latest},
        "shadowWinnerHitRate":avg("shadowWinnerCorrect"),
        "shadowTopThreeCoverageAverage":avg("shadowTopThreeCoverage"),
        "shadowExactTrifectaTop24Rate":avg("shadowExactTrifectaTop24"),
        "shadowWinnerLogLoss":avg("shadowLogLoss"),
        "shadowBrierWin":avg("shadowBrierWin"),
        "shadowBrierTop3":avg("shadowBrierTop3"),
        "baselineWinnerRaces":len(baseline),
        "baselineWinnerHitRate":round(sum(r["baselineWinnerCorrect"] for r in baseline)/len(baseline),6)
            if baseline else None,
        "lockedAxisRaces":len(axes),
        "lockedAxisTop3Rate":round(sum(r["lockedHonmeiTop3"] for r in axes)/len(axes),6)
            if axes else None,
        "byCircuit":{k:{"races":len(rs),"shadowWinnerHitRate":round(
            sum(r["shadowWinnerCorrect"] for r in rs)/len(rs),6),
            "shadowTopThreeCoverageAverage":round(
            sum(r["shadowTopThreeCoverage"] for r in rs)/len(rs),6)}
            for k,rs in sorted(circuits.items())},
        "promotionEligible":False,
        "readiness":("insufficient-genuine-frozen-races" if n<min_races else
                     "candidate-for-further-calibration-and-forward-validation"),
        "minimumRacesBeforeReview":min_races,
        "warning":"Research scores are NOT calibrated probabilities, purchase odds, forecasts approved for publication, or proof of positive ROI.",
    }
