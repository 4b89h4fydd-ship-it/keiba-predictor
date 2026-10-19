"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/api/v1/model-audit")
def model_audit(date: str = Query(""), days: int = Query(30, ge=1, le=180)):
    end=date or _today_iso()
    try:end_dt=datetime.strptime(end,"%Y-%m-%d").date()
    except Exception:raise HTTPException(status_code=400,detail="date must be YYYY-MM-DD")
    start_dt=end_dt-timedelta(days=max(0,int(days)-1));start=start_dt.isoformat()
    rows=[];cal=[];segments={}
    if not RACEDB.path.exists():return {"version":PRERACE_AUDIT_VERSION,"races":0,"audited":0,"start":start,"end":end}
    conn=sqlite3.connect(RACEDB.path,timeout=3);conn.row_factory=sqlite3.Row
    try:dbrows=conn.execute("SELECT payload FROM race_snapshots WHERE race_date BETWEEN ? AND ? ORDER BY race_date,track,race_no",(start,end)).fetchall()
    finally:conn.close()
    for row in dbrows:
        try:d=json.loads(row["payload"])
        except Exception:continue
        a=d.get("predictionAudit") if isinstance(d.get("predictionAudit"),dict) else _prediction_audit_from_lock(d)
        if not a:continue
        rows.append(a)
        seg=str(a.get("circuit") or "不明");z=segments.setdefault(seg,{"races":0,"hits":0,"marked":0});z["races"]+=1;z["hits"]+=1 if a.get("honHit") else 0;z["marked"]+=1 if a.get("winnerMarked") else 0
        lock=d.get("preRacePrediction") if isinstance(d.get("preRacePrediction"),dict) else {};winner=int(a.get("winnerNo") or 0)
        for h in lock.get("horses") or []:
            try:p=max(0.0,min(1.0,float(h.get("decisionProbability") or 0)))
            except Exception:continue
            cal.append((p,1 if int(h.get("horseNumber") or 0)==winner else 0))
    n=len(rows);hits=sum(1 for a in rows if a.get("honHit"));marked=sum(1 for a in rows if a.get("winnerMarked"));top2=sum(1 for a in rows if a.get("top2Hit"));top3=sum(1 for a in rows if a.get("top3Hit"));hc=[a for a in rows if a.get("highConfidence")]
    reasons={}
    for a in rows:
        if a.get("honHit"):continue
        k=str(a.get("reason") or "その他");reasons[k]=reasons.get(k,0)+1
    bins=[];ece=0.0
    for bi in range(10):
        lo=bi/10;hi=(bi+1)/10;vals=[x for x in cal if (x[0]>=lo and (x[0]<hi or (bi==9 and x[0]<=hi)))]
        if not vals:continue
        pm=sum(x[0] for x in vals)/len(vals);ar=sum(x[1] for x in vals)/len(vals);ece+=abs(pm-ar)*len(vals)/max(1,len(cal));bins.append({"lo":lo,"hi":hi,"count":len(vals),"predicted":round(pm,4),"actual":round(ar,4),"gap":round(ar-pm,4)})
    segout={k:{"races":v["races"],"top1":round(v["hits"]/v["races"],4) if v["races"] else 0,"winnerMarked":round(v["marked"]/v["races"],4) if v["races"] else 0} for k,v in segments.items()}
    learning={}
    for c in ("地方","中央"):
        try:learning[c]=_winner_learning_profile({"date":end,"circuit":c})
        except Exception as exc:learning[c]={"version":WINNER_LEARNING_VERSION,"active":False,"reason":"profile-error","error":str(exc)[:120]}
    return {"version":PRERACE_AUDIT_VERSION,"start":start,"end":end,"races":len(dbrows),"audited":n,"learningReady":n>=WINNER_LEARNING_MIN_RACES,"learning":learning,
            "honTop1":round(hits/n,4) if n else 0,"winnerMarked":round(marked/n,4) if n else 0,"winnerTop2":round(top2/n,4) if n else 0,"winnerTop3":round(top3/n,4) if n else 0,
            "highConfidence":{"races":len(hc),"hits":sum(1 for a in hc if a.get("honHit")),"rate":round(sum(1 for a in hc if a.get("honHit"))/len(hc),4) if hc else 0},
            "brier":round(sum(float(a.get("brier") or 0) for a in rows)/n,6) if n else None,"logLoss":round(sum(float(a.get("logLoss") or 0) for a in rows)/n,6) if n else None,
            "calibration":{"horseSamples":len(cal),"ece":round(ece,6) if cal else None,"bins":bins},"segments":segout,
            "missReasons":dict(sorted(reasons.items(),key=lambda kv:(-kv[1],kv[0]))),"audits":rows[-100:]}

@app.get("/api/v1/model-learning")
def model_learning(date: str = Query(""), circuit: str = Query("地方")):
    target=date or _today_iso();c=_clean(circuit) or "地方"
    if c not in {"中央","地方"}:raise HTTPException(status_code=400,detail="circuit must be 中央 or 地方")
    try:datetime.strptime(target,"%Y-%m-%d")
    except Exception:raise HTTPException(status_code=400,detail="date must be YYYY-MM-DD")
    return _winner_learning_profile({"date":target,"circuit":c})
