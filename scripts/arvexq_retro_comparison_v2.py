import json, math, datetime, statistics, hashlib
import numpy as np
import duckdb
import lightgbm as lgb
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, brier_score_loss

SOURCE="my_db.arvexq_analytics.race_snapshots"
DEST="arvexq_history_research.main"

def fl(v):
 try:
  x=float(v)
  return x if math.isfinite(x) else None
 except (TypeError,ValueError): return None

def is_banei(rid, snap):
 return "帯広" in rid or snap.get("track")=="帯広"

def extract(rid, snap, day):
 result=snap.get("result")
 if not isinstance(result,dict) or result.get("status")!="確定": return None,"unsettled"
 horses=snap.get("horses")
 fins=result.get("finishers")
 if not isinstance(horses,list) or not isinstance(fins,list): return None,"missing_roster"
 entries={}
 for f in fins:
  if not isinstance(f,dict):continue
  n=fl(f.get("horseNumber")); pos=fl(f.get("finish"))
  if n and pos and int(n)==n and int(pos)==pos and pos>0:
   if int(n) in entries:return None,"duplicate_result_number"
   entries[int(n)]=int(pos)
 active=[]
 for h in horses:
  if not isinstance(h,dict):continue
  n=fl(h.get("horseNumber"))
  if not n or int(n)!=n: return None,"invalid_horse_number"
  if h.get("scratched") is True or h.get("withdrawn") is True or str(h.get("status") or "") in ("取消","除外"):continue
  active.append((int(n),h))
 if len(set(n for n,_ in active))!=len(active):return None,"duplicate_entry_number"
 if set(entries)!=set(n for n,_ in active) or len(active)<4: return None,"incomplete_roster"
 if any(pos != 1+sum(q<pos for q in entries.values()) for pos in entries.values()): return None,"invalid_competition_ranks"
 rows=[]
 for n,h in active:
  allruns=h.get("allPastRuns") if isinstance(h.get("allPastRuns"),list) and h["allPastRuns"] else h.get("recentRaces")
  if not isinstance(allruns,list):allruns=[]
  prior=[]
  seen_runs=set()
  for r in allruns:
   if not isinstance(r,dict):continue
   when=str(r.get("date") or r.get("raceDate") or "")
   try:when=datetime.date.fromisoformat(when).isoformat()
   except ValueError:continue
   if when>=day:continue
   identity=(when,str(r.get("raceId"))) if r.get("raceId") else (when,hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest())
   if identity in seen_runs:continue
   seen_runs.add(identity)
   if len(when)<10 or not when[:10][:4].isdigit():continue
   finish=fl(r.get("finish"))
   distance=fl(r.get("distance"))
   pos=fl(r.get("fieldSize"))
   margin=fl(r.get("timeSeconds"))
   if finish and finish>0:prior.append((when,finish,distance,pos,margin))
  prior.sort(reverse=True)
  lasts=prior[:5]
  f=[fl(h.get("age")),fl(h.get("carriedWeight")),fl(h.get("frameNumber")),
     float(n),fl(snap.get("distance")),float(len(active)),
     float(len(prior)),float(len(lasts)),
     statistics.mean([r[1] for r in lasts]) if lasts else None,
     min([r[1] for r in lasts]) if lasts else None,
     sum(r[1]==1 for r in prior)/len(prior) if prior else None,
     sum(r[1]<=3 for r in prior)/len(prior) if prior else None,
     statistics.mean([r[2] for r in lasts if r[2]]) if any(r[2] for r in lasts) else None,
     abs(float(snap.get("distance"))-lasts[0][2]) if lasts and lasts[0][2] and fl(snap.get("distance")) else None,
     (datetime.date.fromisoformat(day)-datetime.date.fromisoformat(lasts[0][0][:10])).days if lasts else None]
  f=[x if x is not None and math.isfinite(x) else np.nan for x in f]
  rows.append({"race_id":rid,"day":day,"circuit":"jra" if str(snap.get("circuit") or "").lower() in ("中央","jra") or rid.startswith("jra-") else "nar",
     "horse_number":n,"label":max(0,4-entries[n]),"finish":entries[n],"features":f})
 return rows,"eligible"

def split(races):
 days=sorted(set(d for d,_ in races))
 if len(days)<3: return [],[],[]
 a=max(1,int(len(days)*.70)); b=max(a+1,int(len(days)*.85))
 train=set(days[:a]); valid=set(days[a:b]); test=set(days[b:])
 return ([r for d,r in races if d in train],[r for d,r in races if d in valid],[r for d,r in races if d in test])

def arrays(races):
 X=np.array([h["features"] for race in races for h in race],dtype=np.float32)
 y=np.array([h["label"] for race in races for h in race],dtype=np.int32)
 g=[len(race) for race in races]
 return X,y,g

def metrics(races,model):
 correct=0; top3=0; podium=0
 for r in races:
  s=model.predict(np.array([h["features"] for h in r],dtype=np.float32))
  order=sorted(range(len(r)),key=lambda i:(-s[i],r[i]["horse_number"]))
  winners={i for i,e in enumerate(r) if e["finish"]==1}
  correct+=order[0] in winners
  top3+=bool(winners.intersection(order[:3]))
  podium+=r[order[0]]["finish"]<=3
 n=len(races)
 return {"races":n,"top1_win":correct/n if n else None,"winner_top3":top3/n if n else None,"top1_podium":podium/n if n else None}

FEATURES=['age','carried_weight','frame','horse_number','distance','field_size','prior_count','last5_count','last5_mean_finish','last5_best_finish','prior_win_rate','prior_podium_rate','last5_mean_distance','distance_delta','days_since_run']

