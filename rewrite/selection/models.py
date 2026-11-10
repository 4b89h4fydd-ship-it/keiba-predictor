"""Separate winner residual and 2nd/3rd-place models, fit by race and date.

Inputs are frozen pre-off diagnosis values only, never mutable current odds,
horse stats, or results reconstructed as features. Scores for the partner
model are NOT joint ticket probabilities. No model is promoted by this file.
"""
from __future__ import annotations
from datetime import date
from math import exp, log, isfinite, sqrt, fsum
from .market import timestamp, off_time, digest

FEATURES = ("ability","ability_relative","win_logit","win_rank","field_size")
MODEL_VERSION = "separate-targets-research-v1"


def prepare(detail):
    uf=detail.get("unifiedForecast") or {}
    captured,off=timestamp(uf.get("capturedAt")),off_time(detail)
    if not captured or not off or captured>=off or not uf.get("receiptSha256"):
        raise ValueError("unverified-preoff-diagnosis")
    circuit=detail.get("circuit")
    if circuit not in ("地方","中央") or detail.get("track") in ("帯広","帯広ば"):
        raise ValueError("unsupported-circuit")
    segment="nar" if circuit=="地方" else "jra_flat"
    if segment=="jra_flat" and any(t in str(detail.get("title", "")) for t in ("障害","新馬","メイクデビュー")):
        raise ValueError("dedicated-box-not-in-training")
    rows=uf.get("diagnosis") or []
    numbers=[r.get("horseNumber") for r in rows]
    if len(rows)<5 or len(set(numbers))!=len(rows) or any(type(n) is not int for n in numbers):
        raise ValueError("invalid-roster")
    for r in rows:
        if any(type(r.get(k)) not in (float,int) or not isfinite(r[k]) for k in ("abilityScore","winProbability")):
            raise ValueError("missing-frozen-features")
        if not 0<=r['abilityScore']<=1 or not 0<r['winProbability']<1:
            raise ValueError("invalid-frozen-features")
    if abs(fsum(r['winProbability'] for r in rows)-1)>.005:
        raise ValueError("invalid-win-vector")
    mean=fsum(r['abilityScore'] for r in rows)/len(rows)
    order=sorted(rows,key=lambda r:(-r['winProbability'],r['horseNumber']))
    ranks={r['horseNumber']:i for i,r in enumerate(order)}
    inputs=[]
    for r in rows:
        p=r['winProbability'];a=r['abilityScore'];no=r['horseNumber']
        inputs.append({"number":no,"baseWin":p,"x":[a,a-mean,log(p/(1-p)),ranks[no]/(len(rows)-1),len(rows)/18]})
    return {"id":detail['id'],"date":detail['date'],"segment":segment,"rows":inputs,
            "capturedAt":uf['capturedAt'],"sourceReceipt":uf['receiptSha256'],
            "sourceVectorSha256":digest(rows),"modelHash":uf.get('modelHash')}


def labelled(detail):
    record=prepare(detail)
    result=detail.get('result') or {}
    if result.get('status')!='確定':raise ValueError('pending-result')
    finishers=result.get('finishers') or []
    winners=[f['horseNumber'] for f in finishers if f.get('finish')==1]
    partners={f['horseNumber'] for f in finishers if f.get('finish') in (2,3)}
    top3={f['horseNumber'] for f in finishers if type(f.get('finish')) is int and 1<=f['finish']<=3}
    # Dead heats have different joint payout rules. Preserve them in source;
    # exclude explicitly instead of silently assigning one synthetic order.
    if len(winners)!=1 or len(partners)!=2 or len(top3)!=3:
        raise ValueError('incomplete-or-dead-heat-result')
    numbers={r['number'] for r in record['rows']}
    if not top3<=numbers:raise ValueError('result-roster-mismatch')
    record.update(winner=winners[0],partners=sorted(partners),top3=sorted(top3))
    return record


def _sigmoid(z):
    return 1/(1+exp(-max(-35,min(35,z))))


def fit(records, *, target, segment, iterations=400, l2=.1):
    if target not in ('winner','partner'):raise ValueError('unknown-target')
    records=[r for r in records if r['segment']==segment]
    if len(records)<20:raise ValueError('fewer-than-20-training-races')
    ids=[r['id'] for r in records]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate-training-race')
    vectors=[r['x'] for race in records for r in race['rows']]
    mean=[fsum(x[j] for x in vectors)/len(vectors) for j in range(len(FEATURES))]
    scale=[max(.01,sqrt(fsum((x[j]-mean[j])**2 for x in vectors)/len(vectors))) for j in range(len(FEATURES))]
    def xx(row):return [1]+[(v-m)/s for v,m,s in zip(row['x'],mean,scale)]
    training=[(race,[xx(row) for row in race['rows']]) for race in records]
    w=[0.0]*(len(FEATURES)+1)
    for step in range(iterations):
        gradient=[0.0]*len(w)
        for race,features in training:
            if target=='winner':
                logits=[log(r['baseWin'])+fsum(a*b for a,b in zip(w,x)) for r,x in zip(race['rows'],features)]
                high=max(logits);den=fsum(exp(z-high) for z in logits)
                probabilities=[exp(z-high)/den for z in logits]
                labels=[int(r['number']==race['winner']) for r in race['rows']]
                weight=1/len(training)
            else:
                probabilities=[_sigmoid(fsum(a*b for a,b in zip(w,x))) for x in features]
                labels=[int(r['number'] in race['partners']) for r in race['rows']]
                weight=1/(len(training)*len(features))
            for x,p,y in zip(features,probabilities,labels):
                for j in range(len(w)):gradient[j]+=(p-y)*x[j]*weight
        rate=.15/(1+step/200)
        w=[v-rate*(g+(l2*v if j else 0)) for j,(v,g) in enumerate(zip(w,gradient))]
    model={'version':MODEL_VERSION,'target':target,'segment':segment,'features':FEATURES,
           'mean':mean,'scale':scale,'weights':w,'l2':l2,'iterations':iterations,
           'trainedThrough':max(r['date'] for r in records),'trainingRaces':len(records),
           'trainingSha256':digest(sorted(records,key=lambda r:r['id'])),'status':'research-only-not-approved'}
    model['artifactSha256']=digest(model)
    return model


def predict(model, record):
    if model['segment']!=record['segment']:raise ValueError('circuit-model-mismatch')
    if record['date']<=model['trainedThrough']:raise ValueError('time-split-violation')
    unsigned={k:v for k,v in model.items() if k!='artifactSha256'}
    if digest(unsigned)!=model.get('artifactSha256'):raise ValueError('model-hash-mismatch')
    values={}
    for row in record['rows']:
        x=[1]+[(v-m)/s for v,m,s in zip(row['x'],model['mean'],model['scale'])]
        z=fsum(a*b for a,b in zip(model['weights'],x))
        values[row['number']]=(log(row['baseWin'])+z if model['target']=='winner' else _sigmoid(z))
    if model['target']=='winner':
        high=max(values.values());den=fsum(exp(v-high) for v in values.values())
        return {n:exp(v-high)/den for n,v in values.items()}
    return values


def partner_pool(record, scores):
    heads=[r['number'] for r in sorted(record['rows'],key=lambda r:(-r['baseWin'],r['number']))[:2]]
    return heads+sorted((n for n in scores if n not in heads),key=lambda n:(-scores[n],n))[:3]
