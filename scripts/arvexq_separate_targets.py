#!/usr/bin/env python3
"""Fit / calibrate / compare separate targets on date-disjoint saved forecasts.

This retrospective diagnostic cannot approve production or recreate market
prices. Future forward seals use the exported model artifacts unchanged.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from itertools import permutations
import json
from math import fsum,log
from pathlib import Path
import random
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rewrite.selection.market import digest
from rewrite.selection.models import labelled,fit,predict,partner_pool
from rewrite.selection.policy import POLICY


def mark_order(detail,record):
    rows=detail.get('predictionMarks') or []
    lookup={r.get('mark'):r.get('horseNumber') for r in rows}
    if any(s not in lookup for s in '◎○▲△☆'):raise ValueError('incomplete-five-marks')
    marks=[lookup[s] for s in '◎○▲△☆']
    numbers={r['number'] for r in record['rows']}
    if len(set(marks))!=5 or not set(marks)<=numbers:raise ValueError('mark-roster-mismatch')
    ranking=sorted(record['rows'],key=lambda r:(-r['baseWin'],r['number']))
    if marks[:2]!=[r['number'] for r in ranking[:2]]:raise ValueError('diagnosis-marks-parity-mismatch')
    return marks


def valid_payouts(result):
    widths={'単勝':1,'複勝':1,'馬連':2,'馬単':2,'ワイド':2,'3連複':3,'3連単':3}
    rows=result.get('payouts') or []
    if not rows:return False
    has_tri=False
    for p in rows:
        if p.get('type') not in widths:continue
        nums=re.findall(r'\d+',str(p.get('combination') or ''))
        if (len(nums)!=widths[p['type']] or len(set(nums))!=len(nums)
                or type(p.get('amount')) is not int or p['amount']<0):return False
        has_tri|=p['type']=='3連単'
    return has_tri


def r24(pool,result):
    combos={tuple(c) for c in permutations(pool,3) if c[0] in pool[:2]}
    stake=100*len(combos)
    if len(combos)!=24:raise ValueError('non-24-point-arm')
    returned=0
    for p in result['payouts']:
        if p['type']=='3連単' and tuple(map(int,re.findall(r'\d+',p['combination']))) in combos:
            returned+=p['amount']
    return {'stake':stake,'returned':returned,'hit':int(returned>0)}


def summary(rows):
    out={'races':len(rows)}
    if not rows:return out
    for arm in ('baseline','partner','winner'):
        scored=[r[arm] for r in rows]
        n=len(scored)
        money=[s['money'] for s in scored if s['money'] is not None]
        stake=sum(x['stake'] for x in money);returned=sum(x['returned'] for x in money)
        out[arm]={'honmeiWins':sum(s['win'] for s in scored),'honmeiTop3':sum(s['top3'] for s in scored),
                  'honmeiWinRate':sum(s['win'] for s in scored)/n,
                  'honmeiTop3Rate':sum(s['top3'] for s in scored)/n,
                  'winnerInHeads':sum(s['winnerInHeads'] for s in scored),
                  'podiumCovered':sum(s['podiumCovered'] for s in scored),
                  'logLoss':fsum(s['logLoss'] for s in scored)/n,
                  'brier':fsum(s['brier'] for s in scored)/n,
                  'gradedMoneyRaces':len(money),'stake':stake,'returned':returned,
                  'r24Hits':sum(m['hit'] for m in money),'roi':returned/stake if stake else None,
                  'roiWithoutLargestPayout':((returned-max(m['returned'] for m in money))/(stake-2400)
                      if len(money)>1 else None)}
    return out


def day_interval(rows,arm,metric,draws=2000):
    byday=defaultdict(list)
    for r in rows:byday[r['date']].append(r)
    days=sorted(byday)
    if len(days)<2:return None
    rng=random.Random(20261111);ds=[]
    for _ in range(draws):
        sample=[r for day in rng.choices(days,k=len(days)) for r in byday[day]]
        ds.append(fsum(r[arm][metric]-r['baseline'][metric] for r in sample)/len(sample))
    ds.sort();return {'low':ds[int(.025*draws)],'high':ds[int(.975*draws)],'days':len(days),'draws':draws}


def evaluate(details,train_end,calibration_end):
    if train_end>=calibration_end:raise ValueError('train-and-calibration-dates-must-increase')
    usable=[];excluded=Counter();byid={}
    for d in details:
        if d.get('id') in byid:raise ValueError('duplicate-race-id')
        byid[d.get('id')]=d
        try:
            r=labelled(d);r['marks']=mark_order(d,r);usable.append(r)
        except ValueError as exc:excluded[str(exc)]+=1
    output={'version':'separated-evaluation-v1','status':'retrospective-diagnostic-not-promotion',
            'inputRaces':len(details),'excluded':dict(excluded),'corpusSha256':digest(details),
            'trainEnd':train_end,'calibrationEnd':calibration_end,'purchasePolicy':POLICY,
            'marketBenchmark':'unavailable-without-same-time-actual-odds',
            'purchaseEvaluation':'unavailable-without-preoff-wide-market-and-heldout-joint-calibration',
            'boxes':{},'models':{},'pairs':[]}
    for segment in ('nar','jra_flat'):
        train=[r for r in usable if r['segment']==segment and r['date']<=train_end]
        cal=[r for r in usable if r['segment']==segment and train_end<r['date']<=calibration_end]
        test=[r for r in usable if r['segment']==segment and r['date']>calibration_end]
        counts={'train':len(train),'calibration':len(cal),'test':len(test)}
        if min(len(train),len(cal),len(test))<20:
            output['boxes'][segment]={'status':'insufficient-date-disjoint-data','counts':counts};continue
        partner=fit(train,target='partner',segment=segment)
        winner=fit(train,target='winner',segment=segment)
        # Calibration period is evaluated separately; never selected by test performance.
        bins=[{'count':0,'probabilitySum':0.,'positiveCount':0} for _ in range(5)]
        for r in cal:
            for no,p in predict(partner,r).items():
                b=bins[min(4,int(p*5))];b['count']+=1;b['probabilitySum']+=p;b['positiveCount']+=int(no in r['partners'])
        output['models'][segment]={'partner':partner,'winner':winner}
        pairs=[]
        for r in test:
            d=byid[r['id']];base={x['number']:x['baseWin'] for x in r['rows']}
            scores=predict(partner,r);wp=predict(winner,r)
            partner_marks=partner_pool(r,scores)
            winner_marks=sorted(wp,key=lambda n:(-wp[n],n))[:5]
            money_ok=valid_payouts(d['result'])
            pair={'raceId':r['id'],'date':r['date'],'segment':segment,'moneyEligible':money_ok,
                  'moneyExclusion':None if money_ok else 'missing-or-malformed-payout-combinations',
                  'sourceReceipt':r['sourceReceipt'],'sourceVectorSha256':r['sourceVectorSha256']}
            for arm,pool,probs in (('baseline',r['marks'],base),('partner',partner_marks,base),('winner',winner_marks,wp)):
                pick=pool[0]
                pair[arm]={'pick':pick,'pool':pool,'win':int(pick==r['winner']),
                    'top3':int(pick in r['top3']),'winnerInHeads':int(r['winner'] in pool[:2]),
                    'podiumCovered':int(set(r['top3'])<=set(pool)),
                    'logLoss':-log(max(probs[r['winner']],1e-12)),
                    'brier':fsum((p-int(no==r['winner']))**2 for no,p in probs.items()),
                    'money':r24(pool,d['result']) if money_ok else None}
            pairs.append(pair)
        stats=summary(pairs)
        stats.update(counts=counts,byDate={day:summary([r for r in pairs if r['date']==day]) for day in sorted({r['date'] for r in pairs})},
                     partnerCalibrationBins=bins,
                     uncertainty={a:{m:day_interval(pairs,a,m) for m in ('win','logLoss')} for a in ('partner','winner')},
                     verdict='not-promoted-retrospective-and-no-independent-forward-seals')
        output['boxes'][segment]=stats;output['pairs'].extend(pairs)
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    p.add_argument('--train-end',required=True);p.add_argument('--calibration-end',required=True)
    p.add_argument('--model-dir')
    a=p.parse_args();data=json.loads(Path(a.input).read_text())
    report=evaluate(data,a.train_end,a.calibration_end)
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if a.model_dir:
        Path(a.model_dir).mkdir(parents=True,exist_ok=True)
        for segment,models in report['models'].items():
            for target,model in models.items():
                Path(a.model_dir,f'{segment}-{target}.json').write_text(json.dumps(model,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('pairs','models')},ensure_ascii=False))
    return 0


if __name__=='__main__':raise SystemExit(main())
