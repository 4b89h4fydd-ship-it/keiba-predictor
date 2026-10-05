#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, re, sys, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from catboost import CatBoostRanker
from lightgbm import LGBMRanker
import backtest_v206 as core

JST=timezone(timedelta(hours=9))
API='https://kraiz-api.4b89h4fydd.workers.dev'
BASE_FEATURES=list(core.FEATURES)
EXTRA=['age','carried_weight','body_weight','body_change']
FEATURES=BASE_FEATURES+EXTRA


def iv(v,d=0):
    try:return int(float(v))
    except:return d

def fv(v,d=0.0):
    try:
        x=float(v); return x if math.isfinite(x) else d
    except:return d

def age_of(h):
    for k in ('age','horseAge'):
        if h.get(k) is not None:return fv(h.get(k))
    s=str(h.get('sexAge') or h.get('ageSex') or '')
    m=re.search(r'(\d+)',s)
    return float(m.group(1)) if m else 0.0

def carried(h):
    for k in ('carriedWeight','weight','burdenWeight'):
        if h.get(k) is not None:
            m=re.search(r'\d+(?:\.\d+)?',str(h.get(k)))
            if m:return float(m.group())
    return 0.0

def body(h):
    bw=fv(h.get('bodyWeight'))
    bc=fv(h.get('bodyWeightChange'))
    return bw,bc

