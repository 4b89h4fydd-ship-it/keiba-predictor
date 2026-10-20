"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _jra_profile_runs(cname:str, cutoff:str, limit:int=5)->list[dict]:
    if not cname:return []
    try: html=_jra_request("https://www.jra.go.jp/JRADB/accessU.html",cname,86400)
    except Exception:return []
    soup=BeautifulSoup(html,"html.parser")
    out=[]
    for table in soup.find_all("table"):
        head=_jra_text(table.find("thead") or table.find("tr"))
        if "年月日" not in head or "レース名" not in head: continue
        for tr in table.find_all("tr"):
            cells=tr.find_all(["th","td"])
            if len(cells)<8: continue
            vals=[_jra_text(c) for c in cells]
            dm=re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日",vals[0])
            if not dm:continue
            iso=_jra_iso_date(int(dm.group(1)),int(dm.group(2)),int(dm.group(3)))
            if cutoff and iso>=cutoff:continue
            track=vals[1]
            title=vals[2]
            disttxt=vals[3]
            dsm=re.search(r"(芝|ダ|障)(\d{3,4})",disttxt)
            surface=dsm.group(1) if dsm else ""; dist=int(dsm.group(2)) if dsm else 0
            cond=vals[4] if len(vals)>4 else "不明"
            field=_int(vals[5]) if len(vals)>5 else 0
            finish=_int(vals[7]) if len(vals)>7 else 0
            jockey=vals[8] if len(vals)>8 else ""
            cw=float(re.sub(r"[^0-9.]","",vals[9]) or 0) if len(vals)>9 else 0
            tm=_jra_parse_time_seconds(vals[11] if len(vals)>11 else "")
            rc=_jra_attr_cname(tr,JRA_RESULT_CNAME_RE)
            rid=("jraresult-"+base64.urlsafe_b64encode(rc.encode()).decode().rstrip("=")) if rc else ""
            out.append({"date":iso,"track":track,"title":title,"distance":dist,"surface":surface,"condition":cond or "不明","weather":"不明","fieldSize":field,"finish":finish,"timeSeconds":tm,"cornerPositions":[],"carriedWeight":cw,"jockey":jockey,"raceId":rid,"source":"JRA公式競走馬情報"})
            if len(out)>=limit:return out
    return out

def _jra_run_core_complete(r:dict)->bool:
    try:finish=int(r.get("finish") or 0);field=int(r.get("fieldSize") or 0);distance=int(r.get("distance") or 0)
    except (TypeError,ValueError):return False
    return bool(str(r.get("date") or "") and str(r.get("track") or "") and finish>0 and field>1 and distance>0)

def _jra_history_complete(runs:list[dict],career_complete:bool=False)->bool:
    rows=[r for r in (runs or []) if isinstance(r,dict)]
    target=min(5,len(rows)) if career_complete else 5
    if target==0:return bool(career_complete)
    return len(rows)>=target and sum(1 for r in rows[:target] if _jra_run_core_complete(r))>=target

