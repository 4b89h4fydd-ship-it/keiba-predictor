#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, json, math, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier

ROOT=Path(__file__).resolve().parents[1]; RESEARCH=Path(__file__).resolve().parent
for p in (ROOT,RESEARCH):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ.setdefault('ARVEXQ_BOOTSTRAP_WARM','0'); os.environ.setdefault('ARVEXQ_DATA_CORE','0'); os.environ.setdefault('RACEDB_AUTO_UPDATE','0')
import arvexq_axis_v213 as v213
import arvexq_ranker_v209 as v209

FEATURES=v213.FEATURES

def fv(v,d=0.0):
    try:
        x=float(str(v).replace(',','')); return x if math.isfinite(x) else d
    except:return d

def iv(v,d=0):
    try:return int(float(str(v).replace(',','')))
    except:return d

def fetch_html(url,retries=2):
    last=None
    for i in range(retries+1):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (ARVEXQ research)','Accept-Language':'ja,en;q=0.8'})
            with urllib.request.urlopen(req,timeout=20) as r:return r.read().decode('euc-jp','ignore')
        except Exception as e:
            last=e; time.sleep(.4*(i+1))
    raise last

def parse_market(nkid):
    url=f'https://race.netkeiba.com/race/result.html?race_id={nkid}'
    soup=BeautifulSoup(fetch_html(url),'html.parser'); table=soup.select_one('table.RaceTable01') or soup.find('table')
    out={}
    if not table:return out
    for tr in table.find_all('tr')[1:]:
        no=tr.select_one('td.Num.Txt_C'); pop=tr.select_one('td.Odds.Txt_C'); odds=tr.select_one('td.Odds.Txt_R')
        if not no or not odds:continue
        n=iv(no.get_text(' ',strip=True)); o=fv(odds.get_text(' ',strip=True)); p=iv(pop.get_text(' ',strip=True)) if pop else 0
        if n>0 and o>1.0:out[n]={'winOdds':o,'popularity':p}
    return out

def summary_map(details):
    missing=[d for d in details if not d.get('netkeibaRaceId')]
    if not missing:return {}
    import app as prod
    mp={}
    for ds in sorted({str(d.get('date') or '') for d in missing if d.get('date')}):
        try: rows=prod._netkeiba_race_summaries(ds) or []
        except Exception: rows=[]
        for r in rows:
            key=(str(r.get('date') or ''),str(r.get('track') or ''),iv(r.get('raceNumber')))
            nk=str(r.get('netkeibaRaceId') or '')
            if nk:mp[key]=nk
    return mp

def enrich_market(details,workers=6):
    details=copy.deepcopy(details); sm=summary_map(details); ids={}
    for d in details:
        nk=str(d.get('netkeibaRaceId') or '')
        if not nk:nk=sm.get((str(d.get('date') or ''),str(d.get('track') or ''),iv(d.get('raceNumber'))),'')
        if nk:ids[str(d.get('id') or '')]=nk
    results={}; done=0
    with ThreadPoolExecutor(max_workers=max(1,min(workers,8))) as ex:
        fut={ex.submit(parse_market,nk):(rid,nk) for rid,nk in ids.items()}
        for f in as_completed(fut):
            rid,nk=fut[f]
            try:results[rid]=f.result()
            except Exception as e: print('MARKET_ERR',rid,nk,str(e)[:100])
            done+=1
            if done%50==0 or done==len(fut):print('MARKET_PROGRESS',done,'/',len(fut),'usable',sum(bool(x) for x in results.values()))
    usable=0
    for d in details:
        m=results.get(str(d.get('id') or ''),{})
        if len(m)>=3:usable+=1
        for h in d.get('horses') or []:
            x=m.get(iv(h.get('horseNumber')))
            if x:h['winOdds']=x['winOdds']; h['popularity']=x['popularity']; h['oddsSource']='netkeiba-final-result-table-research'
    return details,{'targetRaces':len(ids),'usableMarketRaces':usable,'coverage':usable/len(ids) if ids else 0.0}

def rnorm(z,col,out):z[out]=z.groupby('race_id')[col].rank(method='average',pct=True);return z

def racepicks(df,col):
    a=[]
    for rid,g in df.groupby('race_id'):
        q=g.sort_values(col,ascending=False); top=q.iloc[0]; sec=q.iloc[1]
        fav=g.sort_values(['market_prob','horse_no'],ascending=[False,True]).iloc[0] if g.market_prob.max()>0 else None
        model=g.sort_values('_model',ascending=False).iloc[0] if '_model' in g else None
        p1=g.sort_values('p1',ascending=False).iloc[0]
        a.append({'race_id':rid,'place':int(top.finish<=3),'win':int(top.finish==1),'gap':float(top[col]-sec[col]),'score':float(top[col]),'marketProb':float(top.market_prob),'odds':float(top.odds),'agreeMarket':int(fav is not None and int(fav.horse_no)==int(top.horse_no)),'agreeModel':int(model is not None and int(model.horse_no)==int(top.horse_no)),'agreeP1':int(int(p1.horse_no)==int(top.horse_no))})
    return pd.DataFrame(a)
def met(q):return {'races':len(q),'placeRate':float(q.place.mean()) if len(q) else 0.,'winRate':float(q.win.mean()) if len(q) else 0.}
def market(df):return v213.market(df)

