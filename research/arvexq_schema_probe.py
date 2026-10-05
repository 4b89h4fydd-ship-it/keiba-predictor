#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RESEARCH=Path(__file__).resolve().parent
for p in (ROOT,RESEARCH):
    s=str(p)
    if s not in sys.path: sys.path.insert(0,s)
import arvexq_ranker_v209 as v209


def walk(obj,prefix='',depth=0,out=None):
    if out is None: out=Counter()
    if depth>4: return out
    if isinstance(obj,dict):
        for k,v in obj.items():
            p=f'{prefix}.{k}' if prefix else str(k)
            out[p]+=1
            if isinstance(v,(dict,list)): walk(v,p,depth+1,out)
    elif isinstance(obj,list):
        for v in obj[:5]:
            if isinstance(v,(dict,list)): walk(v,prefix+'[]',depth+1,out)
    return out


def main():
    details=v209.load_d1(4)
    allh=Counter(); samples=[]
    for d in details:
        for h in d.get('horses') or []:
            allh.update(walk(h))
            if len(samples)<3:
                samples.append({'race':d.get('id'),'horse':h.get('horseNumber'),'keys':sorted(h.keys())})
    print('DETAILS',len(details),'HORSE_PATHS',len(allh))
    for k,n in allh.most_common():
        lk=k.lower()
        if any(x in lk for x in ('past','recent','history','last','race','run','time','finish','corner','pace','lap','speed','style','fit','weight','jockey','trainer')):
            print(f'{n:5d} {k}')
    print('SAMPLES',json.dumps(samples,ensure_ascii=False))

if __name__=='__main__': main()