def _nar_attach_recent_batch(detail: dict, limit: int = 5) -> dict:
    """Attach recent NAR runs for all horses with one SQL query, avoiding N+1."""
    if not isinstance(detail,dict) or str(detail.get("circuit") or "")!="地方":
        return detail
    horses=detail.get("horses") or []
    names=[str(h.get("name") or "") for h in horses if h.get("name")]
    cutoff=str(detail.get("date") or "9999-12-31")
    if not names or not DB_PATH.exists():return detail
    conn=_new_conn(DB_PATH)
    try:
        ph=",".join("?" for _ in names)
        sql=f"""
        SELECT e.name,e.date,e.track,e.race_no,e.finish,e.time_seconds,e.corner_positions_json,
               e.carried_weight,e.jockey,e.trainer,
               r.title,r.distance,r.weather,r.condition,r.field_size,r.prize1
        FROM entries e
        JOIN races r ON r.track=e.track AND r.date=e.date AND r.race_no=e.race_no
        WHERE e.name IN ({ph}) AND e.date<? AND e.finish>0
        ORDER BY e.name,e.date DESC,e.race_no DESC
        """
        rows=conn.execute(sql,[*names,cutoff]).fetchall()
    finally:
        conn.close()
    grouped={n:[] for n in names}
    for row in rows:
        arr=grouped.get(str(row["name"]) or "")
        # SQL has already fetched every earlier result. Do not silently turn
        # lifetime NAR history into a five-start history here.
        if arr is None:continue
        try:cp=json.loads(row["corner_positions_json"] or "[]")
        except Exception:cp=[]
        arr.append({
            "date":row["date"],"track":row["track"],"raceNumber":int(row["race_no"] or 0),
            "raceId":f"nar-{row['date']}-{row['track']}-{int(row['race_no'] or 0):02d}",
            "title":row["title"] or f"{int(row['race_no'] or 0)}R",
            "distance":int(row["distance"] or 0),"condition":row["condition"] or "不明",
            "weather":row["weather"] or "不明","finish":int(row["finish"] or 0),
            "timeSeconds":float(row["time_seconds"] or 0),"cornerPositions":cp,
            "fieldSize":int(row["field_size"] or 0),"racePrize1":int(row["prize1"] or 0),
            "carriedWeight":float(row["carried_weight"] or 0),
            "jockey":row["jockey"] or "","trainer":row["trainer"] or "",
            "source":"NAR公式ローカル履歴",
        })
    from arvexq.ingest.full_career import merge_career
    from arvexq.ingest.career_transport import recover_horse
    for h in horses:
        # Preserve all previously stored starts (including packed full-career
        # archives), even when this local monthly SQLite database is sparse.
        # The five-run limit applies to the mobile display only.
        try:
            previous=recover_horse(h,cutoff) if isinstance(h.get("careerArchive"),dict) else h
        except (ValueError,KeyError,TypeError) as exc:
            # A corrupt archive must remain visible as a verification error,
            # never be silently discarded or reported as a complete career.
            previous=h
            h.setdefault("careerHistoryWarnings",[]).append("archive-recovery:"+type(exc).__name__)
        old_runs=[*(previous.get("allPastRuns") or []),*(previous.get("recentRaces") or [])]
        full=merge_career(old_runs,grouped.get(str(h.get("name") or ""),[]),cutoff)
        h["allPastRuns"]=full
        h["recentRaces"]=full[:max(1,int(limit))]
        # Do not change _careerHistoryAudit.complete: an observed list alone
        # cannot prove there were no earlier JRA/NAR starts.
    return detail

def _central_find_horse(race: dict, horse_name: str) -> tuple[dict | None, dict | None]:
    key = _horse_key(horse_name)
    horse = None
    for h in race.get("horses", []) or []:
        if _horse_key(h.get("name")) == key:
            horse = h
            break
    finisher = None
    result = race.get("result") if isinstance(race.get("result"), dict) else {}
    finishers = result.get("finishers") if isinstance(result.get("finishers"), list) else []
    for f in finishers:
        same_no = horse is not None and int(f.get("horseNumber") or 0) == int(horse.get("horseNumber") or 0)
        same_name = _horse_key(f.get("name")) == key
        if same_no or same_name:
            finisher = f
            break
    return horse, finisher

def _central_run_from_race(race: dict, horse_name: str) -> dict | None:
    horse, fin = _central_find_horse(race, horse_name)
    if horse is None and fin is None:
        return None
    horse = horse or {}
    fin = fin or {}
    finish = int(fin.get("finish") or horse.get("finish") or 0)
    corners = fin.get("cornerPositions") or horse.get("cornerPositions") or []
    if not isinstance(corners, list):
        corners = []
    last3f = fin.get("last3FSeconds") or fin.get("last3F") or horse.get("last3FSeconds") or horse.get("last3F")
    try:last3f=float(last3f) if last3f not in (None,"") else None
    except (TypeError,ValueError):last3f=None
    last3f = fin.get("last3FSeconds") or fin.get("last3F") or horse.get("last3FSeconds") or horse.get("last3F")
    try:last3f=float(last3f) if last3f not in (None,"") else None
    except (TypeError,ValueError):last3f=None
    last3f_rank=fin.get("last3FRank") or horse.get("last3FRank")
    try:last3f_rank=int(last3f_rank) if last3f_rank not in (None,"") else None
    except (TypeError,ValueError):last3f_rank=None
    last3f_pct=fin.get("last3FPercentile") if fin.get("last3FPercentile") is not None else horse.get("last3FPercentile")
    try:last3f_pct=float(last3f_pct) if last3f_pct is not None else None
    except (TypeError,ValueError):last3f_pct=None
    return {
        "raceId": race.get("id") or "",
        "date": race.get("date") or "",
        "track": race.get("track") or "",
        "raceNumber": int(race.get("raceNumber") or 0),
        "title": race.get("title") or "",
        "distance": int(race.get("distance") or 0),
        "condition": race.get("condition") or "不明",
        "weather": race.get("weather") or "不明",
        "surface": race.get("surface") or "",
        "fieldSize": int(race.get("fieldSize") or len(race.get("horses") or [])),
        "finish": finish,
        "timeSeconds": float(fin.get("timeSeconds") or horse.get("timeSeconds") or 0),
        "last3FSeconds": last3f,
        "last3FRank": last3f_rank,
        "last3FPercentile": last3f_pct,
        "cornerPositions": [int(x) for x in corners if str(x).strip().isdigit()],
        "carriedWeight": float(horse.get("carriedWeight") or fin.get("carriedWeight") or 0),
        "racePrize1": int(race.get("racePrize1") or 0),
        "jockey": horse.get("jockey") or fin.get("jockey") or "",
        "trainer": horse.get("trainer") or fin.get("trainer") or "",
        "source": race.get("source") or "中央フィード",
    }

