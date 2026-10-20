"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _merge_enrichment(detail:dict,data:dict)->dict:
    hs=detail.get("horses") or [];by_no={int(h.get("horseNumber") or 0):h for h in hs if h.get("horseNumber")};by_name={str(h.get("name") or "").strip():h for h in hs if h.get("name")};sources=[]
    for row in data.get("smartRows") or []:
        h=by_no.get(int(row.get("horseNumber") or 0)) or by_name.get(str(row.get("name") or "").strip())
        if not h:continue
        if "SmartRc" not in sources:sources.append("SmartRc")
        if row.get("smartRc"):h["smartRc"]={**(h.get("smartRc") or {}),**row.get("smartRc")}
        if row.get("pedigree"):h["pedigree"]={**(h.get("pedigree") or {}),**row.get("pedigree")}
        for k in ("owner","producer","birthday"):
            if h.get(k) in (None,"") and row.get(k) not in (None,""):h[k]=row.get(k)
        if row.get("recentRaces"):h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],row.get("recentRaces") or [],5)
    for row in data.get("netkeibaRows") or []:
        h=by_no.get(int(row.get("horseNumber") or 0)) or by_name.get(str(row.get("name") or "").strip())
        if not h:continue
        sources.append("netkeiba") if "netkeiba" not in sources else None
        for k in ("sex","age","carriedWeight","jockey","trainer","bodyWeight","bodyWeightChange","owner","producer"):
            if (h.get(k) in (None,"",0)) and row.get(k) not in (None,""):h[k]=row.get(k)
        if row.get("pedigree"):h["pedigree"]={**(h.get("pedigree") or {}),**row.get("pedigree")}
        if row.get("_netkeibaHorseId"):h["_netkeibaHorseId"]=row.get("_netkeibaHorseId")
        if row.get("recentRaces") or row.get("allPastRuns"):
            # The fallback can carry an entire dated JRA/NAR history. Do not
            # collapse it to a five-run UI projection when enriching a local
            # race and never replace an already longer official history.
            from arvexq.ingest.full_career import merge_career
            cutoff=str(detail.get("date") or "")
            existing=[*(h.get("allPastRuns") or []),*(h.get("recentRaces") or [])]
            incoming=row.get("allPastRuns") or row.get("recentRaces") or []
            if cutoff:
                merged=merge_career(existing,incoming,cutoff)
                if merged:
                    h["allPastRuns"]=merged
                    h["recentRaces"]=merged[:5]
    for b in data.get("extra") or []:
        src=str(b.get("source") or "補助")
        for row in b.get("rows") or []:
            h=by_no.get(int(row.get("horseNumber") or 0)) or by_name.get(str(row.get("name") or "").strip())
            if h:
                extra=_strip_excluded(row.get("extra") or {})
                h.setdefault("extraSources",{})[src]=extra
                for key in ("pedigree","jockeyStats","trainerStats","jumpJockeyStats","jumpTrainerStats","jumpStats","isTransfer","transferFrom","ten1f","agari3f","pedigreeScore","distanceSuitabilityScore","surfaceSuitabilityScore","drawScore","bodyWeightScore","opponentLevelScore","lapScore","conditionChangeScore","jockeyScore","trainerScore","jumpJockeyScore","jumpTrainerScore"):
                    if extra.get(key) is not None:h[key]=extra[key]
                if isinstance(extra.get("allPastRuns"),list) and detail.get("date"):
                    # An older supplemental lane used to overwrite the whole
                    # lifetime archive with any partial third-party response.
                    # Reuse the one date-safe deduplicating merge operation.
                    from arvexq.ingest.full_career import merge_career
                    observed=[*(h.get("allPastRuns") or []),*(h.get("recentRaces") or [])]
                    merged=merge_career(observed,extra["allPastRuns"],detail["date"])
                    if merged:
                        h["allPastRuns"]=merged
                        h["recentRaces"]=merged[:5]
        if src not in sources:sources.append(src)
    base=list(detail.get("dataSources") or []);official="JRA公式" if detail.get("circuit")=="中央" else "NAR公式"
    for s in [official]+sources:
        if s not in base:base.append(s)
    detail["dataSources"]=base;return detail

