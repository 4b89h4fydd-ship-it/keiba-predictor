"""Verify JRA measured time differences and lossless D1 publication."""
import argparse
import json
import math
from pathlib import Path
from arvexq.components.item_057.full_career import merge_career

def measure(bundle):
    counts={'races':0,'horses':0,'runs':0,'marginRuns':0,'provenRuns':0,'horsesWithMargin':0}
    evidence={};errors=[]
    for d in bundle.get('details') or []:
        if d.get('circuit') not in ('JRA','中央'):continue
        counts['races']+=1
        for h in d.get('horses') or []:
            counts['horses']+=1;found=False
            duplicates={}
            for r in [*(h.get('recentRaces') or []),*(h.get('allPastRuns') or [])]:
                if not isinstance(r,dict) or not r.get('marginEvidence'):continue
                k=r.get('date');signature=(r.get('timeBehindWinner'),r.get('marginEvidence'))
                if k in duplicates and duplicates[k]!=signature:
                    errors.append({'id':d['id'],'horse':h['name'],'date':k,'reason':'conflicting-visible-proof'})
                duplicates[k]=signature
            for r in merge_career(h.get('allPastRuns'),h.get('recentRaces'),d['date'])[:5]:
                counts['runs']+=1
                value=r.get('timeBehindWinner')
                if value is not None and value!='':counts['marginRuns']+=1;found=True
                e=r.get('marginEvidence')
                if not isinstance(e,dict):continue
                key=(d['id'],int(h['horseNumber']),r['date'])
                try:
                    assert e['horseName']==h['name']
                    assert e['date']==r['date'] and r['date']<d['date']
                    assert e['track']==r['track'] and e['resultCname']
                    assert e['raceNumber']==r['raceNumber']
                    own=float(e['horseTimeSeconds']);winner=float(e['winnerTimeSeconds'])
                    assert math.isfinite(own) and math.isfinite(winner) and own>0 and winner>0
                    assert 0<=round(own-winner,2)<=30
                    assert abs(round(own-winner,2)-float(value))<1e-8
                    assert float(e['timeBehindWinner'])==float(value)
                except (AssertionError,KeyError,TypeError,ValueError) as exc:
                    errors.append({'id':d['id'],'horse':h['name'],'date':r['date'],'reason':type(exc).__name__})
                    continue
                counts['provenRuns']+=1
                evidence[key]={'value':value,'proof':e}
            counts['horsesWithMargin']+=found
    return counts,evidence,errors

def verify(expected,actual):
    ec,ee,errors=measure(expected);ac,ae,after_errors=measure(actual)
    lost=[k for k,v in ee.items() if ae.get(k)!=v]
    if errors or after_errors or lost:raise ValueError(f'JRA_MARGIN_D1_MISMATCH invalid={len(errors)+len(after_errors)} lost={len(lost)}')
    for d in expected.get('details') or []:
        if d.get('circuit') not in ('JRA','中央'):continue
        saved=next((x for x in actual.get('details') or [] if x.get('id')==d['id']),{})
        for field in ('preRacePrediction','preRaceBet','morningMarkSnapshot'):
            if d.get(field) is not None and saved.get(field)!=d[field]:raise ValueError('JRA_FROZEN_ORIGINAL_CHANGED '+d['id']+' '+field)
    return {'expected':ec,'reloaded':ac,'verifiedProofs':len(ee),'lostProofs':0,'invalidProofs':0}

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--expected');p.add_argument('--output',required=True);p.add_argument('--require-positive',action='store_true');a=p.parse_args()
    b=json.loads(Path(a.input).read_text());c,_,errors=measure(b)
    report=verify(json.loads(Path(a.expected).read_text()),b) if a.expected else {'counts':c,'invalidProofs':len(errors)}
    Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('JRA_MARGIN_AUDIT='+json.dumps(report,ensure_ascii=False))
    if errors or a.require_positive and c['provenRuns']==0:raise SystemExit('No valid observed JRA margins')
if __name__=='__main__':main()
