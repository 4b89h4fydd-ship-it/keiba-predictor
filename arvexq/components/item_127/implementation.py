"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _prediction_audit_from_lock(detail:dict)->dict|None:
    lock=(detail or {}).get("preRacePrediction")
    result=(detail or {}).get("result") or {}
    if not isinstance(lock,dict) or not isinstance(lock.get("horses"),list) or result.get("status")!="確定":return None
    finishers=[x for x in (result.get("finishers") or []) if isinstance(x,dict) and int(x.get("finish") or 0)>0]
    if not finishers:return None
    finishers.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)))
    winner=int(finishers[0].get("horseNumber") or 0);top3={int(x.get("horseNumber") or 0) for x in finishers[:3]}
    rows=[x for x in lock.get("horses") or [] if int(x.get("horseNumber") or 0)>0]
    by={int(x.get("horseNumber") or 0):x for x in rows};w=by.get(winner)
    hon=next((x for x in rows if str(x.get("mark") or "")=="◎"),None)
    if not hon or not w:return None
    valid_marks={"◎","○","▲","☆+","☆","△","注+","注"}
    mark=str(w.get("mark") or "");marked=mark in valid_marks
    marked_nos={int(x.get("horseNumber") or 0) for x in rows if str(x.get("mark") or "") in valid_marks}
    podium_marked_count=len(top3 & marked_nos);podium_all_marked=len(top3)>=3 and podium_marked_count==3
    hit=int(hon.get("horseNumber") or 0)==winner
    ranked=sorted(rows,key=lambda x:(-float(x.get("decisionProbability") or 0),int(x.get("horseNumber") or 0)))
    winner_rank=next((i+1 for i,x in enumerate(ranked) if int(x.get("horseNumber") or 0)==winner),999)
    hp=max(1e-9,min(.999999,float(hon.get("decisionProbability") or 0)));wp=max(1e-9,min(.999999,float(w.get("decisionProbability") or 0)))
    brier=sum((float(x.get("decisionProbability") or 0)-(1.0 if int(x.get("horseNumber") or 0)==winner else 0.0))**2 for x in rows)
    axis_labels={"pure":"PURE","trueRun":"TRUE RUN","sectional":"SECTIONAL","positionScenario":"展開適合","conditions":"今回条件","opponentLevel":"相手レベル","stateConsistency":"状態・再現性"}
    diffs={}
    wa=w.get("axes") if isinstance(w.get("axes"),dict) else {};ha=hon.get("axes") if isinstance(hon.get("axes"),dict) else {}
    for k in axis_labels:
        try:diffs[k]=round(float(wa.get(k) or 0)-float(ha.get(k) or 0),6)
        except Exception:diffs[k]=0.0
    frag_gap=float(ha.get("fragility") or 0)-float(wa.get("fragility") or 0)
    if hit:reason="的中"
    elif frag_gap>=.08:reason="◎の脆さを過小評価"
    else:
        best_key=max(diffs,key=lambda k:diffs[k]) if diffs else ""
        best_val=diffs.get(best_key,0)
        if best_val>=.035:reason=axis_labels.get(best_key,best_key)+"を過小評価"
        elif hp-wp<=.03:reason="僅差順位"
        elif marked:reason="候補内の1着順位付け"
        else:reason="候補抽出"
    return {
        "version":PRERACE_AUDIT_VERSION,"raceId":str(detail.get("id") or ""),"raceDate":str(detail.get("date") or ""),"circuit":str(detail.get("circuit") or ""),"track":str(detail.get("track") or ""),"raceNumber":int(detail.get("raceNumber") or 0),"dataQuality":round(float(lock.get("dataQuality") or 0),6),"winnerNo":winner,"honNo":int(hon.get("horseNumber") or 0),
        "honHit":hit,"winnerMarked":marked,"winnerMark":mark,"winnerRank":winner_rank,"top2Hit":winner_rank<=2,"top3Hit":winner_rank<=3,
        "podiumAllMarked":podium_all_marked,"podiumMarkedCount":podium_marked_count,"markCount":int(lock.get("markCount") or 0),
        "honProbability":round(hp,8),"winnerProbability":round(wp,8),"probabilityGap":round(hp-wp,8),
        "winnerConfidence":round(float(lock.get("winnerConfidence") or 0),8),"winnerStable":bool(lock.get("winnerStable")),
        "highConfidence":float(lock.get("winnerConfidence") or 0)>=.70,"brier":round(brier,8),"logLoss":round(-math.log(wp),8),
        "missClass":"hit" if hit else ("candidate-order" if marked else "candidate-miss"),"reason":reason,"axisDiffs":diffs,
        "lockedAtEpoch":int(lock.get("capturedAtEpoch") or 0),"modelVersion":str(lock.get("modelVersion") or ""),
        "learningProfileId":str((lock.get("learningProfile") or {}).get("profileId") or "baseline"),"learningActive":bool((lock.get("learningProfile") or {}).get("active")),
        "top3Finishers":[int(x.get("horseNumber") or 0) for x in finishers[:3]],
    }

def _attach_prerace_audit(detail:dict)->dict:
    if not isinstance(detail,dict):return detail
    state,_=_prediction_clock_state(detail)
    current=detail.get("preRacePrediction") if isinstance(detail.get("preRacePrediction"),dict) else None
    if state in {"pre","future"} and not _snapshot_final(detail):
        # Once the final pre-race window has been captured, never rewrite it.
        # This keeps the audit/training label immutable even if later refreshes arrive.
        if not (current and current.get("frozen")):
            fresh=_build_prerace_prediction(detail)
            if fresh:
                old_q=float((current or {}).get("dataQuality") or 0)
                new_q=float(fresh.get("dataQuality") or 0)
                entering_freeze=bool(fresh.get("frozen"))
                # In the freeze window, prefer the latest snapshot unless it is badly sparser.
                if not current or (entering_freeze and new_q+.08>=old_q) or (not entering_freeze and new_q+.02>=old_q):
                    detail["preRacePrediction"]=fresh
    if _snapshot_final(detail) and isinstance(detail.get("preRacePrediction"),dict):
        audit=_prediction_audit_from_lock(detail)
        if audit:detail["predictionAudit"]=audit
    return detail
