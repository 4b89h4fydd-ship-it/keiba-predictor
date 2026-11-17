import json, math, datetime, statistics, hashlib
import numpy as np
import duckdb
import lightgbm as lgb

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
  if n and pos and int(n)==n and int(pos)==pos and pos>0:entries[int(n)]=int(pos)
 active=[]
 for h in horses:
  if not isinstance(h,dict):continue
  n=fl(h.get("horseNumber"))
  if not n or int(n)!=n: return None,"invalid_horse_number"
  if h.get("scratched") is True or h.get("withdrawn") is True or str(h.get("status") or "") in ("取消","除外"):continue
  active.append((int(n),h))
 if set(entries)!=set(n for n,_ in active) or len(active)<4: return None,"incomplete_roster"
 if sorted(entries.values())[:3]!=[1,2,3] or len(set(entries.values()))!=len(entries): return None,"ambiguous_finish"
 rows=[]
 for n,h in active:
  allruns=h.get("allPastRuns") if isinstance(h.get("allPastRuns"),list) and h["allPastRuns"] else h.get("recentRaces")
  if not isinstance(allruns,list):allruns=[]
  prior=[]
  for r in allruns:
   if not isinstance(r,dict):continue
   when=str(r.get("date") or r.get("raceDate") or "")
   if not (len(when)>=10 and when[:10]<day):continue
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
  winner=next(i for i,e in enumerate(r) if e["finish"]==1)
  correct+=order[0]==winner
  top3+=winner in order[:3]
  podium+=r[order[0]]["finish"]<=3
 n=len(races)
 return {"races":n,"top1_win":correct/n if n else None,"winner_top3":top3/n if n else None,"top1_podium":podium/n if n else None}

def main():
 conn=duckdb.connect("md:")
 by={"jra":[],"nar":[]}; excluded={}; scanned=0
 days=[d for (d,) in conn.execute(f"SELECT DISTINCT CAST(race_date AS VARCHAR) FROM {SOURCE} ORDER BY 1").fetchall()]
 for day in days:
  cur=conn.execute(f"SELECT race_id,CAST(snapshot_json AS VARCHAR) FROM {SOURCE} WHERE race_date=? ORDER BY race_id",[day])
  while rows:=cur.fetchmany(1):
   for rid,raw in rows:
    scanned+=1
    snap=json.loads(raw)
    if is_banei(rid,snap):
     excluded["banei"]=excluded.get("banei",0)+1;continue
    try: r,status=extract(rid,snap,day)
    except Exception as e:
     excluded["parse_or_date_error"]=excluded.get("parse_or_date_error",0)+1;continue
    if r is None:excluded[status]=excluded.get(status,0)+1
    else:by[r[0]["circuit"]].append((day,r))
 print("AUDIT",json.dumps({"scanned":scanned,"eligible":{k:len(v) for k,v in by.items()},"excluded":excluded}),flush=True)
 conn.execute(f"""CREATE TABLE IF NOT EXISTS {DEST}.retrospective_ltr_runs
   (run_id VARCHAR, circuit VARCHAR, split VARCHAR, race_count INTEGER,
    horse_count INTEGER, metrics_json JSON, model_text VARCHAR, created_at TIMESTAMP DEFAULT current_timestamp)""")
 run_id="retro-20261111-"+hashlib.sha256(json.dumps({"eligible":{k:len(v) for k,v in by.items()},"excluded":excluded},sort_keys=True).encode()).hexdigest()[:12]
 for circuit, grouped in by.items():
  grouped.sort(key=lambda x:(x[0],x[1][0]["race_id"]))
  train,valid,test=split(grouped)
  if len(train)<40 or len(valid)<5 or len(test)<5:
   print("INSUFFICIENT",circuit,len(train),len(valid),len(test),flush=True); continue
  x,y,g=arrays(train); xv,yv,gv=arrays(valid)
  model=lgb.LGBMRanker(objective="lambdarank",learning_rate=0.04,n_estimators=250,
   num_leaves=7,min_child_samples=20,reg_lambda=2.0,verbosity=-1,
   random_state=20261111,n_jobs=2,label_gain=[0,1,3,7])
  model.fit(x,y,group=g,eval_set=[(xv,yv)],eval_group=[gv],
   eval_at=[1,3],callbacks=[lgb.early_stopping(20,verbose=False)])
  for name,races in (("train",train),("valid",valid),("test",test)):
   stats=metrics(races,model)
   stats["warning"]="RETROSPECTIVE DEVELOPMENT ONLY. historical feature availability at race time is unverified; test not sealed."
   stats["model"]="LGBMRanker"
   stats["feature_count"]=x.shape[1]
   conn.execute(f"DELETE FROM {DEST}.retrospective_ltr_runs WHERE run_id=? AND circuit=? AND split=?",
    [run_id,circuit,name])
   conn.execute(f"INSERT INTO {DEST}.retrospective_ltr_runs(run_id,circuit,split,race_count,horse_count,metrics_json,model_text) VALUES (?,?,?,?,?,?,?)",
    [run_id,circuit,name,len(races),sum(len(r) for r in races),json.dumps(stats),model.booster_.model_to_string() if name=="train" else None])
   print("TRAINED",circuit,name,json.dumps(stats),flush=True)
 print("DONE",run_id,flush=True)

if __name__=="__main__":main()
