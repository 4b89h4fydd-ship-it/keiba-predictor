#!/usr/bin/env python3
"""Read-only frozen ARVEXQ prediction diagnostics: circuit, popularity baseline, confidence."""
import base64, collections, datetime, gzip, hashlib, json, os, statistics
import duckdb
assert os.environ.get("motherduck_token"),"missing MotherDuck token"
con=duckdb.connect("md:my_db",config={"access_mode":"READ_ONLY"})
try:
 records=con.execute("""SELECT race_id, CAST(snapshot_json AS VARCHAR)
 FROM my_db.arvexq_analytics.race_snapshots
 WHERE json_array_length(json_extract(snapshot_json,'$.result.finishers')) >= 3
 ORDER BY race_date,race_id""").fetchall()
finally: con.close()
sets=collections.defaultdict(lambda:[0,0,0,0,0])
details=[]
reasons=collections.Counter()
for rid,txt in records:
 w=json.loads(txt); ref=w.get("arvexqFullPayload") or {}
 try:
  raw=gzip.decompress(base64.b64decode(ref["gzipBase64"],validate=True))
  assert hashlib.sha256(raw).hexdigest()==ref["sha256"] and len(raw)==ref["bytes"]
  d=json.loads(raw)
 except Exception:reasons["decode_invalid"]+=1;continue
 p=d.get("preRacePrediction")
 if not isinstance(p,dict) or p.get("frozen") is not True:continue
 t=p.get("sealedAtEpoch") or p.get("capturedAtEpoch")
 date=str(p.get("raceDate") or d.get("date") or "")
 clock=str(p.get("startTime") or d.get("startTime") or "")
 try:
  h,m=map(int,clock.replace("時",":").replace("分","").split(":")[:2])
  post=datetime.datetime.fromisoformat(date+"T00:00:00+09:00").replace(hour=h,minute=m).timestamp()
  minutes=(post-float(t))/60
 except Exception:reasons["bad_clock"]+=1;continue
 if not 0<minutes<=1440:reasons["poststart_or_invalid"]+=1;continue
 rows=[x for x in ((d.get("result") or {}).get("finishers") or []) if isinstance(x,dict)]
 finishers={int(x["horseNumber"]):int(x["finish"]) for x in rows if str(x.get("horseNumber") or "").isdigit() and str(x.get("finish") or "").isdigit()}
 winners=[no for no,pos in finishers.items() if pos==1]
 if len(winners)!=1:reasons["winner_ambiguous"]+=1;continue
 winner=winners[0]
 try:pick=int(p.get("winnerNo") or p.get("honmeiHorseNumber") or 0)
 except Exception:pick=0
 if not pick:reasons["no_pick"]+=1;continue
 candidates=[x for x in (d.get("horses") or []) if isinstance(x,dict) and not x.get("scratched")]
 first=sorted([x for x in candidates if str(x.get("popularity") or "").isdigit() and int(x["popularity"])>0],key=lambda x:int(x["popularity"]))
 top_pop=int(first[0]["horseNumber"]) if first and int(first[0]["popularity"])==1 else None
 chosen=next((x for x in candidates if str(x.get("horseNumber") or "")==str(pick)),{})
 popularity=chosen.get("popularity")
 try:popularity=int(popularity)
 except Exception:popularity=None
 confidence=p.get("winnerProbability")
 try:confidence=float(confidence)
 except Exception:confidence=None
 circuit=str(p.get("circuit") or d.get("circuit") or "unknown")
 category="JRA" if circuit.lower() in ("jra","中央") or rid.startswith("jra-") else "NAR" if rid.startswith("nar-") or circuit.lower() in ("nar","地方") else "OTHER"
 hit=int(pick==winner)
 top3=int(finishers.get(pick,99)<=3)
 baselinehit=int(top_pop==winner) if top_pop is not None else None
 def bump(k):
  a=sets[k]; a[0]+=1;a[1]+=hit;a[2]+=top3
  if baselinehit is not None:a[3]+=1;a[4]+=baselinehit
 bump("ALL");bump("CIRCUIT:"+category)
 bump("TRACK:"+str(d.get("track") or "unknown"))
 bump("FIELD:"+("<=8" if len(candidates)<=8 else "9-12" if len(candidates)<=12 else "13+"))
 bump("PICK_POP:"+("unknown" if popularity is None else "1" if popularity==1 else "2-3" if popularity<=3 else "4+"))
 bump("SEAL:"+("<=5m" if minutes<=5 else "5-15m" if minutes<=15 else ">15m"))
 if confidence is not None:
  bump("CONF:"+("<=.3" if confidence<=.3 else ".3-.5" if confidence<=.5 else ">.5"))
 details.append({"id":rid,"hit":hit,"top3":top3,"popular":popularity,"probability":confidence,"minutes":round(minutes,1),"baseline":baselinehit,"circuit":category,"field":len(candidates),"frozen_status":str(p.get("status")),"winner_stable":p.get("winnerStable"),"data_quality":str(p.get("dataQuality"))[:80]})
summary={k:{"n":v[0],"hit":v[1],"win_pct":round(100*v[1]/v[0],1),"top3_pct":round(100*v[2]/v[0],1),"popularity_baseline_n":v[3],"popularity_baseline_win_pct":round(100*v[4]/v[3],1) if v[3] else None} for k,v in sorted(sets.items())}
print("FROZEN_DIAGNOSTIC_AGGREGATES",json.dumps(summary,ensure_ascii=False))
print("FROZEN_DIAGNOSTIC_STATUS",json.dumps({"status_counts":dict(collections.Counter(x["frozen_status"] for x in details)),"stable_counts":dict(collections.Counter(str(x["winner_stable"]) for x in details)),"quality_counts":dict(collections.Counter(x["data_quality"] for x in details)),"probability_available":sum(x["probability"] is not None for x in details),"other_errors":dict(reasons)},ensure_ascii=False))
