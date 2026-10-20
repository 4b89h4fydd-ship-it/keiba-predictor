"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/api/v1/race/{race_id}/collect")
def collect_race_info(
    race_id: str,
    force: int = Query(1),
    horse_no: int | None = Query(None, ge=1, le=99),
):
    """Retry enrichment + prior-race collection for the selected race.

    The previous UI already called this URL, but the server route was missing, so the
    request always returned 404 and the app showed the history-fetch failure.
    Keep the work asynchronous so the button returns immediately and the
    existing polling UI can refresh the completed data.
    """
    cached=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if cached and (cached.get("date","")!=_today_iso() or _snapshot_final(cached)):
        return {"status":"saved","raceId":race_id,"historySearch":cached.get("historySearch",{}),"enrichmentSearch":cached.get("enrichmentSearch",{})}
    detail = nar_race_detail(race_id) if race_id.startswith("nar-") else central_race_detail(race_id)
    if not detail:
        raise HTTPException(status_code=404, detail="race not found")

    force_flag = bool(force)

    # Re-run supplemental sources (netkeiba / configured extras) without blocking.
    try:
        enrich = _start_enrichment(race_id, detail, force=force_flag, horse_no=horse_no)
    except Exception as exc:
        print("collect enrichment start failed", race_id, exc)
        enrich = {"status":"unavailable","sources":[],"error":str(exc)}

    # Re-run official history only when it is actually incomplete. Avoid launching
    # a duplicate worker while the same race is already running.
    history = _race_history_status(race_id)
    try:
        if race_id.startswith("nar-"):
            names = [str(h.get("name") or "") for h in detail.get("horses", []) if h.get("name")]
            cov = _history_counts(names, detail.get("date") or "9999-12-31")
            if _history_is_enough(cov, int((history or {}).get("monthsDone") or 0)):
                history = {"status":"done","monthsDone":int((history or {}).get("monthsDone") or 0),
                           "maxMonths":int((history or {}).get("maxMonths") or 0),"coverage":cov,"error":"",
                           "source":(history or {}).get("source") or "NAR公式ローカル履歴"}
            elif not history or history.get("status") != "running":
                history = _start_race_history_search(
                    race_id, detail.get("date") or _today_iso(), names,
                    force=force_flag or bool(history and history.get("status") == "error")
                )
        else:
            cov = _central_detail_coverage(detail)
            total = int(cov.get("totalHorses") or 0)
            resolved = int(cov.get("horsesResolved") or cov.get("horsesWith5Plus") or 0)
            if total == 0 or assess_career_readiness(detail).get("ready"):
                history = {"status":"done","monthsDone":int((history or {}).get("monthsDone") or 0),
                           "maxMonths":int((history or {}).get("maxMonths") or 0),"coverage":cov,"error":"",
                           "source":(history or {}).get("source") or "JRA公式 競走馬情報5走補完"}
            elif not history or history.get("status") != "running":
                history = _start_central_history_search(
                    race_id, detail.get("date") or _today_iso(),
                    force=force_flag or bool(history and history.get("status") == "error")
                )
    except Exception as exc:
        print("collect history start failed", race_id, exc)
        history = history or {"status":"error","monthsDone":0,"maxMonths":0,"coverage":{},"error":str(exc),"source":""}

    # Drop stale display snapshots so the next poll can see newly collected runs.
    try:
        PREPARED_STORE.delete(race_id)
    except Exception:
        pass
    with _detail_cache_lock:
        _detail_cache.pop(race_id, None)

    return {
        "status":"started",
        "raceId":race_id,
        "horseNumber":horse_no,
        "historySearch":history or {"status":"done","coverage":{}},
        "enrichmentSearch":enrich,
    }

