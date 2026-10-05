#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, CatBoostRanker
from lightgbm import LGBMClassifier, LGBMRanker
from sklearn.isotonic import IsotonicRegression

ROOT=Path(__file__).resolve().parents[1]
RESEARCH=Path(__file__).resolve().parent
for p in (ROOT,RESEARCH):
    s=str(p)
    if s not in sys.path: sys.path.insert(0,s)

import arvexq_ranker_v209 as v209

RAW=list(v209.FEATURES)
REL_Z=[f'{x}__z' for x in RAW]
REL_RANK=[f'{x}__pct' for x in RAW]
FEATURES=RAW+REL_Z+REL_RANK


def add_relative(df: pd.DataFrame) -> pd.DataFrame:
    z=df.copy()
    for f in RAW:
        g=z.groupby('race_id')[f]
        mu=g.transform('mean')
        sd=g.transform('std').replace(0,np.nan)
        z[f'{f}__z']=((z[f]-mu)/sd).replace([np.inf,-np.inf],np.nan).fillna(0.0)
        z[f'{f}__pct']=g.rank(method='average',pct=True).fillna(.5)
    return z


def market(df: pd.DataFrame) -> pd.DataFrame:
    z=df.copy(); z['market_prob']=0.0
    for _,g in z.groupby('race_id',sort=False):
        inv=np.array([1/max(.01,float(x)) if float(x)>0 else 0 for x in g.odds],float)
        s=inv.sum(); p=inv/s if s>0 else np.zeros(len(g))
        z.loc[g.index,'market_prob']=p
    return z


def race_ids(df):
    return df[['race_id','date']].drop_duplicates().sort_values(['date','race_id']).race_id.tolist()