def _central_resolve_race_id(run: dict) -> str:
    if run.get("raceId"):
        return str(run.get("raceId"))
    d = _clean(str(run.get("date") or ""))
    tr = _clean(str(run.get("track") or ""))
    rn = int(run.get("raceNumber") or 0)
    if not d or not tr or rn <= 0 or not CENTRAL_DB_PATH.exists():
        return ""
    conn = _new_conn(CENTRAL_DB_PATH)
    try:
        row = conn.execute(
            "SELECT id FROM central_races WHERE date=? AND track=? AND race_no=? LIMIT 1",
            (d, tr, rn),
        ).fetchone()
        return str(row["id"]) if row else ""
    finally:
        conn.close()

def _central_recent_from_store(horse_name: str, cutoff: str, limit: int = 5) -> list[dict]:
    if not CENTRAL_DB_PATH.exists() or not horse_name:
        return []
    conn = _new_conn(CENTRAL_DB_PATH)
    try:
        # Pull newest races first. We stop as soon as this horse has five actual starts.
        rows = conn.execute(
            "SELECT payload FROM central_races WHERE date<? ORDER BY date DESC,track DESC,race_no DESC LIMIT 4000",
            (cutoff,),
        ).fetchall()
        out = []
        seen = set()
        for row in rows:
            try:
                race = json.loads(row["payload"])
            except Exception:
                continue
            run = _central_run_from_race(race, horse_name)
            if not run:
                continue
            key = (run.get("date"), run.get("track"), int(run.get("raceNumber") or 0))
            if key in seen:
                continue
            seen.add(key)
            # A finish can be missing in a future-entry payload. Keep the race only when
            # the historical payload contains an actual result or explicit run result data.
            if int(run.get("finish") or 0) <= 0 and not run.get("cornerPositions") and not float(run.get("timeSeconds") or 0):
                continue
            out.append(run)
            if len(out) >= limit:
                break
        return out
    finally:
        conn.close()

def _merge_central_recent(existing: list[dict], stored: list[dict], cutoff: str, limit: int = 5) -> list[dict]:
    all_runs = []
    seen = set()
    for src in (existing or []) + (stored or []):
        if not isinstance(src, dict):
            continue
        run = dict(src)
        if cutoff and run.get("date") and str(run.get("date")) >= cutoff:
            continue
        rid = _central_resolve_race_id(run)
        if rid:
            run["raceId"] = rid
        key = run.get("raceId") or (str(run.get("date") or "") + "|" + str(run.get("track") or "") + "|" + str(int(run.get("raceNumber") or 0)))
        if key in seen:
            continue
        seen.add(key)
        all_runs.append(run)
    all_runs.sort(key=lambda x: (str(x.get("date") or ""), int(x.get("raceNumber") or 0)), reverse=True)
    return all_runs[:limit]

def _central_month_dates(year: int, month: int, cutoff: str) -> list[str]:
    last = calendar.monthrange(year, month)[1]
    cutoff_date = datetime.strptime(cutoff, "%Y-%m-%d").date()
    dates = []
    # JRA standard meetings are Sat/Sun and holiday Mondays. Searching these days first
    # avoids hundreds of empty requests while still covering ordinary and holiday meetings.
    for day in range(last, 0, -1):
        d = dt_date(year, month, day)
        if d >= cutoff_date:
            continue
        if d.weekday() in (0, 5, 6):
            dates.append(d.isoformat())
    return dates

def _fetch_central_days_parallel(days: list[str]) -> tuple[list[dict], list[str]]:
    if not days:
        return [], []
    workers = max(2, min(10, int(os.getenv("CENTRAL_HISTORY_WORKERS", "6"))))
    rows: list[dict] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(days))) as pool:
        future_map = {pool.submit(fetch_central_feed, day, True):day for day in days}
        for fut in as_completed(future_map):
            day = future_map[fut]
            try:
                rows.extend(fut.result() or [])
            except Exception as exc:
                errors.append(f"{day}:{exc}")
    return rows, errors