def tune(valid):
    best=None
    for wm in np.arange(0,1.01,.1):
      for wp1 in np.arange(0,1.01-wm,.1):
        wmk=1-wm-wp1
        valid['_final']=wm*valid._modeln+wp1*valid._p1n+wmk*valid.market_prob
        m=met(racepicks(valid,'_final'));cand=((m['placeRate'],m['winRate']),float(wm),float(wp1),float(wmk))
        if best is None or cand[0]>best[0]:best=cand
    return best[1:]
def tune_gate(valid,target=.75):
    q=racepicks(valid,'_final');best=None
    for votes in (1,2,3):
      for mq in (0,.25,.5,.65,.75):
       for gq in (0,.25,.5,.65,.75):
        mp=float(q.marketProb.quantile(mq));gap=float(q.gap.quantile(gq));votesum=q.agreeMarket+q.agreeModel+q.agreeP1
        x=q[(votesum>=votes)&(q.marketProb>=mp)&(q.gap>=gap)]
        if len(x)<max(8,int(len(q)*.08)):continue
        m=met(x);ok=m['placeRate']>=target;key=(int(ok),len(x) if ok else m['placeRate'],m['placeRate'],m['winRate'])
        if best is None or key>best[0]:best=(key,votes,mp,gap,m)
    return best[1:] if best else (1,0.,0.,met(q))
def apply_gate(q,votes,mp,gap):
    vs=q.agreeMarket+q.agreeModel+q.agreeP1;return q[(vs>=votes)&(q.marketProb>=mp)&(q.gap>=gap)]

def run(df):
    d=v213.relative(df.copy()); folds=v213.folds(v213.race_ids(d)); out=[]
    for i,(tr,va,te) in enumerate(folds,1):
        train=d[d.race_id.isin(tr)].copy();valid=market(d[d.race_id.isin(va)].copy());test=market(d[d.race_id.isin(te)].copy())
        # Only evaluate races with real market coverage. Pure ability inputs still exclude odds.
        valid=valid[valid.groupby('race_id').market_ok.transform('max')].copy();test=test[test.groupby('race_id').market_ok.transform('max')].copy()
        y=(train.finish<=3).astype(int)
        l=LGBMClassifier(n_estimators=350,learning_rate=.035,num_leaves=31,colsample_bytree=.8,reg_lambda=1.5,min_child_samples=25,random_state=215,verbosity=-1).fit(train[FEATURES],y)
        cb=CatBoostClassifier(iterations=350,depth=7,learning_rate=.04,loss_function='Logloss',l2_leaf_reg=4,random_seed=215,verbose=False,allow_writing_files=False).fit(train[FEATURES],y)
        for z in (valid,test):
            z['_l']=l.predict_proba(z[FEATURES])[:,1];z['_c']=cb.predict_proba(z[FEATURES])[:,1];z['_model']=(z._l+z._c)/2
            rnorm(z,'_model','_modeln');rnorm(z,'p1','_p1n')
        wm,wp1,wmk=tune(valid);valid['_final']=wm*valid._modeln+wp1*valid._p1n+wmk*valid.market_prob;test['_final']=wm*test._modeln+wp1*test._p1n+wmk*test.market_prob
        votes,mp,gap,gv=tune_gate(valid,.75);sq=apply_gate(racepicks(test,'_final'),votes,mp,gap)
        current=test.copy();current['_current']=current.p1
        out.append({'fold':i,'testRaces':test.race_id.nunique(),'current':met(racepicks(current,'_current')),'market':met(racepicks(test,'market_prob')),'final':met(racepicks(test,'_final')),'selected':{**met(sq),'coverage':len(sq)/max(1,test.race_id.nunique())},'validationSelected':gv,'weights':{'model':wm,'p1':wp1,'market':wmk},'gate':{'votes':votes,'marketProb':mp,'gap':gap}})
    def agg(k):
        x=[r[k] for r in out];n=sum(v['races'] for v in x);return {'races':n,'placeRate':sum(v['placeRate']*v['races'] for v in x)/n if n else 0.,'winRate':sum(v['winRate']*v['races'] for v in x)/n if n else 0.}
    a={k:agg(k) for k in ('current','market','final','selected')};a['selected']['coverage']=sum(r['selected']['races'] for r in out)/max(1,sum(r['testRaces'] for r in out))
    return {'races':d.race_id.nunique(),'folds':out,'aggregate':a}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',required=True);ap.add_argument('--out',default='jra-market-v215.json');ap.add_argument('--workers',type=int,default=6);a=ap.parse_args()
    raw=json.loads(Path(a.seed).read_text(encoding='utf-8'));details=list(raw.get('details') or [])
    details,mc=enrich_market(details,a.workers);df=v213.dataset(details);df=df[df.circuit=='中央'].copy()
    rep={'generatedAt':datetime.now(v209.JST).isoformat(),'version':'v215-jra-real-market','marketCollection':mc,'leakageGuard':{'oddsInPureFeatures':False,'resultUsedAsFeature':False,'finalWinOddsUsedOnlyForPostModelCalibration':True},'central':run(df)}
    print('MARKET',json.dumps(mc,ensure_ascii=False));print('CENTRAL',json.dumps(rep['central']['aggregate'],ensure_ascii=False));Path(a.out).write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
