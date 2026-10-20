"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _environment_http_get(url:str, ttl:int=30)->str:
    now=time.time()
    with _environment_http_lock:
        hit=_environment_http_cache.get(url)
        if hit and now-hit[0]<ttl:return str(hit[1].get("html") or "")
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1",
        "Accept-Language":"ja-JP,ja;q=0.9",
    })
    with urllib.request.urlopen(req,timeout=float(os.getenv("RACE_ENV_TIMEOUT_SEC","2.8"))) as res:
        html=_jra_decode(res.read())
    with _environment_http_lock:
        _environment_http_cache[url]=(now,{"html":html})
        if len(_environment_http_cache)>80:
            oldest=min(_environment_http_cache.items(),key=lambda kv:kv[1][0])[0]
            _environment_http_cache.pop(oldest,None)
    return html

def _nar_fetch_environment(track:str, iso_date:str, race_no:int)->dict:
    code=NAR_BABA_CODES.get(str(track or "").strip())
    if not code or not race_no:return {}
    q=urllib.parse.urlencode({"k_babaCode":code,"k_raceDate":iso_date.replace("-","/"),"k_raceNo":int(race_no)})
    urls=[
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/DebaTableSmall?"+q,
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceMarkTable?"+q,
    ]
    out={}
    for url in urls:
        try:parsed=_parse_nar_environment_html(_environment_http_get(url,25 if iso_date==_today_iso() else 86400))
        except Exception as exc:
            print("NAR environment fetch failed",track,iso_date,race_no,exc);continue
        for k in ("weather","condition"):
            if parsed.get(k) not in (None,"","不明"):out[k]=parsed[k]
        if parsed.get("scratchMap"):out["scratchMap"]=parsed["scratchMap"]
        if out.get("weather") and out.get("condition") and "scratchMap" in out:break
    if out:
        out.update({"source":"NAR公式","updatedAtEpoch":int(time.time()),"raceNo":int(race_no)})
    return out

def _jra_fetch_environment(row:dict)->dict:
    # This reader owns only central/JRA rows.  A missing identity is tolerated
    # for legacy in-process callers, but an explicit NAR row must fail closed.
    row_id=str(row.get("id") or "")
    if row_id and not row_id.startswith("jra-"):
        return {}
    date=str(row.get("date") or "")
    track=str(row.get("track") or "")
    race_no=int(row.get("raceNumber") or 0)
    surface=str(row.get("surface") or "")
    cname=str(row.get("jraCname") or "")
    if not cname:
        try:cname=_jra_find_cname(date,track,race_no)
        except Exception:cname=""
    out={}
    if cname:
        try:
            html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,20 if date==_today_iso() else 86400)
            out=_parse_jra_environment_html(html,surface)
        except Exception as exc:
            print("JRA environment official failed",date,track,race_no,exc)
    # Historical JRA cards are no longer published after the meeting. Use the
    # official result page as an observed fallback; never derive weather from
    # going, surface, or another race.
    if (out.get("weather") in (None,"","不明") or
            out.get("condition") in (None,"","不明")) and date:
        try:
            result_cnames=_jra_prior_result_cnames(date,track)
            result_cname=next(
                (x for x in result_cnames if _jra_any_race_no(x)==race_no), "")
            if result_cname:
                observed=_jra_parse_result(
                    result_cname,
                    {"date":date,"track":track,"raceNumber":race_no,
                     "surface":surface},
                    strict_errors=True,
                ) or {}
                if (out.get("weather") in (None,"","不明") and
                        observed.get("weather") not in (None,"","不明")):
                    out["weather"]=_env_clean_weather(observed["weather"])
                if (out.get("condition") in (None,"","不明") and
                        observed.get("condition") not in (None,"","不明")):
                    out["condition"]=_env_clean_condition(observed["condition"])
        except Exception as exc:
            print("JRA result environment fallback failed",
                  date,track,race_no,exc)
    # Secondary source only fills a field the official page did not provide.
    if out.get("weather") in (None,"","不明") or out.get("condition") in (None,"","不明"):
        try:
            meta=_netkeiba_race_meta(row)
            if out.get("weather") in (None,"","不明") and meta.get("weather") not in (None,"","不明"):
                out["weather"]=_env_clean_weather(meta.get("weather"))
            if out.get("condition") in (None,"","不明") and meta.get("condition") not in (None,"","不明"):
                out["condition"]=_env_clean_condition(meta.get("condition"))
        except Exception as exc:
            print("JRA environment secondary failed",date,track,race_no,exc)
    if out.get("weather") not in (None,"","不明") or out.get("condition") not in (None,"","不明"):
        out.update({"source":"JRA公式優先","updatedAtEpoch":int(time.time())})
    return out

