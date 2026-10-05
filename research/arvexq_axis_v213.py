#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math,re,sys
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from sklearn.isotonic import IsotonicRegression

ROOT=Path(__file__).resolve().parents[1]; RESEARCH=Path(__file__).resolve().parent
for p in (ROOT,RESEARCH):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import arvexq_ranker_v209 as v209

BASE=list(v209.FEATURES)
HIST=['nrun','form_wavg','form_last','form_best','form_consistency','top3rate','winrate','form_trend','dist_match','dist_form','track_match','track_form','surface_match','surface_form','cond_match','cond_form','speed_avg','speed_best','early_pos','late_pos','position_gain','front_rate','carried_delta','body_delta','days_since','prize_log','jockey_same','jockey_win','trainer_win','rf_ability','rf_class','rf_form','rf_pace','rf_suitability']
REL=BASE+HIST
FEATURES=BASE+HIST+[f'{x}__z' for x in REL]+[f'{x}__pct' for x in REL]

def fv(v,d=0.):
    try:
        x=float(v); return x if math.isfinite(x) else d
    except:return d

def iv(v,d=0):
    try:return int(float(v))
    except:return d

def date(v):
    try:return pd.Timestamp(str(v or '')[:10])
    except:return pd.NaT

def corners(v):
    xs=v if isinstance(v,list) else re.findall(r'\d+',str(v or ''))
    return [iv(x) for x in xs if iv(x)>0]

def stat_rate(o):
    o=o if isinstance(o,dict) else {}; n=fv(o.get('starts')); return fv(o.get('wins'))/n if n>0 else 0.

def form(r):
    f=iv(r.get('finish')); n=iv(r.get('fieldSize'))
    if f<=0:return None
    return 1. if n<=1 and f==1 else max(0.,min(1.,1-(f-1)/max(1,n-1)))

def hist(h,d):
    rd=date(d.get('date')); rid=str(d.get('id') or ''); rs=[]
    for r in h.get('recentRaces') or []:
        if not isinstance(r,dict):continue
        dt=date(r.get('date')); fs=form(r)
        if fs is None or str(r.get('raceId') or '')==rid:continue
        if not pd.isna(rd) and not pd.isna(dt) and dt>=rd:continue
        q=dict(r); q['_date']=dt; q['_form']=fs; rs.append(q)
    rs.sort(key=lambda x:x['_date'] if not pd.isna(x['_date']) else pd.Timestamp('1900-01-01'),reverse=True); rs=rs[:5]
    out={k:0. for k in HIST}; e=h.get('integratedEvaluation') or {}; rf=e.get('researchFactors') or {}
    out.update(jockey_win=stat_rate(h.get('jockeyStats')),trainer_win=stat_rate(h.get('trainerStats')),rf_ability=fv(rf.get('ability'),.5),rf_class=fv(rf.get('classLevel'),.5),rf_form=fv(rf.get('form'),.5),rf_pace=fv(rf.get('pace'),.5),rf_suitability=fv(rf.get('suitability'),.5))
    if not rs:return out
    fs=np.array([x['_form'] for x in rs]); w=np.array([5,4,3,2,1][:len(rs)])
    curdist=iv(d.get('distance')); track=str(d.get('track') or ''); surf=str(d.get('surface') or ''); cond=str(d.get('condition') or '')
    def mf(pred):
        z=[x['_form'] for x in rs if pred(x)]; return float(np.mean(z)) if z else 0.
    speeds=[]; ep=[]; lp=[]; gain=[]; front=[]
    for x in rs:
        sec=fv(x.get('timeSeconds')); dist=fv(x.get('distance')); speeds.append(dist/sec if sec>20 and dist>400 else np.nan)
        cs=corners(x.get('cornerPositions')); field=max(1,iv(x.get('fieldSize')))
        if cs:
            a=1-(cs[0]-1)/max(1,field-1); b=1-(cs[-1]-1)/max(1,field-1); ep.append(a); lp.append(b); gain.append(b-a); front.append(float(cs[0]<=max(3,round(field*.3))))
    good=[x for x in speeds if math.isfinite(x)]; last2=float(np.mean(fs[:2])); old=float(np.mean(fs[2:])) if len(fs)>2 else last2
    dt=[x['_date'] for x in rs if not pd.isna(x['_date'])]; days=max(0.,float((rd-dt[0]).days)) if dt and not pd.isna(rd) else 0.
    cw=fv(h.get('carriedWeight')); bw=fv(h.get('bodyWeight')); lastcw=fv(rs[0].get('carriedWeight')); lastbw=fv(rs[0].get('bodyWeight'))
    out.update(nrun=len(rs),form_wavg=float(np.average(fs,weights=w)),form_last=float(fs[0]),form_best=float(fs.max()),form_consistency=max(0.,1-float(fs.std())),top3rate=float(np.mean([iv(x.get('finish'))<=3 for x in rs])),winrate=float(np.mean([iv(x.get('finish'))==1 for x in rs])),form_trend=last2-old,dist_match=float(np.mean([abs(iv(x.get('distance'))-curdist)<=200 for x in rs])),dist_form=mf(lambda x:abs(iv(x.get('distance'))-curdist)<=200),track_match=float(np.mean([str(x.get('track') or '')==track and bool(track) for x in rs])),track_form=mf(lambda x:str(x.get('track') or '')==track and bool(track)),surface_match=float(np.mean([str(x.get('surface') or '')==surf and bool(surf) for x in rs])),surface_form=mf(lambda x:str(x.get('surface') or '')==surf and bool(surf)),cond_match=float(np.mean([str(x.get('condition') or '')==cond and bool(cond) for x in rs])),cond_form=mf(lambda x:str(x.get('condition') or '')==cond and bool(cond)),speed_avg=float(np.mean(good)) if good else 0.,speed_best=float(np.max(good)) if good else 0.,early_pos=float(np.mean(ep)) if ep else .5,late_pos=float(np.mean(lp)) if lp else .5,position_gain=float(np.mean(gain)) if gain else 0.,front_rate=float(np.mean(front)) if front else 0.,carried_delta=cw-lastcw if lastcw else 0.,body_delta=bw-lastbw if bw and lastbw else 0.,days_since=days,prize_log=float(np.log1p(np.mean([max(0.,fv(x.get('racePrize1'))) for x in rs]))),jockey_same=float(bool(h.get('jockey')) and str(h.get('jockey'))==str(rs[0].get('jockey') or '')))
    return out