@app.get("/api/v1/odds-refresh/{race_id}")
def odds_refresh(race_id:str, force: int = Query(0)):
    saved=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    saved_has_odds=bool(saved and any((h.get("winOdds") not in (None,"") and float(h.get("winOdds") or 0)>0) for h in (saved.get("horses") or [])))
    saved_horses=(saved.get("horses") or []) if saved else []
    saved_has_weights=bool(saved_horses and all(h.get("bodyWeight") not in (None,"") for h in saved_horses if not h.get("scratched")))
    if saved and saved.get("date")!=_today_iso() and saved_has_odds:
        return {"raceId":race_id,"horses":saved_horses,"oddsSource":saved.get("oddsSource") or "保存済み","storedInRaceDB":True,"oddsUpdatedAt":saved.get("oddsUpdatedAt") or ""}
    if saved and _snapshot_final(saved) and saved_has_odds and saved_has_weights:
        return {"raceId":race_id,"horses":saved_horses,"oddsSource":saved.get("oddsSource") or "保存済み","storedInRaceDB":True,"oddsUpdatedAt":saved.get("oddsUpdatedAt") or ""}
    horses=[]; source=""
    if race_id.startswith("nar-"):
        m=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$",race_id)
        if m:
            odds=_nar_live_odds(m.group(2),m.group(1),int(m.group(3)),bool(force))
            merged={int(no):dict(z or {}) for no,z in odds.items()}
            # NAR current body weight is published on the official DebaTable.
            # Pull it directly instead of trying to resolve a JRA-style netkeiba race id.
            if not merged or any(not (z or {}).get("bodyWeight") for z in merged.values()):
                try:
                    detail=dict(saved or {})
                    detail.update({"id":race_id,"date":m.group(1),"track":m.group(2),"raceNumber":int(m.group(3))})
                    if not detail.get("horses"):
                        try:
                            qd=_fast_local_race_detail(race_id)
                            if qd:detail=qd
                        except Exception:pass
                    for h in _nar_official_card_rows_fast(detail):
                        no=int(h.get("horseNumber") or 0)
                        if not no:continue
                        z=merged.setdefault(no,{})
                        for k in ("bodyWeight","bodyWeightChange","status","scratched"):
                            if z.get(k) in (None,"") and h.get(k) not in (None,""):z[k]=h.get(k)
                    if merged and not odds:source="NAR公式出馬表"
                except Exception as exc:print("NAR official body weight fallback failed",race_id,exc)
            # v232: before official live odds/weights are posted, fill the screen with
            # netkeiba NAR predicted odds and any current weight already exposed there.
            try:
                detail=dict(saved or {})
                detail.update({"id":race_id,"date":m.group(1),"track":m.group(2),"raceNumber":int(m.group(3))})
                nk=_nar_netkeiba_preview_rows(detail,bool(force)) or {}
                for no,z0 in nk.items():
                    z=merged.setdefault(int(no),{})
                    official_live=bool(z.get("winOdds") and not z.get("oddsForecast"))
                    if not official_live and z0.get("winOdds"):
                        z["winOdds"]=z0.get("winOdds");z["popularity"]=z0.get("popularity");z["oddsSource"]=z0.get("oddsSource");z["oddsForecast"]=bool(z0.get("oddsForecast"))
                    for k in ("bodyWeight","bodyWeightChange"):
                        if z.get(k) in (None,"") and z0.get(k) not in (None,""):z[k]=z0.get(k)
                if nk and not odds:source="netkeiba予想オッズ"
            except Exception as exc:print("NAR netkeiba preview fallback failed",race_id,exc)
            # Always attach a truthful previous-race weight reference while current weigh-in is pending.
            if saved:
                saved_by={int(h.get("horseNumber") or 0):h for h in (saved.get("horses") or [])}
                for no,h0 in saved_by.items():
                    z=merged.setdefault(no,{})
                    if not z.get("bodyWeight"):
                        rw,rd=_reference_weight_from_horse(h0)
                        if rw:z["referenceBodyWeight"]=rw;z["referenceBodyWeightDate"]=rd
            if saved and _snapshot_final(saved):
                for f in ((saved.get("result") or {}).get("finishers") or []):
                    no=int(f.get("horseNumber") or 0)
                    if not no:continue
                    z=merged.setdefault(no,{})
                    for k in ("bodyWeight","bodyWeightChange","popularity","winOdds"):
                        if z.get(k) in (None,"") and f.get(k) not in (None,""):z[k]=f.get(k)
            for no,z in sorted(merged.items()):
                horses.append({"horseNumber":int(no),**{k:v for k,v in z.items() if v is not None}})
            if not source:source="NAR公式" if odds else (next((str(z.get("oddsSource") or "") for z in merged.values() if z.get("oddsSource")),"") or ("NAR公式出馬表" if horses else ""))
    else:
        mm=re.match(r"^jra-(20\d{2}-\d{2}-\d{2})-([^\-]+)-(\d{2})$",race_id)
        detail={}
        if mm:
            detail=_jra_program_lookup(mm.group(1),mm.group(2),int(mm.group(3))) or {"date":mm.group(1),"track":mm.group(2),"raceNumber":int(mm.group(3))}
            detail["netkeibaRaceId"]=detail.get("netkeibaRaceId") or _netkeiba_program_race_id(mm.group(1),mm.group(2),int(mm.group(3)))
            merged={}
            # v228: official JRA first. The live/full dde10 card carries odds and body weight.
            try:
                cname=_jra_find_cname(mm.group(1),mm.group(2),int(mm.group(3)))
                if cname:
                    jr=_jra_parse_race(cname,supplement_profiles=False) or {}
                    for h in jr.get("horses",[]) or []:
                        no=int(h.get("horseNumber") or 0)
                        if not no:continue
                        z=merged.setdefault(no,{})
                        for k in ("winOdds","popularity","bodyWeight","bodyWeightChange","status","scratched"):
                            if h.get(k) not in (None,""):z[k]=h.get(k)
                    if any(float((h.get("winOdds") or 0))>0 or h.get("bodyWeight") for h in (jr.get("horses") or [])):
                        source="JRA公式"
            except Exception as exc: print("fast odds JRA failed",race_id,exc)

            # Secondary public-page fallback only fills fields still missing after JRA official.
            try:
                nk=_netkeiba_live_win_odds(detail,bool(force)) or {}
                for no,z0 in nk.items():
                    z=merged.setdefault(int(no),{})
                    for k in ("winOdds","popularity","bodyWeight","bodyWeightChange","status","scratched"):
                        if z.get(k) in (None,"") and (z0 or {}).get(k) not in (None,""):
                            z[k]=(z0 or {}).get(k)
            except Exception as exc: print("fast odds secondary fallback failed",race_id,exc)

            # Fast shutuba scrape fallback (same page used for the card).
            if not any(float((z or {}).get("winOdds") or 0)>0 for z in merged.values()):
                try:
                    card_detail=dict(detail);card_detail["id"]=race_id
                    for h in _netkeiba_card_rows_fast(card_detail):
                        no=int(h.get("horseNumber") or 0)
                        if not no:continue
                        z=merged.setdefault(no,{})
                        for k in ("winOdds","popularity","bodyWeight","bodyWeightChange","status","scratched"):
                            if h.get(k) not in (None,""):z[k]=h.get(k)
                    if any(float((z or {}).get("winOdds") or 0)>0 for z in merged.values()):source="netkeiba出馬表"
                except Exception as exc:print("fast odds card scrape failed",race_id,exc)

            # Yesterday/final races: result page carries final odds.
            if not any(float((z or {}).get("winOdds") or 0)>0 for z in merged.values()):
                try:
                    result_detail=(saved or detail or {})
                    nkres=_netkeiba_current_result(result_detail) or {}
                    for f in nkres.get("finishers",[]) or []:
                        no=int(f.get("horseNumber") or 0)
                        if not no:continue
                        z=merged.setdefault(no,{})
                        for k in ("winOdds","popularity","bodyWeight","bodyWeightChange"):
                            if f.get(k) not in (None,""):z[k]=f.get(k)
                    if any(float((z or {}).get("winOdds") or 0)>0 for z in merged.values()):source="netkeiba最終"
                except Exception as exc:print("final odds result fallback failed",race_id,exc)

            for no,z in sorted(merged.items()):horses.append({"horseNumber":no,**z})
            if not source and horses:source="netkeiba"
    # v305: a source can momentarily return a sparse odds table. Merge it with the
    # best already-saved per-horse live fields so one missing row never falls back
    # to the endless "取得中" state after another horse was successfully refreshed.
    horses=_merge_live_market_rows(race_id,horses,saved)
    if not source:
        source=next((str(h.get("oddsSource") or "") for h in horses if h.get("oddsSource")),"")
    if horses:
        try:RACEDB.save_odds(race_id,horses,source)
        except Exception as exc:print("RaceDB odds save failed",race_id,exc)
        try:
            snapshot,_=PREPARED_STORE.get(race_id)
            if snapshot:
                by_no={int(h.get("horseNumber") or 0):h for h in horses}
                for h in snapshot.get("horses",[]):
                    update=by_no.get(int(h.get("horseNumber") or 0),{})
                    for key in ("winOdds","popularity","bodyWeight","bodyWeightChange","oddsForecast","referenceBodyWeight","referenceBodyWeightDate","status","scratched"):
                        if update.get(key) is not None:h[key]=update[key]
                    if update.get("oddsSource"):h["oddsSource"]=update.get("oddsSource")
                snapshot["oddsSource"]=source
                snapshot["oddsUpdatedAt"]=_now_jst().strftime("%H:%M:%S")
                PREPARED_STORE.put(snapshot,force=True)
                try:RACEDB.upsert_race(snapshot)
                except Exception:pass
        except Exception as exc:print("odds snapshot update failed",exc)
        try:
            with _site_bootstrap_lock:_site_bootstrap_cache.pop(_today_iso(),None)
        except Exception:pass
    if not horses:
        try:
            stored=RACEDB.odds_latest(race_id) or []
            if stored:
                horses=stored
                source=next((str(x.get("oddsSource") or "") for x in stored if x.get("oddsSource")),"保存済み")
        except Exception:pass
    live=[h for h in horses if not h.get("scratched") and int(h.get("horseNumber") or 0)>0]
    odds_count=sum(1 for h in live if float(h.get("winOdds") or 0)>0)
    return {"raceId":race_id,"horses":horses,"oddsSource":source,
            "oddsUpdatedAt":_now_jst().strftime("%H:%M:%S"),"storedInRaceDB":bool(horses),
            "fieldCount":len(live),"oddsCount":odds_count,
            "oddsComplete":bool(live) and odds_count==len(live)}
