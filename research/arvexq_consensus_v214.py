#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from lightgbm import LGBMRanker
from catboost import CatBoostRanker

ROOT=Path(__file__).resolve().parents[1]; RESEARCH=Path(__file__).resolve().parent
for p in (ROOT,RESEARCH):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
import arvexq_axis_v213 as v213
import arvexq_ranker_v209 as v209

FEATURES=v213.FEATURES

def rnorm(df,col,out):
    z=df.copy(); z[out]=z.groupby('race_id')[col].rank(method='average',pct=True); return z

def picks(df,col):
    out=[]
    for rid,g in df.groupby('race_id'):
        q=g.sort_values(col,ascending=False); a=q.iloc[0]; b=q.iloc[1]
        top_no=int(a.horse_no)
        src=[]
        for c in ('_p1n','_ln','_cn','market_prob'):
            if c in g.columns and (c!='market_prob' or bool(g.market_ok.max())):
                src.append(int(g.sort_values(c,ascending=False).iloc[0].horse_no)==top_no)
        out.append({'race_id':rid,'place':int(a.finish<=3),'win':int(a.finish==1),'score':float(a[col]),'gap':float(a[col]-b[col]),'votes':int(sum(src)),'sources':len(src)})
    return pd.DataFrame(out)
def met(t):return {'races':len(t),'placeRate':float(t.place.mean()) if len(t) else 0.,'winRate':float(t.win.mean()) if len(t) else 0.}

def tune_mix(valid):
    best=None
    for w in np.arange(0,1.01,.1):
        valid['_m']=w*valid._ln+(1-w)*valid._cn
        for a in np.arange(0,1.01,.1):
            valid['_b']=a*valid._m+(1-a)*valid._p1n
            m=met(picks(valid,'_b')); cand=((m['placeRate'],m['winRate']),float(w),float(a))
            if best is None or cand[0]>best[0]:best=cand
    return best[1],best[2]

def tune_market(valid,col):
    vm=v213.market(valid); cov=float(vm.groupby('race_id').market_ok.max().mean())
    if cov<.6:return 1.,cov
    best=None
    for a in np.arange(0,1.01,.05):
        vm['_f']=np.where(vm.market_ok,a*vm[col]+(1-a)*vm.market_prob,vm[col]);m=met(picks(vm,'_f'));cand=((m['placeRate'],m['winRate']),float(a))
        if best is None or cand[0]>best[0]:best=cand
    return best[1],cov

def tune_select(valid,col,target):
    t=picks(valid,col); best=None
    for votes in range(1,5):
      for qgap in (0,.25,.5,.65,.75):
        gap=float(t.gap.quantile(qgap)); q=t[(t.votes>=votes)&(t.gap>=gap)]
        if len(q)<max(8,int(len(t)*.08)):continue
        m=met(q); ok=m['placeRate']>=target; key=(int(ok),len(q) if ok else m['placeRate'],m['placeRate'],m['winRate'])
        if best is None or key>best[0]:best=(key,votes,gap,m)
    if best is None:return 1,-1e9,met(t)
    return best[1],best[2],best[3]

def circuit(df,c):
    d=v213.relative(df[df.circuit==c].copy()); out=[]; target=.75 if c=='中央' else .80
    for i,(tr,va,te) in enumerate(v213.folds(v213.race_ids(d)),1):
        train=d[d.race_id.isin(tr)].sort_values(['date','race_id','horse_no']).copy();valid=d[d.race_id.isin(va)].copy();test=d[d.race_id.isin(te)].copy()
        groups=train.groupby('race_id',sort=False).size().tolist(); y=(train.finish<=3).astype(int)
        l=LGBMRanker(objective='lambdarank',n_estimators=300,learning_rate=.035,num_leaves=31,colsample_bytree=.8,reg_lambda=1.5,random_state=214,verbosity=-1).fit(train[FEATURES],y,group=groups)
        cb=CatBoostRanker(iterations=300,depth=7,learning_rate=.04,loss_function='YetiRankPairwise',l2_leaf_reg=4,random_seed=214,verbose=False,allow_writing_files=False).fit(train[FEATURES],y,group_id=train.race_id.astype(str).tolist())
        for z in (valid,test):z['_l']=l.predict(z[FEATURES]);z['_c']=cb.predict(z[FEATURES]);z['_p1']=z.p1
        for z in (valid,test):
            for col,outcol in (('_l','_ln'),('_c','_cn'),('_p1','_p1n')):z[outcol]=z.groupby('race_id')[col].rank(method='average',pct=True)
        w,a=tune_mix(valid);valid['_m']=w*valid._ln+(1-w)*valid._cn;test['_m']=w*test._ln+(1-w)*test._cn;valid['_b']=a*valid._m+(1-a)*valid._p1n;test['_b']=a*test._m+(1-a)*test._p1n
        alpha,cov=tune_market(valid,'_b');valid=v213.market(valid);test=v213.market(test);valid['_f']=np.where(valid.market_ok,alpha*valid._b+(1-alpha)*valid.market_prob,valid._b);test['_f']=np.where(test.market_ok,alpha*test._b+(1-alpha)*test.market_prob,test._b)
        votes,gap,vm=tune_select(valid,'_f',target);sel=picks(test,'_f');sel=sel[(sel.votes>=votes)&(sel.gap>=gap)];sm=met(sel);sm['coverage']=len(sel)/len(te)
        base=test.copy();base['_base']=base.p1
        out.append({'fold':i,'testRaces':len(te),'current':met(picks(base,'_base')),'consensus':met(picks(test,'_b')),'final':met(picks(test,'_f')),'selected':sm,'validationSelected':vm,'minVotes':votes,'minGap':gap,'lgbWeight':w,'modelWeight':a,'marketAlpha':alpha,'marketCoverage':cov})
    def agg(k):
        x=[r[k] for r in out];n=sum(v['races'] for v in x);return {'races':n,'placeRate':sum(v['placeRate']*v['races'] for v in x)/n if n else 0.,'winRate':sum(v['winRate']*v['races'] for v in x)/n if n else 0.}
    ag={'current':agg('current'),'consensus':agg('consensus'),'final':agg('final'),'selected':agg('selected')};ag['selected']['coverage']=sum(r['selected']['races'] for r in out)/sum(r['testRaces'] for r in out)
    return {'races':d.race_id.nunique(),'target':target,'folds':out,'aggregate':ag}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--days',type=int,default=28);ap.add_argument('--extra-jra');ap.add_argument('--out',default='consensus-v214.json');a=ap.parse_args()
    details=v209.load_d1(a.days)+v209.load_extra(a.extra_jra);df=v213.dataset(details)
    rep={'generatedAt':datetime.now(v209.JST).isoformat(),'version':'v214-consensus-pairwise','objective':'only issue honmei when independent signals agree','circuits':{}}
    for c in ('中央','地方'):
        rep['circuits'][c]=circuit(df,c);print(c,json.dumps(rep['circuits'][c]['aggregate'],ensure_ascii=False))
    Path(a.out).write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
