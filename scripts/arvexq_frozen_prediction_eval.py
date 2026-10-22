#!/usr/bin/env python3
"""Read-only ARVEXQ strictly pre-start frozen prediction evaluation.
Never uses result/odds as a prediction input; evaluates only persisted frozen snapshots.
"""
import base64, collections, datetime, gzip, hashlib, json, os
import duckdb
assert os.environ.get("motherduck_token"), "missing MotherDuck token"
con=duckdb.connect("md:my_db",config={"access_mode":"READ_ONLY"})
try:
    records=con.execute("""SELECT race_id,cast(snapshot_json as varchar)
    FROM my_db.arvexq_analytics.race_snapshots
    WHERE json_array_length(json_extract(snapshot_json,'$.result.finishers')) >= 3
    ORDER BY race_date,race_id""").fetchall()
finally:
    con.close()
counts=collections.Counter()
winner_hits=0
top3_hits=0
predicted={}
examples=[]
for rid,thin in records:
    wrap=json.loads(thin); ref=wrap.get("arvexqFullPayload") or {}
    try:
        raw=gzip.decompress(base64.b64decode(ref["gzipBase64"],validate=True))
        assert len(raw)==ref["bytes"] and hashlib.sha256(raw).hexdigest()==ref["sha256"]
        full=json.loads(raw)
    except Exception:
        counts["decode_invalid"]+=1
        continue
    pred=full.get("preRacePrediction")
    if not isinstance(pred,dict):
        counts["no_prerace_prediction"]+=1
        continue
    counts["prerace_snapshot"]+=1
    if pred.get("frozen") is not True:
        counts["not_frozen"]+=1
        continue
    counts["frozen"]+=1
    # Evidence cannot be inferred from a snapshot saved after the finish.
    capture=pred.get("sealedAtEpoch") or pred.get("capturedAtEpoch")
    start=str(pred.get("startTime") or full.get("startTime") or "")
    date=str(pred.get("raceDate") or full.get("date") or "")
    if not isinstance(capture,(int,float)) or len(date)!=10 or len(start)<4:
        counts["missing_capture_or_start"]+=1
        continue
    try:
        clock=start.strip().replace("時",":").replace("分","").split(":")
        hh,mm=int(clock[0]),int(clock[1])
        post=datetime.datetime.fromisoformat(date+"T00:00:00+09:00").replace(hour=hh,minute=mm).timestamp()
    except Exception:
        counts["unparseable_start"]+=1
        continue
    minutes=(post-float(capture))/60
    if not 0<minutes<=1440:
        counts["not_provably_before_post"]+=1
        continue
    counts["sealed_before_post"]+=1
    result=full.get("result") or {}
    order=sorted([(int(f.get("finish")),int(f.get("horseNumber"))) for f in (result.get("finishers") or []) if isinstance(f,dict) and str(f.get("finish") or "").isdigit() and str(f.get("horseNumber") or "").isdigit()])
    if len(order)<3 or order[0][0]!=1:
        counts["result_incomplete"]+=1
        continue
    winner=order[0][1]
    pick=pred.get("winnerNo") or pred.get("honmeiHorseNumber")
    try:pick=int(pick)
    except (TypeError,ValueError):pick=0
    if not pick:
        counts["missing_pick"]+=1
        continue
    counts["scorable_frozen_winner"]+=1
    winner_hits+=int(pick==winner)
    top3_hits+=int(pick in [no for _,no in order[:3]])
    examples.append(round(minutes,1))
    predicted[rid]=pick
n=counts["scorable_frozen_winner"]
print("FROZEN_PREPOST_AUDIT",json.dumps({"total_finalized":len(records),"counts":counts,"scorable":n,"winner_hits":winner_hits,"winner_hit_rate":round(winner_hits/n,4) if n else None,"selected_horse_top3_hits":top3_hits,"selected_horse_top3_rate":round(top3_hits/n,4) if n else None,"seal_to_post_min_minutes":min(examples) if examples else None,"seal_to_post_max_minutes":max(examples) if examples else None,"return_on_investment":"NOT_COMPUTED_NO_VERIFIED_BET_ODDS"},ensure_ascii=False))
