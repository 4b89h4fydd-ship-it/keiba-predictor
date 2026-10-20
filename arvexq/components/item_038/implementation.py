"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _data_core_refresh_race(race_id:str,force:bool=False)->dict:
    rid=str(race_id or "")
    if not rid:return {"raceId":rid,"ok":False,"error":"empty race id"}
    # Fail closed before acquiring the shared refresh lock or touching stores.
    # Previously any ID without the JRA prefix could reach NAR refresh paths.
    if not rid.startswith(("jra-","nar-")):
        return {"raceId":rid,"ok":False,"error":"unsupported race id circuit"}
    with _data_core_lock:
        if rid in _data_core_running:
            d=_data_core_snapshot(rid);return {"raceId":rid,"ok":True,"running":True,"health":_data_core_health(d)}
        _data_core_running.add(rid)
    started=int(time.time());run_id=f"dc-{started}-{hashlib.sha1(rid.encode()).hexdigest()[:8]}";attempted=set();errors=[]
    try:
        d=_data_core_snapshot(rid)
        before=_data_core_health(d)
        # Card: hydrate only when basic starter rows are incomplete.
        if force or before.get("card",{}).get("status")!="ready":
            attempted.add("card")
            try:_hydrate_fast_card_now(rid,deep_history=False)
            except Exception as exc:errors.append("card:"+str(exc))
            d=_data_core_snapshot(rid)

        h=_data_core_health(d)
        # Live odds + current body weight are one official/live fetch but tracked separately.
        if str((d or {}).get("date") or "")==_today_iso() and (force or h.get("odds",{}).get("status")!="ready" or h.get("body_weight",{}).get("status")!="ready"):
            attempted.update({"odds","body_weight"})
            try:odds_refresh(rid,1)
            except Exception as exc:errors.append("live:"+str(exc))
            d=_data_core_snapshot(rid)

        h=_data_core_health(d)
        if force or h.get("environment",{}).get("status")!="ready":
            attempted.add("environment")
            try:
                if rid.startswith("jra-"):
                    fresh=central_race_detail(rid)
                    if fresh:
                        base=d or fresh
                        for k in ("weather","condition","title","distance","surface","startTime","scheduledStartTime"):
                            if fresh.get(k) not in (None,"",0,"不明"):base[k]=fresh.get(k)
                        RACEDB.upsert_race(base);PREPARED_STORE.put(base,force=True);d=base
                else:
                    _schedule_track_environment(str((d or {}).get("date") or _today_iso()),str((d or {}).get("circuit") or "地方"),str((d or {}).get("track") or ""),True)
            except Exception as exc:errors.append("env:"+str(exc))

        h=_data_core_health(d)
        if force or h.get("history",{}).get("status")!="ready":
            attempted.add("history")
            try:
                if rid.startswith("jra-"):
                    _start_central_history_search(rid,str((d or {}).get("date") or _today_iso()),force=bool(force))
                else:
                    names=[str(x.get("name") or "") for x in ((d or {}).get("horses") or []) if x.get("name")]
                    if names:_start_race_history_search(rid,str((d or {}).get("date") or _today_iso()),names,force=bool(force))
            except Exception as exc:errors.append("history:"+str(exc))

        h=_data_core_health(d)
        if _data_core_result_due(d or {}) and (force or h.get("result",{}).get("status")!="ready"):
            attempted.add("result")
            try:_refresh_result_fast(rid)
            except Exception as exc:errors.append("result:"+str(exc))
            d=_data_core_snapshot(rid)

        h=_data_core_health(d)
        if h.get("result",{}).get("status")=="ready" and (force or h.get("payouts",{}).get("status")!="ready"):
            attempted.add("payouts")
            try:payout_refresh(rid)
            except Exception as exc:errors.append("payouts:"+str(exc))
            d=_data_core_snapshot(rid)

        h=_data_core_health(d)
        if force or h.get("analysis",{}).get("status")!="ready":
            attempted.add("analysis")
            try:_build_fast_diagnosis_snapshot(rid,allow_network=False,deep_context=False)
            except Exception as exc:errors.append("analysis:"+str(exc))
            d=_data_core_snapshot(rid)

        after=_data_core_store_health(d,attempted,"ARVEXQ Data Core")
        if isinstance(d,dict) and d.get("id"):
            d["dataCoreHealth"]=after;d["dataCoreVersion"]=ARVEXQ_DATA_CORE_VERSION;d["dataCoreUpdatedAt"]=int(time.time())
            try:RACEDB.upsert_race(d);PREPARED_STORE.put(d,force=True)
            except Exception as exc:errors.append("persist-health:"+str(exc))
        _data_core_record_run(run_id,rid,started,"partial" if errors else "ok",attempted,before,after," | ".join(errors[-5:]))
        return {"raceId":rid,"ok":not errors,"attempted":sorted(attempted),"health":after,"errors":errors[-5:],"version":ARVEXQ_DATA_CORE_VERSION}
    finally:
        with _data_core_lock:_data_core_running.discard(rid)