def _schedule_full_history_harvest(detail: dict) -> None:
    """Persist every career run exposed by the currently available official source without blocking the race screen."""
    if not bool(int(os.getenv("RACEDB_FULL_HISTORY","1"))) or not isinstance(detail,dict):return
    # Historical/final cards also need pre-race career data for backtests.
    # Source functions receive the race-date cutoff, so later races are excluded.
    if not detail.get("date"):return
    # Never route an unknown circuit into the JRA collector by default.
    circuit=str(detail.get("circuit") or "")
    if circuit not in ("中央","地方"):return
    race_id=str(detail.get("id") or "");horses=[h for h in (detail.get("horses") or []) if isinstance(h,dict) and h.get("name")]
    if not race_id or not horses:return
    with _full_history_lock:
        if race_id in _full_history_running:return
        _full_history_running.add(race_id)
    def worker():
        ttl=max(1800,int(os.getenv("RACEDB_FULL_HISTORY_TTL_SEC","21600")));cutoff=str(detail.get("date") or _today_iso())
        try:
            if circuit=="地方":
                store=NarStore()
                try:
                    for h in horses:
                        key="fullhist:nar:"+RACEDB._horse_key(h);last=RACEDB.source_updated(key)
                        if last and int(time.time())-last<ttl:continue
                        try:
                            runs=store.recent_races(str(h.get("name") or ""),cutoff,100000)
                            n=RACEDB.upsert_past_runs(h,runs);RACEDB.mark_source(key,"done",f"{n} runs")
                        except Exception as exc:RACEDB.mark_source(key,"error",str(exc))
                finally:
                    try:store.conn.close()
                    except Exception:pass
            else:
                def one(h):
                    key="fullhist:jra:"+RACEDB._horse_key(h);last=RACEDB.source_updated(key)
                    if last and int(time.time())-last<ttl:return
                    cname=str(h.get("_jraHorseCname") or "")
                    if not cname:
                        RACEDB.mark_source(key,"unavailable","JRA horse id unavailable");return
                    try:
                        runs=_jra_profile_runs(cname,cutoff,10000)
                        n=RACEDB.upsert_past_runs(h,runs);RACEDB.mark_source(key,"done",f"{n} runs")
                    except Exception as exc:RACEDB.mark_source(key,"error",str(exc))
                workers=max(1,min(4,int(os.getenv("RACEDB_FULL_HISTORY_WORKERS","3"))))
                with ThreadPoolExecutor(max_workers=min(workers,max(1,len(horses)))) as pool:list(pool.map(one,horses))
            latest,_=PREPARED_STORE.get(race_id)
            if latest:
                latest=_precompute_detail_metrics(_attach_evaluation_context(_attach_stored_career(latest)))
                latest.setdefault("historySearch",{})["status"]="complete-local-history"
                pm=latest.setdefault("preparedMeta",{})
                pm.pop("diagnosisVersion",None)
                pm["diagnosisReady"]=False
                PREPARED_STORE.put(latest,force=True)
                RACEDB.upsert_race(latest)
        finally:
            with _full_history_lock:_full_history_running.discard(race_id)
    threading.Thread(target=worker,daemon=True).start()

def _netkeiba_past_rows_fast(detail:dict)->list[dict]:
    """One cached page gets recent runs for every JRA starter."""
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(
        str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0)
    )
    if not rid:return []
    url=f"https://race.netkeiba.com/race/shutuba_past.html?race_id={rid}&rf=shutuba_submenu"
    try:
        html=_netkeiba_get(
            url,
            float(os.getenv("FAST_HISTORY_TIMEOUT_SEC","1.8")),
            int(os.getenv("FAST_HISTORY_CACHE_SEC","300")),
        )
    except Exception as exc:
        print("fast JRA past page failed",rid,exc);return []
    soup=BeautifulSoup(html,"html.parser");out=[]
    for tr in soup.select("tr.HorseList"):
        horse=_nk_row_horse(tr)
        if not horse:continue
        runs=[]
        for td in tr.find_all("td"):
            z=_parse_recent_cell(td.get_text(" ",strip=True))
            if z:runs.append(z)
            if len(runs)>=5:break
        horse["recentRaces"]=runs[:5]
        out.append(horse)
    return out

def _merge_fast_history(detail:dict, history_rows:list[dict])->dict:
    by_no={int(h.get("horseNumber") or 0):h for h in detail.get("horses",[]) or []}
    by_name={str(h.get("name") or ""):h for h in detail.get("horses",[]) or [] if h.get("name")}
    for row in history_rows or []:
        h=by_no.get(int(row.get("horseNumber") or 0)) or by_name.get(str(row.get("name") or ""))
        if not h:continue
        runs=list(row.get("recentRaces") or [])
        if runs:
            old=list(h.get("allPastRuns") or h.get("recentRaces") or [])
            merged=_jra_merge_runs(old,runs,max(5,len(old)+len(runs)))
            h["recentRaces"]=merged[:5]
            h["allPastRuns"]=merged
    return detail
