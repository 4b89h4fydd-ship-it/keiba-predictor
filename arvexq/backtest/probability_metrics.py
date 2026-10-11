"""Extracted legacy behavior; network and stores stay outside this module."""
from __future__ import annotations

import math
from arvexq.prediction.pure_diagnostics import _prob_vector


def _learning_probability(rows:list[dict], weights:dict, power:float=1.0, shrink:float=0.0)->list[float]:
    """Market-independent winner distribution from immutable pre-race lock fields."""
    if not rows:return []
    p1=_prob_vector([float(x.get("p1Probability") or 0) for x in rows])
    win=_prob_vector([float(x.get("winEvidenceProbability") or 0) for x in rows])
    pair=_prob_vector([float(x.get("pairwiseWinRate") or .5) for x in rows])
    w1=float(weights.get("p1",.58));w2=float(weights.get("winEvidence",.24));w3=float(weights.get("pairwise",.18))
    raw=[max(1e-12,w1*p1[i]+w2*win[i]+w3*pair[i]) for i in range(len(rows))]
    pw=max(.55,min(1.65,float(power or 1.0)))
    raw=[x**pw for x in raw];sm=sum(raw) or 1.0;probs=[x/sm for x in raw]
    sh=max(0.0,min(.25,float(shrink or 0.0)));u=1.0/len(rows)
    if sh:probs=[(1-sh)*x+sh*u for x in probs]
    sm=sum(probs) or 1.0
    return [x/sm for x in probs]


def _learning_metric(races:list[dict], weights:dict, power:float=1.0, shrink:float=0.0)->dict:
    """Winner metrics from immutable pre-race probabilities only.

    Top-1 is the primary objective. Log loss, Brier and ECE are calibration guards;
    they prevent a superficially good ranker from becoming over-confident.
    """
    if not races:return {"races":0,"top1":0.0,"logLoss":None,"brier":None,"ece":None,"hits":0,"horseSamples":0}
    hits=0;ll=0.0;br=0.0;used=0;cal=[]
    for z in races:
        rows=z.get("horses") or [];winner=int(z.get("winnerNo") or 0)
        probs=_learning_probability(rows,weights,power,shrink)
        if not probs or winner<=0:continue
        try:wi=next(i for i,x in enumerate(rows) if int(x.get("horseNumber") or 0)==winner)
        except StopIteration:continue
        pred=max(range(len(probs)),key=lambda i:(probs[i],-int(rows[i].get("horseNumber") or 999)))
        hits+=1 if pred==wi else 0;ll-=math.log(max(1e-12,probs[wi]));br+=sum((p-(1.0 if i==wi else 0.0))**2 for i,p in enumerate(probs));used+=1
        cal.extend((float(p),1 if i==wi else 0) for i,p in enumerate(probs))
    ece=0.0
    if cal:
        for bi in range(10):
            lo=bi/10;hi=(bi+1)/10
            vals=[x for x in cal if x[0]>=lo and (x[0]<hi or (bi==9 and x[0]<=hi))]
            if vals:
                pm=sum(x[0] for x in vals)/len(vals);ar=sum(x[1] for x in vals)/len(vals)
                ece+=abs(pm-ar)*len(vals)/len(cal)
    return {"races":used,"hits":hits,"top1":round(hits/used,6) if used else 0.0,
            "logLoss":round(ll/used,6) if used else None,"brier":round(br/used,6) if used else None,
            "ece":round(ece,6) if cal else None,"horseSamples":len(cal)}


def _learning_paired_top1(races:list[dict], base_w:dict, cand_w:dict, power:float, shrink:float)->dict:
    base_only=cand_only=both=neither=0
    for z in races:
        rows=z.get("horses") or [];winner=int(z.get("winnerNo") or 0)
        bp=_learning_probability(rows,base_w,1.0,0.0);cp=_learning_probability(rows,cand_w,power,shrink)
        if not bp or not cp:continue
        b=rows[max(range(len(bp)),key=lambda i:(bp[i],-int(rows[i].get("horseNumber") or 999)))]
        c=rows[max(range(len(cp)),key=lambda i:(cp[i],-int(rows[i].get("horseNumber") or 999)))]
        bh=int(b.get("horseNumber") or 0)==winner;ch=int(c.get("horseNumber") or 0)==winner
        if bh and ch:both+=1
        elif bh:base_only+=1
        elif ch:cand_only+=1
        else:neither+=1
    return {"candidateOnly":cand_only,"baselineOnly":base_only,"both":both,"neither":neither,"netWins":cand_only-base_only}