def evaluate(races,model,cal):
 stats=metrics(races,model)
 top5=[];mrr=[];ndcg=[]; probs=[];labels=[]
 for race in races:
  scores=model.predict(np.array([h['features'] for h in race],dtype=np.float32))
  order=np.argsort(-scores,kind='stable');winners={i for i,h in enumerate(race) if h['finish']==1}
  rank=min(list(order).index(w)+1 for w in winners)
  top5.append(rank<=5);mrr.append(1/rank)
  gains=[2**h['label']-1 for h in race]
  dcg=sum(gains[i]/math.log2(k+2) for k,i in enumerate(order[:3]))
  ideal=sum(g/math.log2(k+2) for k,g in enumerate(sorted(gains,reverse=True)[:3]))
  ndcg.append(dcg/ideal if ideal else 0)
  pp=[c.predict_proba(np.asarray(scores).reshape(-1,1))[:,1] for c in cal]
  probs.extend(zip(*pp));labels.extend((int(h['finish']==1),int(h['finish']<=3)) for h in race)
 stats.update(winner_top5=float(np.mean(top5)),mrr=float(np.mean(mrr)),ndcg3=float(np.mean(ndcg)))
 for i,name in enumerate(('win','podium')):
  y=[r[i] for r in labels];p=[r[i] for r in probs]
  stats[name+'_logloss']=float(log_loss(y,p,labels=[0,1]));stats[name+'_brier']=float(brier_score_loss(y,p))
 return stats

def main():
 conn=duckdb.connect('md:');by={'jra':[],'nar':[]};excluded={};source=[]
 for (day,) in conn.execute(f'SELECT DISTINCT CAST(race_date AS VARCHAR) FROM {SOURCE} ORDER BY 1').fetchall():
  for rid,sha,raw in conn.execute(f'SELECT race_id,sha256,CAST(snapshot_json AS VARCHAR) FROM {SOURCE} WHERE race_date=? ORDER BY race_id',[day]).fetchall():
   source.append((rid,sha));snap=json.loads(raw)
   if is_banei(rid,snap):excluded['banei']=excluded.get('banei',0)+1;continue
   r,status=extract(rid,snap,day)
   if r is None:excluded[status]=excluded.get(status,0)+1
   else:by[r[0]['circuit']].append((day,r))
 dataset=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()
 # UUID identifies executions; no old result/model is deleted or overwritten.
 import uuid
 run_id='retro-v2-'+str(uuid.uuid4())
 conn.execute(f'''CREATE TABLE IF NOT EXISTS {DEST}.retrospective_comparison_v2
 (run_id VARCHAR,dataset_hash VARCHAR,circuit VARCHAR,model VARCHAR,split VARCHAR,
 race_count INTEGER,horse_count INTEGER,metrics_json JSON,model_text VARCHAR,manifest_json JSON)''')
 print('AUDIT',json.dumps(dict(dataset_hash=dataset,eligible={k:len(v) for k,v in by.items()},excluded=excluded)),flush=True)
 for circuit,grouped in by.items():
  grouped.sort(key=lambda x:(x[0],x[1][0]['race_id']))
  train,valid,test=split(grouped)
  if min(map(len,(train,valid,test)))<5:print('INSUFFICIENT',circuit,flush=True);continue
  x,y,g=arrays(train);xv,yv,gv=arrays(valid)
  manifest=dict(features=FEATURES,source=SOURCE,dataset_hash=dataset,
      partitions={k:[r[0]['race_id'] for r in v] for k,v in [('train',train),('valid',valid),('development_test',test)]},
      warning='Retrospective C research only. Evaluation dates previously consumed; not sealed. No production adoption.',
      exclusions=excluded,calibration='Platt, validation only, per-horse marginals; not normalized race win probabilities')
  for name in ('pointwise','lambdamart','xgboost','winner','podium'):
   target=y if name not in ('winner','podium') else np.array([int(h['finish']==1 if name=='winner' else h['finish']<=3) for r in train for h in r])
   if name=='pointwise':
    model=lgb.LGBMRegressor(n_estimators=100,num_leaves=7,verbosity=-1,n_jobs=2,random_state=20261111)
    model.fit(x,target)
   elif name=='xgboost':
    model=xgb.XGBRanker(objective='rank:ndcg',n_estimators=100,max_depth=3,n_jobs=2,random_state=20261111)
    model.fit(x,target,group=g)
   else:
    model=lgb.LGBMRanker(objective='lambdarank',n_estimators=100,num_leaves=7,verbosity=-1,n_jobs=2,random_state=20261111,label_gain=[0,1,3,7])
    model.fit(x,target,group=g)
   scores=model.predict(xv).reshape(-1,1)
   cal=[]
   for mode in ('win','podium'):
    truth=[int(h['finish']==1 if mode=='win' else h['finish']<=3) for r in valid for h in r]
    calibrator=LogisticRegression(random_state=20261111).fit(scores,truth);cal.append(calibrator)
   manifest['calibrators']=[dict(coef=c.coef_.tolist(),intercept=c.intercept_.tolist()) for c in cal]
   model_text=bytes(model.get_booster().save_raw(raw_format='json')).decode() if name=='xgboost' else model.booster_.model_to_string()
   for split_name,races in [('train',train),('valid',valid),('development_test',test)]:
    stats=evaluate(races,model,cal)
    conn.execute(f'INSERT INTO {DEST}.retrospective_comparison_v2 VALUES (?,?,?,?,?,?,?,?,?,?)',[run_id,dataset,circuit,name,split_name,len(races),sum(map(len,races)),json.dumps(stats),model_text if split_name=='train' else None,json.dumps(manifest)])
    print('TRAINED',circuit,name,split_name,json.dumps(stats),flush=True)
 print('DONE',run_id,flush=True)

if __name__=='__main__':main()