def _upcoming_rows(rows:list[dict])->list[dict]:
    if not rows:return []
    if str(rows[0].get("date") or "")!=_today_iso():return rows
    nowj=_now_jst();nowm=nowj.hour*60+nowj.minute
    future=[r for r in rows if _race_minutes_server(r)>=nowm-12 and not _snapshot_final(r)]
    return future or [r for r in rows if not _snapshot_final(r)] or rows[-1:]

def _patch_nar_environment(date:str, track:str, rows:list[dict], env:dict)->list[str]:
    if not env:return []
    affected=[]
    upcoming=_upcoming_rows(rows)
    if not upcoming:return affected
    conn=_new_conn(DB_PATH)
    try:
        with conn:
            for r in upcoming:
                no=int(r.get("raceNumber") or 0)
                if not no:continue
                sets=[];args=[]
                if env.get("weather") not in (None,"","不明"):
                    sets.append("weather=?");args.append(env["weather"])
                if env.get("condition") not in (None,"","不明"):
                    sets.append("condition=?");args.append(env["condition"])
                if sets:
                    args.extend([track,date,no])
                    conn.execute("UPDATE races SET "+",".join(sets)+" WHERE track=? AND date=? AND race_no=?",args)
                    affected.append(str(r.get("id") or f"nar-{date}-{track}-{no:02d}"))
                scratch_map=env.get("scratchMap") or {}
                if scratch_map and int(env.get("raceNo") or 0)==no:
                    for horse_no,status in scratch_map.items():
                        conn.execute("UPDATE entries SET status=? WHERE track=? AND date=? AND race_no=? AND horse_no=?",
                                     (str(status),track,date,no,int(horse_no)))
                    rid=str(r.get("id") or f"nar-{date}-{track}-{no:02d}")
                    if rid not in affected:affected.append(rid)
    finally:conn.close()
    return affected

def _patch_central_environment(rows:list[dict], env_by_surface:dict, weather:str)->list[str]:
    if not rows:return []
    upcoming=_upcoming_rows(rows)
    st=CentralStore();affected=[]
    try:
        for r in upcoming:
            z=dict(r)
            changed=False
            if weather not in (None,"","不明") and z.get("weather")!=weather:
                z["weather"]=weather;changed=True
            surf=str(z.get("surface") or "")
            cond=env_by_surface.get(surf) or (env_by_surface.get("芝") if surf=="障害" else None)
            if cond not in (None,"","不明") and z.get("condition")!=cond:
                z["condition"]=cond;changed=True
            if changed:
                z["environmentMeta"]={"source":"JRA公式優先","updatedAtEpoch":int(time.time())}
                st.upsert([z]);affected.append(str(z.get("id") or ""))
    finally:
        st.conn.close()
    return [x for x in affected if x]