def api_json(url):
    req=urllib.request.Request(url,headers={'user-agent':'ARVEXQ-v209-ranker/1.0','accept':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode('utf-8'))

def load_d1(days):
    today=datetime.now(JST).date(); out=[]
    for off in range(1,days+1):
        ds=(today-timedelta(days=off)).isoformat()
        url=API+'/api/day?'+urllib.parse.urlencode({'date':ds,'details':'1'})
        try:p=api_json(url)
        except Exception as e:
            print('D1_ERR',ds,str(e)[:120]); continue
        for d in p.get('details') or []:
            if isinstance(d,dict):out.append(d)
        print('D1',ds,'details',len(p.get('details') or []))
    return out

def load_extra(path):
    if not path:return []
    p=Path(path)
    if not p.exists():return []
    z=json.loads(p.read_text(encoding='utf-8'))
    return list(z.get('details') or [])

def finish_map(d):
    z={}
    for r in ((d.get('result') or {}).get('finishers') or []):
        n=iv(r.get('horseNumber')); f=iv(r.get('finish'))
        if n>0 and f>0:z[n]=f
    return z

def scratched(h):
    return h.get('scratched') is True or bool(re.search(r'取消|除外',str(h.get('status') or '')))

def rows_from_details(details):
    rows=[]; seen=set()
    for d in details:
        rid=str(d.get('id') or '')
        if not rid or rid in seen:continue
        fm=finish_map(d)
        if len(fm)<3:continue
        hs=[]
        for h in d.get('horses') or []:
            if scratched(h):continue
            n=iv(h.get('horseNumber')); e=h.get('integratedEvaluation') or {}
            if n<=0 or n not in fm or not e:continue
            feat=core.feature_vector(h)
            bw,bc=body(h)
            rec={k:fv(feat.get(k),.5) for k in BASE_FEATURES}
            rec.update({'age':age_of(h),'carried_weight':carried(h),'body_weight':bw,'body_change':bc})
            odds=fv(h.get('winOdds'),0.0)
            hs.append({'race_id':rid,'date':str(d.get('date') or ''),'circuit':str(d.get('circuit') or ('中央' if rid.startswith('jra-') else '地方')),'track':str(d.get('track') or ''),'surface':str(d.get('surface') or ''),'distance':iv(d.get('distance')),'horse_no':n,'finish':fm[n],'label':max(0,6-min(fm[n],6)),'p1':fv(e.get('p1Score'),0.0),'odds':odds,**rec})
        if len(hs)>=4:
            rows.extend(hs); seen.add(rid)
    return rows

def split_races(df):
    races=(df[['race_id','date']].drop_duplicates().sort_values(['date','race_id']))
    ids=races.race_id.tolist(); n=len(ids)
    a=max(1,int(n*.60)); b=max(a+1,int(n*.80)); b=min(b,n-1)
    return set(ids[:a]),set(ids[a:b]),set(ids[b:])

def group_order(df, ids):
    z=df[df.race_id.isin(ids)].sort_values(['date','race_id','horse_no']).copy()
    return z, z.groupby('race_id',sort=False).size().tolist()

def fit_models(df, train_ids):
    tr,groups=group_order(df,train_ids)
    X=tr[FEATURES]; y=tr.label
    lgb=LGBMRanker(objective='lambdarank',n_estimators=450,learning_rate=.035,num_leaves=31,max_depth=-1,subsample=.9,colsample_bytree=.9,reg_lambda=.8,random_state=209,verbosity=-1)
    lgb.fit(X,y,group=groups)
    cb=CatBoostRanker(iterations=450,depth=7,learning_rate=.04,loss_function='YetiRankPairwise',random_seed=209,verbose=False,allow_writing_files=False)
    cb.fit(X,y,group_id=tr.race_id.astype(str).tolist())
    return {'lightgbm':lgb,'catboost':cb}

def metrics_for(df, score_col):
    n=t1=t3=0; rr=0.0
    for _,g in df.groupby('race_id'):
        g=g.sort_values(score_col,ascending=False)
        win=g[g.finish==1]
        if win.empty:continue
        n+=1; rank=list(g.horse_no).index(int(win.iloc[0].horse_no))+1
        t1+=rank==1; t3+=rank<=3; rr+=1/rank
    return {'races':n,'top1':t1/n if n else 0,'top3':t3/n if n else 0,'mrr':rr/n if n else 0}

def add_market(df):
    probs=[]
    for _,g in df.groupby('race_id',sort=False):
        inv=np.array([1/max(.01,x) if x>0 else 0 for x in g.odds],float); s=inv.sum()
        p=inv/s if s>0 else np.zeros(len(g))
        probs.extend(p.tolist())
    z=df.copy(); z['market_prob']=probs; return z

def add_model_prob(df,score,temp):
    vals=[]
    for _,g in df.groupby('race_id',sort=False):
        x=np.asarray(g[score],float); sd=x.std() or 1.0; zz=(x-x.mean())/sd
        ex=np.exp(np.clip(zz/max(.15,temp),-20,20)); vals.extend((ex/(ex.sum() or 1)).tolist())
    z=df.copy(); z['model_prob']=vals; return z

def tune_blend(valid,score):
    best=None
    for temp in (.3,.5,.7,1.0,1.4,2.0):
        z=add_market(add_model_prob(valid,score,temp))
        mz=z[z.market_prob>0]
        for alpha in np.arange(0,1.01,.1):
            q=mz.copy(); q['blend']=alpha*q.model_prob+(1-alpha)*q.market_prob
            m=metrics_for(q,'blend'); obj=.70*m['top1']+.20*m['top3']+.10*m['mrr']
            cand=(obj,temp,float(alpha),m)
            if best is None or cand[0]>best[0]:best=cand
    return best

def confidence_report(df,score):
    z=add_market(add_model_prob(df,score,1.0)); out={}
    race=[]
    for rid,g in z.groupby('race_id'):
        g=g.sort_values(score,ascending=False); top=g.iloc[0]; second=g.iloc[1]
        fav=g.sort_values('market_prob',ascending=False).iloc[0] if g.market_prob.max()>0 else None
        race.append({'rid':rid,'win':int(top.finish)==1,'top3':int(top.finish)<=3,'margin':float(top.model_prob-second.model_prob),'agree':bool(fav is not None and int(fav.horse_no)==int(top.horse_no))})
    if not race:return out
    r=pd.DataFrame(race)
    for name,mask in [('agree',r.agree),('disagree',~r.agree)]:
        q=r[mask]; out[name]={'races':len(q),'top1':float(q.win.mean()) if len(q) else 0,'top3':float(q.top3.mean()) if len(q) else 0}
    cut=r.margin.quantile(.5); q=r[r.margin>=cut]; out['high_margin50']={'races':len(q),'top1':float(q.win.mean()),'top3':float(q.top3.mean())}
    q=r[(r.margin>=cut)&r.agree]; out['agree_high_margin']={'races':len(q),'top1':float(q.win.mean()) if len(q) else 0,'top3':float(q.top3.mean()) if len(q) else 0}
    return out

def circuit_run(df,circuit):
    d=df[df.circuit==circuit].copy(); tr,va,ho=split_races(d)
    if len(ho)<10:return {'error':'insufficient','races':d.race_id.nunique()}
    models=fit_models(d,tr); valid=d[d.race_id.isin(va)].copy(); hold=d[d.race_id.isin(ho)].copy()
    hold['baseline']=hold.p1; res={'races':d.race_id.nunique(),'train':len(tr),'valid':len(va),'holdout':len(ho),'baseline':metrics_for(hold,'baseline'),'models':{}}
    for name,m in models.items():
        valid[name]=m.predict(valid[FEATURES]); hold[name]=m.predict(hold[FEATURES])
        pure=metrics_for(hold,name); tuned=tune_blend(valid,name)
        blend=None
        if tuned:
            _,temp,alpha,vm=tuned; q=add_market(add_model_prob(hold,name,temp)); q['blend']=alpha*q.model_prob+(1-alpha)*q.market_prob
            q=q[q.market_prob>0]; blend={'alphaModel':alpha,'temperature':temp,'validation':vm,'holdout':metrics_for(q,'blend'),'marketOnly':metrics_for(q,'market_prob'),'marketRaces':q.race_id.nunique()}
        res['models'][name]={'pure':pure,'blend':blend,'confidence':confidence_report(hold,name)}
    return res

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--days',type=int,default=28); ap.add_argument('--extra-jra'); ap.add_argument('--out',default='ranker-v209.json'); a=ap.parse_args()
    details=load_d1(a.days)+load_extra(a.extra_jra); rows=rows_from_details(details); df=pd.DataFrame(rows)
    if df.empty:raise SystemExit('no usable rows')
    report={'generatedAt':datetime.now(JST).isoformat(),'featureCount':len(FEATURES),'features':FEATURES,'leakageGuard':{'resultAsFeature':False,'payoutAsFeature':False,'oddsInPureRanker':False,'oddsOnlyPostModelCalibration':True},'circuits':{}}
    for c in ('中央','地方'):
        report['circuits'][c]=circuit_run(df,c)
        print(c,json.dumps(report['circuits'][c],ensure_ascii=False))
    Path(a.out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