def folds(ids, k=4):
    n=len(ids); start=max(30,int(n*.40)); rem=n-start; step=max(1,rem//k); out=[]
    for i in range(k):
        te0=start+i*step; te1=n if i==k-1 else min(n,te0+step)
        va0=max(0,te0-step)
        if te1-te0<8 or va0<25: continue
        out.append((ids[:va0],ids[va0:te0],ids[te0:te1]))
    return out


def pick_metrics(df, col):
    n=w=p=0
    for _,g in df.groupby('race_id'):
        if g.empty: continue
        top=g.sort_values(col,ascending=False).iloc[0]
        n+=1; w+=int(int(top.finish)==1); p+=int(int(top.finish)<=3)
    return {'races':n,'winRate':w/n if n else 0.0,'placeRate':p/n if n else 0.0}


def winner_rank_metrics(df,col):
    n=t1=t3=0; rr=0.0
    for _,g in df.groupby('race_id'):
        q=g.sort_values(col,ascending=False)
        wins=q[q.finish==1]
        if wins.empty: continue
        n+=1; no=int(wins.iloc[0].horse_no); order=list(q.horse_no.astype(int)); r=order.index(no)+1
        t1+=r==1; t3+=r<=3; rr+=1/r
    return {'races':n,'top1':t1/n if n else 0.0,'top3':t3/n if n else 0.0,'mrr':rr/n if n else 0.0}


def calibrate(valid, test, col):
    va=valid.copy(); te=test.copy()
    y=(va.finish<=3).astype(int).to_numpy()
    if len(va)>=50 and len(np.unique(y))==2:
        iso=IsotonicRegression(out_of_bounds='clip')
        iso.fit(va[col].to_numpy(),y)
        va[col+'_cal']=iso.predict(va[col].to_numpy())
        te[col+'_cal']=iso.predict(te[col].to_numpy())
    else:
        va[col+'_cal']=va[col]; te[col+'_cal']=te[col]
    return va,te,col+'_cal'


def tune_axis(valid,col):
    q=market(valid); best=None
    for a in np.arange(0,1.01,.05):
        x=q.copy(); x['_b']=a*x[col]+(1-a)*x.market_prob
        m=pick_metrics(x,'_b'); cand=((m['placeRate'],m['winRate']),float(a))
        if best is None or cand[0]>best[0]: best=cand
    return best[1] if best else 1.0


def softmax_score(df,col,temp):
    z=df.copy(); z['_model_prob']=0.0
    for _,g in z.groupby('race_id',sort=False):
        x=np.asarray(g[col],float); sd=x.std() or 1.0; zz=(x-x.mean())/sd
        ex=np.exp(np.clip(zz/max(.15,temp),-20,20)); p=ex/(ex.sum() or 1.0)
        z.loc[g.index,'_model_prob']=p
    return z


def tune_rank(valid,col):
    best=None
    for t in (.3,.5,.7,1.0,1.4,2.0):
        q=market(softmax_score(valid,col,t))
        for a in np.arange(0,1.01,.1):
            x=q.copy(); x['_b']=a*x._model_prob+(1-a)*x.market_prob
            m=winner_rank_metrics(x,'_b'); obj=.7*m['top1']+.2*m['top3']+.1*m['mrr']
            cand=(obj,t,float(a))
            if best is None or cand[0]>best[0]: best=cand
    return (best[1],best[2]) if best else (1.0,1.0)


def fit_axis(train,valid,test,name):
    y=(train.finish<=3).astype(int)
    if name=='lgb':
        m=LGBMClassifier(n_estimators=500,learning_rate=.03,num_leaves=31,subsample=.9,colsample_bytree=.85,reg_lambda=1.0,random_state=212,verbosity=-1)
    else:
        m=CatBoostClassifier(iterations=500,depth=7,learning_rate=.035,loss_function='Logloss',random_seed=212,verbose=False,allow_writing_files=False)
    m.fit(train[FEATURES],y)
    va=valid.copy(); te=test.copy(); va['_raw']=m.predict_proba(va[FEATURES])[:,1]; te['_raw']=m.predict_proba(te[FEATURES])[:,1]
    va,te,col=calibrate(va,te,'_raw'); a=tune_axis(va,col)
    te=market(te); te['_blend']=a*te[col]+(1-a)*te.market_prob
    return {'alphaModel':a,'pure':pick_metrics(te,col),'blend':pick_metrics(te,'_blend')}


def fit_rank(train,valid,test,name):
    tr=train.sort_values(['date','race_id','horse_no']).copy(); groups=tr.groupby('race_id',sort=False).size().tolist()
    y=np.maximum(0,6-np.minimum(tr.finish.astype(int),6))
    if name=='lgb':
        m=LGBMRanker(objective='lambdarank',n_estimators=500,learning_rate=.03,num_leaves=31,subsample=.9,colsample_bytree=.85,reg_lambda=1.0,random_state=212,verbosity=-1)
        m.fit(tr[FEATURES],y,group=groups)
    else:
        m=CatBoostRanker(iterations=500,depth=7,learning_rate=.035,loss_function='YetiRankPairwise',random_seed=212,verbose=False,allow_writing_files=False)
        m.fit(tr[FEATURES],y,group_id=tr.race_id.astype(str).tolist())
    va=valid.copy(); te=test.copy(); va['_rank']=m.predict(va[FEATURES]); te['_rank']=m.predict(te[FEATURES])
    temp,a=tune_rank(va,'_rank'); q=market(softmax_score(te,'_rank',temp)); q['_blend']=a*q._model_prob+(1-a)*q.market_prob
    return {'temperature':temp,'alphaModel':a,'pure':winner_rank_metrics(te,'_rank'),'blend':winner_rank_metrics(q,'_blend')}


def agg(rows,path,keys):
    vals=[]
    for r in rows:
        x=r
        for p in path:x=x[p]
        vals.append(x)
    n=sum(v['races'] for v in vals); out={'races':n}
    for k in keys: out[k]=sum(v[k]*v['races'] for v in vals)/n if n else 0.0
    return out


def circuit(df,c):
    d=add_relative(df[df.circuit==c].copy()); fs=folds(race_ids(d),4); out=[]
    for i,(tr,va,te) in enumerate(fs,1):
        train=d[d.race_id.isin(tr)].copy(); valid=d[d.race_id.isin(va)].copy(); test=d[d.race_id.isin(te)].copy()
        base=test.copy(); base['_p1']=base.p1; mk=market(test)
        out.append({'fold':i,'trainRaces':len(tr),'validRaces':len(va),'testRaces':len(te),
            'currentAxis':pick_metrics(base,'_p1'),'marketAxis':pick_metrics(mk,'market_prob'),
            'axisLGB':fit_axis(train,valid,test,'lgb'),'axisCat':fit_axis(train,valid,test,'cat'),
            'currentRank':winner_rank_metrics(base,'_p1'),'marketRank':winner_rank_metrics(mk,'market_prob'),
            'rankLGB':fit_rank(train,valid,test,'lgb'),'rankCat':fit_rank(train,valid,test,'cat')})
    return {'races':d.race_id.nunique(),'folds':out,'aggregate':{
        'currentAxis':agg(out,['currentAxis'],['placeRate','winRate']),
        'marketAxis':agg(out,['marketAxis'],['placeRate','winRate']),
        'axisLGBPure':agg(out,['axisLGB','pure'],['placeRate','winRate']),
        'axisLGBBlend':agg(out,['axisLGB','blend'],['placeRate','winRate']),
        'axisCatPure':agg(out,['axisCat','pure'],['placeRate','winRate']),
        'axisCatBlend':agg(out,['axisCat','blend'],['placeRate','winRate']),
        'currentRank':agg(out,['currentRank'],['top1','top3','mrr']),
        'marketRank':agg(out,['marketRank'],['top1','top3','mrr']),
        'rankLGBPure':agg(out,['rankLGB','pure'],['top1','top3','mrr']),
        'rankLGBBlend':agg(out,['rankLGB','blend'],['top1','top3','mrr']),
        'rankCatPure':agg(out,['rankCat','pure'],['top1','top3','mrr']),
        'rankCatBlend':agg(out,['rankCat','blend'],['top1','top3','mrr'])}}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--days',type=int,default=28); ap.add_argument('--extra-jra'); ap.add_argument('--out',default='relative-v212.json'); a=ap.parse_args()
    details=v209.load_d1(a.days)+v209.load_extra(a.extra_jra); df=pd.DataFrame(v209.rows_from_details(details))
    if df.empty: raise SystemExit('no usable rows')
    rep={'generatedAt':datetime.now(v209.JST).isoformat(),'version':'v212-relative-dual-head','featureCount':len(FEATURES),'objective':'axis place-rate first; winner rank second','leakageGuard':{'resultUsedOnlyAsLabel':True,'oddsInPureModels':False,'oddsOnlyPostModelBlend':True},'circuits':{}}
    for c in ('中央','地方'):
        rep['circuits'][c]=circuit(df,c); print(c,json.dumps(rep['circuits'][c]['aggregate'],ensure_ascii=False))
    Path(a.out).write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__': main()