def _start_enrichment(race_id:str,detail:dict,force:bool=False,horse_no:int|None=None)->dict:
    now=time.time()
    with _enrich_jobs_lock:
        old=_enrich_jobs.get(race_id)
        if old and old.get("status")=="running" and not force:return dict(old)
        if old and old.get("status") in {"done","unavailable"} and not force and now-float(old.get("finishedAt") or 0)<300:return dict(old)
        _enrich_jobs[race_id]={"status":"running","sources":[],"error":"","startedAt":now,"horseNumber":horse_no}
    snap=json.loads(json.dumps(detail,ensure_ascii=False,default=str))
    def worker():
        errs=[];sources=[];netkeibaRows=[];smartRows=[];extra=[]
        def get_netkeiba():
            if snap.get("circuit")!="中央":return []
            try:return _netkeiba_detail_rows(snap)
            except Exception as exc:errs.append("netkeiba: "+str(exc));return []
        def get_smart():
            # v146: SmartRc tempo/final-section metrics are intentionally suspended.
            return []
        def get_extra():
            try:return _fetch_extra_sources(snap)
            except Exception as exc:errs.append("補助: "+str(exc));return []
        try:
            with ThreadPoolExecutor(max_workers=3) as pool:
                f_net=pool.submit(get_netkeiba);f_smart=pool.submit(get_smart);f_extra=pool.submit(get_extra)
                netkeibaRows=f_net.result() or [];smartRows=f_smart.result() or [];extra=f_extra.result() or []
            if netkeibaRows:sources.append("netkeiba")
            if smartRows:sources.append("SmartRc")
            for b in extra:
                if b.get("source") not in sources:sources.append(b.get("source"))
        except Exception as exc:errs.append("情報取得: "+str(exc))
        if horse_no:
            netkeibaRows=[x for x in netkeibaRows if int(x.get("horseNumber") or 0)==int(horse_no)]
            smartRows=[x for x in smartRows if int(x.get("horseNumber") or 0)==int(horse_no)]
        with _enrich_data_lock:
            olddata=_enrich_data.get(race_id) or {}
            nk={}
            for rr in (olddata.get("netkeibaRows") or [])+netkeibaRows:
                key=int(rr.get("horseNumber") or 0) or str(rr.get("name") or "")
                nk[key]=rr
            sk={}
            for rr in (olddata.get("smartRows") or [])+smartRows:
                key=int(rr.get("horseNumber") or 0) or str(rr.get("name") or "")
                sk[key]=rr
            _enrich_data[race_id]={"netkeibaRows":list(nk.values()),"smartRows":list(sk.values()),"extra":extra or olddata.get("extra") or []}
        with _enrich_jobs_lock:_enrich_jobs[race_id]={"status":"done" if sources else "unavailable","sources":sources,"error":" | ".join(errs[-3:]),"finishedAt":time.time(),"horseNumber":horse_no}
        try:
            enriched=json.loads(json.dumps(snap,ensure_ascii=False,default=str))
            with _enrich_data_lock:
                saved_data=_enrich_data.get(race_id) or {}
            enriched=_merge_enrichment(enriched,saved_data)
            enriched["enrichmentSearch"]=_enrichment_status(race_id)
            latest,_=PREPARED_STORE.get(race_id)
            if latest:
                enriched=_merge_enrichment(latest,saved_data)
                enriched["enrichmentSearch"]=_enrichment_status(race_id)
            enriched=_precompute_detail_metrics(_attach_evaluation_context(_attach_stored_career(enriched)))
            PREPARED_STORE.put(enriched)
            RACEDB.upsert_race(enriched)
        except Exception as exc:print("RaceDB enrichment save failed",race_id,exc)
        with _detail_cache_lock:_detail_cache.pop(race_id,None)
    threading.Thread(target=worker,daemon=True).start();return _enrichment_status(race_id)

def _apply_enrichment(race_id:str,detail:dict)->dict:
    with _enrich_data_lock:data=_enrich_data.get(race_id)
    if data:_merge_enrichment(detail,data)
    detail["enrichmentSearch"]=_enrichment_status(race_id)
    title=str(detail.get("title") or "");surface=str(detail.get("surface") or "")
    mode="障害" if (surface=="障害" or "障害" in title or re.search(r"(?:J[･・.]?G[ⅠⅡⅢ123]|\\bJS\\b|ジャンプ)",title,re.I)) else ("新馬" if re.search(r"(?:新馬|メイクデビュー)",title) else "平地")
    detail["analysisMode"]=mode
    for h in detail.get("horses",[]) or []:
        from arvexq.career_missing import build_career_analysis
        verified_no_starts = (detail.get("analysisMode") == "新馬" and
            build_career_analysis(h,detail).get("career_state") == "complete-no-starts")
        if verified_no_starts:
            h["debutNoHistory"]=True
        else:
            h.pop("debutNoHistory",None)
    return detail
