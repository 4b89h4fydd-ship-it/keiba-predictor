#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, sys
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = Path(__file__).resolve().parent
for p in (ROOT, RESEARCH):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from arvexq_ranker_v209 import JST, FEATURES, load_d1, load_extra, rows_from_details


def race_ids_by_time(df: pd.DataFrame) -> list[str]:
    return df[['race_id','date']].drop_duplicates().sort_values(['date','race_id']).race_id.tolist()


def fold_ranges(ids: list[str], folds: int = 4):
    n=len(ids)
    start=max(20,int(n*.40))
    remain=n-start
    step=max(1,remain//folds)
    out=[]
    for i in range(folds):
        te0=start+i*step
        te1=n if i==folds-1 else min(n,te0+step)
        if te1-te0<5: continue
        va0=max(0,te0-step)
        train=ids[:va0] if va0>=20 else ids[:te0]
        valid=ids[va0:te0] if va0>=20 else []
        test=ids[te0:te1]
        if len(train)>=20 and len(test)>=5:
            out.append((train,valid,test))
    return out


def add_market_prob(z: pd.DataFrame) -> pd.DataFrame:
    z=z.copy(); vals=[]
    for _,g in z.groupby('race_id',sort=False):
        inv=np.array([1/max(.01,float(x)) if float(x)>0 else 0 for x in g.odds],float)
        s=inv.sum(); p=inv/s if s>0 else np.zeros(len(g)); vals.extend(p.tolist())
    z['market_prob']=vals
    return z


def selection_metrics(z: pd.DataFrame, score: str) -> dict:
    n=win=place=0
    for _,g in z.groupby('race_id'):
        if g.empty: continue
        top=g.sort_values(score,ascending=False).iloc[0]
        n+=1; win += int(top.finish==1); place += int(top.finish<=3)
    return {'races':n,'winRate':win/n if n else 0.0,'placeRate':place/n if n else 0.0}


def tune_alpha(valid: pd.DataFrame, model_col: str):
    if valid.empty: return 1.0, selection_metrics(valid.assign(_blend=0.0),'_blend')
    q=add_market_prob(valid)
    best=None
    for a in np.arange(0,1.01,.05):
        x=q.copy(); x['_blend']=a*x[model_col]+(1-a)*x.market_prob
        m=selection_metrics(x,'_blend')
        obj=(m['placeRate'],m['winRate'])
        if best is None or obj>best[0]: best=(obj,float(a),m)
    return best[1],best[2]


def fit_predict(train: pd.DataFrame, valid: pd.DataFrame, test: pd.DataFrame, model_name: str):
    Xtr=train[FEATURES]; ytr=(train.finish<=3).astype(int)
    if model_name=='lightgbm':
        m=LGBMClassifier(n_estimators=500,learning_rate=.03,num_leaves=31,subsample=.9,colsample_bytree=.9,reg_lambda=1.0,random_state=211,verbosity=-1)
    else:
        m=CatBoostClassifier(iterations=500,depth=7,learning_rate=.035,loss_function='Logloss',random_seed=211,verbose=False,allow_writing_files=False)
    m.fit(Xtr,ytr)
    va=valid.copy(); te=test.copy()
    va['model_prob']=m.predict_proba(va[FEATURES])[:,1] if len(va) else []
    te['model_prob']=m.predict_proba(te[FEATURES])[:,1]
    alpha,_=tune_alpha(va,'model_prob') if len(va) else (1.0,{})
    te=add_market_prob(te); te['blend']=alpha*te.model_prob+(1-alpha)*te.market_prob
    return {
        'alphaModel':alpha,
        'pure':selection_metrics(te,'model_prob'),
        'blend':selection_metrics(te,'blend')
    }


def run_circuit(df: pd.DataFrame, circuit: str):
    d=df[df.circuit==circuit].copy()
    ids=race_ids_by_time(d); folds=fold_ranges(ids,4)
    detail=[]
    for i,(tr,va,te) in enumerate(folds,1):
        train=d[d.race_id.isin(tr)].copy(); valid=d[d.race_id.isin(va)].copy(); test=d[d.race_id.isin(te)].copy()
        base=test.copy(); base['p1score']=base.p1
        market=add_market_prob(test)
        row={
            'fold':i,'trainRaces':len(tr),'validRaces':len(va),'testRaces':len(te),
            'currentHonmei':selection_metrics(base,'p1score'),
            'marketFavorite':selection_metrics(market,'market_prob'),
            'lightgbm':fit_predict(train,valid,test,'lightgbm'),
            'catboost':fit_predict(train,valid,test,'catboost')
        }
        detail.append(row)
    def agg(path):
        vals=[]
        for r in detail:
            x=r
            for k in path: x=x[k]
            vals.append(x)
        races=sum(v['races'] for v in vals)
        return {'races':races,'winRate':sum(v['winRate']*v['races'] for v in vals)/races if races else 0,'placeRate':sum(v['placeRate']*v['races'] for v in vals)/races if races else 0}
    return {
        'races':d.race_id.nunique(),'folds':detail,
        'aggregate':{
            'currentHonmei':agg(['currentHonmei']),
            'marketFavorite':agg(['marketFavorite']),
            'lightgbmPure':agg(['lightgbm','pure']),
            'lightgbmBlend':agg(['lightgbm','blend']),
            'catboostPure':agg(['catboost','pure']),
            'catboostBlend':agg(['catboost','blend'])
        }
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--days',type=int,default=28); ap.add_argument('--extra-jra'); ap.add_argument('--out',default='axis-v211.json'); a=ap.parse_args()
    details=load_d1(a.days)+load_extra(a.extra_jra)
    df=pd.DataFrame(rows_from_details(details))
    if df.empty: raise SystemExit('no usable rows')
    report={'generatedAt':datetime.now(JST).isoformat(),'objective':'maximize honmei place rate first, then win rate','leakageGuard':{'resultAsFeature':False,'payoutAsFeature':False,'marketOnlyPostModel':True},'circuits':{}}
    for c in ('中央','地方'):
        report['circuits'][c]=run_circuit(df,c)
        print(c,json.dumps(report['circuits'][c]['aggregate'],ensure_ascii=False))
    Path(a.out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__': main()
