#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys,math
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from lightgbm import LGBMRanker
from catboost import CatBoostRanker
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

ROOT=Path(__file__).resolve().parents[1]; RESEARCH=Path(__file__).resolve().parent
for p in (ROOT,RESEARCH):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import arvexq_axis_v213 as v213
import arvexq_ranker_v209 as v209

FEATURES=v213.FEATURES
META=['score','gap','p1gap','lgap','cgap','votes','agree_frac','field','market_top','market_gap','nrun','form_wavg','form_last','form_best','form_consistency','top3rate','winrate','dist_form','track_form','surface_form','speed_avg','speed_best','early_pos','late_pos','position_gain','jockey_win','trainer_win']

def normalize_cols(z):
    for col,out in (('_l','_ln'),('_c','_cn'),('_p1','_p1n')):
        z[out]=z.groupby('race_id')[col].rank(method='average',pct=True)
    return z

def tune_mix(cal):
    best=None
    for w in np.arange(0,1.01,.1):
        cal['_m']=w*cal._ln+(1-w)*cal._cn
        for a in np.arange(0,1.01,.1):
            cal['_b']=a*cal._m+(1-a)*cal._p1n
            m=v213.met(v213.picks(cal,'_b')); cand=((m['placeRate'],m['winRate']),float(w),float(a))
            if best is None or cand[0]>best[0]:best=cand
    return best[1],best[2]

def tune_market(cal,c):
    if c=='中央': return 1.0
    cm=v213.market(cal); cov=float(cm.groupby('race_id').market_ok.max().mean())
    if cov<.6:return 1.0
    best=None
    for a in np.arange(0,1.01,.05):
        cm['_f']=np.where(cm.market_ok,a*cm._b+(1-a)*cm.market_prob,cm._b)
        m=v213.met(v213.picks(cm,'_f')); cand=((m['placeRate'],m['winRate']),float(a))
        if best is None or cand[0]>best[0]:best=cand
    return best[1]

def apply_final(z,c,alpha):
    z=v213.market(z)
    z['_f']=z._b if c=='中央' else np.where(z.market_ok,alpha*z._b+(1-alpha)*z.market_prob,z._b)
    return z

def candidate_rows(z):
    out=[]
    for rid,g in z.groupby('race_id'):
        q=g.sort_values('_f',ascending=False); a=q.iloc[0]; b=q.iloc[1]
        top=int(a.horse_no)
        def gap(col):
            qq=g.sort_values(col,ascending=False); return float(qq.iloc[0][col]-qq.iloc[1][col])
        tops=[]
        for col in ('_p1n','_ln','_cn'):
            tops.append(int(g.sort_values(col,ascending=False).iloc[0].horse_no)==top)
        if bool(g.market_ok.max()):tops.append(int(g.sort_values('market_prob',ascending=False).iloc[0].horse_no)==top)
        market_top=float(a.market_prob) if bool(a.market_ok) else 0.0
        if bool(g.market_ok.max()):
            mg=g.sort_values('market_prob',ascending=False); market_gap=float(mg.iloc[0].market_prob-mg.iloc[1].market_prob)
        else:market_gap=0.0
        rec={'race_id':rid,'place':int(a.finish<=3),'win':int(a.finish==1),'score':float(a._f),'gap':float(a._f-b._f),'p1gap':gap('_p1n'),'lgap':gap('_ln'),'cgap':gap('_cn'),'votes':float(sum(tops)),'agree_frac':float(sum(tops)/max(1,len(tops))),'field':float(len(g)),'market_top':market_top,'market_gap':market_gap}
        for k in META:
            if k in rec:continue
            try:rec[k]=float(a.get(k,0.0))
            except:rec[k]=0.0
        out.append(rec)
    return pd.DataFrame(out)

def threshold(tune,target):
    if tune.empty:return .5,{'races':0,'placeRate':0.,'winRate':0.,'coverage':0.}
    best=None
    for th in sorted(set(np.quantile(tune.gate_prob,np.linspace(0,.95,20)).tolist())):
        q=tune[tune.gate_prob>=th]
        if len(q)<max(4,int(len(tune)*.08)):continue
        m=v213.met(q); ok=m['placeRate']>=target
        key=(int(ok),len(q) if ok else m['placeRate'],m['placeRate'],m['winRate'])
        if best is None or key>best[0]:best=(key,float(th),m)
    if best is None:return 1.1,{'races':0,'placeRate':0.,'winRate':0.,'coverage':0.}
    m=best[2];m['coverage']=m['races']/len(tune);return best[1],m

