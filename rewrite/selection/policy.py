"""Frozen research purchase policy: actual wide odds, joint coverage, no quota.

70% / 105% / 10% adverse-price move are registered candidate thresholds,
not claims of verified accuracy. No selection without out-of-sample approval.
"""
from __future__ import annotations
from itertools import combinations
from math import fsum, isfinite
from .market import digest, off_time, timestamp

VERSION = "arvexq-ticket-selection-v2"
START_DATE = "2026-11-11"
POLICY = {"maxPoints":3,"minHitProbability":0.70,"minExpectedReturn":1.05,
          "oddsStress":0.90,"maxMarketAgeSeconds":600,"maxForecastAgeSeconds":1800,
          "candidatePool":12}


def evaluate(detail, market=None, *, outcomes=None, validation=None, decided_at=None):
    uf=detail.get("unifiedForecast") or {}
    decision={"version":VERSION,"raceId":detail.get("id"),"raceDate":detail.get("date"),
              "selected":False,"status":"unassessed","reasons":[],"items":[],
              "modelVersion":uf.get("modelVersion"),"modelHash":uf.get("modelHash"),
              "forecastReceipt":uf.get("receiptSha256"),"forecastCapturedAt":uf.get("capturedAt"),
              "decidedAt":decided_at,"policy":POLICY.copy(),
              "policySha256":digest(POLICY),"validationStatus":"unvalidated"}
    reasons=decision["reasons"]
    at,off,captured=timestamp(decided_at),off_time(detail),timestamp(uf.get("capturedAt"))
    if not at or not off or not captured or not captured <= at < off:
        reasons.append("unverified-preoff-time")
    elif (at-captured).total_seconds()>POLICY["maxForecastAgeSeconds"]:
        reasons.append("forecast-too-old-for-purchase")
    if not uf.get("receiptSha256") or not uf.get("modelHash"):
        reasons.append("forecast-provenance-missing")
    validation=validation or {}
    through=validation.get("validatedThrough")
    if not (validation.get("status")=="approved-out-of-sample"
            and validation.get("modelHash")==uf.get("modelHash")
            and validation.get("policySha256")==digest(POLICY)
            and isinstance(through,str) and through<str(detail.get("date"))
            and validation.get("evidenceSha256")):
        reasons.append("ticket-probability-and-policy-unvalidated")
    else:
        decision["validationStatus"]="approved-out-of-sample"
        decision["validationEvidence"]=validation
    market=market or {}
    observed=timestamp(market.get("observedAt"))
    unsigned={k:v for k,v in market.items() if k!="contentSha256"}
    if (not market or market.get("kind")!="wide" or market.get("raceId")!=detail.get("id")
            or market.get("contentSha256")!=digest(unsigned)):
        reasons.append("actual-wide-market-unavailable")
    else:
        decision["marketSha256"]=market["contentSha256"]
        decision["marketObservedAt"]=market["observedAt"]
        if (not observed or not at or not captured or observed<captured
                or not 0 <= (at-observed).total_seconds() <= POLICY["maxMarketAgeSeconds"]):
            reasons.append("actual-wide-market-stale")
        if market.get("forecastReceipt")!=uf.get("receiptSha256"):
            reasons.append("market-forecast-identity-mismatch")
        if market.get('forecastVectorSha256')!=digest(uf.get('diagnosis') or []):
            reasons.append('market-forecast-vector-mismatch')
        numbers=sorted(d.get("horseNumber") for d in uf.get("diagnosis",[]))
        if market.get("roster")!=numbers:
            reasons.append("market-forecast-roster-mismatch")
    roster={d.get('horseNumber') for d in uf.get('diagnosis',[])}
    if (not outcomes or any(not isfinite(p) or p<0 for p in outcomes.values())
            or abs(fsum(outcomes.values())-1)>1e-6
            or any(len(order)!=3 or len(set(order))!=3 or not set(order)<=roster for order in outcomes)):
        reasons.append("joint-probabilities-unavailable")
    if reasons:
        return decision
    available=[]
    for q in market.get("quotes",[]):
        pair=frozenset(q["combo"])
        p=fsum(p for order,p in outcomes.items() if pair<=set(order[:3]))
        ev=p*q["oddsLow"]*POLICY["oddsStress"]
        if ev>=POLICY["minExpectedReturn"]:
            available.append({"combo":q["combo"],"probability":p,"oddsLow":q["oddsLow"],
                              "stressExpectedReturn":ev})
    available.sort(key=lambda q:(-q["probability"],q["combo"]))
    available=available[:POLICY["candidatePool"]]
    portfolios=[]
    for n in range(1,POLICY["maxPoints"]+1):
        for items in combinations(available,n):
            pairs=[set(q["combo"]) for q in items]
            hit=fsum(p for order,p in outcomes.items() if any(pair<=set(order[:3]) for pair in pairs))
            ev=fsum(q["stressExpectedReturn"] for q in items)/n
            if hit>=POLICY["minHitProbability"]:
                portfolios.append((n,-hit,-ev,items))
    if not portfolios:
        decision.update(status="not-selected",reasons=["no-qualified-portfolio"])
        return decision
    _,negative_hit,negative_ev,items=min(portfolios,key=lambda x:(x[0],x[1],x[2],str(x[3])))
    decision.update(selected=True,status="selected",hitProbability=-negative_hit,
                    stressExpectedReturn=-negative_ev,
                    items=[{"kind":"ワイド","combo":q["combo"],"probability":q["probability"],
                            "oddsLow":q["oddsLow"]} for q in items])
    decision["decisionSha256"]=digest(decision)
    return decision
