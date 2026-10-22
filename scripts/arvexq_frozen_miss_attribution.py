#!/usr/bin/env python3
"""ARVEXQ frozen-winner error attribution; read-only, no new prediction model.
Compares saved original horse feature scores for the picked horse and actual winner.
"""
import base64,collections,datetime,gzip,hashlib,json,os
import duckdb
assert os.getenv("motherduck_token"),"Missing MotherDuck token"
con=duckdb.connect("md:my_db",config={"access_mode":"READ_ONLY"})
try:
 records=con.execute("""SELECT race_id,CAST(snapshot_json AS VARCHAR) FROM my_db.arvexq_analytics.race_snapshots
 WHERE json_array_length(json_extract(snapshot_json,'$.result.finishers')) >= 3 ORDER BY race_date,race_id""").fetchall()
finally:con.close()
paths={
 "ability_p1":("integratedEvaluation","p1Score"),
 "ability_score":("integratedEvaluation","score"),
 "ability_race_performance":("integratedEvaluation","components","racePerformance"),
 "ability_distance_fit":("integratedEvaluation","components","distanceFit"),
 "ability_course_fit":("integratedEvaluation","components","courseFit"),
 "ability_opponent_level":("integratedEvaluation","components","opponentLevelScore"),
 "ability_lap":("integratedEvaluation","components","lapScore"),
 "ability_jockey":("integratedEvaluation","components","jockeyScore"),
 "ability_trainer":("integratedEvaluation","components","trainerScore"),
 "ability_completeness":("integratedEvaluation","dataCompleteness"),
 "style_early":("precomputedMetrics","style","early3"),
 "style_ten":("precomputedMetrics","style","ten"),
 "style_close":("precomputedMetrics","style","close"),
 "style_late":("precomputedMetrics","style","moved3"),
 "style_samples":("precomputedMetrics","style","samples"),
 "fit_distance":("precomputedMetrics","fit","distance"),
 "fit_track":("precomputedMetrics","fit","track"),
 "fit_condition":("precomputedMetrics","fit","condition"),
}
stats={k:collections.Counter() for k in paths}
missing=collections.Counter()
examples=[]
tot=collections.Counter()
def get(d,path):
 for p in path:
  if not isinstance(d,dict):return None
  d=d.get(p)
 try:
  if d is None or isinstance(d,bool):return None
  v=float(d)
  return v if v==v and abs(v)<1e9 else None
 except (ValueError,TypeError):return None
for rid,txt in records:
 w=json.loads(txt);ref=w.get("arvexqFullPayload") or {}
 try:
  raw=gzip.decompress(base64.b64decode(ref["gzipBase64"],validate=True))
  if len(raw)!=ref["bytes"] or hashlib.sha256(raw).hexdigest()!=ref["sha256"]:raise ValueError()
  d=json.loads(raw)
 except Exception:tot["invalid_payload"]+=1;continue
 p=d.get("preRacePrediction")
 if not isinstance(p,dict) or p.get("frozen") is not True:continue
 t=p.get("sealedAtEpoch") or p.get("capturedAtEpoch")
 date=str(p.get("raceDate") or d.get("date") or "")
 clock=str(p.get("startTime") or d.get("startTime") or "")
 try:
  hh,mm=map(int,clock.replace("時",":").replace("分","").split(":")[:2])
  start=datetime.datetime.fromisoformat(date+"T00:00:00+09:00").replace(hour=hh,minute=mm).timestamp()
  if not 0<(start-float(t))/60<=1440:continue
 except Exception:continue
 finishers=(d.get("result") or {}).get("finishers") or []
 winners=[int(f["horseNumber"]) for f in finishers if isinstance(f,dict) and str(f.get("finish"))=="1" and str(f.get("horseNumber") or "").isdigit()]
 if len(winners)!=1:continue
 try:pick=int(p.get("winnerNo") or p.get("honmeiHorseNumber") or 0)
 except (ValueError,TypeError):continue
 if not pick:continue
 horses={int(h["horseNumber"]):h for h in (d.get("horses") or []) if isinstance(h,dict) and str(h.get("horseNumber") or "").isdigit()}
 if pick not in horses or winners[0] not in horses:tot["missing_horse"]+=1;continue
 if pick==winners[0]:tot["correct"]+=1;continue
 tot["misses"]+=1
 chosen=horses[pick];actual=horses[winners[0]]
 row={"race_id":rid,"pick":pick,"winner":winners[0],"winner_higher":[],"pick_higher":[],"missing":[]}
 for key,path in paths.items():
  a=get(chosen,path);b=get(actual,path)
  if a is None or b is None:
   stats[key]["missing_pair"]+=1;row["missing"].append(key);continue
  stats[key]["comparable"]+=1
  if b>a:stats[key]["winner_higher"]+=1;row["winner_higher"].append(key)
  elif a>b:stats[key]["pick_higher"]+=1;row["pick_higher"].append(key)
  else:stats[key]["tie"]+=1
 examples.append(row)
summary={k:dict(v) for k,v in stats.items()}
print("FROZEN_MISS_ATTRIBUTION",json.dumps({"counts":dict(tot),"metrics":summary},ensure_ascii=False))
print("FROZEN_MISS_CASES",json.dumps(examples,ensure_ascii=False))
print("ATTRIBUTION_CAUTION","Post-race race snapshot may contain updated evaluation fields; these are diagnostic correlations, not verified pre-race feature values.")