def _refresh_track_environment(date:str,circuit:str,track:str,force:bool=False)->dict:
    key=f"{date}|{circuit}|{track}"
    with _environment_lock:
        state=_environment_state.get(key) or {}
        if state.get("running"):return dict(state)
        if not force and int(time.time())-int(state.get("updatedAtEpoch") or 0)<25:
            return dict(state)
        _environment_state[key]={"running":True,"updatedAtEpoch":int(state.get("updatedAtEpoch") or 0),"changed":0,"error":""}
    affected=[];error=""
    try:
        rows=nar_race_summaries(date) if circuit=="地方" else central_race_summaries(date,allow_network=False)
        rows=[r for r in rows if str(r.get("track") or "")==str(track)]
        if not rows:return {"running":False,"changed":0}
        if circuit=="地方":
            reps=_upcoming_rows(rows)
            rep=reps[0] if reps else rows[0]
            env=_nar_fetch_environment(track,date,int(rep.get("raceNumber") or 0))
            if env:
                affected=_patch_nar_environment(date,track,rows,env)
        else:
            reps=_upcoming_rows(rows)
            by_surface={}
            weather="不明"
            for surf in ("芝","ダート","障害"):
                cand=next((r for r in reps if str(r.get("surface") or "")==surf),None)
                if not cand:continue
                env=_jra_fetch_environment(cand)
                if env.get("weather") not in (None,"","不明"):weather=env["weather"]
                if env.get("condition") not in (None,"","不明"):
                    by_surface[surf]=env["condition"]
                for k,v in (env.get("surfaceConditions") or {}).items():
                    if v not in (None,"","不明"):by_surface[k]=v
            affected=_patch_central_environment(rows,by_surface,weather)

        if affected:
            with _race_list_cache_lock:
                [_race_list_cache.pop(k,None) for k in list(_race_list_cache) if k.startswith(date+"|")]
            # Only recalc races whose live environment actually changed.
            for rid in affected:
                try:_build_fast_diagnosis_snapshot(rid,allow_network=False,deep_context=False)
                except Exception as exc:print("environment diagnosis rebuild failed",rid,exc)
    except Exception as exc:
        error=str(exc);print("track environment refresh failed",date,circuit,track,exc)
    finally:
        with _environment_lock:
            _environment_state[key]={
                "running":False,"updatedAtEpoch":int(time.time()),"changed":len(affected),"error":error
            }
    return dict(_environment_state.get(key) or {})

def _schedule_track_environment(date:str,circuit:str,track:str,force:bool=False)->None:
    key=f"{date}|{circuit}|{track}"
    with _environment_lock:
        if key in _environment_running:return
        state=_environment_state.get(key) or {}
        if not force and int(time.time())-int(state.get("updatedAtEpoch") or 0)<25:return
        _environment_running.add(key)
    def worker():
        try:_refresh_track_environment(date,circuit,track,force)
        finally:
            with _environment_lock:_environment_running.discard(key)
    threading.Thread(target=worker,daemon=True,name="env-"+track).start()

def _environment_cycle():
    date=_today_iso()
    rows=[]
    try:rows.extend(nar_race_summaries(date))
    except Exception:pass
    try:rows.extend(central_race_summaries(date,allow_network=False))
    except Exception:pass
    groups=[]
    seen=set()
    for r in rows:
        key=(str(r.get("circuit") or ""),str(r.get("track") or ""))
        if not key[0] or not key[1] or key[1]=="帯広" or key in seen:continue
        seen.add(key);groups.append(key)
    for circuit,track in groups:
        _schedule_track_environment(date,circuit,track,False)

def _environment_loop():
    time.sleep(float(os.getenv("ENVIRONMENT_START_DELAY_SEC","0.8")))
    while True:
        try:_environment_cycle()
        except Exception as exc:print("environment cycle failed",exc)
        time.sleep(max(30,int(os.getenv("ENVIRONMENT_REFRESH_SEC","45"))))

@app.on_event("startup")
def _start_environment_collector():
    enabled=str(os.getenv("ARVEXQ_ENVIRONMENT_COLLECTOR","1")).lower() in {"1","true","yes","on"}
    if enabled:
        threading.Thread(target=_environment_loop,daemon=True,name="arvexq-environment").start()