def _merge_current_card_fields(detail:dict, rows:list[dict])->dict:
    if not rows:return detail
    by={int(x.get("horseNumber") or 0):x for x in rows if int(x.get("horseNumber") or 0)>0}
    changed=False
    for h in detail.get("horses",[]) or []:
        z=by.get(int(h.get("horseNumber") or 0))
        if not z:continue
        for k in ("bodyWeight","bodyWeightChange","carriedWeight","status","scratched"):
            if z.get(k) not in (None,"") and h.get(k)!=z.get(k):
                h[k]=z.get(k);changed=True
    if changed:
        detail["bodyWeightSource"]="NAR公式出馬表"
        detail["bodyWeightUpdatedAt"]=_now_jst().strftime("%H:%M:%S")
    return detail

def _merge_card_rows_preserve(base:dict, fresh_rows:list[dict])->dict:
    """Refresh today's card fields without deleting history/metrics already collected."""
    old_horses=base.get("horses") or []
    by_no={int(h.get("horseNumber") or 0):h for h in old_horses if int(h.get("horseNumber") or 0)>0}
    by_name={str(h.get("name") or ""):h for h in old_horses if h.get("name")}
    merged=[]
    for fresh in fresh_rows or []:
        no=int(fresh.get("horseNumber") or 0)
        old=by_no.get(no) or by_name.get(str(fresh.get("name") or "")) or {}
        z=json.loads(json.dumps(old,ensure_ascii=False,default=str)) if old else {}
        for k,v in fresh.items():
            if k in {"recentRaces","allPastRuns","precomputedMetrics","integratedEvaluation",
                     "jockeyStats","trainerStats","jockeyProfile","trainerProfile","prizeMoneyAtRace"}:
                continue
            if v not in (None,"",[],{}):z[k]=v
        # preserve rich local data
        for k in ("recentRaces","allPastRuns","precomputedMetrics","integratedEvaluation",
                  "jockeyStats","trainerStats","jockeyProfile","trainerProfile","prizeMoneyAtRace",
                  "pedigree","representativeRun"):
            if old.get(k) not in (None,"",[],{}):z[k]=old.get(k)
        z.setdefault("recentRaces",[])
        z.setdefault("jockeyStats",{})
        z.setdefault("trainerStats",{})
        z.setdefault("jockeyProfile",{})
        z.setdefault("trainerProfile",{})
        merged.append(z)
    if merged:
        base["horses"]=merged
        base["fieldSize"]=len(merged)
    return base

