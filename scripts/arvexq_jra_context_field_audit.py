#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

API_BASE=os.environ.get('ARVEXQ_API_BASE','https://kraiz-api.4b89h4fydd.workers.dev').rstrip('/')
DAYS=max(1,int(os.environ.get('ARVEXQ_DAYS','7') or 7))
END=os.environ.get('ARVEXQ_END_DATE','2026-10-05')


def present(v:Any)->bool:
    return v not in (None,'',[],{},'不明')


def api_json(url:str)->dict:
    req=urllib.request.Request(url,headers={'user-agent':'ARVEXQ-jra-context-field-audit/1.0','accept':'application/json'})
    with urllib.request.urlopen(req,timeout=45) as r:
        return json.loads(r.read().decode('utf-8'))


def main()->None:
    end=datetime.strptime(END,'%Y-%m-%d').date()
    dates=[(end-timedelta(days=i)).isoformat() for i in range(DAYS-1,-1,-1)]
    run_keys=Counter(); source_values=Counter(); title_tokens=Counter(); races=horses=runs=0
    title=number=race_id=source=0
    bias_total=bias_nonzero=bias_missing=0; bias_values=Counter()
    examples=[]
    for ds in dates:
        payload=api_json(API_BASE+'/api/day?'+urllib.parse.urlencode({'date':ds,'details':'1'}))
        for detail in payload.get('details') or []:
            if not isinstance(detail,dict) or str(detail.get('circuit') or '')!='中央':continue
            races+=1
            for h in detail.get('horses') or []:
                if not isinstance(h,dict):continue
                horses+=1
                ev=h.get('integratedEvaluation') if isinstance(h.get('integratedEvaluation'),dict) else {}
                bv=ev.get('sameDayMarkAdjustment',h.get('sameDayMarkAdjustment'))
                if not present(bv): bias_missing+=1
                else:
                    bias_total+=1
                    try:
                        x=float(bv); bias_nonzero+=int(abs(x)>1e-12); bias_values[round(x,4)]+=1
                    except (TypeError,ValueError): bias_values[str(bv)]+=1
                rr=h.get('recentRaces') or h.get('allPastRuns') or []
                for r in rr:
                    if not isinstance(r,dict):continue
                    runs+=1
                    run_keys.update(r.keys())
                    t=str(r.get('title') or r.get('raceName') or '')
                    rn=r.get('raceNumber',r.get('raceNo'))
                    rid=r.get('raceId')
                    src=str(r.get('source') or '')
                    title+=int(bool(t)); number+=int(present(rn)); race_id+=int(present(rid)); source+=int(bool(src))
                    if src:source_values[src]+=1
                    for tok in ('G1','G2','G3','GI','GII','GIII','重賞','OP','オープン','L','リステッド','3勝','2勝','1勝','新馬','未勝利'):
                        if tok.lower() in t.lower():title_tokens[tok]+=1
                    if len(examples)<8:
                        examples.append({k:r.get(k) for k in ('date','track','raceNumber','title','raceName','distance','surface','condition','finish','fieldSize','time','timeSeconds','cornerPositions','source') if k in r})
    top_keys=[{'key':k,'count':v,'rate':round(v/runs,4) if runs else None} for k,v in run_keys.most_common()]
    out={
        'version':'arvexq-jra-context-field-audit-v1','start':dates[0],'end':dates[-1],
        'races':races,'horses':horses,'runs':runs,
        'identityCoverage':{
            'title':{'count':title,'rate':round(title/runs,4) if runs else None},
            'raceNumber':{'count':number,'rate':round(number/runs,4) if runs else None},
            'raceId':{'count':race_id,'rate':round(race_id/runs,4) if runs else None},
            'source':{'count':source,'rate':round(source/runs,4) if runs else None},
        },
        'classTokens':dict(title_tokens),'sourceValues':dict(source_values),
        'bias':{'present':bias_total,'missing':bias_missing,'nonzero':bias_nonzero,'nonzeroRate':round(bias_nonzero/bias_total,4) if bias_total else None,'values':dict(bias_values.most_common(20))},
        'runKeys':top_keys,'examples':examples,
        'warning':'Audit only; examples are structural race-history fields, not used to alter production.'
    }
    print('ARVEXQ_JRA_CONTEXT_FIELD_AUDIT_JSON='+json.dumps(out,ensure_ascii=False,separators=(',',':')))

if __name__=='__main__':main()