def split_valid(valid):
    ids=v213.race_ids(valid); cut=max(8,int(len(ids)*.6)); cut=min(cut,max(1,len(ids)-5)); return set(ids[:cut]),set(ids[cut:])

def circuit(df,c):
    d=v213.relative(df[df.circuit==c].copy()); out=[]; target=.72 if c=='中央' else .80
    for i,(tr,va,te) in enumerate(v213.folds(v213.race_ids(d)),1):
        train=d[d.race_id.isin(tr)].sort_values(['date','race_id','horse_no']).copy(); valid=d[d.race_id.isin(va)].copy(); test=d[d.race_id.isin(te)].copy()
        groups=train.groupby('race_id',sort=False).size().tolist(); y=(train.finish<=3).astype(int)
        l=LGBMRanker(objective='lambdarank',n_estimators=340,learning_rate=.035,num_leaves=31,colsample_bytree=.82,reg_lambda=1.5,random_state=215,verbosity=-1).fit(train[FEATURES],y,group=groups)
        cb=CatBoostRanker(iterations=340,depth=7,learning_rate=.04,loss_function='YetiRankPairwise',l2_leaf_reg=4,random_seed=215,verbose=False,allow_writing_files=False).fit(train[FEATURES],y,group_id=train.race_id.astype(str).tolist())
        for z in (valid,test):z['_l']=l.predict(z[FEATURES]);z['_c']=cb.predict(z[FEATURES]);z['_p1']=z.p1;normalize_cols(z)
        cal_ids,tune_ids=split_valid(valid); cal=valid[valid.race_id.isin(cal_ids)].copy(); tune=valid[valid.race_id.isin(tune_ids)].copy()
        w,a=tune_mix(cal)
        for z in (cal,tune,test):z['_m']=w*z._ln+(1-w)*z._cn;z['_b']=a*z._m+(1-a)*z._p1n
        alpha=tune_market(cal,c)
        cal=apply_final(cal,c,alpha); tune=apply_final(tune,c,alpha); test=apply_final(test,c,alpha)
        mc=candidate_rows(cal); mt=candidate_rows(tune); ms=candidate_rows(test)
        if len(mc)>=12 and mc.place.nunique()==2:
            gate=make_pipeline(StandardScaler(),LogisticRegression(C=.7,class_weight='balanced',max_iter=1000,random_state=215))
            gate.fit(mc[META],mc.place)
            mt['gate_prob']=gate.predict_proba(mt[META])[:,1];ms['gate_prob']=gate.predict_proba(ms[META])[:,1]
        else:
            mt['gate_prob']=mt.agree_frac+.2*mt.gap;ms['gate_prob']=ms.agree_frac+.2*ms.gap
        th,vm=threshold(mt,target); sel=ms[ms.gate_prob>=th].copy(); sm=v213.met(sel);sm['coverage']=len(sel)/len(te)
        base=test.copy();base['_base']=base.p1
        out.append({'fold':i,'testRaces':len(te),'current':v213.met(v213.picks(base,'_base')),'final':v213.met(v213.picks(test,'_f')),'selected':sm,'validationSelected':vm,'threshold':th,'lgbWeight':w,'modelWeight':a,'marketAlpha':alpha})
    def agg(k):
        x=[r[k] for r in out];n=sum(v['races'] for v in x);return {'races':n,'placeRate':sum(v['placeRate']*v['races'] for v in x)/n if n else 0.,'winRate':sum(v['winRate']*v['races'] for v in x)/n if n else 0.}
    ag={'current':agg('current'),'final':agg('final'),'selected':agg('selected')};ag['selected']['coverage']=sum(r['selected']['races'] for r in out)/sum(r['testRaces'] for r in out)
    return {'races':d.race_id.nunique(),'target':target,'folds':out,'aggregate':ag}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--days',type=int,default=28);ap.add_argument('--extra-jra');ap.add_argument('--out',default='gate-v215.json');a=ap.parse_args()
    details=v209.load_d1(a.days)+v209.load_extra(a.extra_jra);df=v213.dataset(details)
    rep={'generatedAt':datetime.now(v209.JST).isoformat(),'version':'v215-meta-gate','objective':'honmei place precision via second-stage gate','circuits':{}}
    for c in ('中央','地方'):
        rep['circuits'][c]=circuit(df,c);print(c,json.dumps(rep['circuits'][c]['aggregate'],ensure_ascii=False))
    Path(a.out).write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