def dataset(details):
    base=v209.rows_from_details(details); hm={}
    for d in details:
        rid=str(d.get('id') or '')
        for h in d.get('horses') or []:
            n=iv(h.get('horseNumber'))
            if rid and n>0:hm[(rid,n)]=hist(h,d)
    for r in base:r.update(hm.get((r['race_id'],r['horse_no']),{k:0. for k in HIST}))
    return pd.DataFrame(base)

def relative(df):
    z=df.copy()
    for f in REL:
        g=z.groupby('race_id')[f]; mu=g.transform('mean'); sd=g.transform('std').replace(0,np.nan)
        z[f'{f}__z']=((z[f]-mu)/sd).replace([np.inf,-np.inf],np.nan).fillna(0.); z[f'{f}__pct']=g.rank(pct=True).fillna(.5)
    return z

def market(df):
    z=df.copy(); z['market_prob']=0.; z['market_ok']=False
    for _,g in z.groupby('race_id',sort=False):
        odds=np.array([fv(x) for x in g.odds]); good=odds>1
        if good.sum()>=max(3,int(len(g)*.7)):
            inv=np.where(good,1/odds,0.); p=inv/inv.sum(); z.loc[g.index,'market_prob']=p; z.loc[g.index,'market_ok']=True
    return z

def race_ids(d):return d[['race_id','date']].drop_duplicates().sort_values(['date','race_id']).race_id.tolist()
def folds(xs):
    n=len(xs); start=max(30,int(n*.4)); step=max(1,(n-start)//4); out=[]
    for i in range(4):
        a=start+i*step; b=n if i==3 else min(n,a+step); v=max(0,a-step)
        if b-a>=8 and v>=25:out.append((xs[:v],xs[v:a],xs[a:b]))
    return out

def picks(df,col):
    out=[]
    for rid,g in df.groupby('race_id'):
        q=g.sort_values(col,ascending=False); a=q.iloc[0]; b=q.iloc[1]
        out.append({'race_id':rid,'place':int(a.finish<=3),'win':int(a.finish==1),'score':float(a[col]),'gap':float(a[col]-b[col])})
    return pd.DataFrame(out)
def met(t):return {'races':len(t),'placeRate':float(t.place.mean()) if len(t) else 0.,'winRate':float(t.win.mean()) if len(t) else 0.}
def cal(va,te,col):
    name=col+'c'; y=(va.finish<=3).astype(int)
    if len(np.unique(y))==2:
        iso=IsotonicRegression(out_of_bounds='clip').fit(va[col],y); va[name]=iso.predict(va[col]); te[name]=iso.predict(te[col])
    else:va[name]=va[col];te[name]=te[col]
    return name

def tune_gate(va,col,target=.70):
    t=picks(va,col); best=None
    for s in np.unique(np.quantile(t.score,np.linspace(0,.8,9))):
      for g in np.unique(np.quantile(t.gap,np.linspace(0,.8,9))):
        q=t[(t.score>=s)&(t.gap>=g)]
        if len(q)<max(10,int(len(t)*.1)):continue
        m=met(q); ok=m['placeRate']>=target; key=(int(ok),len(q) if ok else m['placeRate'],m['placeRate'],m['winRate'])
        if best is None or key>best[0]:best=(key,float(s),float(g),m)
    return best[1:] if best else (-1e9,-1e9,met(t))

def circuit(df,c):
    d=relative(df[df.circuit==c].copy()); out=[]
    for i,(tr,va,te) in enumerate(folds(race_ids(d)),1):
        train=d[d.race_id.isin(tr)].copy(); valid=d[d.race_id.isin(va)].copy(); test=d[d.race_id.isin(te)].copy(); y=(train.finish<=3).astype(int)
        l=LGBMClassifier(n_estimators=320,learning_rate=.035,num_leaves=31,colsample_bytree=.8,reg_lambda=1.5,min_child_samples=25,random_state=213,verbosity=-1).fit(train[FEATURES],y)
        cb=CatBoostClassifier(iterations=320,depth=7,learning_rate=.04,loss_function='Logloss',l2_leaf_reg=4,random_seed=213,verbose=False,allow_writing_files=False).fit(train[FEATURES],y)
        for z in (valid,test):z['_l']=l.predict_proba(z[FEATURES])[:,1];z['_c']=cb.predict_proba(z[FEATURES])[:,1]
        lc=cal(valid,test,'_l'); cc=cal(valid,test,'_c'); best=None
        for w in np.arange(0,1.01,.1):
            valid['_e']=w*valid[lc]+(1-w)*valid[cc]; m=met(picks(valid,'_e')); cand=((m['placeRate'],m['winRate']),float(w))
            if best is None or cand[0]>best[0]:best=cand
        w=best[1]; valid['_e']=w*valid[lc]+(1-w)*valid[cc]; test['_e']=w*test[lc]+(1-w)*test[cc]
        vm=market(valid); tm=market(test); cov=float(vm.groupby('race_id').market_ok.max().mean()); alpha=1.
        if cov>=.6:
            best=None
            for a in np.arange(0,1.01,.05):
                vm['_f']=np.where(vm.market_ok,a*vm._e+(1-a)*vm.market_prob,vm._e); m=met(picks(vm,'_f')); cand=((m['placeRate'],m['winRate']),float(a))
                if best is None or cand[0]>best[0]:best=cand
            alpha=best[1]
        tm['_f']=np.where(tm.market_ok,alpha*tm._e+(1-alpha)*tm.market_prob,tm._e); vm['_f']=np.where(vm.market_ok,alpha*vm._e+(1-alpha)*vm.market_prob,vm._e)
        s,g,gv=tune_gate(vm,'_f'); sel=picks(tm,'_f'); sel=sel[(sel.score>=s)&(sel.gap>=g)]; sm=met(sel); sm['coverage']=len(sel)/len(te)
        base=test.copy();base['_b']=base.p1
        out.append({'fold':i,'testRaces':len(te),'current':met(picks(base,'_b')),'ensemble':met(picks(test,'_e')),'final':met(picks(tm,'_f')),'selected':sm,'gateValidation':gv,'lgbWeight':w,'marketAlpha':alpha,'marketCoverage':cov})
    def agg(k):
        x=[r[k] for r in out]; n=sum(v['races'] for v in x); return {'races':n,'placeRate':sum(v['placeRate']*v['races'] for v in x)/n if n else 0.,'winRate':sum(v['winRate']*v['races'] for v in x)/n if n else 0.}
    a={'current':agg('current'),'ensemble':agg('ensemble'),'final':agg('final'),'selected':agg('selected')}; a['selected']['coverage']=sum(r['selected']['races'] for r in out)/sum(r['testRaces'] for r in out)
    return {'races':d.race_id.nunique(),'folds':out,'aggregate':a}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--days',type=int,default=28);ap.add_argument('--extra-jra');ap.add_argument('--out',default='axis-v213.json');a=ap.parse_args()
    details=v209.load_d1(a.days)+v209.load_extra(a.extra_jra);df=dataset(details)
    rep={'generatedAt':datetime.now(v209.JST).isoformat(),'version':'v213-recent5-axis','featureCount':len(FEATURES),'objective':'honmei place-rate first','circuits':{}}
    for c in ('中央','地方'):
        rep['circuits'][c]=circuit(df,c);print(c,json.dumps(rep['circuits'][c]['aggregate'],ensure_ascii=False))
    Path(a.out).write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
