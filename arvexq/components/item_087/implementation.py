"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _data_core_active_horses(detail:dict)->list[dict]:
    return [h for h in (detail.get("horses") or []) if isinstance(h,dict) and not h.get("scratched") and int(h.get("horseNumber") or 0)>0]

def _data_core_health(detail:dict|None)->dict:
    d=detail if isinstance(detail,dict) else {}
    horses=_data_core_active_horses(d); total=len(horses)
    field_size=max(total,int(d.get("fieldSize") or 0))
    named=sum(1 for h in horses if str(h.get("name") or "").strip() and str(h.get("jockey") or "").strip())
    card_pct=int(round(100*named/max(1,field_size))) if field_size else 0
    card_ready=bool(field_size>=2 and named>=max(2,field_size-1))

    hist_counts=[]
    for h in horses:
        if h.get("debutNoHistory"):
            hist_counts.append(5)
        else:
            runs=[x for x in (h.get("recentRaces") or h.get("allPastRuns") or []) if isinstance(x,dict)]
            hist_counts.append(min(5,len(runs)))
    hist_total=max(1,total*5)
    hist_points=sum(hist_counts)
    hist_pct=int(round(100*hist_points/hist_total)) if total else 0
    history_ready=bool(total and all(x>=5 for x in hist_counts))

    real_odds=[]
    weights=[]
    for h in horses:
        try:odd=float(h.get("winOdds") or 0)
        except Exception:odd=0.0
        real_odds.append(bool(odd>1 and not h.get("oddsForecast") and not re.search(r"予想|forecast",str(h.get("oddsSource") or ""),re.I)))
        try:bw=int(h.get("bodyWeight") or 0)
        except Exception:bw=0
        weights.append(bool(250<=bw<=800))
    odds_pct=int(round(100*sum(real_odds)/max(1,total))) if total else 0
    body_pct=int(round(100*sum(weights)/max(1,total))) if total else 0
    clock_state,minutes_to_post=_prediction_clock_state(d)
    is_today=str(d.get("date") or "")==_today_iso()
    odds_due=bool((not is_today) or clock_state=="started" or minutes_to_post is None or minutes_to_post<=360 or any(real_odds))
    body_due=bool((not is_today) or clock_state=="started" or minutes_to_post is None or minutes_to_post<=120 or any(weights))

    weather=str(d.get("weather") or "").strip();condition=str(d.get("condition") or "").strip()
    env_ready=weather not in ("","不明","—") and condition not in ("","不明","—")
    env_pct=(50 if weather not in ("","不明","—") else 0)+(50 if condition not in ("","不明","—") else 0)

    result=d.get("result") if isinstance(d.get("result"),dict) else {}
    finishers=[x for x in (result.get("finishers") or []) if isinstance(x,dict)]
    ranks={int(x.get("finish") or 0) for x in finishers}
    result_ready=all(x in ranks for x in (1,2,3))
    final=bool(str(result.get("status") or "")=="確定" or _snapshot_final(d))
    payouts=result.get("payouts") if isinstance(result.get("payouts"),list) else []
    payouts_ready=bool(payouts)
    due=_data_core_result_due(d)

    pm=d.get("preparedMeta") if isinstance(d.get("preparedMeta"),dict) else {}
    analysis_ready=bool(pm.get("diagnosisReady") and pm.get("diagnosisVersion")==PREDICTION_ENGINE_VERSION)

    srcs=[str(x) for x in (d.get("dataSources") or []) if x]
    default_source=" / ".join(srcs[:4]) or str(d.get("source") or "")
    def rec(status,pct,source="",note=""):
        return {"status":status,"completeness":max(0,min(100,int(pct))),"source":source or default_source,"note":note}
    return {
        "card":rec("ready" if card_ready else "missing",card_pct,note=f"{named}/{field_size or total}頭 基本項目"),
        "history":rec("ready" if history_ready else ("partial" if hist_points else "missing"),hist_pct,note=f"{hist_points}/{total*5 if total else 0}走"),
        "odds":rec("ready" if total and all(real_odds) else (("partial" if any(real_odds) else "missing") if odds_due else "not_due"),odds_pct,str(d.get("oddsSource") or default_source),f"{sum(real_odds)}/{total}頭 実単勝"+(" / 取得時間前" if not odds_due else "")),
        "body_weight":rec("ready" if total and all(weights) else (("partial" if any(weights) else "missing") if body_due else "not_due"),body_pct,note=f"{sum(weights)}/{total}頭 現在馬体重"+(" / 発表時間前" if not body_due else "")),
        "environment":rec("ready" if env_ready else ("partial" if env_pct else "missing"),env_pct,note=f"天候 {weather or '—'} / 馬場 {condition or '—'}"),
        "result":rec("ready" if result_ready else ("pending" if due else "not_due"),100 if result_ready else 0,str(result.get("source") or default_source),"上位3頭" if result_ready else "確定待ち"),
        "payouts":rec("ready" if payouts_ready else ("pending" if final else "not_due"),100 if payouts_ready else 0,str(result.get("payoutSource") or default_source),f"{len(payouts)}件" if payouts_ready else "確定待ち"),
        "analysis":rec("ready" if analysis_ready else "missing",100 if analysis_ready else 0,note=str(pm.get("diagnosisVersion") or "")),
    }

def _data_core_store_health(detail:dict|None, attempted:set[str]|None=None, source_hint:str="")->dict:
    if not isinstance(detail,dict) or not detail.get("id"):return {}
    rid=str(detail.get("id")); health=_data_core_health(detail); now=int(time.time()); attempted=attempted or set()
    conn=sqlite3.connect(RACEDB.path,timeout=3)
    try:
        for key,item in health.items():
            src=str(item.get("source") or source_hint or "")[:180]
            status=str(item.get("status") or "missing")
            pct=int(item.get("completeness") or 0)
            note=str(item.get("note") or "")[:400]
            vh=_data_core_health_hash(key,item)
            row=conn.execute("SELECT attempts FROM field_state WHERE race_id=? AND field_key=?",(rid,key)).fetchone()
            attempts=int(row[0] or 0) if row else 0
            if key in attempted and status!="ready":attempts+=1
            conn.execute("""INSERT INTO field_state(race_id,field_key,status,completeness,source,updated_at,last_attempt_at,attempts,note,value_hash)
                            VALUES(?,?,?,?,?,?,?,?,?,?)
                            ON CONFLICT(race_id,field_key) DO UPDATE SET status=excluded.status,completeness=excluded.completeness,
                            source=CASE WHEN excluded.source<>'' THEN excluded.source ELSE field_state.source END,
                            updated_at=excluded.updated_at,last_attempt_at=excluded.last_attempt_at,attempts=excluded.attempts,note=excluded.note,value_hash=excluded.value_hash""",
                         (rid,key,status,pct,src,now,now if key in attempted else 0,attempts,note,vh))
        conn.commit()
    finally:conn.close()
    return health