def _hydrate_fast_card_now(race_id:str, deep_history:bool=False)->None:
    # NAR: hydrate the date once. v117 called a non-existent sync_day(), so selected
    # local races could stay empty until another background job happened to fill the DB.
    if race_id.startswith("nar-"):
        m=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$",race_id)
        if not m:return
        iso_date,track,race_no=m.group(1),m.group(2),int(m.group(3))
        sync=None
        try:
            target=datetime.strptime(iso_date,"%Y-%m-%d").date()
            sync=NarSync()
            with _nar_sync_io_lock:
                if iso_date==_today_iso():sync.sync_daily(force=False)
                else:sync.sync_month(target.year,target.month,force=False)
        except Exception as exc:
            print("fast NAR date hydrate failed",race_id,exc)
        finally:
            try:
                if sync:sync.store.conn.close()
            except Exception:pass
        q=_fast_local_race_detail(race_id)
        if q:
            # Finished/started races: RaceMarkTable is the fastest authoritative source and also
            # carries body weight. Before the race, use the official card from multiple layouts.
            official_result=None
            if _nar_result_should_be_available(q):
                try:official_result=_nar_official_result_fast(q)
                except Exception as exc:print("fast NAR official result failed",race_id,exc)
            if official_result:
                q["result"]=official_result
                if official_result.get("weather") not in (None,"","不明"):q["weather"]=official_result["weather"]
                if official_result.get("condition") not in (None,"","不明"):q["condition"]=official_result["condition"]
                q=_merge_result_fields(q,official_result)
                q["bodyWeightSource"]="NAR公式競走成績"
                q["bodyWeightUpdatedAt"]=_now_jst().strftime("%H:%M:%S")
            else:
                try:q=_merge_current_card_fields(q,_nar_official_card_rows_fast(q))
                except Exception as exc:print("fast NAR official body weight failed",race_id,exc)
            _store_fast_snapshot(q)
            if deep_history:
                names=[str(h.get("name") or "") for h in q.get("horses",[]) if h.get("name")]
                cov=_history_counts(names,iso_date)
                if names and not _history_is_enough(cov,0):
                    _start_race_history_search(race_id,iso_date,names,force=False)
        return

    m=re.match(r"^jra-(20\d{2}-\d{2}-\d{2})-([^\-]+)-(\d{2})$",race_id)
    if not m:return
    date,track,rno=m.group(1),m.group(2),int(m.group(3))
    base=None
    if CENTRAL_DB_PATH.exists():
        conn=_new_conn(CENTRAL_DB_PATH)
        try:
            row=conn.execute("SELECT payload FROM central_races WHERE id=?",(race_id,)).fetchone()
            if row:
                try:base=json.loads(row["payload"])
                except Exception:base=None
        finally:conn.close()
    if not base:
        base={"id":race_id,"circuit":"中央","date":date,"track":track,"raceNumber":rno,
              "title":f"{rno}R","distance":0,"surface":"","condition":"不明","weather":"不明",
              "horses":[],"source":"高速出走表"}

    rows=_netkeiba_card_rows_fast(base)
    if rows:
        base=_merge_card_rows_preserve(base,rows)
        base["id"]=race_id;base["circuit"]="中央"
        # Weather/going is a separate lightweight feed; do not let the fast
        # horse-card path leave the race at "不明".
        if date==_today_iso() and (base.get("weather") in (None,"","不明") or base.get("condition") in (None,"","不明")):
            try:
                env=_jra_fetch_environment(base)
                if env.get("weather") not in (None,"","不明"):base["weather"]=env["weather"]
                if env.get("condition") not in (None,"","不明"):base["condition"]=env["condition"]
                if env:base["environmentMeta"]={"source":env.get("source","JRA公式優先"),"updatedAtEpoch":env.get("updatedAtEpoch",int(time.time()))}
            except Exception as exc:print("fast JRA environment failed",race_id,exc)
        # One past page hydrates all starters; collector does this before the customer taps.
        if not _diagnosis_history_quality(base).get("ready"):
            base=_merge_fast_history(base,_netkeiba_past_rows_fast(base))
        try:
            st=CentralStore();st.upsert([base]);st.conn.close()
        except Exception as exc:print("fast card central save failed",exc)
        try:RACEDB.upsert_race(base)
        except Exception as exc:print("fast card racedb save failed",exc)
        q=_fast_local_race_detail(race_id)
        if q:_store_fast_snapshot(q)
        return

    # Official fallback only after the faster single-page route fails.
    try:
        cname=_jra_find_cname(date,track,rno)
        live=_jra_parse_race(cname,supplement_profiles=False) if cname else None
        if live:
            live["id"]=race_id
            st=CentralStore();st.upsert([live]);st.conn.close()
            q=_fast_local_race_detail(race_id)
            if q:_store_fast_snapshot(q)
    except Exception as exc:print("fast JRA card hydrate failed",race_id,exc)

def _schedule_fast_card_refresh(race_id:str,priority:int=50)->None:
    _queue_fast_card(race_id,priority)

def _schedule_racedb_snapshot_refresh(race_id:str)->None:
    with _racedb_refresh_lock:
        if race_id in _racedb_refresh_running:return
        _racedb_refresh_running.add(race_id)
    def worker():
        try:
            fresh=_prepare_race_snapshot(race_id,True)
            if fresh:_ensure_detail_background_jobs(race_id,fresh)
        except Exception as exc:print("RaceDB refresh failed",race_id,exc)
        finally:
            with _racedb_refresh_lock:_racedb_refresh_running.discard(race_id)
    threading.Thread(target=worker,daemon=True).start()
